"""基础设备

定义设备的基本接口和通用功能。
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

class BaseDevice(ABC):
    """基础设备类"""
    
    def __init__(self, device_id: str, name: str, device_type: str):
        """初始化基础设备
        
        Args:
            device_id: 设备ID
            name: 设备名称
            device_type: 设备类型
        """
        self.device_id = device_id
        self.name = name
        self.type = device_type
        self.logger = logging.getLogger(f"device.{device_id}")
        self._functions: Dict[str, Callable] = {}
        
    def register_function(self, name: str, function: Callable) -> None:
        """注册设备函数
        
        Args:
            name: 函数名称
            function: 函数对象
        """
        self._functions[name] = function
        
    def get_function(self, name: str) -> Optional[Callable]:
        """获取设备函数
        
        Args:
            name: 函数名称
            
        Returns:
            Optional[Callable]: 函数对象
        """
        return self._functions.get(name)
        
    def get_functions(self) -> Dict[str, Callable]:
        """获取所有函数
        
        Returns:
            Dict[str, Callable]: 函数字典
        """
        return self._functions
        
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """获取设备状态
        
        Returns:
            Dict[str, Any]: 状态字典
        """
        pass 