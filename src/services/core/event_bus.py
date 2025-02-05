from typing import Dict, Any, Callable, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
import logging

logger = logging.getLogger(__name__)

class Event(BaseModel):
    """事件模型"""
    event_type: str = Field(..., description="事件类型")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    origin: str = Field(..., description="事件来源")
    time_fired: datetime = Field(default_factory=datetime.now, description="触发时间")

class EventBus:
    """事件总线"""
    
    def __init__(self):
        """初始化事件总线"""
        self._listeners: Dict[str, List[Callable]] = {}
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> Callable:
        """订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
            
        Returns:
            Callable: 取消订阅的函数
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        
        def unsubscribe():
            self._listeners[event_type].remove(callback)
            if not self._listeners[event_type]:
                del self._listeners[event_type]
                
        return unsubscribe
        
    async def fire(self, event: Event) -> None:
        """触发事件
        
        Args:
            event: 事件对象
        """
        await self._queue.put(event)
        
    async def start(self) -> None:
        """启动事件总线"""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._process_events())
        logger.info("事件总线已启动")
        
    async def stop(self) -> None:
        """停止事件总线"""
        if not self._running:
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("事件总线已停止")
        
    async def _process_events(self) -> None:
        """处理事件队列"""
        while self._running:
            try:
                event = await self._queue.get()
                logger.debug(f"处理事件: {event.event_type}")
                
                if event.event_type in self._listeners:
                    for callback in self._listeners[event.event_type]:
                        try:
                            await asyncio.create_task(self._call_listener(callback, event))
                        except Exception as e:
                            logger.error(f"处理事件 {event.event_type} 时出错: {str(e)}")
                            
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"事件处理循环出错: {str(e)}")
                
    async def _call_listener(self, callback: Callable, event: Event) -> None:
        """调用事件监听器
        
        Args:
            callback: 回调函数
            event: 事件对象
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error(f"调用事件监听器时出错: {str(e)}")

# 全局事件总线
bus = EventBus() 