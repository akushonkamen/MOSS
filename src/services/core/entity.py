"""实体基类

提供系统中所有实体的基础定义和功能。
"""
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from .event_bus import event_bus, Event

class EntityCategory(str, Enum):
    """实体类别"""
    LIGHT = "light"
    CLIMATE = "climate"
    COVER = "cover"
    SENSOR = "sensor"
    SWITCH = "switch"
    SCENE = "scene"

@dataclass
class EntityState:
    """实体状态"""
    state: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    last_changed: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "state": self.state,
            "attributes": self.attributes,
            "last_updated": self.last_updated.isoformat(),
            "last_changed": self.last_changed.isoformat()
        }

class Entity(ABC):
    """实体基类"""
    
    def __init__(self, entity_id: str, name: str):
        """初始化实体
        
        Args:
            entity_id: 实体ID
            name: 实体名称
        """
        self.entity_id = entity_id
        self.name = name
        self.logger = logging.getLogger(f"entity.{entity_id}")
        self._state = EntityState(state="unknown")
        
    @property
    def state(self) -> str:
        """获取状态值"""
        return self._state.state
        
    @property
    def attributes(self) -> Dict[str, Any]:
        """获取属性字典"""
        return self._state.attributes.copy()
        
    async def set_state(self, state: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """设置状态
        
        Args:
            state: 状态值
            attributes: 属性字典
        """
        old_state = self._state
        now = datetime.now()
        
        # 更新状态
        self._state = EntityState(
            state=state,
            attributes=attributes or {},
            last_updated=now,
            last_changed=now if state != old_state.state else old_state.last_changed
        )
        
        # 发布状态变更事件
        await event_bus.publish(Event(
            type="state_changed",
            data={
                "entity_id": self.entity_id,
                "old_state": old_state.to_dict(),
                "new_state": self._state.to_dict()
            }
        ))
        
    @abstractmethod
    async def update(self) -> None:
        """更新实体状态"""
        pass
        
    async def turn_on(self, **kwargs) -> None:
        """打开实体"""
        await self.set_state("on", kwargs)
        
    async def turn_off(self, **kwargs) -> None:
        """关闭实体"""
        await self.set_state("off", kwargs)
        
    def is_on(self) -> bool:
        """检查是否打开"""
        return self.state == "on"
        
    def is_off(self) -> bool:
        """检查是否关闭"""
        return self.state == "off"
        
    def get_capabilities(self) -> List[str]:
        """获取实体能力列表"""
        return ["turn_on", "turn_off"]
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "state": self._state.to_dict(),
            "capabilities": self.get_capabilities()
        }

class EntityRegistry:
    """实体注册表"""
    
    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        
    def register(self, entity: Entity) -> None:
        """注册实体"""
        self._entities[entity.entity_id] = entity
        
    def unregister(self, entity_id: str) -> None:
        """注销实体"""
        if entity_id in self._entities:
            del self._entities[entity_id]
            
    def get(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self._entities.get(entity_id)
        
    def list_entities(self, category: Optional[EntityCategory] = None) -> List[Entity]:
        """列出实体"""
        if category:
            return [e for e in self._entities.values() if e.category == category]
        return list(self._entities.values())
        
    async def update_all(self) -> None:
        """更新所有实体状态"""
        for entity in self._entities.values():
            try:
                await entity.update()
            except Exception as e:
                print(f"更新实体 {entity.entity_id} 状态失败: {str(e)}")

# 全局实体注册表
registry = EntityRegistry() 