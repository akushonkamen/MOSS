from abc import ABC, abstractmethod
from typing import AsyncIterator, BinaryIO

class TTSService(ABC):
    """语音合成服务接口"""
    
    @abstractmethod
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """
        流式语音合成
        
        Args:
            text: 要转换的文本
            
        Returns:
            AsyncIterator[bytes]: 音频数据流
        """
        pass 