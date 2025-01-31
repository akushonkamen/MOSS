from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

class LLMService(ABC):
    """语言模型服务接口"""
    
    @abstractmethod
    async def chat_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        流式对话
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            temperature: 温度参数
            
        Yields:
            str: 模型响应片段
        """
        pass 