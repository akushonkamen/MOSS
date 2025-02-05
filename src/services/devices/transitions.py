"""设备状态转换规则

定义各类设备的状态转换规则和条件。
"""

from typing import Dict, Any, List, Callable
from .state_manager import StateTransition, state_manager
from .validators import LightState, ACMode, CurtainState

def _check_light_brightness_change(
    from_state: Dict[str, Any],
    to_state: Dict[str, Any]
) -> bool:
    """检查亮度变化是否合法
    
    Args:
        from_state: 当前状态
        to_state: 目标状态
        
    Returns:
        bool: 是否合法
    """
    # 如果是关闭状态，亮度必须为0
    if to_state["power"] == LightState.OFF:
        return to_state["brightness"] == 0
        
    # 如果是调光状态，亮度必须在变化范围内
    if to_state["power"] == LightState.DIMMING:
        return abs(
            to_state["brightness"] - from_state["brightness"]
        ) <= 20
        
    return True

def _check_ac_temp_change(
    from_state: Dict[str, Any],
    to_state: Dict[str, Any]
) -> bool:
    """检查温度变化是否合法
    
    Args:
        from_state: 当前状态
        to_state: 目标状态
        
    Returns:
        bool: 是否合法
    """
    # 如果是关闭状态，不允许改变温度
    if not to_state["power"]:
        return to_state["temperature"] == from_state["temperature"]
        
    # 温度变化不能太大
    return abs(
        to_state["temperature"] - from_state["temperature"]
    ) <= 2

def _check_curtain_position_change(
    from_state: Dict[str, Any],
    to_state: Dict[str, Any]
) -> bool:
    """检查位置变化是否合法
    
    Args:
        from_state: 当前状态
        to_state: 目标状态
        
    Returns:
        bool: 是否合法
    """
    # 如果是停止状态，位置不能变化
    if to_state["state"] == CurtainState.STOPPED:
        return to_state["position"] == from_state["position"]
        
    # 开启状态下位置必须增加
    if to_state["state"] == CurtainState.OPENING:
        return to_state["position"] > from_state["position"]
        
    # 关闭状态下位置必须减少
    if to_state["state"] == CurtainState.CLOSING:
        return to_state["position"] < from_state["position"]
        
    return True

# 灯光设备转换规则
light_transitions = [
    # 关闭状态到开启状态
    StateTransition(
        from_state={"power": LightState.OFF},
        to_state={"power": LightState.ON},
        conditions=[],
        priority=1
    ),
    # 开启状态到关闭状态
    StateTransition(
        from_state={"power": LightState.ON},
        to_state={"power": LightState.OFF},
        conditions=[_check_light_brightness_change],
        priority=1
    ),
    # 开启状态到调光状态
    StateTransition(
        from_state={"power": LightState.ON},
        to_state={"power": LightState.DIMMING},
        conditions=[_check_light_brightness_change],
        priority=2
    ),
    # 调光状态到开启状态
    StateTransition(
        from_state={"power": LightState.DIMMING},
        to_state={"power": LightState.ON},
        conditions=[],
        priority=2
    )
]

# 空调设备转换规则
ac_transitions = [
    # 关闭状态到开启状态
    StateTransition(
        from_state={"power": False},
        to_state={"power": True},
        conditions=[],
        priority=1
    ),
    # 开启状态到关闭状态
    StateTransition(
        from_state={"power": True},
        to_state={"power": False},
        conditions=[_check_ac_temp_change],
        priority=1
    ),
    # 制冷模式到制热模式
    StateTransition(
        from_state={"mode": ACMode.COOL},
        to_state={"mode": ACMode.HEAT},
        conditions=[_check_ac_temp_change],
        priority=2
    ),
    # 制热模式到制冷模式
    StateTransition(
        from_state={"mode": ACMode.HEAT},
        to_state={"mode": ACMode.COOL},
        conditions=[_check_ac_temp_change],
        priority=2
    )
]

# 窗帘设备转换规则
curtain_transitions = [
    # 关闭状态到开启状态
    StateTransition(
        from_state={"state": CurtainState.CLOSED},
        to_state={"state": CurtainState.OPENING},
        conditions=[_check_curtain_position_change],
        priority=1
    ),
    # 开启状态到关闭状态
    StateTransition(
        from_state={"state": CurtainState.OPEN},
        to_state={"state": CurtainState.CLOSING},
        conditions=[_check_curtain_position_change],
        priority=1
    ),
    # 开启中到停止状态
    StateTransition(
        from_state={"state": CurtainState.OPENING},
        to_state={"state": CurtainState.STOPPED},
        conditions=[_check_curtain_position_change],
        priority=2
    ),
    # 关闭中到停止状态
    StateTransition(
        from_state={"state": CurtainState.CLOSING},
        to_state={"state": CurtainState.STOPPED},
        conditions=[_check_curtain_position_change],
        priority=2
    )
]

# 注册转换规则
for transition in light_transitions:
    state_manager.register_transition("light", transition)
    
for transition in ac_transitions:
    state_manager.register_transition("ac", transition)
    
for transition in curtain_transitions:
    state_manager.register_transition("curtain", transition) 