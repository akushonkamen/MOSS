"""智能家居系统集成测试"""
import pytest
from unittest.mock import patch, AsyncMock
from src.services.llm.decoderAgent import decoderAgent, Intent
from src.services.llm.expertAgent import ExpertAgent, ActionResponse
from src.services.devices.base import (
    DeviceInfo, 
    DeviceParameter, 
    DeviceStatus,
    registry as device_registry
)
from src.services.function_calling.registry import FunctionRegistry, FunctionDefinition, FunctionParameter
from aioresponses import aioresponses
import json
import logging
from typing import Dict, Any, List
from src.services.smart_home import SmartHomeController

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_api_response():
    """模拟API响应"""
    def _create_response(content: str):
        return {
            "message": {
                "content": content
            }
        }
    return _create_response

@pytest.fixture
def mock_device():
    """模拟设备"""
    return DeviceInfo(
        id="ac001",
        name="客厅空调",
        type="air_conditioner",
        location="客厅",
        status=DeviceStatus.ONLINE,
        capabilities=["power_control", "temperature_control", "mode_control"],
        parameters={
            "power": DeviceParameter(
                type="boolean",
                description="电源状态",
                current_value=False
            ),
            "temperature": DeviceParameter(
                type="number",
                description="温度设置",
                current_value=26,
                min_value=16,
                max_value=30,
                unit="°C"
            ),
            "mode": DeviceParameter(
                type="string",
                description="运行模式",
                current_value="auto",
                enum_values=["auto", "cool", "heat", "dry", "fan"]
            )
        }
    )

@pytest.fixture
def mock_functions():
    """模拟函数"""
    registry = FunctionRegistry()
    
    # 注册电源控制函数
    registry.register_function(
        name="set_power",
        description="控制设备电源",
        implementation=AsyncMock(),
        parameters={
            "device_id": FunctionParameter(
                type="string",
                description="设备ID",
                required=True
            ),
            "power": FunctionParameter(
                type="boolean",
                description="电源状态",
                required=True
            )
        }
    )
    
    # 注册温度控制函数
    registry.register_function(
        name="set_temperature",
        description="设置温度",
        implementation=AsyncMock(),
        parameters={
            "device_id": FunctionParameter(
                type="string",
                description="设备ID",
                required=True
            ),
            "temperature": FunctionParameter(
                type="number",
                description="目标温度",
                required=True,
                min_value=16,
                max_value=30
            )
        }
    )
    
    # 注册模式控制函数
    registry.register_function(
        name="set_mode",
        description="设置运行模式",
        implementation=AsyncMock(),
        parameters={
            "device_id": FunctionParameter(
                type="string",
                description="设备ID",
                required=True
            ),
            "mode": FunctionParameter(
                type="string",
                description="运行模式",
                required=True,
                enum_values=["auto", "cool", "heat", "dry", "fan"]
            )
        }
    )
    
    return registry

@pytest.mark.asyncio
async def test_smart_home_control(mock_api_response, mock_device, mock_functions):
    """测试智能家居控制"""
    # 创建控制器
    controller = SmartHomeController()
    
    # 注册设备
    controller.register_device(mock_device)
    
    # 替换函数注册表
    controller.function_registry = mock_functions
    
    # 模拟意图理解响应
    intent_response = """```json
{
    "intent_type": "power_control",
    "device": {
        "id": "ac001",
        "name": "客厅空调",
        "type": "air_conditioner"
    },
    "parameters": {
        "operation": "turn_on",
        "direction": null,
        "target_value": null,
        "current_value": false,
        "reason": "感觉热"
    }
}
```"""
    
    # 模拟动作生成响应
    action_response = """```json
{
    "function_calls": [
        {
            "name": "set_power",
            "parameters": {
                "device_id": "ac001",
                "power": true
            }
        },
        {
            "name": "set_mode",
            "parameters": {
                "device_id": "ac001",
                "mode": "cool"
            }
        },
        {
            "name": "set_temperature",
            "parameters": {
                "device_id": "ac001",
                "temperature": 24
            }
        }
    ],
    "explanation": "好的，我来帮您打开空调，设置为制冷模式，温度调到24度。"
}
```"""
    
    # 模拟API调用
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(side_effect=[
            mock_api_response(intent_response),
            mock_api_response(action_response)
        ])
        
        # 处理用户命令
        result = await controller.process_command("好热啊")
        
        # 验证API调用
        assert mock_post.call_count == 2
        
        # 验证函数调用
        set_power = mock_functions.get_function("set_power")
        assert set_power.implementation.call_count == 1
        set_power.implementation.assert_called_with(device_id="ac001", power=True)
        
        set_mode = mock_functions.get_function("set_mode")
        assert set_mode.implementation.call_count == 1
        set_mode.implementation.assert_called_with(device_id="ac001", mode="cool")
        
        set_temperature = mock_functions.get_function("set_temperature")
        assert set_temperature.implementation.call_count == 1
        set_temperature.implementation.assert_called_with(device_id="ac001", temperature=24)
        
        # 验证返回结果
        assert "打开空调" in result
        assert "24度" in result 