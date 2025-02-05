"""设备状态验证器实现

提供各类设备的状态验证规则。
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import re
from .state_manager import StateValidator, StateValidationError

class LightState(str, Enum):
    """灯光状态枚举"""
    ON = "on"
    OFF = "off"
    DIMMING = "dimming"

class ACMode(str, Enum):
    """空调模式枚举"""
    COOL = "cool"
    HEAT = "heat"
    AUTO = "auto"
    DRY = "dry"
    FAN = "fan"

class CurtainState(str, Enum):
    """窗帘状态枚举"""
    OPEN = "open"
    CLOSED = "closed"
    OPENING = "opening"
    CLOSING = "closing"
    STOPPED = "stopped"

class LightValidator(StateValidator):
    """灯光设备状态验证器"""
    
    def validate(self, state: Dict[str, Any]) -> bool:
        """验证灯光状态
        
        Args:
            state: 要验证的状态
            
        Returns:
            bool: 验证是否通过
            
        Raises:
            StateValidationError: 验证失败时抛出
        """
        try:
            # 验证必需字段
            required_fields = {"power", "brightness"}
            if not all(field in state for field in required_fields):
                raise StateValidationError(
                    f"缺少必需字段: {required_fields - state.keys()}"
                )
                
            # 验证power字段
            if not isinstance(state["power"], str):
                raise StateValidationError("power字段必须是字符串")
            try:
                LightState(state["power"])
            except ValueError:
                raise StateValidationError(
                    f"无效的power值: {state['power']}"
                )
                
            # 验证brightness字段
            if not isinstance(state["brightness"], (int, float)):
                raise StateValidationError(
                    "brightness字段必须是数字"
                )
            if not 0 <= state["brightness"] <= 100:
                raise StateValidationError(
                    "brightness必须在0-100范围内"
                )
                
            # 验证可选字段
            if "color_temp" in state:
                if not isinstance(state["color_temp"], int):
                    raise StateValidationError(
                        "color_temp字段必须是整数"
                    )
                if not 2700 <= state["color_temp"] <= 6500:
                    raise StateValidationError(
                        "color_temp必须在2700-6500范围内"
                    )
                    
            if "rgb" in state:
                if not isinstance(state["rgb"], list):
                    raise StateValidationError("rgb字段必须是列表")
                if len(state["rgb"]) != 3:
                    raise StateValidationError("rgb必须包含3个值")
                if not all(
                    isinstance(v, int) and 0 <= v <= 255
                    for v in state["rgb"]
                ):
                    raise StateValidationError(
                        "rgb值必须是0-255范围内的整数"
                    )
                    
            return True
            
        except StateValidationError:
            raise
        except Exception as e:
            raise StateValidationError(f"验证失败: {str(e)}")

class ACValidator(StateValidator):
    """空调设备状态验证器"""
    
    def validate(self, state: Dict[str, Any]) -> bool:
        """验证空调状态
        
        Args:
            state: 要验证的状态
            
        Returns:
            bool: 验证是否通过
            
        Raises:
            StateValidationError: 验证失败时抛出
        """
        try:
            # 验证必需字段
            required_fields = {"power", "mode", "temperature"}
            if not all(field in state for field in required_fields):
                raise StateValidationError(
                    f"缺少必需字段: {required_fields - state.keys()}"
                )
                
            # 验证power字段
            if not isinstance(state["power"], bool):
                raise StateValidationError("power字段必须是布尔值")
                
            # 验证mode字段
            if not isinstance(state["mode"], str):
                raise StateValidationError("mode字段必须是字符串")
            try:
                ACMode(state["mode"])
            except ValueError:
                raise StateValidationError(
                    f"无效的mode值: {state['mode']}"
                )
                
            # 验证temperature字段
            if not isinstance(state["temperature"], (int, float)):
                raise StateValidationError(
                    "temperature字段必须是数字"
                )
            if not 16 <= state["temperature"] <= 30:
                raise StateValidationError(
                    "temperature必须在16-30范围内"
                )
                
            # 验证可选字段
            if "fan_speed" in state:
                if not isinstance(state["fan_speed"], int):
                    raise StateValidationError(
                        "fan_speed字段必须是整数"
                    )
                if not 1 <= state["fan_speed"] <= 5:
                    raise StateValidationError(
                        "fan_speed必须在1-5范围内"
                    )
                    
            if "swing" in state:
                if not isinstance(state["swing"], bool):
                    raise StateValidationError(
                        "swing字段必须是布尔值"
                    )
                    
            return True
            
        except StateValidationError:
            raise
        except Exception as e:
            raise StateValidationError(f"验证失败: {str(e)}")

class CurtainValidator(StateValidator):
    """窗帘设备状态验证器"""
    
    def validate(self, state: Dict[str, Any]) -> bool:
        """验证窗帘状态
        
        Args:
            state: 要验证的状态
            
        Returns:
            bool: 验证是否通过
            
        Raises:
            StateValidationError: 验证失败时抛出
        """
        try:
            # 验证必需字段
            required_fields = {"state", "position"}
            if not all(field in state for field in required_fields):
                raise StateValidationError(
                    f"缺少必需字段: {required_fields - state.keys()}"
                )
                
            # 验证state字段
            if not isinstance(state["state"], str):
                raise StateValidationError("state字段必须是字符串")
            try:
                CurtainState(state["state"])
            except ValueError:
                raise StateValidationError(
                    f"无效的state值: {state['state']}"
                )
                
            # 验证position字段
            if not isinstance(state["position"], (int, float)):
                raise StateValidationError(
                    "position字段必须是数字"
                )
            if not 0 <= state["position"] <= 100:
                raise StateValidationError(
                    "position必须在0-100范围内"
                )
                
            # 验证可选字段
            if "speed" in state:
                if not isinstance(state["speed"], int):
                    raise StateValidationError(
                        "speed字段必须是整数"
                    )
                if not 1 <= state["speed"] <= 3:
                    raise StateValidationError(
                        "speed必须在1-3范围内"
                    )
                    
            return True
            
        except StateValidationError:
            raise
        except Exception as e:
            raise StateValidationError(f"验证失败: {str(e)}")

# 注册验证器
from .state_manager import state_manager

state_manager.register_validator(
    "light",
    LightValidator(device_type="light", rules={})
)
state_manager.register_validator(
    "ac",
    ACValidator(device_type="ac", rules={})
)
state_manager.register_validator(
    "curtain",
    CurtainValidator(device_type="curtain", rules={})
) 