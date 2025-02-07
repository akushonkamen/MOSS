"""Agent注册中心"""
from typing import Dict, List, Any, Optional, Set
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from .base import BaseAgent, AgentType, AgentStatus, AgentCapability

logger = logging.getLogger(__name__)

@dataclass
class AgentRegistration:
    """Agent注册信息"""
    agent: BaseAgent
    registered_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

class AgentRegistry:
    """Agent注册中心"""
    
    def __init__(self):
        """初始化注册中心"""
        self._agents: Dict[str, AgentRegistration] = {}
        self._lock = asyncio.Lock()
        self._type_index: Dict[AgentType, Set[str]] = {
            agent_type: set() for agent_type in AgentType
        }
        self._capability_index: Dict[str, Set[str]] = {}
        
    async def register(
        self,
        agent: BaseAgent,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """注册Agent
        
        Args:
            agent: 要注册的Agent
            dependencies: Agent依赖的其他Agent ID列表
            metadata: Agent元数据
        
        Raises:
            ValueError: Agent ID已存在或依赖的Agent不存在
        """
        async with self._lock:
            # 检查ID是否已存在
            if agent.id in self._agents:
                raise ValueError(f"Agent {agent.id} already registered")
            
            # 验证依赖
            if dependencies:
                missing = [dep for dep in dependencies if dep not in self._agents]
                if missing:
                    raise ValueError(f"Dependencies not found: {missing}")
            
            # 创建注册信息
            registration = AgentRegistration(
                agent=agent,
                dependencies=set(dependencies or []),
                metadata=metadata or {}
            )
            
            # 更新索引
            self._agents[agent.id] = registration
            self._type_index[agent.type].add(agent.id)
            
            # 更新能力索引
            for capability in agent.capabilities.values():
                if capability.name not in self._capability_index:
                    self._capability_index[capability.name] = set()
                self._capability_index[capability.name].add(agent.id)
            
            # 更新依赖关系
            if dependencies:
                for dep_id in dependencies:
                    self._agents[dep_id].dependents.add(agent.id)
            
            logger.info(f"Registered agent: {agent} with dependencies: {dependencies}")
            
    async def unregister(self, agent_id: str) -> None:
        """注销Agent
        
        Args:
            agent_id: Agent ID
            
        Raises:
            ValueError: Agent不存在或有其他Agent依赖它
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not registered")
            
            registration = self._agents[agent_id]
            
            # 检查是否有依赖它的Agent
            if registration.dependents:
                raise ValueError(
                    f"Cannot unregister agent {agent_id}, "
                    f"it has dependents: {registration.dependents}"
                )
            
            # 从依赖Agent中移除
            for dep_id in registration.dependencies:
                self._agents[dep_id].dependents.remove(agent_id)
            
            # 更新索引
            self._type_index[registration.agent.type].remove(agent_id)
            
            # 更新能力索引
            for capability in registration.agent.capabilities.values():
                self._capability_index[capability.name].remove(agent_id)
                if not self._capability_index[capability.name]:
                    del self._capability_index[capability.name]
            
            # 移除注册信息
            del self._agents[agent_id]
            
            logger.info(f"Unregistered agent: {agent_id}")
            
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取Agent实例
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[BaseAgent]: Agent实例，不存在则返回None
        """
        registration = self._agents.get(agent_id)
        return registration.agent if registration else None
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAgent]:
        """获取指定类型的所有Agent
        
        Args:
            agent_type: Agent类型
            
        Returns:
            List[BaseAgent]: Agent实例列表
        """
        return [
            self._agents[agent_id].agent
            for agent_id in self._type_index[agent_type]
        ]
    
    def get_agents_by_capability(self, capability_name: str) -> List[BaseAgent]:
        """获取具有指定能力的所有Agent
        
        Args:
            capability_name: 能力名称
            
        Returns:
            List[BaseAgent]: Agent实例列表
        """
        agent_ids = self._capability_index.get(capability_name, set())
        return [self._agents[agent_id].agent for agent_id in agent_ids]
    
    def get_dependencies(self, agent_id: str) -> List[BaseAgent]:
        """获取Agent的依赖
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List[BaseAgent]: 依赖的Agent实例列表
            
        Raises:
            ValueError: Agent不存在
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not registered")
            
        registration = self._agents[agent_id]
        return [
            self._agents[dep_id].agent
            for dep_id in registration.dependencies
        ]
    
    def get_dependents(self, agent_id: str) -> List[BaseAgent]:
        """获取依赖该Agent的其他Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List[BaseAgent]: 依赖该Agent的实例列表
            
        Raises:
            ValueError: Agent不存在
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not registered")
            
        registration = self._agents[agent_id]
        return [
            self._agents[dep_id].agent
            for dep_id in registration.dependents
        ]
    
    async def update_agent_status(self, agent_id: str, is_active: bool) -> None:
        """更新Agent状态
        
        Args:
            agent_id: Agent ID
            is_active: 是否活跃
            
        Raises:
            ValueError: Agent不存在
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not registered")
                
            registration = self._agents[agent_id]
            registration.is_active = is_active
            registration.last_active = datetime.now()
            
    async def update_agent_metadata(
        self,
        agent_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """更新Agent元数据
        
        Args:
            agent_id: Agent ID
            metadata: 新的元数据
            
        Raises:
            ValueError: Agent不存在
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} not registered")
                
            registration = self._agents[agent_id]
            registration.metadata.update(metadata)
            
    def get_all_agents(self) -> List[BaseAgent]:
        """获取所有注册的Agent
        
        Returns:
            List[BaseAgent]: 所有Agent实例列表
        """
        return [reg.agent for reg in self._agents.values()]
    
    def get_active_agents(self) -> List[BaseAgent]:
        """获取所有活跃的Agent
        
        Returns:
            List[BaseAgent]: 活跃的Agent实例列表
        """
        return [
            reg.agent
            for reg in self._agents.values()
            if reg.is_active
        ]
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent详细信息
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[Dict[str, Any]]: Agent信息字典，不存在则返回None
        """
        registration = self._agents.get(agent_id)
        if not registration:
            return None
            
        return {
            "agent": registration.agent.to_dict(),
            "registered_at": registration.registered_at.isoformat(),
            "last_active": registration.last_active.isoformat(),
            "is_active": registration.is_active,
            "dependencies": list(registration.dependencies),
            "dependents": list(registration.dependents),
            "metadata": registration.metadata
        }

# 创建全局注册中心实例
registry = AgentRegistry() 