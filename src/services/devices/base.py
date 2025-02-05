"""设备模拟基础类"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
import asyncio
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)

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

class DeviceError(Exception):
    """设备操作异常"""
    pass

class Device(ABC):
    """设备基类"""
    
    def __init__(self, device_id: str, name: str):
        self.device_id = device_id
        self.name = name
        self._status = DeviceStatus.ONLINE
        
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        pass
        
    @abstractmethod
    async def turn_on(self) -> bool:
        """打开设备"""
        pass
        
    @abstractmethod
    async def turn_off(self) -> bool:
        """关闭设备"""
        pass
        
    async def _simulate_delay(self, min_delay: float = 0.1, max_delay: float = 0.5):
        """模拟设备响应延迟"""
        delay = (max_delay - min_delay) * 0.5 + min_delay
        await asyncio.sleep(delay)
        
class DeviceClient:
    """设备客户端基类"""
    
    def __init__(self, device_id: str):
        """初始化设备客户端
        
        Args:
            device_id: 设备ID
        """
        self.device_id = device_id
        self.state: Dict[str, Any] = {}
        self.last_update: Optional[datetime] = None
        self.update_interval = timedelta(seconds=5)  # 状态更新间隔
        self.retry_count = 3  # 重试次数
        self.retry_delay = 1  # 重试延迟(秒)
        
    async def _make_request(self, method: str, **kwargs) -> Dict[str, Any]:
        """发送请求
        
        Args:
            method: 请求方法
            **kwargs: 请求参数
            
        Returns:
            Dict[str, Any]: 响应数据
            
        Raises:
            DeviceError: 设备操作异常
        """
        raise NotImplementedError
                
    async def get_status(self) -> Dict[str, Any]:
        """获取设备状态
        
        Returns:
            Dict[str, Any]: 设备状态
            
        Raises:
            DeviceError: 设备操作异常
        """
        try:
            # 检查缓存是否有效
            now = datetime.now()
            if (self.last_update and 
                now - self.last_update < self.update_interval):
                return self.state
                
            # 获取最新状态
            status = await self._make_request("get_status")
            self.state = status
            self.last_update = now
            return status
        except Exception as e:
            raise DeviceError(f"获取设备状态失败: {str(e)}")
        
    async def update_state(self, state: Dict[str, Any]) -> bool:
        """更新设备状态
        
        Args:
            state: 新状态
            
        Returns:
            bool: 是否更新成功
            
        Raises:
            DeviceError: 设备操作异常
        """
        try:
            result = await self._make_request("update_state", state=state)
            return result.get("success", False)
        except Exception as e:
            raise DeviceError(f"更新设备状态失败: {str(e)}")
            
    async def execute_command(self, command: str, **params) -> bool:
        """执行设备命令
        
        Args:
            command: 命令名称
            **params: 命令参数
            
        Returns:
            bool: 是否执行成功
            
        Raises:
            DeviceError: 设备操作异常
        """
        try:
            result = await self._make_request(
                "execute", 
                command=command,
                params=params
            )
            if result.get("success"):
                # 命令执行成功后立即更新状态
                await self.get_status()
            return result.get("success", False)
        except Exception as e:
            raise DeviceError(f"执行设备命令失败: {str(e)}")

class DeviceRegistry:
    """设备注册表"""
    
    def __init__(self):
        """初始化设备注册表"""
        self._devices: Dict[str, DeviceInfo] = {}
        self._status_subscribers = set()
        
    def register(self, device_info: DeviceInfo) -> None:
        """注册设备
        
        Args:
            device_info: 设备信息
        """
        self._devices[device_info.id] = device_info
        # 发布设备上线状态
        self._publish_status_update(device_info.id, DeviceStatus.ONLINE)
        
    def unregister(self, device_id: str) -> None:
        """注销设备
        
        Args:
            device_id: 设备ID
        """
        if device_id in self._devices:
            # 发布设备下线状态
            self._publish_status_update(device_id, DeviceStatus.OFFLINE)
            del self._devices[device_id]
            
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[DeviceInfo]: 设备信息
        """
        return self._devices.get(device_id)
        
    def list_devices(self) -> List[DeviceInfo]:
        """获取所有设备列表
        
        Returns:
            List[DeviceInfo]: 设备列表
        """
        return list(self._devices.values())
        
    def update_parameter(self, device_id: str, parameter_name: str, value: Any) -> None:
        """更新设备参数值
        
        Args:
            device_id: 设备ID
            parameter_name: 参数名
            value: 新的参数值
        """
        if device_id in self._devices:
            device = self._devices[device_id]
            if parameter_name in device.parameters:
                device.parameters[parameter_name].current_value = value
                # 发布参数更新
                self._publish_parameter_update(device_id, parameter_name, value)
                
    def subscribe_status(self, callback) -> None:
        """订阅设备状态更新
        
        Args:
            callback: 回调函数
        """
        self._status_subscribers.add(callback)
        
    def unsubscribe_status(self, callback) -> None:
        """取消订阅设备状态更新
        
        Args:
            callback: 回调函数
        """
        self._status_subscribers.discard(callback)
        
    def _publish_status_update(self, device_id: str, status: DeviceStatus) -> None:
        """发布设备状态更新
        
        Args:
            device_id: 设备ID
            status: 新的状态
        """
        for callback in self._status_subscribers:
            asyncio.create_task(callback(device_id, status))
            
    def _publish_parameter_update(self, device_id: str, parameter_name: str, value: Any) -> None:
        """发布设备参数更新
        
        Args:
            device_id: 设备ID
            parameter_name: 参数名
            value: 新的参数值
        """
        for callback in self._status_subscribers:
            asyncio.create_task(callback(device_id, {parameter_name: value}))

# 全局设备注册表
registry = DeviceRegistry() 