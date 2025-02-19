"""事件总线实现

提供事件发布和订阅功能。
"""
import logging
import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime

logger = logging.getLogger(__name__)

class EventType(Enum):
    """事件类型"""
    SYSTEM = auto()
    DEVICE = auto()
    AGENT = auto()
    ERROR = auto()

@dataclass
class Event:
    """事件数据类"""
    type: str
    name: str
    source: str
    data: Dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class EventBus:
    """事件总线"""
    
    def __init__(self):
        """初始化事件总线"""
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        
    async def publish(self, event_type: EventType, event_name: str, data: Dict[str, Any]) -> None:
        """发布事件
        
        Args:
            event_type: 事件类型
            event_name: 事件名称
            data: 事件数据
        """
        event = Event(
            type=event_type,
            name=event_name,
            source=data.get("source", "unknown"),
            data=data
        )
        
        # 通知所有订阅者
        subscribers = self._subscribers.get(event_type, [])
        event_subscribers = self._event_handlers.get(event_name, [])
        
        tasks = []
        for subscriber in subscribers + event_subscribers:
            try:
                task = asyncio.create_task(subscriber(event))
                tasks.append(task)
            except Exception as e:
                logger.error(f"调用事件处理器失败: {e}")
                
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    def subscribe(self, event_type: EventType, callback: Callable,
                 event_name: Optional[str] = None) -> None:
        """订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            event_name: 事件名称（可选）
        """
        if event_name:
            if event_name not in self._event_handlers:
                self._event_handlers[event_name] = []
            self._event_handlers[event_name].append(callback)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
            
    def unsubscribe(self, event_type: EventType, callback: Callable,
                    event_name: Optional[str] = None) -> None:
        """取消订阅
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            event_name: 事件名称（可选）
        """
        if event_name and event_name in self._event_handlers:
            self._event_handlers[event_name].remove(callback)
        elif event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

# 创建全局事件总线实例
event_bus = EventBus() 