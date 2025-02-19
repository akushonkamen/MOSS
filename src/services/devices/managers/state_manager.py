"""状态同步管理器

负责设备状态的同步和持久化。
"""
import asyncio
import logging
from typing import Dict, Set, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import json
import aiofiles
import os

logger = logging.getLogger(__name__)

@dataclass
class StateChange:
    """状态变更记录"""
    device_id: str
    old_state: Dict[str, Any]
    new_state: Dict[str, Any]
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

class StateManager:
    """状态管理器"""
    
    def __init__(self, state_dir: str = "data/device_states"):
        self._states: Dict[str, Dict[str, Any]] = {}
        self._subscribers: Dict[str, Set[Callable[[StateChange], None]]] = {}
        self._lock = asyncio.Lock()
        self._state_dir = state_dir
        self._dirty_states: Set[str] = set()
        self._save_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """初始化状态管理器"""
        # 创建状态存储目录
        os.makedirs(self._state_dir, exist_ok=True)
        
        # 加载持久化的状态
        await self._load_states()
        
        # 启动状态保存任务
        self._save_task = asyncio.create_task(self._periodic_save())
        
        logger.info("State manager initialized")
        
    async def shutdown(self) -> None:
        """关闭状态管理器"""
        if self._save_task:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
            
        # 保存所有未保存的状态
        await self._save_states()
        logger.info("State manager shut down")
        
    async def get_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Dict[str, Any]]: 设备状态
        """
        return self._states.get(device_id)
        
    async def update_state(self,
        device_id: str,
        new_state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """更新设备状态
        
        Args:
            device_id: 设备ID
            new_state: 新状态
            metadata: 元数据
        """
        async with self._lock:
            old_state = self._states.get(device_id, {})
            self._states[device_id] = new_state
            self._dirty_states.add(device_id)
            
            # 创建状态变更记录
            change = StateChange(
                device_id=device_id,
                old_state=old_state,
                new_state=new_state,
                timestamp=asyncio.get_event_loop().time(),
                metadata=metadata
            )
            
            # 通知订阅者
            await self._notify_subscribers(device_id, change)
            
        logger.debug(f"State updated for device {device_id}")
        
    def subscribe(self,
        device_id: str,
        callback: Callable[[StateChange], None]
    ) -> None:
        """订阅状态变更
        
        Args:
            device_id: 设备ID
            callback: 回调函数
        """
        if device_id not in self._subscribers:
            self._subscribers[device_id] = set()
        self._subscribers[device_id].add(callback)
        
    def unsubscribe(self,
        device_id: str,
        callback: Callable[[StateChange], None]
    ) -> None:
        """取消订阅
        
        Args:
            device_id: 设备ID
            callback: 回调函数
        """
        if device_id in self._subscribers:
            self._subscribers[device_id].discard(callback)
            
    async def _notify_subscribers(self,
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
                    logger.error(f"Error in state change callback: {e}")
                    
    async def _load_states(self) -> None:
        """加载持久化的状态"""
        try:
            for filename in os.listdir(self._state_dir):
                if filename.endswith(".json"):
                    device_id = filename[:-5]  # 移除.json后缀
                    file_path = os.path.join(self._state_dir, filename)
                    
                    async with aiofiles.open(file_path, 'r') as f:
                        content = await f.read()
                        self._states[device_id] = json.loads(content)
                        
            logger.info(f"Loaded states for {len(self._states)} devices")
        except Exception as e:
            logger.error(f"Error loading states: {e}")
            
    async def _save_states(self) -> None:
        """保存设备状态"""
        async with self._lock:
            for device_id in self._dirty_states:
                if device_id in self._states:
                    file_path = os.path.join(
                        self._state_dir,
                        f"{device_id}.json"
                    )
                    try:
                        async with aiofiles.open(file_path, 'w') as f:
                            state_json = json.dumps(
                                self._states[device_id],
                                indent=2
                            )
                            await f.write(state_json)
                    except Exception as e:
                        logger.error(f"Error saving state for {device_id}: {e}")
                        
            self._dirty_states.clear()
            
    async def _periodic_save(self) -> None:
        """定期保存状态"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟保存一次
                await self._save_states()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic save: {e}")
                await asyncio.sleep(5)  # 发生错误时等待短暂时间

# 创建状态管理器实例
state_manager = StateManager() 