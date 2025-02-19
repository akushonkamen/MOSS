"""解码器配置类"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class DecoderConfig:
    """解码器配置
    
    Attributes:
        model_name: 使用的语言模型名称
        temperature: 采样温度
        max_tokens: 最大token数
        top_p: 核采样阈值
    """
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95
    
    def __post_init__(self):
        """验证配置参数"""
        if not isinstance(self.temperature, float) or not 0 <= self.temperature <= 1:
            raise ValueError("temperature must be a float between 0 and 1")
        if not isinstance(self.max_tokens, int) or self.max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")
        if not isinstance(self.top_p, float) or not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be a float between 0 and 1") 