from abc import ABC, abstractmethod
from typing import BinaryIO

class STTService(ABC):
    """语音识别服务接口"""
    
    @abstractmethod
    async def transcribe(self, audio_data: BinaryIO) -> str:
        """
        将音频转换为文本
        
        Args:
            audio_data: 音频数据流
            
        Returns:
            str: 识别出的文本
        """
        pass 