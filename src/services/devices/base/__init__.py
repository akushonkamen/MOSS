"""设备基础模块

提供设备相关的基础类和接口定义。
"""

from .device_base import (
    BaseDevice,
    DeviceStatus,
    DeviceError,
    DeviceInfo,
    DeviceParameter
)
from .client_base import DeviceClient

__all__ = [
    'BaseDevice',
    'DeviceStatus',
    'DeviceError',
    'DeviceInfo',
    'DeviceParameter',
    'DeviceClient'
] 