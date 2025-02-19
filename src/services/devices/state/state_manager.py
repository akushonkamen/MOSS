"""状态管理器

负责管理和持久化设备状态。
"""
import logging
import json
import os
from typing import Dict, Any, Optional, Callable, List
import aiofiles
import asyncio
from pathlib import Path

class StateManager:
    """状态管理器"""
    
    def __init__(self, state_dir: str = "data/device_states"):
        """初始化状态管理器
        
        Args:
            state_dir: 状态文件存储目录
        """
        self.logger = logging.getLogger("StateManager")
        self.state_dir = Path(state_dir)
        self._states: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}
        
    def subscribe(self, device_id: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """订阅设备状态变化
        
        Args:
            device_id: 设备ID
            callback: 回调函数，接收设备ID和新状态
        """
        if device_id not in self._subscribers:
            self._subscribers[device_id] = []
        self._subscribers[device_id].append(callback)
        
    def unsubscribe(self, device_id: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """取消订阅设备状态变化
        
        Args:
            device_id: 设备ID
            callback: 回调函数
        """
        if device_id in self._subscribers:
            if callback in self._subscribers[device_id]:
                self._subscribers[device_id].remove(callback)
            if not self._subscribers[device_id]:
                del self._subscribers[device_id]
        
    async def initialize(self) -> None:
        """初始化管理器"""
        self.logger.info("正在初始化状态管理器...")
        
        # 创建状态目录
        os.makedirs(self.state_dir, exist_ok=True)
        
        # 加载所有设备状态
        await self._load_all_states()
        
        self.logger.info("状态管理器初始化完成")
        
    async def stop(self) -> None:
        """停止管理器"""
        self.logger.info("正在停止状态管理器...")
        
        # 保存所有设备状态
        await self._save_all_states()
        
        self.logger.info("状态管理器已停止")
        
    async def get_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Dict[str, Any]]: 设备状态
        """
        async with self._lock:
            return self._states.get(device_id)
            
    async def set_state(self, device_id: str, state: Dict[str, Any]) -> None:
        """设置设备状态
        
        Args:
            device_id: 设备ID
            state: 新的状态
        """
        async with self._lock:
            self._states[device_id] = state
            await self._save_state(device_id)
            
    async def update_state(self, device_id: str, updates: Dict[str, Any]) -> None:
        """更新设备状态
        
        Args:
            device_id: 设备ID
            updates: 状态更新
        """
        async with self._lock:
            current_state = self._states.get(device_id, {})
            current_state.update(updates)
            self._states[device_id] = current_state
            await self._save_state(device_id)
            
    async def delete_state(self, device_id: str) -> None:
        """删除设备状态
        
        Args:
            device_id: 设备ID
        """
        async with self._lock:
            if device_id in self._states:
                del self._states[device_id]
            
            # 删除状态文件
            state_file = self.state_dir / f"{device_id}.json"
            try:
                if state_file.exists():
                    os.remove(state_file)
            except Exception as e:
                self.logger.error(f"删除状态文件失败: {e}")
                
    async def _load_all_states(self) -> None:
        """加载所有设备状态"""
        try:
            for state_file in self.state_dir.glob("*.json"):
                device_id = state_file.stem
                try:
                    async with aiofiles.open(state_file, mode='r') as f:
                        content = await f.read()
                        self._states[device_id] = json.loads(content)
                except Exception as e:
                    self.logger.error(f"加载设备 {device_id} 状态失败: {e}")
        except Exception as e:
            self.logger.error(f"加载设备状态失败: {e}")
            
    async def _save_all_states(self) -> None:
        """保存所有设备状态"""
        try:
            for device_id in self._states:
                await self._save_state(device_id)
        except Exception as e:
            self.logger.error(f"保存设备状态失败: {e}")
            
    async def _save_state(self, device_id: str) -> None:
        """保存设备状态
        
        Args:
            device_id: 设备ID
        """
        try:
            state_file = self.state_dir / f"{device_id}.json"
            async with aiofiles.open(state_file, mode='w') as f:
                await f.write(json.dumps(self._states[device_id], indent=2))
        except Exception as e:
            self.logger.error(f"保存设备 {device_id} 状态失败: {e}") 