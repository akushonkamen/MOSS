"""解码代理

负责理解和解析用户意图。
"""
import logging
from typing import Dict, Any, Optional
import aiohttp
import json
from dataclasses import dataclass
import re

from ..base import BaseAgent
from .decoder_config import DecoderConfig

logger = logging.getLogger(__name__)

@dataclass
class DecoderConfig:
    """解码器配置"""
    api_url: str = "http://localhost:11434/api/generate"  # Ollama API地址
    model_name: str = "llama3.1:latest"  # 使用的模型名称
    temperature: float = 0.1    # 较低的temperature以获得更确定的输出
    max_tokens: int = 1000      # 输出长度限制
    timeout: int = 30           # API超时时间

class DecoderAgent(BaseAgent):
    """解码代理"""
    
    def __init__(self, agent_id: str, config: Optional[DecoderConfig] = None):
        """初始化解码代理
        
        Args:
            agent_id: 智能体ID
            config: 解码器配置，如果为None则使用默认配置
        """
        super().__init__(agent_id)
        self.config = config or DecoderConfig()
        self._is_ready = False
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info("Decoder agent initialized with config: %s", self.config)
        
    async def initialize(self) -> None:
        """初始化智能体"""
        if self._is_ready:
            return
            
        try:
            self._session = aiohttp.ClientSession()
            self._is_ready = True
            logger.info(f"解码代理 {self.agent_id} 初始化完成")
        except Exception as e:
            logger.error(f"初始化解码代理失败: {str(e)}")
            raise
            
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求
        
        Args:
            context: 请求上下文
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        if not self._is_ready:
            raise RuntimeError("Decoder agent not initialized")
            
        try:
            input_text = context.get("text")
            if not input_text:
                return {
                    "error": "No input text provided"
                }
                
            return await self.decode(input_text)
            
        except Exception as e:
            logger.error(f"处理请求失败: {str(e)}")
            return {
                "error": f"Processing failed: {str(e)}"
            }
            
    async def stop(self) -> None:
        """停止解码器智能体"""
        if not self._is_ready:
            return
            
        try:
            if self._session:
                await self._session.close()
            self._is_ready = False
            logger.info(f"解码代理 {self.agent_id} 已停止")
        except Exception as e:
            logger.error(f"停止解码代理失败: {str(e)}")
            raise
            
    async def decode(self, input_text: str) -> Dict[str, Any]:
        """解码用户输入
        
        Args:
            input_text: 用户输入文本
            
        Returns:
            解码后的指令字典
        """
        if not self._is_ready:
            raise RuntimeError("Decoder agent not started")
            
        try:
            # TODO: 实现实际的解码逻辑
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "parameters": {}
            }
        except Exception as e:
            logger.error("Failed to decode input: %s", e)
            raise
            
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """调用LLM服务
        
        Args:
            prompt: 提示词
            
        Returns:
            Optional[str]: LLM响应
        """
        if not self._session:
            raise RuntimeError("代理未初始化")
            
        request = {
            "model": self.config.model_name,
            "prompt": prompt,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False
        }
        
        try:
            async with self._session.post(
                self.config.api_url,
                json=request,
                timeout=self.config.timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"LLM API调用失败: {error_text}")
                    
                result = await response.json()
                
                # 处理Ollama的响应格式
                if "response" in result:
                    return result["response"]
                elif "content" in result:
                    return result["content"]
                elif "text" in result:
                    return result["text"]
                else:
                    raise ValueError(f"未知的响应格式: {result}")
                    
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            return None
            
    def _build_prompt(self, text: str) -> str:
        """构建提示词
        
        Args:
            text: 用户输入
            
        Returns:
            str: 提示词
        """
        return f"""请理解用户的控制命令，并返回结构化的意图对象。

用户输入:
{text}

请返回JSON格式的意图对象，包含以下字段：
- device_type: 设备类型
- device_id: 设备ID（如果有）
- action: 动作名称
- parameters: 参数对象

示例：
{{
    "device_type": "空调",
    "device_id": "客厅空调",
    "action": "set_temperature",
    "parameters": {{
        "temperature": 26
    }}
}}

如果无法理解用户意图，请返回null。"""
        
    def _parse_intent(self, response: str) -> Optional[Dict[str, Any]]:
        """解析意图
        
        Args:
            response: LLM响应
            
        Returns:
            Optional[Dict[str, Any]]: 意图对象
        """
        try:
            # 清理响应文本
            response = response.strip()
            
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
                
            # 解析JSON
            intent = json.loads(json_match.group())
            
            # 验证意图格式
            if not isinstance(intent, dict):
                return None
                
            required_fields = ["device_type", "action", "parameters"]
            if not all(field in intent for field in required_fields):
                return None
                
            return intent
            
        except Exception as e:
            logger.error(f"解析意图失败: {e}")
            return None 