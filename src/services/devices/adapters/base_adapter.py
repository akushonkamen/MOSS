"""设备适配器基类

为不同类型的设备提供统一的接口适配层。
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

class DeviceAdapter(ABC):
    """设备适配器基类"""
    
    def __init__(self, device_id: str, device_info: Dict[str, Any]):
        """初始化适配器
        
        Args:
            device_id: 设备ID
            device_info: 设备信息
        """
        self.device_id = device_id
        self.device_info = device_info
        self.logger = logging.getLogger(f"adapter.{device_id}")
        self._connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """连接到设备"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """断开设备连接"""
        pass
        
    @abstractmethod
    async def get_state(self) -> Dict[str, Any]:
        """获取设备状态"""
        pass
        
    @abstractmethod
    async def set_state(self, state: Dict[str, Any]) -> bool:
        """设置设备状态"""
        pass
        
    @abstractmethod
    async def execute_command(self, command: str, params: Dict[str, Any]) -> Any:
        """执行设备命令"""
        pass
        
    @abstractmethod
    async def get_capabilities(self) -> List[str]:
        """获取设备能力列表"""
        pass
        
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected
        
    async def validate_command(self, command: str, params: Dict[str, Any]) -> bool:
        """验证命令参数
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            bool: 是否有效
        """
        capabilities = await self.get_capabilities()
        if command not in capabilities:
            self.logger.warning(f"设备不支持命令: {command}")
            return False
        return True
        
    async def _ensure_connected(self) -> bool:
        """确保设备已连接
        
        Returns:
            bool: 是否已连接
        """
        if not self.is_connected:
            try:
                return await self.connect()
            except Exception as e:
                self.logger.error(f"连接设备失败: {e}")
                return False
        return True 