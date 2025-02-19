"""场景执行器实现"""
import asyncio
from typing import Dict, List, Any
import logging

from .models.scene import Scene
from .models.action import Action
from .models.condition import Condition

logger = logging.getLogger(__name__)

class SceneExecutor:
    """场景执行器
    
    负责场景的执行和动作调度。
    """
    
    def __init__(self):
        """初始化场景执行器"""
        self._running_scenes: Dict[str, asyncio.Task] = {}
        
    async def execute(self, scene: Scene, context: Dict[str, Any]) -> bool:
        """执行场景
        
        Args:
            scene: 场景对象
            context: 执行上下文
            
        Returns:
            bool: 是否执行成功
        """
        try:
            # 检查场景是否已在执行
            if scene.id in self._running_scenes:
                logger.warning(f"场景正在执行中: {scene.id}")
                return False
                
            # 检查条件是否满足
            if not await self._check_conditions(scene.conditions, context):
                logger.info(f"场景条件不满足: {scene.id}")
                return False
                
            # 创建执行任务
            task = asyncio.create_task(self._execute_scene(scene, context))
            self._running_scenes[scene.id] = task
            
            # 等待执行完成
            try:
                await task
                return True
            except Exception as e:
                logger.error(f"场景执行失败: {scene.id}, 错误: {str(e)}")
                return False
            finally:
                # 清理执行任务
                del self._running_scenes[scene.id]
                
        except Exception as e:
            logger.error(f"场景执行失败: {scene.id}, 错误: {str(e)}")
            return False
            
    async def _execute_scene(self, scene: Scene, context: Dict[str, Any]):
        """执行场景的具体实现
        
        Args:
            scene: 场景对象
            context: 执行上下文
        """
        try:
            logger.info(f"开始执行场景: {scene.id}")
            
            # 执行所有动作
            for action in scene.actions:
                try:
                    # 执行单个动作
                    success = await action.execute(context)
                    if not success:
                        logger.warning(f"动作执行失败: {scene.id} - {action.type}")
                        
                except Exception as e:
                    logger.error(f"动作执行异常: {scene.id} - {action.type}, 错误: {str(e)}")
                    
            logger.info(f"场景执行完成: {scene.id}")
            
        except Exception as e:
            logger.error(f"场景执行异常: {scene.id}, 错误: {str(e)}")
            raise
            
    async def _check_conditions(self, conditions: List[Condition], context: Dict[str, Any]) -> bool:
        """检查条件是否满足
        
        Args:
            conditions: 条件列表
            context: 执行上下文
            
        Returns:
            bool: 是否满足所有条件
        """
        try:
            # 检查所有条件
            for condition in conditions:
                if not condition.evaluate(context):
                    return False
            return True
            
        except Exception as e:
            logger.error(f"条件检查失败: {str(e)}")
            return False
            
    def cancel_scene(self, scene_id: str) -> bool:
        """取消场景执行
        
        Args:
            scene_id: 场景ID
            
        Returns:
            bool: 是否取消成功
        """
        try:
            # 检查场景是否在执行
            if scene_id not in self._running_scenes:
                logger.warning(f"场景未在执行: {scene_id}")
                return False
                
            # 取消执行任务
            task = self._running_scenes[scene_id]
            task.cancel()
            
            # 清理执行任务
            del self._running_scenes[scene_id]
            
            logger.info(f"场景执行已取消: {scene_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消场景执行失败: {scene_id}, 错误: {str(e)}")
            return False
            
    def is_scene_running(self, scene_id: str) -> bool:
        """检查场景是否正在执行
        
        Args:
            scene_id: 场景ID
            
        Returns:
            bool: 是否正在执行
        """
        return scene_id in self._running_scenes
        
    def get_running_scenes(self) -> List[str]:
        """获取正在执行的场景ID列表
        
        Returns:
            List[str]: 场景ID列表
        """
        return list(self._running_scenes.keys())
        
    def __repr__(self) -> str:
        """返回场景执行器的字符串表示"""
        return f"SceneExecutor(running_scenes={len(self._running_scenes)})"


