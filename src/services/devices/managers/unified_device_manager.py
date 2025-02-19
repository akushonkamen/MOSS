"""统一设备管理器

提供统一的设备管理和控制接口。
"""
import logging
from typing import Dict, Any, Optional, List, Set
import asyncio
from datetime import datetime
from ..base.device_base import BaseDevice, DeviceError, DeviceStatus
from ..state.state_manager import StateManager
from ..device_registry_server import DeviceInfo
from services.events.event_bus import event_bus, EventType
from services.devices.validators import DeviceValidator, ValidationError as DeviceValidationError

logger = logging.getLogger(__name__)

class UnifiedDeviceManager:
    """统一设备管理器"""
    
    def __init__(self):
        """初始化设备管理器"""
        self._devices: Dict[str, DeviceInfo] = {}
        self._validator = DeviceValidator()
        self._state_manager = StateManager()
        self._lock = asyncio.Lock()
        self._metrics: Dict[str, Dict[str, Any]] = {}
        
        # 订阅设备相关事件
        event_bus.subscribe(EventType.DEVICE, self._on_device_discovered, "discovered")
        event_bus.subscribe(EventType.DEVICE, self._on_device_state_changed, "state_changed")
        
    async def initialize(self) -> None:
        """初始化管理器"""
        logger.info("正在初始化设备管理器...")
        
        await self._state_manager.initialize()
        logger.info("设备管理器初始化完成")
        
    async def stop(self) -> None:
        """停止管理器"""
        logger.info("正在停止设备管理器...")
        await self._state_manager.stop()
        logger.info("设备管理器已停止")
        
    async def register_device(self, device_info: Dict[str, Any]) -> bool:
        """注册新设备
        
        Args:
            device_info: 设备信息
            
        Returns:
            bool: 注册是否成功
        """
        try:
            logger.info(f"开始注册设备: {device_info.get('name', 'Unknown')}")
            
            # 验证设备信息
            if not self._validate_device_info(device_info):
                logger.error(f"设备信息验证失败: {device_info.get('device_id', 'Unknown')}")
                # 发布设备注册失败事件
                await event_bus.publish(
                    EventType.DEVICE,
                    "device_registration_failed",
                    {
                        "device_id": device_info.get("device_id"),
                        "reason": "设备信息验证失败",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return False
                
            device_id = device_info["device_id"]
            
            # 检查设备是否已存在
            if device_id in self._devices:
                logger.info(f"设备已存在，更新信息: {device_id}")
                self._devices[device_id].update(device_info)
            else:
                logger.info(f"注册新设备: {device_id}")
                self._devices[device_id] = device_info
                
            # 初始化设备状态
            await self._state_manager.initialize_device_state(device_id)
            
            # 发布设备注册成功事件
            await event_bus.publish(
                EventType.DEVICE,
                "device_registered",
                {
                    "device_id": device_id,
                    "name": device_info.get("name"),
                    "type": device_info.get("device_type"),
                    "capabilities": device_info.get("capabilities", []),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"设备注册成功: {device_info.get('name')} ({device_id})")
            
            # 刷新设备状态
            await self.refresh_device_status(device_id)
            
            return True
            
        except Exception as e:
            logger.error(f"设备注册失败: {str(e)}")
            # 发布设备注册失败事件
            await event_bus.publish(
                EventType.DEVICE,
                "device_registration_failed",
                {
                    "device_id": device_info.get("device_id"),
                    "reason": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            return False
        
    async def unregister_device(self, device_id: str) -> None:
        """注销设备
        
        Args:
            device_id: 设备ID
        """
        if device_id in self._devices:
            del self._devices[device_id]
            logger.info(f"Device unregistered: {device_id}")
            
    async def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[DeviceInfo]: 设备信息对象,不存在时返回None
        """
        return self._devices.get(device_id)
        
    def get_all_devices(self) -> List[DeviceInfo]:
        """获取所有设备
        
        Returns:
            List[DeviceInfo]: 设备列表
        """
        return list(self._devices.values())
        
    async def _on_device_discovered(self, event: Any) -> None:
        """处理设备发现事件"""
        try:
            device_info = event.data
            await self.register_device(device_info)
        except Exception as e:
            logger.error(f"Failed to handle device discovered event: {e}")
            
    async def _on_device_state_changed(self, event: Any) -> None:
        """处理设备状态变更事件"""
        try:
            device_id = event.data["device_id"]
            new_status = event.data["status"]
            
            device = self._devices.get(device_id)
            if device:
                device.status = new_status
                device.last_seen = datetime.now()
                logger.info(f"Device {device_id} status updated to {new_status}")
        except Exception as e:
            logger.error(f"Failed to handle device state changed event: {e}")
            
    def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        """获取设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[DeviceStatus]: 设备状态,不存在时返回None
        """
        device = self._devices.get(device_id)
        return device.status if device else None

# 创建全局设备管理器实例
unified_device_manager = UnifiedDeviceManager()