from datetime import datetime
from typing import Any, Callable, Dict, List
from collections import defaultdict
import asyncio
import logging
import uuid

class EventType:
    """事件类型定义"""
    DEVICE_DISCOVERED = "device_discovered"
    DEVICE_STATE_CHANGED = "device_state_changed"
    DEVICE_REMOVED = "device_removed"
    SYSTEM = "system"  # 系统事件
    COMMAND = "command"  # 命令事件
    RESPONSE = "response"  # 响应事件
    ERROR = "error"  # 错误事件

class Event:
    """事件类"""
    def __init__(self, type: str, source: str, data: Any = None):
        self.type = type
        self.source = source
        self.data = data
        self.timestamp = datetime.now()

class EventBus:
    """事件总线"""
    def __init__(self):
        self._subscribers = defaultdict(dict)  # type -> {callback_id: callback}
        self._history = []
        self._max_history = 1000
        self.logger = logging.getLogger(__name__)

    async def publish(self, event: Event):
        """发布事件"""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # 获取该事件类型的所有订阅者
        subscribers = self._subscribers.get(event.type, {})
        
        # 执行回调
        for callback_id, callback in subscribers.items():
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                self.logger.error(f"执行回调 {callback_id} 时出错: {str(e)}")

    def subscribe(self, event_type: str, callback: Callable, callback_id: str = None) -> str:
        """订阅事件"""
        if callback_id is None:
            callback_id = str(uuid.uuid4())
        
        self._subscribers[event_type][callback_id] = callback
        return callback_id

    def unsubscribe(self, event_type: str, callback_id: str):
        """取消订阅"""
        if event_type in self._subscribers and callback_id in self._subscribers[event_type]:
            del self._subscribers[event_type][callback_id]
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

    def get_history(self, event_type: str = None, source: str = None) -> List[Event]:
        """获取事件历史"""
        if event_type is None and source is None:
            return self._history
        
        filtered_history = []
        for event in self._history:
            if event_type and event.type != event_type:
                continue
            if source and event.source != source:
                continue
            filtered_history.append(event)
        
        return filtered_history 