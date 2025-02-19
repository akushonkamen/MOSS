"""设备管理模块

提供设备管理的核心功能：
1. 设备基类和接口定义
2. 设备管理器和状态管理器
3. 设备模型和工具函数
"""

# 导入基础类
from .base.device_base import (
    BaseDevice,
    DeviceStatus,
    DeviceError,
    DeviceInfo,
    DeviceParameter
)

# 导入管理器
from .managers.unified_device_manager import UnifiedDeviceManager
from .state.state_manager import StateManager

__all__ = [
    # 基础类
    'BaseDevice',
    'DeviceStatus',
    'DeviceError',
    'DeviceInfo',
    'DeviceParameter',
    
    # 管理器
    'UnifiedDeviceManager',
    'StateManager'
] 