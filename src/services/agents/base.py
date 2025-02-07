from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import asyncio
import json
import logging
import time

logger = logging.getLogger(__name__)

class AgentType(Enum):
    """智能体类型枚举"""
    DECODER = "decoder"  # 解码器智能体
    EXPERT = "expert"    # 专家智能体
    MEMORY = "memory"    # 记忆智能体
    LEARNER = "learner"  # 学习智能体
    CUSTOM = "custom"    # 自定义智能体

class AgentStatus(Enum):
    """智能体状态枚举"""
    IDLE = "idle"           # 空闲状态
    PROCESSING = "processing" # 处理中
    LEARNING = "learning"   # 学习中
    EVOLVING = "evolving"   # 进化中
    ERROR = "error"         # 错误状态

@dataclass
class AgentCapability:
    """智能体能力描述"""
    name: str                # 能力名称
    description: str         # 能力描述
    parameters: Dict[str, Any] # 能力参数
    version: str            # 能力版本
    dependencies: List[str] = None  # 依赖能力

@dataclass
class AgentMetrics:
    """智能体度量指标"""
    processing_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_processing_time: float = 0.0
    last_learning_time: float = 0.0
    last_evolution_time: float = 0.0
    learning_count: int = 0
    learning_progress: float = 0.0
    evolution_count: int = 0
    evolution_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "processing_count": self.processing_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "last_processing_time": self.last_processing_time,
            "last_learning_time": self.last_learning_time,
            "last_evolution_time": self.last_evolution_time,
            "learning_count": self.learning_count,
            "learning_progress": self.learning_progress,
            "evolution_count": self.evolution_count,
            "evolution_score": self.evolution_score
        }

class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, agent_id: str, agent_type: AgentType):
        self.id = agent_id
        self.type = agent_type
        self.status = AgentStatus.IDLE
        self.capabilities: Dict[str, AgentCapability] = {}
        self.metrics = AgentMetrics()
        self._lock = asyncio.Lock()
    
    def get_current_time(self) -> float:
        """获取当前时间戳
        
        Returns:
            float: 当前时间戳（秒）
        """
        return time.time()
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入数据"""
        pass
    
    @abstractmethod
    async def learn(self, experience: Dict[str, Any]) -> None:
        """从经验中学习"""
        pass
    
    @abstractmethod
    async def evolve(self) -> None:
        """进化能力"""
        pass
    
    async def register_capability(self, capability: AgentCapability) -> None:
        """注册新能力"""
        async with self._lock:
            if capability.name in self.capabilities:
                logger.warning(f"Capability {capability.name} already exists, updating...")
            self.capabilities[capability.name] = capability
            logger.info(f"Registered capability: {capability.name}")
    
    async def remove_capability(self, capability_name: str) -> None:
        """移除能力"""
        async with self._lock:
            if capability_name in self.capabilities:
                del self.capabilities[capability_name]
                logger.info(f"Removed capability: {capability_name}")
    
    def has_capability(self, capability_name: str) -> bool:
        """检查是否具有某个能力"""
        return capability_name in self.capabilities
    
    def get_capability(self, capability_name: str) -> Optional[AgentCapability]:
        """获取能力信息"""
        return self.capabilities.get(capability_name)
    
    def update_metrics(self, 
                      success: bool = True,
                      processing_time: float = 0.0) -> None:
        """更新度量指标
        
        Args:
            success: 是否成功
            processing_time: 处理时间（秒）
        """
        self.metrics.processing_count += 1
        if success:
            self.metrics.success_count += 1
        else:
            self.metrics.error_count += 1
            
        if processing_time > 0:
            self.metrics.last_processing_time = processing_time
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "capabilities": {name: vars(cap) for name, cap in self.capabilities.items()},
            "metrics": vars(self.metrics)
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.type.value.capitalize()}Agent(id={self.id}, status={self.status.value})" 