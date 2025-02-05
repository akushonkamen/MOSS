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

@dataclass
class StateTransition:
    """状态转换定义"""
    from_state: Dict[str, Any]
    to_state: Dict[str, Any]
    conditions: List[Callable[[Dict[str, Any], Dict[str, Any]], bool]]
    priority: int = 0

class StateValidator(BaseModel):
    """状态验证器基类"""
    device_type: str
    rules: Dict[str, Any]

    def validate(self, state: Dict[str, Any]) -> bool:
        """验证状态
        
        Args:
            state: 要验证的状态
            
        Returns:
            bool: 验证是否通过
            
        Raises:
            StateValidationError: 验证失败时抛出
        """
        raise NotImplementedError

class DeviceStateManager:
    """设备状态管理器"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost",
        max_history: int = 100,
        state_ttl: int = 3600
    ):
        """初始化设备状态管理器
        
        Args:
            redis_url: Redis连接URL
            max_history: 最大历史记录数
            state_ttl: 状态过期时间（秒）
        """
        self.redis = Redis.from_url(redis_url)
        self.max_history = max_history
        self.state_ttl = state_ttl
        self._validators: Dict[str, StateValidator] = {}
        self._transitions: Dict[str, List[StateTransition]] = {}
        self._event_callbacks: List[EventCallback] = []
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.redis.close()
        await asyncio.sleep(0.1)  # 等待连接完全关闭
        
    async def get_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Dict[str, Any]]: 设备状态，如果不存在则返回None
        """
        try:
            if not self.redis.connection:
                logger.error("Redis连接已关闭")
                return None
                
            state_json = await self.redis.get(f"device:{device_id}:state")
            if not state_json:
                return None
            return json.loads(state_json)
        except Exception as e:
            logger.error(f"获取设备状态失败: {str(e)}")
            return None
            
    async def set_state(
        self,
        device_id: str,
        device_type: str,
        state: Dict[str, Any],
        validate: bool = True
    ) -> bool:
        """设置设备状态
        
        Args:
            device_id: 设备ID
            device_type: 设备类型
            state: 新状态
            validate: 是否进行状态验证
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 检查Redis连接
            if not self.redis.connection:
                logger.error("Redis连接已关闭")
                return False
                
            # 1. 状态验证
            if validate and device_type in self._validators:
                validator = self._validators[device_type]
                try:
                    if not validator.validate(state):
                        await self._notify(
                            device_id,
                            DeviceStateEvent.VALIDATION_FAILED,
                            {"state": state}
                        )
                        raise StateValidationError(f"状态验证失败: {device_id}")
                except StateValidationError as e:
                    await self._notify(
                        device_id,
                        DeviceStateEvent.VALIDATION_FAILED,
                        {"state": state}
                    )
                    raise e
                await self._notify(
                    device_id,
                    DeviceStateEvent.VALIDATED,
                    {"state": state}
                )
                
            # 2. 获取当前状态
            current_state = await self.get_state(device_id)
            
            # 3. 状态转换检查
            if current_state and device_type in self._transitions:
                if not await self._check_transition(
                    device_type,
                    current_state,
                    state
                ):
                    await self._notify(
                        device_id,
                        DeviceStateEvent.TRANSITION_FAILED,
                        {
                            "from_state": current_state,
                            "to_state": state
                        }
                    )
                    raise StateTransitionError(
                        f"状态转换失败: {device_id}"
                    )
                    
            # 4. 保存状态
            state_json = json.dumps(state)
            try:
                pipe = self.redis.pipeline()
                # 设置状态
                pipe.set(
                    f"device:{device_id}:state",
                    state_json,
                    ex=self.state_ttl
                )
                # 添加历史记录
                history_entry = json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "state": state
                })
                pipe.lpush(f"device:{device_id}:history", history_entry)
                pipe.ltrim(f"device:{device_id}:history", 0, self.max_history - 1)
                await pipe.execute()
            except Exception as e:
                logger.error(f"Redis操作失败: {str(e)}")
                return False
            
            # 5. 通知订阅者
            try:
                await self._notify(
                    device_id,
                    DeviceStateEvent.UPDATED,
                    {"state": state}
                )
                await self._notify(
                    device_id,
                    DeviceStateEvent.HISTORY_ADDED,
                    {
                        "timestamp": datetime.now().isoformat(),
                        "state": state
                    }
                )
            except Exception as e:
                logger.error(f"通知订阅者失败: {str(e)}")
                # 即使通知失败，状态设置仍然成功
                pass
            
            return True
            
        except (StateValidationError, StateTransitionError) as e:
            logger.error(f"设置设备状态失败: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"设置设备状态失败: {str(e)}")
            return False
            
    async def get_history(
        self,
        device_id: str,
        start: int = 0,
        end: int = -1
    ) -> List[Dict[str, Any]]:
        """获取设备状态历史
        
        Args:
            device_id: 设备ID
            start: 起始位置
            end: 结束位置
            
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        try:
            history = await self.redis.lrange(
                f"device:{device_id}:history",
                start,
                end
            )
            return [json.loads(entry) for entry in history]
        except Exception as e:
            logger.error(f"获取设备状态历史失败: {str(e)}")
            return []
            
    def register_validator(
        self,
        device_type: str,
        validator: StateValidator
    ) -> None:
        """注册状态验证器
        
        Args:
            device_type: 设备类型
            validator: 验证器实例
        """
        self._validators[device_type] = validator
        
    def register_transition(
        self,
        device_type: str,
        transition: StateTransition
    ) -> None:
        """注册状态转换规则
        
        Args:
            device_type: 设备类型
            transition: 转换规则
        """
        if device_type not in self._transitions:
            self._transitions[device_type] = []
        self._transitions[device_type].append(transition)
        # 按优先级排序
        self._transitions[device_type].sort(
            key=lambda x: x.priority,
            reverse=True
        )
        
    def subscribe(
        self,
        device_id: str,
        callback: Callable[[str, DeviceStateEvent, Dict[str, Any]], None]
    ) -> None:
        """订阅设备状态事件
        
        Args:
            device_id: 设备ID
            callback: 回调函数
        """
        if device_id not in self._event_callbacks:
            self._event_callbacks.append((device_id, callback))
        
    def unsubscribe(
        self,
        device_id: str,
        callback: Callable[[str, DeviceStateEvent, Dict[str, Any]], None]
    ) -> None:
        """取消订阅设备状态事件
        
        Args:
            device_id: 设备ID
            callback: 回调函数
        """
        if device_id in self._event_callbacks:
            try:
                self._event_callbacks.remove((device_id, callback))
            except ValueError:
                pass
                
    async def _check_transition(
        self,
        device_type: str,
        from_state: Dict[str, Any],
        to_state: Dict[str, Any]
    ) -> bool:
        """检查状态转换是否合法
        
        Args:
            device_type: 设备类型
            from_state: 当前状态
            to_state: 目标状态
            
        Returns:
            bool: 转换是否合法
        """
        if device_type not in self._transitions:
            return True
            
        for transition in self._transitions[device_type]:
            # 检查状态匹配
            if not all(
                from_state.get(k) == v
                for k, v in transition.from_state.items()
            ):
                continue
                
            if not all(
                to_state.get(k) == v
                for k, v in transition.to_state.items()
            ):
                continue
                
            # 检查转换条件
            if all(
                condition(from_state, to_state)
                for condition in transition.conditions
            ):
                return True
                
        return False
        
    async def _notify(
        self,
        device_id: str,
        event: DeviceStateEvent,
        data: Dict[str, Any]
    ) -> None:
        """通知订阅者
        
        Args:
            device_id: 设备ID
            event: 事件类型
            data: 事件数据
        """
        if device_id not in self._event_callbacks:
            return
            
        for callback in self._event_callbacks:
            try:
                await asyncio.create_task(
                    callback(device_id, event, data)
                )
            except Exception as e:
                logger.error(f"状态事件回调执行失败: {str(e)}")

# 全局状态管理器实例
state_manager = DeviceStateManager() 