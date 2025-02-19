"""智能工业AI自然语言处理测试"""
import pytest
import asyncio
from typing import Dict, Any, List
from src.services.smart_home import Industrial AIController
from src.services.devices.device_info import DeviceInfo, DeviceParameter

@pytest.fixture
async def controller():
    """创建控制器实例"""
    controller = Industrial AIController(
        api_url="http://localhost:11434/api/chat",
        model_name="llama3.1:latest"
    )
    
    # 注册测试设备
    devices = {
        "light.living_room": DeviceInfo(
            id="light.living_room",
            name="客厅灯",
            type="SmartLight",
            location="客厅",
            capabilities=["turn_on", "turn_off", "brightness"],
            parameters={
                "power": DeviceParameter(
                    name="power",
                    type="boolean",
                    description="电源状态",
                    current_value=False
                ),
                "brightness": DeviceParameter(
                    name="brightness",
                    type="integer",
                    description="亮度值",
                    current_value=100,
                    min_value=0,
                    max_value=100
                )
            }
        ),
        "light.bedroom": DeviceInfo(
            id="light.bedroom",
            name="卧室灯",
            type="SmartLight",
            location="卧室",
            capabilities=["turn_on", "turn_off", "brightness"],
            parameters={
                "power": DeviceParameter(
                    name="power",
                    type="boolean",
                    description="电源状态",
                    current_value=False
                ),
                "brightness": DeviceParameter(
                    name="brightness",
                    type="integer",
                    description="亮度值",
                    current_value=100,
                    min_value=0,
                    max_value=100
                )
            }
        ),
        "ac.living_room": DeviceInfo(
            id="ac.living_room",
            name="客厅空调",
            type="SmartAC",
            location="客厅",
            capabilities=["turn_on", "turn_off", "temperature", "mode"],
            parameters={
                "power": DeviceParameter(
                    name="power",
                    type="boolean",
                    description="电源状态",
                    current_value=False
                ),
                "temperature": DeviceParameter(
                    name="temperature",
                    type="integer",
                    description="温度值",
                    current_value=26,
                    min_value=16,
                    max_value=30
                ),
                "mode": DeviceParameter(
                    name="mode",
                    type="string",
                    description="运行模式",
                    current_value="auto",
                    enum_values=["auto", "cool", "heat", "dry", "fan"]
                )
            }
        ),
        "curtain.bedroom": DeviceInfo(
            id="curtain.bedroom",
            name="卧室窗帘",
            type="SmartCurtain",
            location="卧室",
            capabilities=["open", "close", "position"],
            parameters={
                "power": DeviceParameter(
                    name="power",
                    type="boolean",
                    description="电源状态",
                    current_value=False
                ),
                "position": DeviceParameter(
                    name="position",
                    type="integer",
                    description="位置值",
                    current_value=0,
                    min_value=0,
                    max_value=100
                )
            }
        )
    }
    
    for device in devices.values():
        controller.register_device(device)
        
    return controller

@pytest.mark.asyncio
@pytest.mark.parametrize("command,expected_device,expected_state", [
    # 基本控制命令测试
    ("打开客厅灯", "light.living_room", {"power": True}),
    ("关闭卧室灯", "light.bedroom", {"power": False}),
    ("打开空调", "ac.living_room", {"power": True}),
    ("关闭窗帘", "curtain.bedroom", {"power": False}),
    
    # 参数设置测试
    ("把客厅灯调到50%亮度", "light.living_room", {"brightness": 50}),
    ("空调温度调到24度", "ac.living_room", {"temperature": 24}),
    ("把空调设置成制冷模式", "ac.living_room", {"mode": "cool"}),
    ("窗帘打开到一半", "curtain.bedroom", {"position": 50}),
    
    # 模糊表达测试
    ("客厅有点暗", "light.living_room", {"brightness": 80}),
    ("房间有点热", "ac.living_room", {"temperature": 24, "mode": "cool"}),
    ("窗帘开得太大了", "curtain.bedroom", {"position": 30}),
    ("空调温度高了", "ac.living_room", {"temperature": 24}),
])
async def test_nlp_commands(controller: Industrial AIController, command: str, expected_device: str, expected_state: Dict[str, Any]):
    """测试自然语言命令处理"""
    # 获取控制器实例
    ctrl = await controller
    
    # 执行命令
    result = await ctrl.process_command(command)
    assert result is not None
    
    # 获取设备状态
    device = ctrl.get_device(expected_device)
    assert device is not None
    
    # 验证设备状态
    for param, value in expected_state.items():
        assert device.parameters[param].current_value == value

@pytest.mark.asyncio
@pytest.mark.parametrize("command,expected_error", [
    # 错误处理测试
    ("打开电视机", "未找到设备"),
    ("把空调温度调到40度", "温度超出范围"),
    ("把灯光调到200%", "亮度超出范围"),
    ("打开", "无法理解命令"),
])
async def test_error_handling(controller: Industrial AIController, command: str, expected_error: str):
    """测试错误处理"""
    # 获取控制器实例
    ctrl = await controller
    
    # 执行命令
    result = await ctrl.process_command(command)
    assert expected_error in result.lower()

@pytest.mark.asyncio
@pytest.mark.parametrize("command,expected_devices", [
    # 多设备控制测试
    ("把所有的灯都打开", ["light.living_room", "light.bedroom"]),
    ("关闭所有设备", ["light.living_room", "light.bedroom", "ac.living_room", "curtain.bedroom"]),
    ("客厅的设备都打开", ["light.living_room", "ac.living_room"]),
])
async def test_multi_device_control(controller: Industrial AIController, command: str, expected_devices: List[str]):
    """测试多设备控制"""
    # 获取控制器实例
    ctrl = await controller
    
    # 执行命令
    result = await ctrl.process_command(command)
    assert result is not None
    
    # 验证设备状态
    for device_id in expected_devices:
        device = ctrl.get_device(device_id)
        assert device is not None
        assert device.parameters["power"].current_value == True 