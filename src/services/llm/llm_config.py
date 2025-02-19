"""LLM配置模块

提供LLM服务的配置定义。
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class LLMConfig:
    """LLM配置"""
    
    # API配置
    api_url: str
    model_name: str
    api_key: Optional[str] = None
    
    # 请求配置
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 2048
    stop_sequences: Optional[list[str]] = None
    
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    
    # 缓存配置
    enable_cache: bool = True
    cache_dir: str = "data/llm_cache"
    max_cache_size: int = 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "api_url": self.api_url,
            "model_name": self.model_name,
            "api_key": self.api_key,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_tokens": self.max_tokens,
            "stop_sequences": self.stop_sequences,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "enable_cache": self.enable_cache,
            "cache_dir": self.cache_dir,
            "max_cache_size": self.max_cache_size
        } 