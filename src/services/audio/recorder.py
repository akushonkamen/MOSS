"""录音器"""
import logging
import pyaudio
import wave
import numpy as np
from typing import Callable, Optional
import asyncio

class AudioRecorder:
    """录音器"""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        silence_threshold: float = 0.03,
        silence_duration: float = 1.0,
        on_speech_start: Optional[Callable[[], None]] = None,
        on_speech_end: Optional[Callable[[bytes], None]] = None
    ):
        """初始化录音器
        
        Args:
            sample_rate: 采样率
            channels: 声道数
            chunk_size: 块大小
            silence_threshold: 静音阈值
            silence_duration: 静音持续时间
            on_speech_start: 说话开始回调函数
            on_speech_end: 说话结束回调函数
        """
        self.logger = logging.getLogger(__name__)
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.frames = []
        self.silence_count = 0
        self.speech_detected = False
        
    async def start(self):
        """开始录音"""
        try:
            # 打开音频流
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.is_recording = True
            self.frames = []
            self.silence_count = 0
            self.speech_detected = False
            
            self.logger.info("开始录音")
            
        except Exception as e:
            self.logger.error(f"启动录音失败: {str(e)}")
            raise
            
    async def stop(self):
        """停止录音"""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.stream = None
            self.is_recording = False
            
            self.logger.info("停止录音")
            
        except Exception as e:
            self.logger.error(f"停止录音失败: {str(e)}")
            raise
            
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频回调函数
        
        Args:
            in_data: 输入数据
            frame_count: 帧数
            time_info: 时间信息
            status: 状态
            
        Returns:
            tuple: (输出数据, 状态)
        """
        try:
            # 将字节数据转换为numpy数组
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # 计算音量
            volume = np.abs(audio_data).mean()
            
            # 检测是否有声音
            if volume > self.silence_threshold:
                self.silence_count = 0
                if not self.speech_detected:
                    self.speech_detected = True
                    if self.on_speech_start:
                        asyncio.create_task(self._call_speech_start())
            else:
                if self.speech_detected:
                    self.silence_count += 1
                    
            # 如果静音持续时间超过阈值，结束录音
            silence_frames = int(self.silence_duration * self.sample_rate / self.chunk_size)
            if self.speech_detected and self.silence_count >= silence_frames:
                self.speech_detected = False
                if self.on_speech_end:
                    audio_data = b"".join(self.frames)
                    asyncio.create_task(self._call_speech_end(audio_data))
                self.frames = []
                
            # 保存音频数据
            if self.speech_detected:
                self.frames.append(in_data)
                
            return (in_data, pyaudio.paContinue)
            
        except Exception as e:
            self.logger.error(f"音频回调失败: {str(e)}")
            return (in_data, pyaudio.paAbort)
            
    async def _call_speech_start(self):
        """调用说话开始回调函数"""
        try:
            self.on_speech_start()
        except Exception as e:
            self.logger.error(f"调用说话开始回调函数失败: {str(e)}")
            
    async def _call_speech_end(self, audio_data: bytes):
        """调用说话结束回调函数
        
        Args:
            audio_data: 音频数据
        """
        try:
            self.on_speech_end(audio_data)
        except Exception as e:
            self.logger.error(f"调用说话结束回调函数失败: {str(e)}")
            
    def __del__(self):
        """析构函数"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate() 