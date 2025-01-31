import edge_tts
from typing import AsyncIterator
from .interface import TTSService

class EdgeTTSService(TTSService):
    """Edge TTS服务"""
    
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        """
        初始化Edge TTS服务
        
        Args:
            voice: 语音名称，默认使用中文女声
        """
        self.voice = voice
        self.communicate = edge_tts.Communicate
        
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """
        流式语音合成
        
        Args:
            text: 要转换的文本
            
        Returns:
            AsyncIterator[bytes]: 音频数据流
        """
        if not text:
            return
            
        try:
            communicate = self.communicate(text, self.voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            print(f"语音合成出错: {str(e)}")
            return 