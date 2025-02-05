from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re
from datetime import datetime

class DeviceCapability(str, Enum):
    """设备能力枚举"""
    POWER = "power"                # 电源控制
    BRIGHTNESS = "brightness"      # 亮度控制
    TEMPERATURE = "temperature"    # 温度控制
    MODE = "mode"                  # 模式控制
    POSITION = "position"          # 位置控制
    SCHEDULE = "schedule"          # 定时控制
    SCENE = "scene"               # 场景控制
    VOICE = "voice"               # 语音控制

class DeviceMetadata(BaseModel):
    """设备元数据模型"""
    manufacturer: str = Field(..., description="制造商")
    model: str = Field(..., description="型号")
    firmware: str = Field(..., description="固件版本")
    protocol: str = Field(..., description="通信协议版本")
    capabilities: List[DeviceCapability] = Field(default_factory=list, description="设备能力列表")

class DeviceGroup(BaseModel):
    """设备分组模型"""
    group_id: str = Field(..., description="分组ID")
    name: str = Field(..., description="分组名称")
    location: str = Field(..., description="位置信息")
    devices: List[str] = Field(default_factory=list, description="设备ID列表")

    @field_validator('group_id')
    @classmethod
    def validate_group_id(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('分组ID只能包含字母、数字、下划线和连字符')
        return v

class DeviceMetrics(BaseModel):
    """设备性能指标模型"""
    cpu_usage: Optional[float] = Field(None, description="CPU使用率")
    memory_usage: Optional[float] = Field(None, description="内存使用率")
    network_latency: Optional[float] = Field(None, description="网络延迟(ms)")
    signal_strength: Optional[int] = Field(None, description="信号强度(dBm)")
    uptime: Optional[int] = Field(None, description="运行时间(秒)")

class DeviceStatusReport(BaseModel):
    """设备状态报告模型"""
    timestamp: datetime = Field(default_factory=datetime.now, description="状态更新时间戳")
    online: bool = Field(..., description="在线状态")
    error: Optional[str] = Field(None, description="错误信息")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数状态")
    metrics: DeviceMetrics = Field(default_factory=DeviceMetrics, description="性能指标")

class DeviceRegistrationValidation(BaseModel):
    """设备注册验证模型"""
    device_id: str = Field(..., description="设备ID")
    name: str = Field(..., description="设备名称")
    type: str = Field(..., description="设备类型")
    port: int = Field(..., description="设备端口")
    metadata: DeviceMetadata = Field(..., description="设备元数据")

    @field_validator('device_id')
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('设备ID只能包含字母、数字、下划线和连字符')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if len(v) > 32:
            raise ValueError('设备名称长度不能超过32个字符')
        return v

    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1024 <= v <= 65535:
            raise ValueError('端口号必须在1024-65535之间')
        return v

class DeviceParameter(BaseModel):
    """设备参数模型"""
    type: str = Field(..., description="参数类型")
    description: str = Field(..., description="参数描述")
    current_value: Any = Field(None, description="当前值")
    min_value: Optional[float] = Field(None, description="最小值")
    max_value: Optional[float] = Field(None, description="最大值")
    unit: Optional[str] = Field(None, description="单位")
    enum_values: Optional[List[str]] = Field(None, description="枚举值列表")

class DeviceInfo(BaseModel):
    """设备信息模型"""
    id: str = Field(..., description="设备ID")
    name: str = Field(..., description="设备名称")
    type: str = Field(..., description="设备类型")
    metadata: DeviceMetadata = Field(..., description="设备元数据")
    parameters: Dict[str, DeviceParameter] = Field(default_factory=dict, description="设备参数")
    group_id: Optional[str] = Field(None, description="所属分组ID")
    location: Optional[str] = Field(None, description="位置信息")
    status: Optional[DeviceStatusReport] = Field(None, description="设备状态") 