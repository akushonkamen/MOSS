"""状态管理器单元测试"""

import pytest
import asyncio
from typing import Dict, Any, List
from src.services.devices.state_manager import (
    DeviceStateManager,
    DeviceStateEvent,
    StateTransition
)
from src.services.devices.validators import (
    LightValidator,
    ACValidator,
    CurtainValidator
)
import aioredis

@pytest.fixture
async def state_manager():
    """状态管理器测试fixture"""
    manager = DeviceStateManager(
        redis_url="redis://localhost",
        max_history=10,
        state_ttl=60
    )
    # 注册验证器
    manager.register_validator(
        "light",
        LightValidator(device_type="light", rules={})
    )
    manager.register_validator(
        "ac",
        ACValidator(device_type="ac", rules={})
    )
    manager.register_validator(
        "curtain",
        CurtainValidator(device_type="curtain", rules={})
    )
    return manager

@pytest.mark.asyncio
async def test_light_state_validation(state_manager):
    """测试灯光状态验证"""
    async with state_manager as manager:
        # 测试有效状态
        assert await manager.set_state(
            "light1",
            "light",
            {
                "power": True,
                "brightness": 80,
                "color_temp": 4000,
                "rgb": [255, 255, 255]
            }
        )
        
        # 测试无效的power值
        assert not await manager.set_state(
            "light1",
            "light",
            {
                "power": "invalid",
                "brightness": 80
            }
        )
            
        # 测试无效的brightness值
        assert not await manager.set_state(
            "light1",
            "light",
            {
                "power": True,
                "brightness": 101
            }
        )
            
        # 测试无效的color_temp值
        assert not await manager.set_state(
            "light1",
            "light",
            {
                "power": True,
                "color_temp": 7000
            }
        )
            
        # 测试无效的rgb值
        assert not await manager.set_state(
            "light1",
            "light",
            {
                "power": True,
                "rgb": [256, 0, 0]
            }
        )

@pytest.mark.asyncio
async def test_ac_state_validation(state_manager):
    """测试空调状态验证"""
    async with state_manager as manager:
        # 测试有效状态
        assert await manager.set_state(
            "ac1",
            "ac",
            {
                "power": True,
                "mode": "cool",
                "temperature": 25,
                "fan_speed": "medium"
            }
        )
        
        # 测试无效的power值
        assert not await manager.set_state(
            "ac1",
            "ac",
            {
                "power": "invalid",
                "mode": "cool"
            }
        )
            
        # 测试无效的mode值
        assert not await manager.set_state(
            "ac1",
            "ac",
            {
                "power": True,
                "mode": "invalid"
            }
        )
            
        # 测试无效的temperature值
        assert not await manager.set_state(
            "ac1",
            "ac",
            {
                "power": True,
                "temperature": 15
            }
        )
            
        # 测试无效的fan_speed值
        assert not await manager.set_state(
            "ac1",
            "ac",
            {
                "power": True,
                "fan_speed": "invalid"
            }
        )

@pytest.mark.asyncio
async def test_curtain_state_validation(state_manager):
    """测试窗帘状态验证"""
    async with state_manager as manager:
        # 测试有效状态
        assert await manager.set_state(
            "curtain1",
            "curtain",
            {
                "power": True,
                "position": 80
            }
        )
        
        # 测试无效的power值
        assert not await manager.set_state(
            "curtain1",
            "curtain",
            {
                "power": "invalid",
                "position": 80
            }
        )
            
        # 测试无效的position值
        assert not await manager.set_state(
            "curtain1",
            "curtain",
            {
                "power": True,
                "position": 101
            }
        )

@pytest.mark.asyncio
async def test_state_history(state_manager):
    """测试状态历史记录"""
    async with state_manager as manager:
        device_id = "light1"
        
        # 设置多个状态
        states = [
            {
                "power": True,
                "brightness": 80
            },
            {
                "power": False
            },
            {
                "power": True,
                "brightness": 100
            }
        ]
        
        for state in states:
            assert await manager.set_state(
                device_id,
                "light",
                state
            )
            await asyncio.sleep(0.1)  # 确保时间戳不同
            
        # 获取历史记录
        history = await manager.get_history(device_id)
        assert len(history) == len(states)
        
        # 验证历史记录顺序（最新的在前）
        for i, record in enumerate(history):
            assert record["state"] == states[-(i + 1)]

