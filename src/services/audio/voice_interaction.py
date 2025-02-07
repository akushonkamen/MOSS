"""语音交互管理器"""
import os
import asyncio
import logging
import tempfile
import wave
from typing import Optional, Callable, List, Dict, Any, Literal, Awaitable
from dataclasses import dataclass
import concurrent.futures
from functools import partial

# 第三方库
import numpy as np
import whisper
import edge_tts

# 本地模块
from .recorder_service import AudioRecorder, AudioConfig as RecorderConfig
from .player_service import AudioPlayer, AudioConfig as PlayerConfig
from .vad_service import VADService, VADResult
from .tts_service import TTSService
from .config import VoiceConfig

WhisperModelSize = Literal["tiny", "base", "small", "medium", "large"]

@dataclass
class VoiceConfig:
    recorder_config: RecorderConfig = RecorderConfig(
        channels=1,
        sample_rate=16000,
        sample_width=2,
        chunk_size=480
    )
    player_config: PlayerConfig = PlayerConfig(
        channels=1,
        sample_rate=16000,
        sample_width=2,
        chunk_size=480
    )
    vad_aggressiveness: int = 3
    silence_duration: float = 1.0  # 静音持续时间阈值(秒)
    min_audio_length: float = 0.5  # 最小音频长度阈值(秒)
    whisper_model: WhisperModelSize = "large"  # 使用large模型以获得最佳准确率
    whisper_language: str = "zh"  # 设置为中文

class VoiceInteractionManager:
    """语音交互管理器"""
    
    def __init__(
        self,
        config: VoiceConfig,
        on_transcribe: Callable[[str], None],
        on_speech_start: Optional[Callable[[], None]] = None,
        on_speech_end: Optional[Callable[[], None]] = None
    ):
        """初始化语音交互管理器
        
        Args:
            config: 语音配置
            on_transcribe: 语音识别回调函数
            on_speech_start: 说话开始回调函数
            on_speech_end: 说话结束回调函数
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.on_transcribe = on_transcribe
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        
        # 初始化录音器
        self.recorder = AudioRecorder(
            config=config.recorder_config
        )
        
        # 初始化播放器
        self.player = AudioPlayer(
            config=config.player_config
        )
        
        # 初始化VAD服务
        self.vad = VADService(aggressiveness=config.vad_aggressiveness)
        
        # 初始化TTS服务
        self.tts_service = TTSService()
        
        # 初始化语音识别模型
        self.model = None
        
        # 初始化状态变量
        self._is_speaking = False
        self._silence_frames = 0
        self._speech_frames = []
        self._is_running = False
        
        # 创建线程池
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
    async def initialize(self):
        """初始化语音交互管理器"""
        try:
            self.logger.info("开始初始化语音交互管理器...")
            
            # 加载Whisper模型
            self.logger.info("正在加载Whisper large 模型...")
            self.model = whisper.load_model("large")
            self.logger.info("Whisper模型加载完成")
            
            self.logger.info("语音交互管理器初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化语音交互管理器失败: {str(e)}")
            raise
            
    async def start(self):
        """启动语音交互"""
        try:
            # 播放欢迎语
            await self.speak("你好，我是你的智能家居助手，请说话")
            
            # 开始录音
            await self.recorder.start()
            
            # 开始监听
            self._is_running = True
            asyncio.create_task(self.start_listening())
            
        except Exception as e:
            self.logger.error(f"启动语音交互失败: {str(e)}")
            raise
            
    async def stop(self):
        """停止语音交互"""
        try:
            # 停止录音
            await self.recorder.stop()
            
            # 播放告别语
            await self.speak("再见")
            
        except Exception as e:
            self.logger.error(f"停止语音交互失败: {str(e)}")
            raise
            
    async def speak(self, text: str):
        """播放语音
        
        Args:
            text: 要播放的文本
        """
        try:
            await self.player.speak(text)
        except Exception as e:
            self.logger.error(f"播放语音失败: {str(e)}")
            raise
            
    def _on_speech_start(self):
        """说话开始回调"""
        if self.on_speech_start:
            self.on_speech_start()
            
    def _on_speech_end(self, audio_data: bytes):
        """说话结束回调
        
        Args:
            audio_data: 音频数据
        """
        if self.on_speech_end:
            self.on_speech_end()
            
        # 进行语音识别
        try:
            # 保存音频文件
            with open("temp.wav", "wb") as f:
                f.write(audio_data)
                
            # 识别音频
            result = self.model.transcribe("temp.wav", language="zh")
            text = result["text"].strip()
            
            # 调用回调函数
            if text:
                self.on_transcribe(text)
                
        except Exception as e:
            self.logger.error(f"语音识别失败: {str(e)}")
            raise
        
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
                            
                            # 在线程池中执行语音识别
                            loop = asyncio.get_running_loop()
                            result = await loop.run_in_executor(
                                self._thread_pool,
                                partial(
                                    self.model.transcribe,
                                    temp_path,
                                    language=self.config.whisper_language,
                                    task="transcribe",
                                    temperature=0.0,
                                    compression_ratio_threshold=2.4,
                                    no_speech_threshold=0.6,
                                    condition_on_previous_text=False
                                )
                            )
                            
                            text = result["text"].strip()
                            
                            if text and self.on_transcribe:
                                # 使用asyncio.create_task来处理异步回调
                                asyncio.create_task(self.on_transcribe(text))
                        except Exception as e:
                            self.logger.error(f"语音识别错误: {e}")
                        finally:
                            # 删除临时文件
                            if os.path.exists(temp_path):
                                os.unlink(temp_path)
                            
                    self._speech_frames = []
                    
    async def start_listening(self):
        """开始监听音频输入"""
        try:
            while True:
                # 从录音器读取音频数据
                audio_chunk = await self.recorder.read()
                if audio_chunk is None:
                    await asyncio.sleep(0.001)  # 短暂休眠避免CPU占用过高
                    continue
                    
                # 处理音频数据
                await self.process_audio_chunk(audio_chunk)
                
        except Exception as e:
            logger.error(f"音频处理发生错误: {str(e)}")
            raise
        
    async def speak(self, text: str) -> bool:
        """文本转语音并播放
        
        Args:
            text: 要转换的文本
            
        Returns:
            bool: 是否成功
        """
        if not text:
            self.logger.warning("收到空文本，跳过语音合成")
            return False
            
        try:
            # 使用TTS服务合成语音
            temp_path = await self.tts_service.synthesize(text)
            if not temp_path:
                self.logger.error("语音合成失败")
                return False
                
            try:
                # 播放语音
                self.logger.debug("开始播放语音...")
                await self.player.play_file(temp_path)
                self.logger.debug("语音播放完成")
                return True
                
            finally:
                # 确保临时文件被删除
                if os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except Exception as e:
                        self.logger.warning(f"删除临时文件失败: {e}")
                        
        except Exception as e:
            self.logger.error(f"语音合成或播放错误: {e}", exc_info=True)
            return False
        
    async def stop(self):
        """停止语音交互"""
        logger.info("正在停止语音交互...")
        try:
            # 停止录音
            if self.recorder:
                await self.recorder.stop()
                
            # 停止播放
            if self.player:
                await self.player.stop()
                
            # 停止VAD服务
            if self.vad:
                await self.vad.stop()
                
        except Exception as e:
            logger.error(f"停止语音交互错误: {e}") 