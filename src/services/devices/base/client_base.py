"""设备客户端基类

提供与设备通信的基础功能。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
import asyncio
from .device_base import BaseDevice, DeviceStatus, DeviceError
from ..managers.unified_device_manager import unified_device_manager

class DeviceClient(BaseDevice):
    """设备客户端基类"""
    
    def __init__(self, device_id: str, name: str, location: str, port: int):
        """初始化设备客户端
        
        Args:
            device_id: 设备ID
            name: 设备名称
            location: 设备位置
            port: 设备端口
        """
        super().__init__(device_id, name, location)
        self.port = port
        self._state: Dict[str, Any] = {}
        self._is_connected = False
        
    async def initialize(self) -> None:
        """初始化设备客户端"""
        try:
            # 获取初始状态
            self._state = await self.get_initial_state()
            
            # 注册到统一设备管理器
            if await unified_device_manager.register_device(self):
                self.status = DeviceStatus.ONLINE
                self.logger.info(f"设备 {self.name} 初始化完成")
            else:
                raise DeviceError(f"设备 {self.name} 注册失败")
                
        except Exception as e:
            self.status = DeviceStatus.ERROR
            self.logger.error(f"设备 {self.name} 初始化失败: {str(e)}")
            raise DeviceError(f"初始化失败: {str(e)}")
            
    async def get_state(self) -> Dict[str, Any]:
        """获取设备状态"""
        return self._state.copy()
        
    async def set_state(self, state: Dict[str, Any]) -> bool:
        """设置设备状态
        
        Args:
            state: 新的状态
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 验证状态
            await self._validate_state(state)
            
            # 更新状态
            old_state = self._state.copy()
            self._state.update(state)
            
            # 通知状态变更
            await self._notify_state_change(old_state, self._state)
            
            return True
            
        except Exception as e:
            self.logger.error(f"设置设备 {self.name} 状态失败: {str(e)}")
            return False
            
    @abstractmethod
    async def get_initial_state(self) -> Dict[str, Any]:
        """获取初始状态"""
        pass
        
    @abstractmethod
    async def _validate_state(self, state: Dict[str, Any]) -> None:
        """验证状态
        
        Args:
            state: 要验证的状态
            
        Raises:
            DeviceError: 状态无效
        """
        pass
        
    async def _notify_state_change(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> None:
        """通知状态变更
        
        Args:
            old_state: 旧状态
            new_state: 新状态
        """
        # 更新设备状态
        await unified_device_manager.update_device_state(
            self.device_id,
            new_state
        )
        
    async def connect(self) -> bool:
        """连接设备
        
        Returns:
            bool: 是否连接成功
        """
        try:
            if not self._is_connected:
                # 实现具体的连接逻辑
                self._is_connected = True
                self.status = DeviceStatus.ONLINE
                self.logger.info(f"设备 {self.name} 连接成功")
            return True
        except Exception as e:
            self.status = DeviceStatus.ERROR
            self.logger.error(f"设备 {self.name} 连接失败: {str(e)}")
            return False
            
    async def disconnect(self) -> None:
        """断开连接"""
        if self._is_connected:
            # 实现具体的断开逻辑
            self._is_connected = False
            self.status = DeviceStatus.OFFLINE
            self.logger.info(f"设备 {self.name} 已断开连接") 