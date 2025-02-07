import pyaudio
import wave
import numpy as np
import asyncio
from dataclasses import dataclass
from typing import Optional, AsyncIterator, Callable
from queue import Queue
import logging

logger = logging.getLogger(__name__)

@dataclass
class AudioConfig:
    """音频配置"""
    channels: int = 1
    sample_rate: int = 16000
    sample_width: int = 2
    chunk_size: int = 480  # 30ms at 16kHz

class AudioRecorder:
    """音频录制服务"""
    
    def __init__(self, config: AudioConfig):
        """
        初始化录音服务
        
        Args:
            config: 音频配置
        """
        # 验证配置
        if config.sample_rate not in [8000, 16000, 32000]:
            raise ValueError("采样率必须是8000Hz、16000Hz或32000Hz")
        if config.sample_width != 2:
            raise ValueError("采样位宽必须是16位(2字节)")
        if config.channels != 1:
            raise ValueError("只支持单声道录音")
            
        # 确保chunk_size对应于有效的帧长度(10ms、20ms或30ms)
        frame_size = int(config.sample_rate * 0.03)  # 30ms
        if config.chunk_size != frame_size:
            print(f"调整chunk_size为{frame_size}以匹配30ms帧长度")
            config.chunk_size = frame_size
            
        self.config = config
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self._is_recording = False
        self._queue = Queue()
        
    async def start(self):
        """启动录音"""
        if self.stream is None:
            self.stream = self.p.open(
                format=self.p.get_format_from_width(self.config.sample_width),
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback
            )
            self._is_recording = True
            self.stream.start_stream()
            
    async def stop(self):
        """停止录音"""
        self._is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频回调函数,在非事件循环线程中运行"""
        if self._is_recording:
            self._queue.put(in_data)
        return (None, pyaudio.paContinue)
        
    async def read(self) -> Optional[bytes]:
        """读取音频数据
        
        Returns:
            Optional[bytes]: 音频数据
        """
        try:
            return self._queue.get_nowait()
        except:
            return None
            
    def save_to_file(self, filename: str):
        """保存录音到文件"""
        if not self.frames:
            return
            
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(self.config.sample_width)
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(b''.join(self.frames))
            
    def __del__(self):
        """析构函数"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate() 