"""设备模拟基础类"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
import asyncio
from datetime import datetime, timedelta
import logging
from enum import Enum
from .state_manager import state_manager, StateChange

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
        
class DeviceClient(ABC):
    """基础设备客户端"""
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化设备客户端
        
        Args:
            device_id: 设备ID
            name: 设备名称
            port: 设备端口
        """
        self.device_id = device_id
        self.name = name
        self.port = port
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """初始化设备"""
        try:
            # 初始化设备状态
            initial_state = await self.get_initial_state()
            await state_manager.initialize_state(self.device_id, initial_state)
            
            # 订阅状态变更
            state_manager.subscribe(self.device_id, self._on_state_change)
            
            self.logger.info(f"设备 {self.name} 初始化完成")
            
        except Exception as e:
            self.logger.error(f"设备 {self.name} 初始化失败: {str(e)}")
            raise
            
    @abstractmethod
    async def get_initial_state(self) -> Dict[str, Any]:
        """获取初始状态
        
        Returns:
            Dict[str, Any]: 初始状态
        """
        pass
        
    async def get_state(self) -> Dict[str, Any]:
        """获取设备状态
        
        Returns:
            Dict[str, Any]: 设备状态
        """
        return await state_manager.get_state(self.device_id)
        
    async def set_state(self, state: Dict[str, Any]) -> bool:
        """设置设备状态
        
        Args:
            state: 设备状态
            
        Returns:
            bool: 是否设置成功
        """
        return await state_manager.update_state(self.device_id, state)
        
    async def set_power(self, power: bool) -> bool:
        """设置电源状态
        
        Args:
            power: 电源状态
            
        Returns:
            bool: 是否设置成功
        """
        return await self.set_state({"is_on": power})
        
    async def set_brightness(self, brightness: int) -> bool:
        """设置亮度
        
        Args:
            brightness: 亮度值
            
        Returns:
            bool: 是否设置成功
        """
        return await self.set_state({"brightness": brightness})
        
    async def set_temperature(self, temperature: int) -> bool:
        """设置温度
        
        Args:
            temperature: 温度值
            
        Returns:
            bool: 是否设置成功
        """
        return await self.set_state({"temperature": temperature})
        
    async def set_mode(self, mode: str) -> bool:
        """设置模式
        
        Args:
            mode: 运行模式
            
        Returns:
            bool: 是否设置成功
        """
        return await self.set_state({"mode": mode})
        
    async def set_position(self, position: int) -> bool:
        """设置位置
        
        Args:
            position: 位置值
            
        Returns:
            bool: 是否设置成功
        """
        return await self.set_state({"position": position})
        
    def _on_state_change(self, change: StateChange) -> None:
        """状态变更回调
        
        Args:
            change: 状态变更
        """
        self.logger.info(
            f"设备 {self.name} 状态变更: "
            f"{change.type.value} 从 {change.old_value} 变为 {change.new_value}"
        )

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