@pytest.mark.asyncio
async def test_state_events(state_manager):
    """测试状态事件"""
    async with state_manager as manager:
        device_id = "light1"
        events = []
        
        # 注册事件回调
        async def on_state_change(device_id: str, event: DeviceStateEvent, data: Dict[str, Any]):
            events.append(event)
            
        manager.register_event_callback(on_state_change)
        
        # 设置状态
        await manager.set_state(
            device_id,
            "light",
            {
                "power": True,
                "brightness": 80
            }
        )
        
        # 验证事件
        assert DeviceStateEvent.VALIDATED in events
        assert DeviceStateEvent.UPDATED in events
        assert DeviceStateEvent.HISTORY_ADDED in events

@pytest.mark.asyncio
async def test_concurrent_state_updates(state_manager):
    """测试并发状态更新"""
    async with state_manager as manager:
        device_id = "light1"
        
        # 并发设置状态
        async def update_state(brightness: int):
            await manager.set_state(
                device_id,
                "light",
                {
                    "power": True,
                    "brightness": brightness
                }
            )
            
        tasks = [
            update_state(i)
            for i in range(50, 100, 10)
        ]
        await asyncio.gather(*tasks)
        
        # 验证最终状态
        state = await manager.get_state(device_id)
        assert state is not None
        assert state["power"] is True
        assert 50 <= state["brightness"] <= 90

@pytest.mark.asyncio
async def test_state_transitions(state_manager):
    """测试状态转换"""
    async with state_manager as manager:
        device_id = "light1"
        
        # 注册转换规则
        transition = StateTransition(
            from_state={"power": True},
            to_state={"power": False},
            conditions=[lambda x, y: True],
            priority=1
        )
        manager.register_transition(
            "light",
            transition
        )
        
        # 设置初始状态
        await manager.set_state(
            device_id,
            "light",
            {
                "power": True,
                "brightness": 80
            }
        )
        
        # 尝试转换到允许的状态
        assert await manager.set_state(
            device_id,
            "light",
            {
                "power": False
            }
        )
        
        # 验证状态已更新
        state = await manager.get_state(device_id)
        assert state is not None
        assert state["power"] is False

@pytest.mark.asyncio
async def test_transition_events(state_manager):
    """测试转换事件"""
    async with state_manager as manager:
        device_id = "light1"
        events = []
        
        # 注册事件回调
        async def on_state_change(device_id: str, event: DeviceStateEvent, data: Dict[str, Any]):
            if event == DeviceStateEvent.UPDATED:
                events.append(data["state"])
            
        manager.register_event_callback(on_state_change)
        
        # 设置初始状态
        await manager.set_state(
            device_id,
            "light",
            {
                "power": True,
                "brightness": 80
            }
        )
        
        # 更新状态
        await manager.set_state(
            device_id,
            "light",
            {
                "power": False
            }
        )
        
        # 验证事件
        assert len(events) == 2
        assert events[0]["power"] is True
        assert events[1]["power"] is False

@pytest.mark.asyncio
async def test_redis_connection_failure(state_manager):
    """测试Redis连接失败"""
    async with state_manager as manager:
        # 关闭Redis连接
        await manager.redis.close()
        
        # 尝试设置状态
        assert not await manager.set_state(
            "light1",
            "light",
            {
                "power": True
            }
        )

@pytest.mark.asyncio
async def test_max_history_limit(state_manager):
    """测试历史记录数量限制"""
    async with state_manager as manager:
        device_id = "light1"
        
        # 设置超过限制的状态
        for i in range(15):  # 超过max_history=10
            await manager.set_state(
                device_id,
                "light",
                {
                    "power": i % 2 == 0
                }
            )
            await asyncio.sleep(0.1)  # 确保时间戳不同
            
        # 验证历史记录数量
        history = await manager.get_history(device_id)
        assert len(history) <= 10  # 不超过限制

@pytest.mark.asyncio
async def test_event_callback_failure(state_manager):
    """测试事件回调失败"""
    async with state_manager as manager:
        device_id = "light1"
        
        # 注册一个会失败的回调
        async def failing_callback(device_id: str, event: DeviceStateEvent, data: Dict[str, Any]):
            raise Exception("Callback failed")
            
        manager.register_event_callback(failing_callback)
        
        # 设置状态应该仍然成功
        assert await manager.set_state(
            device_id,
            "light",
            {
                "power": True
            }
        )

@pytest.mark.asyncio
async def test_concurrent_validation(state_manager):
    """测试并发验证"""
    async with state_manager as manager:
        # 并发设置多个设备的状态
        async def update_device(device_id: str, device_type: str, state: Dict[str, Any]):
            return await manager.set_state(device_id, device_type, state)
            
        tasks = [
            update_device(f"light{i}", "light", {"power": i % 2 == 0})
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        
        # 验证所有操作都成功
        assert all(results) 