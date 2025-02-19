"""场景管理器实现"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .models.scene import Scene
from .models.trigger import Trigger
from .scene_executor import SceneExecutor
from .scene_validator import SceneValidator

logger = logging.getLogger(__name__)

class SceneManager:
    """场景管理器
    
    负责场景的注册、查询、启用/禁用等管理功能。
    """
    
    def __init__(self):
        """初始化场景管理器"""
        self._scenes: Dict[str, Scene] = {}
        self._executor = SceneExecutor()
        self._validator = SceneValidator()
        self._running = False
        self._event_queue = asyncio.Queue()
        
    async def start(self):
        """启动场景管理器"""
        if self._running:
            return
            
        self._running = True
        asyncio.create_task(self._event_processor())
        logger.info("场景管理器已启动")
        
    async def stop(self):
        """停止场景管理器"""
        if not self._running:
            return
            
        self._running = False
        logger.info("场景管理器已停止")
        
    def register_scene(self, scene: Scene) -> bool:
        """注册场景
        
        Args:
            scene: 场景对象
            
        Returns:
            bool: 是否注册成功
        """
        try:
            # 验证场景
            if not self._validator.validate(scene):
                logger.error(f"场景验证失败: {scene.id}")
                return False
                
            # 注册场景
            self._scenes[scene.id] = scene
            logger.info(f"场景注册成功: {scene.id}")
            return True
        except Exception as e:
            logger.error(f"场景注册失败: {scene.id}, 错误: {str(e)}")
            return False
            
    def unregister_scene(self, scene_id: str) -> bool:
        """注销场景
        
        Args:
            scene_id: 场景ID
            
        Returns:
            bool: 是否注销成功
        """
        try:
            if scene_id not in self._scenes:
                logger.warning(f"场景不存在: {scene_id}")
                return False
                
            del self._scenes[scene_id]
            logger.info(f"场景注销成功: {scene_id}")
            return True
        except Exception as e:
            logger.error(f"场景注销失败: {scene_id}, 错误: {str(e)}")
            return False
            
    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """获取场景
        
        Args:
            scene_id: 场景ID
            
        Returns:
            Optional[Scene]: 场景对象，不存在则返回None
        """
        return self._scenes.get(scene_id)
        
    def list_scenes(self) -> List[Scene]:
        """获取所有场景列表
        
        Returns:
            List[Scene]: 场景列表
        """
        return list(self._scenes.values())
        
    def enable_scene(self, scene_id: str) -> bool:
        """启用场景
        
        Args:
            scene_id: 场景ID
            
        Returns:
            bool: 是否启用成功
        """
        try:
            scene = self.get_scene(scene_id)
            if not scene:
                logger.warning(f"场景不存在: {scene_id}")
                return False
                
            scene.enabled = True
            scene.updated_at = datetime.now()
            logger.info(f"场景已启用: {scene_id}")
            return True
        except Exception as e:
            logger.error(f"启用场景失败: {scene_id}, 错误: {str(e)}")
            return False
            
    def disable_scene(self, scene_id: str) -> bool:
        """禁用场景
        
        Args:
            scene_id: 场景ID
            
        Returns:
            bool: 是否禁用成功
        """
        try:
            scene = self.get_scene(scene_id)
            if not scene:
                logger.warning(f"场景不存在: {scene_id}")
                return False
                
            scene.enabled = False
            scene.updated_at = datetime.now()
            logger.info(f"场景已禁用: {scene_id}")
            return True
        except Exception as e:
            logger.error(f"禁用场景失败: {scene_id}, 错误: {str(e)}")
            return False
            
    async def trigger_event(self, event: Dict[str, Any]):
        """触发事件
        
        Args:
            event: 事件数据
        """
        await self._event_queue.put(event)
        
    async def _event_processor(self):
        """事件处理循环"""
        while self._running:
            try:
                # 获取事件
                event = await self._event_queue.get()
                
                # 处理事件
                await self._process_event(event)
                
                # 标记事件处理完成
                self._event_queue.task_done()
            except Exception as e:
                logger.error(f"事件处理失败: {str(e)}")
                
    async def _process_event(self, event: Dict[str, Any]):
        """处理事件
        
        Args:
            event: 事件数据
        """
        try:
            # 遍历所有启用的场景
            for scene in self._scenes.values():
                if not scene.enabled:
                    continue
                    
                # 检查是否有匹配的触发器
                for trigger in scene.triggers:
                    if trigger.matches_event(event):
                        # 执行场景
                        await self._executor.execute(scene, event)
                        break
        except Exception as e:
            logger.error(f"事件处理失败: {str(e)}")
            
    def __repr__(self) -> str:
        """返回场景管理器的字符串表示"""
        return f"SceneManager(scenes={len(self._scenes)})"


