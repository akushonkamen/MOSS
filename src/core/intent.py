"""核心意图模型

提供统一的意图定义和处理机制。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

class IntentType(Enum):
    """意图类型枚举"""
    DEVICE_CONTROL = "device_control"  # 设备控制
    SCENE_CONTROL = "scene_control"    # 场景控制
    QUERY = "query"                    # 查询
    SYSTEM = "system"                  # 系统操作
    UNKNOWN = "unknown"                # 未知意图

class IntentConfidence(Enum):
    """意图置信度级别"""
    HIGH = "high"        # 高置信度 (>0.8)
    MEDIUM = "medium"    # 中等置信度 (0.5-0.8)
    LOW = "low"          # 低置信度 (<0.5)
    UNKNOWN = "unknown"  # 未知置信度

@dataclass
class EntityValue:
    """实体值"""
    value: Any
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Intent:
    """意图基类"""
    type: IntentType
    confidence: IntentConfidence
    raw_text: str
    entities: Dict[str, EntityValue] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type.value,
            "confidence": self.confidence.value,
            "raw_text": self.raw_text,
            "entities": {
                k: {
                    "value": v.value,
                    "confidence": v.confidence,
                    "metadata": v.metadata
                } for k, v in self.entities.items()
            },
            "context": self.context
        }

@dataclass
class DeviceControlIntent(Intent):
    """设备控制意图"""
    device_id: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "device_id": self.device_id,
            "action": self.action,
            "parameters": self.parameters
        })
        return base_dict

@dataclass
class SceneControlIntent(Intent):
    """场景控制意图"""
    scene_id: str
    action: str = "activate"
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "scene_id": self.scene_id,
            "action": self.action,
            "conditions": self.conditions
        })
        return base_dict

@dataclass
class QueryIntent(Intent):
    """查询意图"""
    query_type: str
    filters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "query_type": self.query_type,
            "filters": self.filters
        })
        return base_dict

@dataclass
class SystemIntent(Intent):
    """系统操作意图"""
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "operation": self.operation,
            "parameters": self.parameters
        })
        return base_dict

class IntentFactory:
    """意图工厂类"""
    
    @staticmethod
    def create_intent(
        intent_type: str,
        raw_text: str,
        confidence: float = 0.0,
        **kwargs
    ) -> Intent:
        """创建意图实例
        
        Args:
            intent_type: 意图类型
            raw_text: 原始文本
            confidence: 置信度
            **kwargs: 其他参数
            
        Returns:
            Intent: 意图实例
        """
        # 确定置信度级别
        if confidence >= 0.8:
            conf_level = IntentConfidence.HIGH
        elif confidence >= 0.5:
            conf_level = IntentConfidence.MEDIUM
        elif confidence > 0:
            conf_level = IntentConfidence.LOW
        else:
            conf_level = IntentConfidence.UNKNOWN
            
        # 根据类型创建具体意图
        try:
            intent_type_enum = IntentType(intent_type)
        except ValueError:
            intent_type_enum = IntentType.UNKNOWN
            
        if intent_type_enum == IntentType.DEVICE_CONTROL:
            return DeviceControlIntent(
                type=intent_type_enum,
                confidence=conf_level,
                raw_text=raw_text,
                **kwargs
            )
        elif intent_type_enum == IntentType.SCENE_CONTROL:
            return SceneControlIntent(
                type=intent_type_enum,
                confidence=conf_level,
                raw_text=raw_text,
                **kwargs
            )
        elif intent_type_enum == IntentType.QUERY:
            return QueryIntent(
                type=intent_type_enum,
                confidence=conf_level,
                raw_text=raw_text,
                **kwargs
            )
        elif intent_type_enum == IntentType.SYSTEM:
            return SystemIntent(
                type=intent_type_enum,
                confidence=conf_level,
                raw_text=raw_text,
                **kwargs
            )
        else:
            return Intent(
                type=intent_type_enum,
                confidence=conf_level,
                raw_text=raw_text
            ) 