"""文本转语音服务"""
import os
import asyncio
import logging
import tempfile
from typing import Optional
import edge_tts

logger = logging.getLogger(__name__)

class TTSService:
    """文本转语音服务"""
    
    def __init__(self, voice: str = "zh-CN-YunxiNeural"):
        """初始化TTS服务
        
        Args:
            voice: 语音名称
        """
        self.voice = voice
        self.logger = logging.getLogger(__name__)
        
    async def synthesize(self, text: str) -> Optional[str]:
        """合成语音
        
        Args:
            text: 要转换的文本
            
        Returns:
            str: 临时音频文件路径，如果失败则返回None
        """
        if not text:
            self.logger.warning("收到空文本，跳过语音合成")
            return None
            
        try:
            # 创建edge-tts通信对象
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate="+0%",
                volume="+0%"
            )
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_path = temp_file.name
                
            try:
                # 合成语音
                self.logger.debug("开始语音合成...")
                await communicate.save(temp_path)
                self.logger.debug("语音合成完成")
                return temp_path
                
            except Exception as e:
                self.logger.error(f"语音合成失败: {e}")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None
                
        except Exception as e:
            self.logger.error(f"创建TTS通信对象失败: {e}")
            return None
            
    async def stop(self):
        """停止服务"""
        pass  # 目前没有需要清理的资源 