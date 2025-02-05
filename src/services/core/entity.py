from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

class EntityCategory(str, Enum):
    """实体类别"""
    LIGHT = "light"
    CLIMATE = "climate"
    COVER = "cover"
    SENSOR = "sensor"
    SWITCH = "switch"
    SCENE = "scene"

class EntityState(BaseModel):
    """实体状态基类"""
    entity_id: str = Field(..., description="实体ID")
    state: str = Field(..., description="当前状态")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="属性")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")
    last_changed: datetime = Field(default_factory=datetime.now, description="最后变更时间")

class ServiceCall(BaseModel):
    """服务调用模型"""
    domain: str = Field(..., description="服务域")
    service: str = Field(..., description="服务名称")
    entity_id: str = Field(..., description="目标实体ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="服务参数")

class Entity:
    """实体基类"""
    
    def __init__(
        self,
        entity_id: str,
        name: str,
        category: EntityCategory,
        supported_features: List[str] = None
    ):
        """初始化实体
        
        Args:
            entity_id: 实体ID
            name: 实体名称
            category: 实体类别
            supported_features: 支持的功能列表
        """
        self.entity_id = entity_id
        self.name = name
        self.category = category
        self._state = EntityState(
            entity_id=entity_id,
            state="unknown",
            attributes={
                "friendly_name": name,
                "supported_features": supported_features or []
            }
        )
        
    @property
    def state(self) -> EntityState:
        """获取实体状态"""
        return self._state
        
    async def update(self) -> None:
        """更新实体状态"""
        pass
        
    def get_service_schema(self) -> Dict[str, Any]:
        """获取服务定义"""
        return {}
        
    async def call_service(self, call: ServiceCall) -> None:
        """调用服务
        
        Args:
            call: 服务调用信息
        """
        pass
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "category": self.category,
            "state": self._state.dict(),
            "services": self.get_service_schema()
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