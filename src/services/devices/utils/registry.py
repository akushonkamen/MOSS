from typing import Dict, List, Optional, Callable, Any
import asyncio
import logging
from datetime import datetime
from .models import (
    DeviceInfo, DeviceGroup, DeviceStatusReport, 
    DeviceRegistrationValidation, DeviceMetadata
)

logger = logging.getLogger(__name__)

class DeviceRegistry:
    """设备注册管理器"""
    
    def __init__(self):
        """初始化设备注册管理器"""
        self._devices: Dict[str, DeviceInfo] = {}
        self._groups: Dict[str, DeviceGroup] = {}
        self._status_subscribers: Dict[str, List[Callable]] = {}
        self._group_subscribers: List[Callable] = []
        
    async def register_device(self, registration: DeviceRegistrationValidation) -> DeviceInfo:
        """注册设备
        
        Args:
            registration: 设备注册信息
            
        Returns:
            DeviceInfo: 设备信息
            
        Raises:
            ValueError: 设备ID已存在
        """
        if registration.device_id in self._devices:
            raise ValueError(f"设备ID已存在: {registration.device_id}")
            
        # 创建设备信息
        device_info = DeviceInfo(
            id=registration.device_id,
            name=registration.name,
            type=registration.type,
            metadata=registration.metadata,
            parameters={},
            status=DeviceStatusReport(
                online=True,
                parameters={}
            )
        )
        
        # 保存设备信息
        self._devices[registration.device_id] = device_info
        logger.info(f"设备注册成功: {registration.device_id} ({registration.name})")
        
        # 通知订阅者
        await self._notify_status_update(registration.device_id)
        
        return device_info
        
    async def unregister_device(self, device_id: str) -> None:
        """注销设备
        
        Args:
            device_id: 设备ID
            
        Raises:
            KeyError: 设备不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"设备不存在: {device_id}")
            
        # 从分组中移除
        for group in self._groups.values():
            if device_id in group.devices:
                group.devices.remove(device_id)
                await self._notify_group_update(group.group_id)
                
        # 删除设备信息
        del self._devices[device_id]
        logger.info(f"设备注销成功: {device_id}")
        
        # 通知订阅者
        await self._notify_status_update(device_id)
        
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[DeviceInfo]: 设备信息
        """
        return self._devices.get(device_id)
        
    def list_devices(self, group_id: Optional[str] = None) -> List[DeviceInfo]:
        """获取设备列表
        
        Args:
            group_id: 分组ID，如果指定则只返回该分组下的设备
            
        Returns:
            List[DeviceInfo]: 设备列表
        """
        if group_id:
            group = self._groups.get(group_id)
            if not group:
                return []
            return [
                self._devices[device_id]
                for device_id in group.devices
                if device_id in self._devices
            ]
        return list(self._devices.values())
        
    async def create_group(self, group: DeviceGroup) -> None:
        """创建设备分组
        
        Args:
            group: 分组信息
            
        Raises:
            ValueError: 分组ID已存在
        """
        if group.group_id in self._groups:
            raise ValueError(f"分组ID已存在: {group.group_id}")
            
        self._groups[group.group_id] = group
        logger.info(f"创建分组成功: {group.group_id} ({group.name})")
        
        # 通知订阅者
        await self._notify_group_update(group.group_id)
        
    async def delete_group(self, group_id: str) -> None:
        """删除设备分组
        
        Args:
            group_id: 分组ID
            
        Raises:
            KeyError: 分组不存在
        """
        if group_id not in self._groups:
            raise KeyError(f"分组不存在: {group_id}")
            
        del self._groups[group_id]
        logger.info(f"删除分组成功: {group_id}")
        
        # 更新设备的分组信息
        for device in self._devices.values():
            if device.group_id == group_id:
                device.group_id = None
                
        # 通知订阅者
        await self._notify_group_update(group_id)
        
    async def add_device_to_group(self, device_id: str, group_id: str) -> None:
        """添加设备到分组
        
        Args:
            device_id: 设备ID
            group_id: 分组ID
            
        Raises:
            KeyError: 设备或分组不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"设备不存在: {device_id}")
        if group_id not in self._groups:
            raise KeyError(f"分组不存在: {group_id}")
            
        group = self._groups[group_id]
        if device_id not in group.devices:
            group.devices.append(device_id)
            self._devices[device_id].group_id = group_id
            logger.info(f"设备 {device_id} 已添加到分组 {group_id}")
            
            # 通知订阅者
            await self._notify_group_update(group_id)
            
    async def remove_device_from_group(self, device_id: str, group_id: str) -> None:
        """从分组中移除设备
        
        Args:
            device_id: 设备ID
            group_id: 分组ID
            
        Raises:
            KeyError: 设备或分组不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"设备不存在: {device_id}")
        if group_id not in self._groups:
            raise KeyError(f"分组不存在: {group_id}")
            
        group = self._groups[group_id]
        if device_id in group.devices:
            group.devices.remove(device_id)
            self._devices[device_id].group_id = None
            logger.info(f"设备 {device_id} 已从分组 {group_id} 移除")
            
            # 通知订阅者
            await self._notify_group_update(group_id)
            
    async def update_device_status(
        self,
        device_id: str,
        status: DeviceStatusReport
    ) -> None:
        """更新设备状态
        
        Args:
            device_id: 设备ID
            status: 设备状态
            
        Raises:
            KeyError: 设备不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"设备不存在: {device_id}")
            
        device = self._devices[device_id]
        device.status = status
        logger.debug(f"设备 {device_id} 状态已更新")
        
        # 通知订阅者
        await self._notify_status_update(device_id)
        
    def subscribe_status(
        self,
        callback: Callable[[str, DeviceStatusReport], None],
        device_id: Optional[str] = None
    ) -> None:
        """订阅设备状态更新
        
        Args:
            callback: 回调函数
            device_id: 设备ID，如果不指定则订阅所有设备
        """
        if device_id:
            if device_id not in self._status_subscribers:
                self._status_subscribers[device_id] = []
            self._status_subscribers[device_id].append(callback)
        else:
            if '*' not in self._status_subscribers:
                self._status_subscribers['*'] = []
            self._status_subscribers['*'].append(callback)
            
    def unsubscribe_status(
        self,
        callback: Callable[[str, DeviceStatusReport], None],
        device_id: Optional[str] = None
    ) -> None:
        """取消订阅设备状态更新
        
        Args:
            callback: 回调函数
            device_id: 设备ID，如果不指定则取消订阅所有设备
        """
        if device_id:
            if device_id in self._status_subscribers:
                try:
                    self._status_subscribers[device_id].remove(callback)
                except ValueError:
                    # 回调函数不存在，忽略错误
                    pass
        else:
            if '*' in self._status_subscribers:
                try:
                    self._status_subscribers['*'].remove(callback)
                except ValueError:
                    # 回调函数不存在，忽略错误
                    pass
                
    def subscribe_group(
        self,
        callback: Callable[[str, DeviceGroup], None]
    ) -> None:
        """订阅分组更新
        
        Args:
            callback: 回调函数
        """
        self._group_subscribers.append(callback)
        
    def unsubscribe_group(
        self,
        callback: Callable[[str, DeviceGroup], None]
    ) -> None:
        """取消订阅分组更新
        
        Args:
            callback: 回调函数
        """
        self._group_subscribers.remove(callback)
        
    async def _notify_status_update(self, device_id: str) -> None:
        """通知设备状态更新
        
        Args:
            device_id: 设备ID
        """
        device = self._devices.get(device_id)
        if not device or not device.status:
            return
            
        # 通知设备特定的订阅者
        if device_id in self._status_subscribers:
            for callback in self._status_subscribers[device_id]:
                try:
                    await asyncio.create_task(callback(device_id, device.status))
                except Exception as e:
                    logger.error(f"状态更新回调执行失败: {str(e)}")
                    
        # 通知全局订阅者
        if '*' in self._status_subscribers:
            for callback in self._status_subscribers['*']:
                try:
                    await asyncio.create_task(callback(device_id, device.status))
                except Exception as e:
                    logger.error(f"状态更新回调执行失败: {str(e)}")
                    
    async def _notify_group_update(self, group_id: str) -> None:
        """通知分组更新
        
        Args:
            group_id: 分组ID
        """
        group = self._groups.get(group_id)
        if not group:
            return
            
        for callback in self._group_subscribers:
            try:
                await asyncio.create_task(callback(group_id, group))
            except Exception as e:
                logger.error(f"分组更新回调执行失败: {str(e)}")

# 全局设备注册管理器实例
registry = DeviceRegistry() 