import asyncio
import io
import wave
import whisper
import tempfile
import os
import numpy as np
import subprocess
from loguru import logger
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, Literal
from .recorder_service import AudioRecorder, AudioConfig as RecorderConfig
from .player_service import AudioPlayer, AudioConfig as PlayerConfig
from .vad_service import VADService, VADResult

WhisperModelSize = Literal["tiny", "base", "small", "medium", "large"]

@dataclass
class VoiceConfig:
    recorder_config: RecorderConfig
    player_config: PlayerConfig
    vad_aggressiveness: int = 3
    silence_duration: float = 1.0  # 静音持续时间阈值(秒)
    min_audio_length: float = 0.5  # 最小音频长度阈值(秒)
    whisper_model: WhisperModelSize = "large"  # 使用large模型以获得最佳准确率
    whisper_language: str = "zh"  # 设置为中文

class VoiceInteractionManager:
    def __init__(
        self,
        config: VoiceConfig,
        on_speech_start: Optional[Callable[[], None]] = None,
        on_speech_end: Optional[Callable[[], None]] = None,
        on_transcribe: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        """
        初始化语音交互管理器
        
        Args:
            config: 语音配置
            on_speech_start: 说话开始回调
            on_speech_end: 说话结束回调
            on_transcribe: 语音识别结果回调
        """
        self.config = config
        self.recorder = AudioRecorder(config.recorder_config)
        self.player = AudioPlayer(config.player_config)
        self.vad = VADService(config.vad_aggressiveness)
        
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_transcribe = on_transcribe
        
        logger.info(f"正在加载Whisper {config.whisper_model} 模型...")
        self.whisper = whisper.load_model(config.whisper_model)
        logger.info("Whisper模型加载完成")
        
        self._is_running = False
        self._is_speaking = False
        self._silence_frames = 0
        self._speech_frames = []
        
    def _save_wav(self, frames: list[bytes], filename: str):
        """保存WAV文件"""
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.config.recorder_config.channels)
            wf.setsampwidth(self.config.recorder_config.sample_width)
            wf.setframerate(self.config.recorder_config.sample_rate)
            wf.writeframes(b''.join(frames))
            
    def _normalize_audio(self, frames: list[bytes]) -> list[bytes]:
        """音频归一化处理"""
        # 将字节数据转换为numpy数组
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        
        # 计算RMS值
        rms = np.sqrt(np.mean(np.square(audio_data, dtype=np.float64)))
        
        if rms > 0:
            # 归一化，但保留一些余量以防止截断
            target_rms = 2000  # 目标RMS值
            gain = target_rms / rms
            normalized_audio = (audio_data * gain).astype(np.int16)
            
            # 将numpy数组转回字节列表
            return [normalized_audio[i:i+self.config.recorder_config.chunk_size].tobytes() 
                   for i in range(0, len(normalized_audio), self.config.recorder_config.chunk_size)]
        
        return frames
        
    async def process_audio_chunk(self, chunk: bytes):
        """处理音频块"""
        # VAD检测
        vad_result = self.vad.process_frame(chunk)
        
        if vad_result.is_speech:
            if not self._is_speaking:
                self._is_speaking = True
                if self.on_speech_start:
                    self.on_speech_start()
            self._silence_frames = 0
            self._speech_frames.append(chunk)
        else:
            if self._is_speaking:
                self._silence_frames += 1
                frames_threshold = int(self.config.silence_duration * self.config.recorder_config.sample_rate / self.config.recorder_config.chunk_size)
                
                if self._silence_frames >= frames_threshold:
                    self._is_speaking = False
                    if self.on_speech_end:
                        self.on_speech_end()
                        
                    # 检查音频长度是否满足最小要求
                    audio_length = len(self._speech_frames) * self.config.recorder_config.chunk_size / self.config.recorder_config.sample_rate
                    if audio_length >= self.config.min_audio_length:
                        # 音频归一化
                        normalized_frames = self._normalize_audio(self._speech_frames)
                        
                        # 保存音频
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                            temp_path = temp_file.name
                            
                        try:
                            # 保存WAV文件
                            self._save_wav(normalized_frames, temp_path)
                            
                            # 语音识别
                            result = self.whisper.transcribe(
                                temp_path,
                                language=self.config.whisper_language,
                                task="transcribe",
                                temperature=0.0,  # 使用确定性解码
                                compression_ratio_threshold=2.4,  # 控制输出长度
                                no_speech_threshold=0.6,  # 提高无语音检测阈值
                                condition_on_previous_text=False  # 不使用上下文
                            )
                            
                            text = result["text"].strip()
                            
                            if text and self.on_transcribe:
                                await self.on_transcribe(text)
                        except Exception as e:
                            logger.error(f"语音识别错误: {e}")
                        finally:
                            # 删除临时文件
                            if os.path.exists(temp_path):
                                os.unlink(temp_path)
                            
                    self._speech_frames = []
                    
    async def start_listening(self):
        """开始监听音频输入"""
        async for chunk in self.recorder.record_stream():
            if not self._is_running:
                break
            try:
                await self.process_audio_chunk(chunk)
            except Exception as e:
                logger.error(f"处理音频块错误: {e}")
            
    async def speak(self, text: str):
        """播放合成语音"""
        logger.info(f"准备播放语音: {text}")
        
        try:
            # 使用系统命令say进行语音合成和播放
            logger.debug("开始语音合成和播放...")
            subprocess.run(["say", "-v", "Tingting", text], check=True)
            logger.debug("语音播放完成")
        except Exception as e:
            logger.error(f"语音合成或播放错误: {e}")
        
    def start(self):
        """启动语音交互服务"""
        self._is_running = True
        asyncio.create_task(self.start_listening())
        
    def stop(self):
        """停止语音交互服务"""
        self._is_running = False
        self.recorder.stop_recording()
        self.player.stop_stream() 