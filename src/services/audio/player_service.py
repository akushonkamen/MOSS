import pyaudio
import wave
import io
import asyncio
import subprocess
import tempfile
import os
from typing import Union, BinaryIO, AsyncIterator
from dataclasses import dataclass
from loguru import logger

@dataclass
class AudioConfig:
    """音频配置"""
    channels: int = 1
    sample_rate: int = 16000
    sample_width: int = 2
    chunk_size: int = 1024

class AudioPlayer:
    """音频播放服务"""
    
    def __init__(self, config: AudioConfig):
        """
        初始化播放服务
        
        Args:
            config: 音频配置
        """
        self.config = config
        
    async def play_stream(self, audio_stream: Union[BinaryIO, AsyncIterator[bytes]]):
        """播放音频流"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            # 将音频流写入临时文件
            if isinstance(audio_stream, io.IOBase):
                # 如果是文件流，直接复制
                with open(temp_path, 'wb') as f:
                    while chunk := audio_stream.read(self.config.chunk_size):
                        f.write(chunk)
            else:
                # 如果是异步迭代器，异步读取
                with open(temp_path, 'wb') as f:
                    async for chunk in audio_stream:
                        f.write(chunk)
                        
            # 使用系统命令播放
            logger.debug(f"使用系统命令播放音频: {temp_path}")
            subprocess.run(["afplay", temp_path], check=True)
            logger.debug("音频播放完成")
            
        except Exception as e:
            logger.error(f"播放音频错误: {e}")
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    async def play_file(self, file_path: str):
        """播放音频文件"""
        try:
            logger.debug(f"使用系统命令播放音频文件: {file_path}")
            subprocess.run(["afplay", file_path], check=True)
            logger.debug("音频文件播放完成")
        except Exception as e:
            logger.error(f"播放音频文件错误: {e}")
            
    def stop_stream(self):
        """停止播放"""
        try:
            # 尝试终止所有afplay进程
            subprocess.run(["pkill", "afplay"], check=False)
        except Exception as e:
            logger.error(f"停止播放错误: {e}") 