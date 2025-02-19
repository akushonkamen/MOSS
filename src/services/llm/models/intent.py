"""意图相关的类定义"""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

class IntentType(str, Enum):
    """意图类型"""
    CONTROL = "control"  # 控制设备
    QUERY = "query"      # 查询状态
    SCENE = "scene"      # 场景控制
    UNKNOWN = "unknown"  # 未知意图

@dataclass
class IntentParameter:
    """意图参数"""
    operation: Optional[str] = None  # 操作类型
    direction: Optional[str] = None  # 调节方向(increase/decrease)
    reason: Optional[str] = None    # 用户意图原因
    target_value: Optional[Any] = None  # 目标值
    current_value: Optional[Any] = None  # 当前值
    
    def dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            Dict[str, Any]: 参数字典
        """
        return {
            "operation": self.operation,
            "direction": self.direction,
            "reason": self.reason,
            "target_value": self.target_value,
            "current_value": self.current_value
        }

@dataclass
class DeviceIntent:
    """设备控制意图"""
    device_id: str           # 设备ID
    device_name: str         # 设备名称
    device_type: str         # 设备类型
    intent_type: IntentType  # 意图类型
    parameters: IntentParameter = None  # 意图参数
    confidence: float = 0.0   # 置信度
    
    def __post_init__(self):
        """初始化后处理"""
        if self.parameters is None:
            self.parameters = IntentParameter()
            
    def dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            Dict[str, Any]: 意图字典
        """
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "intent_type": self.intent_type.value if isinstance(self.intent_type, IntentType) else self.intent_type,
            "parameters": self.parameters.dict() if self.parameters else {},
            "confidence": self.confidence
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（别名方法）
        
        Returns:
            Dict[str, Any]: 意图字典
        """
        return self.dict() 