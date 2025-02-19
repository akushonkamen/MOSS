"""设备基类定义

提供所有设备共用的基础功能和接口定义。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
from enum import Enum

class DeviceStatus(str, Enum):
    """设备状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"

@dataclass
class DeviceParameter:
    """设备参数定义"""
    name: str
    type: str
    description: str
    current_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    enum_values: Optional[List[str]] = None
    unit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "current_value": self.current_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "enum_values": self.enum_values,
            "unit": self.unit
        }

@dataclass
class DeviceInfo:
    """设备信息"""
    id: str
    name: str
    type: str
    location: str
    status: DeviceStatus
    parameters: Dict[str, DeviceParameter]
    capabilities: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "location": self.location,
            "status": self.status.value if isinstance(self.status, DeviceStatus) else self.status,
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()},
            "capabilities": self.capabilities
        }

    def update(self, data: Dict[str, Any]) -> None:
        """更新设备信息
        
        Args:
            data: 新的设备信息
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

class DeviceError(Exception):
    """设备操作异常"""
    pass

class BaseDevice(ABC):
    """设备基类"""
    
    def __init__(self, device_id: str, name: str, device_type: str):
        """初始化设备
        
        Args:
            device_id: 设备ID
            name: 设备名称
            device_type: 设备类型
        """
        self.device_id = device_id
        self.name = name
        self.type = device_type
        self.logger = logging.getLogger(f"device.{device_id}")
        self._functions: Dict[str, Any] = {}
        
    def register_function(self, name: str, function: Any) -> None:
        """注册设备函数
        
        Args:
            name: 函数名称
            function: 函数对象
        """
        self._functions[name] = function
        
    def get_function(self, name: str) -> Optional[Any]:
        """获取设备函数
        
        Args:
            name: 函数名称
            
        Returns:
            Optional[Any]: 函数对象
        """
        return self._functions.get(name)
        
    def get_functions(self) -> Dict[str, Any]:
        """获取所有函数
        
        Returns:
            Dict[str, Any]: 函数字典
        """
        return self._functions.copy()
        
    @abstractmethod
    async def get_state(self) -> Dict[str, Any]:
        """获取设备状态
        
        Returns:
            Dict[str, Any]: 状态字典
        """
        pass
        
    @abstractmethod
    async def set_state(self, state: Dict[str, Any]) -> bool:
        """设置设备状态
        
        Args:
            state: 新的状态
            
        Returns:
            bool: 是否设置成功
        """
        pass
        
    @abstractmethod
    async def get_capabilities(self) -> List[str]:
        """获取设备能力列表
        
        Returns:
            List[str]: 能力列表
        """
        pass

    def get_device_info(self) -> DeviceInfo:
        """获取设备信息"""
        return DeviceInfo(
            id=self.device_id,
            name=self.name,
            type=self.type,
            location=self.location,
            status=self.status,
            parameters={},  # 由子类实现具体参数
            capabilities=[]  # 由子类实现具体能力
        ) 