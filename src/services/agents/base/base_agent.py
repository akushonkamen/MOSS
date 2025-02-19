"""基础智能体类

为所有智能体提供基础功能和接口定义。
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """基础智能体类"""
    
    def __init__(self, agent_id: str):
        """初始化智能体
        
        Args:
            agent_id: 智能体ID
        """
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self._is_running = False
        
    @abstractmethod
    async def initialize(self) -> None:
        """初始化智能体"""
        pass
        
    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求
        
        Args:
            context: 请求上下文
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        pass
        
    async def start(self) -> None:
        """启动智能体"""
        if self._is_running:
            return
            
        await self.initialize()
        self._is_running = True
        self.logger.info(f"智能体 {self.agent_id} 已启动")
        
    async def stop(self) -> None:
        """停止智能体"""
        if not self._is_running:
            return
            
        self._is_running = False
        self.logger.info(f"智能体 {self.agent_id} 已停止")
        
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running 