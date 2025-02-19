"""设备事件模型

此模块定义了设备事件相关的数据模型，用于描述和记录设备状态变化、操作执行等事件。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

class EventType(Enum):
    """设备事件类型"""
    STATE_CHANGE = "state_change"  # 状态变化
    COMMAND_EXECUTED = "command_executed"  # 命令执行
    ERROR = "error"  # 错误事件
    WARNING = "warning"  # 警告事件
    INFO = "info"  # 信息事件

class EventSeverity(Enum):
    """事件严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class DeviceEvent:
    """设备事件数据类"""
    device_id: str  # 设备ID
    event_type: EventType  # 事件类型
    timestamp: datetime  # 事件时间戳
    description: str  # 事件描述
    severity: EventSeverity  # 事件严重程度
    data: Optional[Dict[str, Any]] = None  # 事件相关数据
    source: Optional[str] = None  # 事件来源
    correlation_id: Optional[str] = None  # 关联ID

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "device_id": self.device_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "severity": self.severity.value,
            "data": self.data,
            "source": self.source,
            "correlation_id": self.correlation_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceEvent":
        """从字典创建事件对象"""
        return cls(
            device_id=data["device_id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            description=data["description"],
            severity=EventSeverity(data["severity"]),
            data=data.get("data"),
            source=data.get("source"),
            correlation_id=data.get("correlation_id")
        )

__all__ = ["EventType", "EventSeverity", "DeviceEvent"] 