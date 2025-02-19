"""设备指标模型

此模块定义了设备指标相关的数据模型，用于收集和分析设备运行状态、性能等指标数据。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"  # 计数器类型
    GAUGE = "gauge"  # 仪表类型
    HISTOGRAM = "histogram"  # 直方图类型
    SUMMARY = "summary"  # 摘要类型

class MetricUnit(Enum):
    """指标单位"""
    COUNT = "count"  # 计数
    BYTES = "bytes"  # 字节
    SECONDS = "seconds"  # 秒
    PERCENTAGE = "percentage"  # 百分比
    WATTS = "watts"  # 瓦特
    CELSIUS = "celsius"  # 摄氏度
    CUSTOM = "custom"  # 自定义单位

@dataclass
class MetricValue:
    """指标值数据类"""
    value: float  # 指标值
    timestamp: datetime  # 时间戳
    labels: Optional[Dict[str, str]] = None  # 标签

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricValue":
        """从字典创建指标值对象"""
        return cls(
            value=float(data["value"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            labels=data.get("labels")
        )

@dataclass
class DeviceMetric:
    """设备指标数据类"""
    device_id: str  # 设备ID
    metric_name: str  # 指标名称
    metric_type: MetricType  # 指标类型
    unit: MetricUnit  # 指标单位
    description: str  # 指标描述
    values: List[MetricValue]  # 指标值列表
    aggregation_period: Optional[str] = None  # 聚合周期
    custom_unit: Optional[str] = None  # 自定义单位（当unit为CUSTOM时使用）

    def add_value(self, value: float, timestamp: Optional[datetime] = None,
                 labels: Optional[Dict[str, str]] = None) -> None:
        """添加指标值"""
        if timestamp is None:
            timestamp = datetime.now()
        self.values.append(MetricValue(value, timestamp, labels))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "device_id": self.device_id,
            "metric_name": self.metric_name,
            "metric_type": self.metric_type.value,
            "unit": self.unit.value,
            "description": self.description,
            "values": [v.to_dict() for v in self.values],
            "aggregation_period": self.aggregation_period,
            "custom_unit": self.custom_unit
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceMetric":
        """从字典创建设备指标对象"""
        return cls(
            device_id=data["device_id"],
            metric_name=data["metric_name"],
            metric_type=MetricType(data["metric_type"]),
            unit=MetricUnit(data["unit"]),
            description=data["description"],
            values=[MetricValue.from_dict(v) for v in data["values"]],
            aggregation_period=data.get("aggregation_period"),
            custom_unit=data.get("custom_unit")
        )

__all__ = ["MetricType", "MetricUnit", "MetricValue", "DeviceMetric"] 