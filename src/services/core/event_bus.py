"""事件总线

提供系统内部的事件发布/订阅机制。
"""
import asyncio
import logging
from typing import Dict, List, Any, Callable, Awaitable, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Event:
    """事件数据类"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.now()
    source: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id
        }

class EventBus:
    """事件总线"""
    
    def __init__(self):
        """初始化事件总线"""
        self.logger = logging.getLogger("EventBus")
        self._subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
        self._lock = asyncio.Lock()
        
    async def publish(self, event: Event) -> None:
        """发布事件
        
        Args:
            event: 事件对象
        """
        try:
            self.logger.debug(f"发布事件: {event.type}")
            
            # 获取订阅者
            subscribers = self._subscribers.get(event.type, [])
            if not subscribers:
                return
                
            # 通知所有订阅者
            tasks = []
            for subscriber in subscribers:
                task = asyncio.create_task(self._notify_subscriber(subscriber, event))
                tasks.append(task)
                
            # 等待所有通知完成
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"发布事件失败: {str(e)}")
            
    async def subscribe(self, event_type: str, callback: Callable[[Event], Awaitable[None]]) -> None:
        """订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        try:
            async with self._lock:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                self._subscribers[event_type].append(callback)
                
            self.logger.debug(f"订阅事件: {event_type}")
            
        except Exception as e:
            self.logger.error(f"订阅事件失败: {str(e)}")
            
    async def unsubscribe(self, event_type: str, callback: Callable[[Event], Awaitable[None]]) -> None:
        """取消订阅
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        try:
            async with self._lock:
                if event_type in self._subscribers:
                    self._subscribers[event_type].remove(callback)
                    if not self._subscribers[event_type]:
                        del self._subscribers[event_type]
                        
            self.logger.debug(f"取消订阅: {event_type}")
            
        except Exception as e:
            self.logger.error(f"取消订阅失败: {str(e)}")
            
    async def _notify_subscriber(self, subscriber: Callable[[Event], Awaitable[None]], event: Event) -> None:
        """通知订阅者
        
        Args:
            subscriber: 订阅者回调函数
            event: 事件对象
        """
        try:
            await subscriber(event)
        except Exception as e:
            self.logger.error(f"通知订阅者失败: {str(e)}")

# 创建全局事件总线实例
event_bus = EventBus() 