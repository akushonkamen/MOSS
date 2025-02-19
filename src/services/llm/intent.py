"""意图模型

定义用户控制意图的数据结构。
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class IntentType(Enum):
    """意图类型"""
    DEVICE_CONTROL = "device_control"  # 设备控制
    SCENE_CONTROL = "scene_control"    # 场景控制
    QUERY = "query"                    # 查询
    UNKNOWN = "unknown"                # 未知

@dataclass
class Intent:
    """用户控制意图
    
    属性:
        device_name: 设备名称
        action: 动作名称
        parameters: 动作参数
        intent_type: 意图类型
        confidence: 置信度
    """
    device_name: str
    action: str
    parameters: Dict[str, Any]
    intent_type: IntentType = IntentType.DEVICE_CONTROL
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "device_name": self.device_name,
            "action": self.action,
            "parameters": self.parameters,
            "intent_type": self.intent_type.value,
            "confidence": self.confidence
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Intent":
        """从字典创建意图对象"""
        return cls(
            device_name=data["device_name"],
            action=data["action"],
            parameters=data.get("parameters", {}),
            intent_type=IntentType(data.get("intent_type", "device_control")),
            confidence=data.get("confidence", 1.0)
        ) 