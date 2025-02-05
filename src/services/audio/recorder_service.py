import pyaudio
import wave
import numpy as np
import asyncio
from dataclasses import dataclass
from typing import Optional, AsyncIterator

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
        
    def start_recording(self):
        """启动录音流"""
        if self.stream is None:
            self.stream = self.p.open(
                format=self.p.get_format_from_width(self.config.sample_width),
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size
            )
            self.frames = []
            
    def stop_recording(self):
        """停止录音流"""
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
    async def record_chunk(self) -> bytes:
        """录制一个音频块"""
        if self.stream is None:
            self.start_recording()
        chunk = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
        self.frames.append(chunk)
        return chunk
        
    async def record_stream(self) -> AsyncIterator[bytes]:
        """录制音频流"""
        try:
            self.start_recording()
            while True:
                chunk = await self.record_chunk()
                yield chunk
        finally:
            self.stop_recording()
            
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
        """清理资源"""
        self.stop_recording()
        self.p.terminate() 