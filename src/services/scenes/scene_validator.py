"""场景验证器实现"""
from typing import Dict, List, Any, Optional
import logging
import uuid

from .models.scene import Scene
from .models.action import Action, ActionType
from .models.condition import Condition, ConditionType
from .models.trigger import Trigger, TriggerType

logger = logging.getLogger(__name__)

class SceneValidator:
    """场景验证器
    
    负责验证场景配置的正确性。
    """
    
    def __init__(self):
        """初始化场景验证器"""
        pass
        
    def validate(self, scene: Scene) -> bool:
        """验证场景配置
        
        Args:
            scene: 场景对象
            
        Returns:
            bool: 是否验证通过
        """
        try:
            # 验证基本属性
            if not self._validate_basic_properties(scene):
                return False
                
            # 验证触发器
            if not self._validate_triggers(scene.triggers):
                return False
                
            # 验证条件
            if not self._validate_conditions(scene.conditions):
                return False
                
            # 验证动作
            if not self._validate_actions(scene.actions):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"场景验证失败: {scene.id}, 错误: {str(e)}")
            return False
            
    def _validate_basic_properties(self, scene: Scene) -> bool:
        """验证基本属性
        
        Args:
            scene: 场景对象
            
        Returns:
            bool: 是否验证通过
        """
        try:
            # 验证ID
            if not scene.id:
                scene.id = str(uuid.uuid4())
                
            # 验证名称
            if not scene.name or len(scene.name) > 100:
                logger.error(f"场景名称无效: {scene.id}")
                return False
                
            # 验证描述
            if scene.description and len(scene.description) > 500:
                logger.error(f"场景描述过长: {scene.id}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"基本属性验证失败: {scene.id}, 错误: {str(e)}")
            return False
            
    def _validate_triggers(self, triggers: List[Trigger]) -> bool:
        """验证触发器
        
        Args:
            triggers: 触发器列表
            
        Returns:
            bool: 是否验证通过
        """
        try:
            # 验证触发器数量
            if not triggers:
                logger.error("场景必须包含至少一个触发器")
                return False
                
            # 验证每个触发器
            for trigger in triggers:
                # 验证触发器类型
                if not isinstance(trigger.type, TriggerType):
                    logger.error(f"触发器类型无效: {trigger.type}")
                    return False
                    
                # 验证触发源
                if not trigger.source:
                    logger.error("触发器必须指定触发源")
                    return False
                    
                # 验证事件类型
                if not trigger.event_type:
                    logger.error("触发器必须指定事件类型")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"触发器验证失败: {str(e)}")
            return False
            
    def _validate_conditions(self, conditions: List[Condition]) -> bool:
        """验证条件
        
        Args:
            conditions: 条件列表
            
        Returns:
            bool: 是否验证通过
        """
        try:
            # 验证每个条件
            for condition in conditions:
                # 验证条件类型
                if not isinstance(condition.type, ConditionType):
                    logger.error(f"条件类型无效: {condition.type}")
                    return False
                    
                # 验证条件目标
                if not condition.target:
                    logger.error("条件必须指定目标")
                    return False
                    
                # 验证条件值
                if condition.value is None:
                    logger.error("条件必须指定值")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"条件验证失败: {str(e)}")
            return False
            
    def _validate_actions(self, actions: List[Action]) -> bool:
        """验证动作
        
        Args:
            actions: 动作列表
            
        Returns:
            bool: 是否验证通过
        """
        try:
            # 验证动作数量
            if not actions:
                logger.error("场景必须包含至少一个动作")
                return False
                
            # 验证每个动作
            for action in actions:
                # 验证动作类型
                if not isinstance(action.type, ActionType):
                    logger.error(f"动作类型无效: {action.type}")
                    return False
                    
                # 验证动作目标
                if not action.target:
                    logger.error("动作必须指定目标")
                    return False
                    
                # 验证动作命令
                if not action.command:
                    logger.error("动作必须指定命令")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"动作验证失败: {str(e)}")
            return False
            
    def __repr__(self) -> str:
        """返回场景验证器的字符串表示"""
        return "SceneValidator()"


