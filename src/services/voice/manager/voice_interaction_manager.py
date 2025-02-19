"""语音交互管理器模块"""
import asyncio
from typing import Optional, Callable, Any
import numpy as np
import sounddevice as sd
import webrtcvad
import whisper
from loguru import logger
import os
from playsound import playsound
import logging

from ..config.voice_config import VoiceConfig

class VoiceInteractionManager:
    """语音交互管理器"""
    
    def __init__(
        self,
        config: VoiceConfig,
        on_transcribe: Optional[Callable[[str], None]] = None,
        on_speech_start: Optional[Callable[[], None]] = None,
        on_speech_end: Optional[Callable[[bytes], None]] = None
    ):
        """初始化语音交互管理器
        
        Args:
            config: 语音配置
            on_transcribe: 语音识别回调
            on_speech_start: 说话开始回调
            on_speech_end: 说话结束回调
        """
        self.config = config
        self.on_transcribe = on_transcribe
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.logger = logging.getLogger(__name__)
        
        # 确保采样率是WebRTC VAD支持的值
        supported_rates = [8000, 16000, 32000, 48000]
        if self.config.recorder_config.sample_rate not in supported_rates:
            raise ValueError(f"采样率必须是以下值之一: {supported_rates}")
            
        # 计算帧大小 (30ms)
        self.frame_duration_ms = 30
        self.frame_size = int(self.config.recorder_config.sample_rate * self.frame_duration_ms / 1000)
        
        # 确保chunk_size是frame_size的倍数
        if self.config.recorder_config.chunk_size % self.frame_size != 0:
            new_chunk_size = self.frame_size
            logger.warning(f"调整chunk_size从{self.config.recorder_config.chunk_size}到{new_chunk_size}以匹配帧大小")
            self.config.recorder_config.chunk_size = new_chunk_size
        
        # 初始化VAD
        self.vad = webrtcvad.Vad(config.vad_aggressiveness)
        
        # 初始化Whisper
        self.whisper_model = whisper.load_model(config.whisper_model)
        
        # 初始化状态
        self.is_running = False
        self.is_speaking = False
        self.audio_buffer = []
        self.silence_frames = 0
        self.speech_frames = 0
        
        # 语音检测参数
        self.min_speech_frames = 5  # 最小语音帧数
        self.silence_threshold_frames = 15  # 静音阈值帧数
        self.energy_threshold = 1200.0  # 能量阈值
        
        # 事件循环
        self.loop = None
        
        # 错误提示音路径
        self.error_sound_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "resources",
            "sounds",
            "error.wav"
        )
        
    async def initialize(self) -> None:
        """初始化管理器"""
        try:
            # 保存事件循环引用
            self.loop = asyncio.get_running_loop()
            
            # 获取所有音频设备
            devices = sd.query_devices()
            logger.info(f"可用音频设备:\n{devices}")
            
            # 查找MacBook Pro麦克风
            input_device = None
            output_device = None
            for i, device in enumerate(devices):
                if "MacBook Pro Microphone" in device["name"]:
                    input_device = i
                elif "MacBook Pro Speakers" in device["name"]:
                    output_device = i
                    
            if input_device is None or output_device is None:
                raise RuntimeError("未找到MacBook Pro的麦克风或扬声器")
                
            # 初始化音频设备
            logger.info(f"使用输入设备: {devices[input_device]['name']}")
            logger.info(f"使用输出设备: {devices[output_device]['name']}")
            
            # 强制设置为单声道输入
            self.config.recorder_config.channels = 1
            
            sd.default.device = (input_device, output_device)
            sd.default.channels = (
                self.config.recorder_config.channels,  # 输入通道
                self.config.player_config.channels     # 输出通道
            )
            sd.default.samplerate = self.config.recorder_config.sample_rate
            
            logger.info("语音交互管理器初始化完成")
            
        except Exception as e:
            logger.error(f"初始化语音交互管理器失败: {str(e)}")
            raise
            
    async def start(self) -> None:
        """启动语音交互"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("启动语音交互...")
        
        # 创建后台任务
        asyncio.create_task(self._run_audio_stream())
        
    async def _run_audio_stream(self) -> None:
        """运行音频流处理"""
        try:
            # 启动音频流
            with sd.InputStream(
                channels=self.config.recorder_config.channels,
                samplerate=self.config.recorder_config.sample_rate,
                dtype=np.int16,
                blocksize=self.config.recorder_config.chunk_size,
                callback=self._audio_callback
            ):
                while self.is_running:
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"语音交互出错: {str(e)}")
            self.is_running = False
            raise
            
    def _audio_callback(self, indata: np.ndarray, frames: int, time: Any, status: Any) -> None:
        """音频回调处理
        
        Args:
            indata: 输入音频数据
            frames: 帧数
            time: 时间信息
            status: 状态信息
        """
        try:
            if status:
                self.logger.warning(f"音频回调状态: {status}")
                
            # 确保音频数据是单声道的
            if indata.shape[1] > 1:
                indata = np.mean(indata, axis=1, keepdims=True)
            
            # 将数据转换为16位PCM
            audio_data = indata.astype(np.int16)
            
            # 确保数据是连续的
            if not audio_data.flags['C_CONTIGUOUS']:
                audio_data = np.ascontiguousarray(audio_data)
            
            # 处理每一帧
            is_speech = False
            try:
                # 将数据分成30ms的帧
                frame_data = audio_data.tobytes()
                is_speech = self.vad.is_speech(frame_data, self.config.recorder_config.sample_rate)
            except Exception as e:
                self.logger.error(f"VAD处理失败: {str(e)}")
                return
                
            if is_speech:
                if not self.is_speaking:
                    self.is_speaking = True
                    self.logger.info("检测到语音开始")
                    if self.on_speech_start:
                        self.on_speech_start()
                        
                # 累积音频数据
                self.audio_buffer.append(frame_data)
                self.silence_frames = 0
                self.speech_frames += 1
                
            else:
                if self.is_speaking:
                    self.silence_frames += 1
                    self.audio_buffer.append(frame_data)
                    
                    # 如果静音持续时间超过阈值，认为说话结束
                    if self.silence_frames >= self.silence_threshold_frames:
                        self.logger.info("检测到语音结束")
                        if self.on_speech_end:
                            # 合并音频数据
                            audio_data = b"".join(self.audio_buffer)
                            self.on_speech_end(audio_data)
                            
                        # 如果语音长度足够，进行识别
                        if self.speech_frames >= self.min_speech_frames:
                            self.logger.info(f"语音长度足够，开始处理（{len(self.audio_buffer)} 帧）")
                            # 合并音频数据
                            audio_data = b"".join(self.audio_buffer)
                            
                            # 转换为numpy数组
                            audio_array = np.frombuffer(audio_data, dtype=np.int16)
                            audio_array = audio_array.astype(np.float32) / 32768.0
                            
                            try:
                                # 使用Whisper进行识别
                                self.logger.info("开始语音识别...")
                                result = self.whisper_model.transcribe(
                                    audio_array,
                                    language=self.config.whisper_language
                                )
                                
                                # 获取识别结果
                                text = result["text"].strip()
                                self.logger.info(f"语音识别结果: {text}")
                                
                                # 在事件循环中调用回调函数
                                if self.on_transcribe and text and self.loop:
                                    self.loop.call_soon_threadsafe(
                                        lambda: asyncio.create_task(self.on_transcribe(text))
                                    )
                                    
                            except Exception as e:
                                self.logger.error(f"语音识别失败: {str(e)}")
                                import traceback
                                self.logger.error(traceback.format_exc())
                        else:
                            self.logger.info(f"语音太短，丢弃（{self.speech_frames} 帧）")
                        
                        # 重置状态
                        self.is_speaking = False
                        self.audio_buffer = []
                        self.silence_frames = 0
                        self.speech_frames = 0
                else:
                    # 重置语音帧计数
                    self.silence_frames = 0
                        
        except Exception as e:
            self.logger.error(f"音频处理失败: {str(e)}")
            self.audio_buffer = []
            self.is_speaking = False
            self.speech_frames = 0
            
    async def stop(self) -> None:
        """停止语音交互"""
        self.is_running = False
        logger.info("停止语音交互")

    async def play_error_sound(self):
        """播放错误提示音"""
        try:
            if os.path.exists(self.error_sound_path):
                # 使用 playsound 播放错误音效
                playsound(self.error_sound_path)
            else:
                logger.warning(f"错误音效文件不存在: {self.error_sound_path}")
                # 如果文件不存在，使用 sounddevice 播放简单的提示音
                duration = 0.2  # 200ms
                frequency = 440  # 440Hz
                t = np.linspace(0, duration, int(duration * self.config.player_config.sample_rate))
                error_sound = np.sin(2 * np.pi * frequency * t).astype(np.float32)
                sd.play(error_sound, self.config.player_config.sample_rate)
                sd.wait()
        except Exception as e:
            logger.error(f"播放错误提示音失败: {str(e)}")
            # 如果播放失败，记录错误但不抛出异常

    async def speak(self, text: str):
        """播放语音
        
        Args:
            text: 要播放的文本
        """
        try:
            # 使用sounddevice播放语音
            # 这里需要使用TTS服务将文本转换为语音
            # 暂时使用简单的提示音代替
            duration = 0.2  # 200ms
            frequency = 440  # 440Hz
            t = np.linspace(0, duration, int(duration * self.config.player_config.sample_rate))
            sound = np.sin(2 * np.pi * frequency * t).astype(np.float32)
            sd.play(sound, self.config.player_config.sample_rate)
            sd.wait()
            logger.info(f"播放文本: {text}")
        except Exception as e:
            logger.error(f"播放语音失败: {str(e)}")
            # 如果播放失败，记录错误但不抛出异常