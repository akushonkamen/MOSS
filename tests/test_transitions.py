"""状态转换单元测试"""

import pytest
from typing import Dict, Any
from src.services.devices.state_manager import (
    DeviceStateManager,
    StateTransitionError
)
from src.services.devices.validators import (
    LightState,
    ACMode,
    CurtainState
)
from src.services.devices.transitions import (
    _check_light_brightness_change,
    _check_ac_temp_change,
    _check_curtain_position_change
)

@pytest.fixture
async def state_manager():
    """状态管理器测试fixture"""
    manager = DeviceStateManager(
        redis_url="redis://localhost",
        max_history=10,
        state_ttl=60
    )
    yield manager
    # 清理测试数据
    await manager.redis.flushdb()
    await manager.redis.close()

@pytest.mark.asyncio
async def test_light_transitions(state_manager):
    """测试灯光状态转换"""
    device_id = "light1"
    
    # 测试关闭到开启
    off_state = {
        "power": LightState.OFF,
        "brightness": 0
    }
    on_state = {
        "power": LightState.ON,
        "brightness": 80
    }
    
    # 设置初始状态
    assert await state_manager.set_state(
        device_id,
        "light",
        off_state
    )
    
    # 验证可以转换到开启状态
    assert await state_manager.set_state(
        device_id,
        "light",
        on_state
    )
    
    # 测试开启到调光
    dimming_state = {
        "power": LightState.DIMMING,
        "brightness": 60  # 亮度变化在允许范围内
    }
    assert await state_manager.set_state(
        device_id,
        "light",
        dimming_state
    )
    
    # 测试调光亮度变化过大
    invalid_dimming = {
        "power": LightState.DIMMING,
        "brightness": 0  # 亮度变化超过允许范围
    }
    with pytest.raises(StateTransitionError):
        await state_manager.set_state(
            device_id,
            "light",
            invalid_dimming
        )
        
    # 测试关闭时亮度不为0
    invalid_off = {
        "power": LightState.OFF,
        "brightness": 50  # 关闭状态亮度必须为0
    }
    with pytest.raises(StateTransitionError):
        await state_manager.set_state(
            device_id,
            "light",
            invalid_off
        )

@pytest.mark.asyncio
async def test_ac_transitions(state_manager):
    """测试空调状态转换"""
    device_id = "ac1"
    
    # 测试关闭到开启
    off_state = {
        "power": False,
        "mode": ACMode.COOL,
        "temperature": 25
    }
    on_state = {
        "power": True,
        "mode": ACMode.COOL,
        "temperature": 25
    }
    
    # 设置初始状态
    assert await state_manager.set_state(
        device_id,
        "ac",
        off_state
    )
    
    # 验证可以转换到开启状态
    assert await state_manager.set_state(
        device_id,
        "ac",
        on_state
    )
    
    # 测试温度变化在允许范围内
    valid_temp = {
        "power": True,
        "mode": ACMode.COOL,
        "temperature": 26  # 温度变化1度
    }
    assert await state_manager.set_state(
        device_id,
        "ac",
        valid_temp
    )
    
    # 测试温度变化过大
    invalid_temp = {
        "power": True,
        "mode": ACMode.COOL,
        "temperature": 30  # 温度变化4度
    }
    with pytest.raises(StateTransitionError):
        await state_manager.set_state(
            device_id,
            "ac",
            invalid_temp
        )
        
    # 测试关闭状态下改变温度
    invalid_off_temp = {
        "power": False,
        "mode": ACMode.COOL,
        "temperature": 24  # 关闭状态不能改变温度
    }
    with pytest.raises(StateTransitionError):
        await state_manager.set_state(
            device_id,
            "ac",
            invalid_off_temp
        )

@pytest.mark.asyncio
async def test_curtain_transitions(state_manager):
    """测试窗帘状态转换"""
    device_id = "curtain1"
    
    # 测试关闭到开启
    closed_state = {
        "state": CurtainState.CLOSED,
        "position": 0
    }
    opening_state = {
        "state": CurtainState.OPENING,
        "position": 30
    }
    
    # 设置初始状态
    assert await state_manager.set_state(
        device_id,
        "curtain",
        closed_state
    )
    
    # 验证可以转换到开启状态
    assert await state_manager.set_state(
        device_id,
        "curtain",
        opening_state
    )
    
    # 测试停止状态
    stopped_state = {
        "state": CurtainState.STOPPED,
        "position": 30  # 位置不变
    }
    assert await state_manager.set_state(
        device_id,
        "curtain",
        stopped_state
    )
    
    # 测试停止状态下改变位置
    invalid_stopped = {
        "state": CurtainState.STOPPED,
        "position": 50  # 停止状态不能改变位置
    }
    with pytest.raises(StateTransitionError):
        await state_manager.set_state(
            device_id,
            "curtain",
            invalid_stopped
        )
        
    # 测试开启状态下位置减少
    invalid_opening = {
        "state": CurtainState.OPENING,
        "position": 20  # 开启状态位置必须增加
    }
    with pytest.raises(StateTransitionError):
        await state_manager.set_state(
            device_id,
            "curtain",
            invalid_opening
        )

def test_light_brightness_check():
    """测试灯光亮度变化检查"""
    # 测试关闭状态
    assert _check_light_brightness_change(
        {"power": LightState.ON, "brightness": 80},
        {"power": LightState.OFF, "brightness": 0}
    )
    assert not _check_light_brightness_change(
        {"power": LightState.ON, "brightness": 80},
        {"power": LightState.OFF, "brightness": 50}
    )
    
    # 测试调光状态
    assert _check_light_brightness_change(
        {"power": LightState.ON, "brightness": 80},
        {"power": LightState.DIMMING, "brightness": 70}
    )
    assert not _check_light_brightness_change(
        {"power": LightState.ON, "brightness": 80},
        {"power": LightState.DIMMING, "brightness": 50}
    )

def test_ac_temp_check():
    """测试空调温度变化检查"""
    # 测试关闭状态
    assert _check_ac_temp_change(
        {"power": True, "temperature": 25},
        {"power": False, "temperature": 25}
    )
    assert not _check_ac_temp_change(
        {"power": True, "temperature": 25},
        {"power": False, "temperature": 24}
    )
    
    # 测试温度变化
    assert _check_ac_temp_change(
        {"power": True, "temperature": 25},
        {"power": True, "temperature": 26}
    )
    assert not _check_ac_temp_change(
        {"power": True, "temperature": 25},
        {"power": True, "temperature": 28}
    )

def test_curtain_position_check():
    """测试窗帘位置变化检查"""
    # 测试停止状态
    assert _check_curtain_position_change(
        {"state": CurtainState.OPENING, "position": 50},
        {"state": CurtainState.STOPPED, "position": 50}
    )
    assert not _check_curtain_position_change(
        {"state": CurtainState.OPENING, "position": 50},
        {"state": CurtainState.STOPPED, "position": 60}
    )
    
    # 测试开启状态
    assert _check_curtain_position_change(
        {"state": CurtainState.OPENING, "position": 50},
        {"state": CurtainState.OPENING, "position": 70}
    )
    assert not _check_curtain_position_change(
        {"state": CurtainState.OPENING, "position": 50},
        {"state": CurtainState.OPENING, "position": 30}
    )
    
    # 测试关闭状态
    assert _check_curtain_position_change(
        {"state": CurtainState.CLOSING, "position": 50},
        {"state": CurtainState.CLOSING, "position": 30}
    )
    assert not _check_curtain_position_change(
        {"state": CurtainState.CLOSING, "position": 50},
        {"state": CurtainState.CLOSING, "position": 70}
    ) 