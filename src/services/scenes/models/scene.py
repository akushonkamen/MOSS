"""场景模型定义"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .condition import Condition
from .action import Action
from .trigger import Trigger

@dataclass
class Scene:
    """场景定义类
    
    属性:
        id: 场景ID
        name: 场景名称
        description: 场景描述
        conditions: 触发条件列表
        actions: 执行动作列表
        triggers: 触发器列表
        enabled: 是否启用
        created_at: 创建时间
        updated_at: 更新时间
        metadata: 元数据
    """
    
    id: str
    name: str
    description: str = ""
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    triggers: List[Trigger] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "triggers": [t.to_dict() for t in self.triggers],
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scene":
        """从字典创建场景对象"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            conditions=[Condition.from_dict(c) for c in data.get("conditions", [])],
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            triggers=[Trigger.from_dict(t) for t in data.get("triggers", [])],
            enabled=data.get("enabled", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {})
        )


