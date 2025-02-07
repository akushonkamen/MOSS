"""设备状态管理模块

提供设备状态的存储、验证、转换和历史记录功能。
使用 Redis 作为后端存储，支持状态持久化和历史记录。
"""

from typing import Dict, Any, Optional, Callable, List, Type
from datetime import datetime
import json
import asyncio
import logging
from redis.asyncio import Redis
from pydantic import BaseModel, ValidationError
from enum import Enum
from dataclasses import dataclass
from .models import DeviceStatusReport, DeviceMetrics

logger = logging.getLogger(__name__)

class StateValidationError(Exception):
    """状态验证错误"""
    pass

class StateTransitionError(Exception):
    """状态转换错误"""
    pass

class DeviceStateEvent(str, Enum):
    """设备状态事件类型"""
    UPDATED = "updated"
    VALIDATED = "validated"
    TRANSITION_FAILED = "transition_failed"
    VALIDATION_FAILED = "validation_failed"
    HISTORY_ADDED = "history_added"

class StateChangeType(Enum):
    """状态变更类型"""
    POWER = "power"
    BRIGHTNESS = "brightness"
    TEMPERATURE = "temperature"
    MODE = "mode"
    POSITION = "position"
    CUSTOM = "custom"

@dataclass
class StateChange:
    """状态变更"""
    type: StateChangeType
    device_id: str
    old_value: Any
    new_value: Any
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class StateTransition:
    """状态转换定义"""
    from_state: Dict[str, Any]
    to_state: Dict[str, Any]
    conditions: List[Callable[[Dict[str, Any], Dict[str, Any]], bool]]
    priority: int = 0

class StateValidators:
    """状态验证器"""
    
    @staticmethod
    def validate_power(value: Any) -> bool:
        """验证电源状态
        
        Args:
            value: 要验证的值
            
        Returns:
            bool: 是否有效
        """
        return isinstance(value, bool)
        
    @staticmethod
    def validate_brightness(value: Any) -> bool:
        """验证亮度值
        
        Args:
            value: 要验证的值
            
        Returns:
            bool: 是否有效
        """
        try:
            brightness = int(value)
            return 0 <= brightness <= 100
        except (TypeError, ValueError):
            return False
            
    @staticmethod
    def validate_temperature(value: Any) -> bool:
        """验证温度值
        
        Args:
            value: 要验证的值
            
        Returns:
            bool: 是否有效
        """
        try:
            temp = int(value)
            return 16 <= temp <= 30
        except (TypeError, ValueError):
            return False
            
    @staticmethod
    def validate_mode(value: Any) -> bool:
        """验证模式值
        
        Args:
            value: 要验证的值
            
        Returns:
            bool: 是否有效
        """
        return value in ["auto", "cool", "heat", "dry", "fan"]
        
    @staticmethod
    def validate_position(value: Any) -> bool:
        """验证位置值
        
        Args:
            value: 要验证的值
            
        Returns:
            bool: 是否有效
        """
        try:
            pos = int(value)
            return 0 <= pos <= 100
        except (TypeError, ValueError):
            return False

class DeviceStateManager:
    """设备状态管理器"""
    
    def __init__(self):
        """初始化状态管理器"""
        self._states: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Callable[[Any], bool]] = {
            "is_on": StateValidators.validate_power,
            "brightness": StateValidators.validate_brightness,
            "temperature": StateValidators.validate_temperature,
            "mode": StateValidators.validate_mode,
            "position": StateValidators.validate_position
        }
        self._subscribers: Dict[str, List[Callable[[StateChange], None]]] = {}
        self._lock = asyncio.Lock()
        
    async def initialize_state(self, device_id: str, initial_state: Dict[str, Any]) -> None:
        """初始化设备状态
        
        Args:
            device_id: 设备ID
            initial_state: 初始状态
        """
        async with self._lock:
            self._states[device_id] = initial_state.copy()
            
    async def get_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Dict[str, Any]]: 设备状态
        """
        return self._states.get(device_id, {}).copy()
        
    async def update_state(
        self,
        device_id: str,
        updates: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """更新设备状态
        
        Args:
            device_id: 设备ID
            updates: 状态更新
            metadata: 元数据
            
        Returns:
            bool: 是否更新成功
        """
        if device_id not in self._states:
            logger.error(f"设备 {device_id} 未初始化状态")
            return False
            
        try:
            async with self._lock:
                current_state = self._states[device_id]
                
                # 验证并应用更新
                for key, new_value in updates.items():
                    if key in self._validators:
                        if not self._validators[key](new_value):
                            raise ValueError(f"无效的{key}值: {new_value}")
                            
                        old_value = current_state.get(key)
                        if old_value != new_value:
                            current_state[key] = new_value
                            
                            # 创建状态变更事件
                            change = StateChange(
                                type=StateChangeType[key.upper()],
                                device_id=device_id,
                                old_value=old_value,
                                new_value=new_value,
                                timestamp=asyncio.get_event_loop().time(),
                                metadata=metadata
                            )
                            
                            # 通知订阅者
                            await self._notify_subscribers(device_id, change)
                
                return True
                
        except Exception as e:
            logger.error(f"更新设备 {device_id} 状态失败: {str(e)}")
            return False
            
    def subscribe(
        self,
        device_id: str,
        callback: Callable[[StateChange], None]
    ) -> None:
        """订阅状态变更
        
        Args:
            device_id: 设备ID
            callback: 回调函数
        """
        if device_id not in self._subscribers:
            self._subscribers[device_id] = []
        self._subscribers[device_id].append(callback)
        
    def unsubscribe(
        self,
        device_id: str,
        callback: Callable[[StateChange], None]
    ) -> None:
        """取消订阅状态变更
        
        Args:
            device_id: 设备ID
            callback: 回调函数
        """
        if device_id in self._subscribers:
            self._subscribers[device_id].remove(callback)
            
    async def _notify_subscribers(
        self,
        device_id: str,
        change: StateChange
    ) -> None:
        """通知订阅者
        
        Args:
            device_id: 设备ID
            change: 状态变更
        """
        if device_id in self._subscribers:
            for callback in self._subscribers[device_id]:
                try:
                    callback(change)
                except Exception as e:
                    logger.error(f"调用状态变更回调失败: {str(e)}")

# 全局状态管理器实例
state_manager = DeviceStateManager() 