"""AdaptorAgent 单元测试"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.services.llm.agents.adaptor_agent import AdaptorAgent, AdaptionResult
from src.services.llm.llm_service import LLMService

@pytest.fixture
def llm_service():
    """创建LLM服务mock"""
    service = Mock(spec=LLMService)
    service.classify_device_type = AsyncMock()
    service.map_device_functions = AsyncMock()
    service.understand_command = AsyncMock()
    return service

@pytest.fixture
def agent(llm_service):
    """创建AdaptorAgent实例"""
    return AdaptorAgent(llm_service)

@pytest.mark.asyncio
async def test_adapt_device_success(agent, llm_service):
    """测试设备适配成功场景"""
    # 准备测试数据
    device_info = {
        "device_name": "XiaoMi.AirConditioner.v3",
        "functions": {
            "setPower": {"type": "boolean"},
            "setTemperature": {"type": "number", "range": [16, 32]},
            "setMode": {"type": "enum", "values": ["cool", "heat", "auto"]}
        }
    }
    
    # 配置mock
    llm_service.classify_device_type.return_value = "SmartAC"
    llm_service.map_device_functions.return_value = {
        "set_power": {"type": "boolean"},
        "set_temperature": {"type": "number", "range": [16, 30]},
        "set_mode": {"type": "enum", "values": ["auto", "cool", "heat"]}
    }
    
    # 执行测试
    result = await agent.adapt_device(device_info)
    
    # 验证结果
    assert isinstance(result, AdaptionResult)
    assert result.success
    assert result.error is None
    assert result.result is not None
    
    # 验证设备信息
    device = result.result
    assert device["name"] == "XiaoMi.AirConditioner.v3"
    assert device["type"] == "SmartAC"
    assert "power_control" in device["capabilities"]
    assert "temperature_control" in device["capabilities"]
    
    # 验证调用
    llm_service.classify_device_type.assert_called_once_with(
        device_info,
        ["SmartAC", "SmartLight", "SmartCurtain"]
    )
    llm_service.map_device_functions.assert_called_once()

@pytest.mark.asyncio
async def test_adapt_device_failure(agent, llm_service):
    """测试设备适配失败场景"""
    # 配置mock抛出异常
    llm_service.classify_device_type.side_effect = ValueError("Unknown device type")
    
    # 执行测试
    result = await agent.adapt_device({"device_name": "Unknown.Device"})
    
    # 验证结果
    assert isinstance(result, AdaptionResult)
    assert not result.success
    assert result.error is not None
    assert result.result is None

@pytest.mark.asyncio
async def test_adapt_command_success(agent, llm_service):
    """测试命令适配成功场景"""
    # 准备测试数据
    device_id = "ac_001"
    command = "设置温度到26度"
    params = {"temperature": 26}
    
    # 配置mock
    llm_service.understand_command.return_value = {
        "device_type": "SmartAC",
        "function": "set_temperature"
    }
    
    # 执行测试
    result = await agent.adapt_command(device_id, command, params)
    
    # 验证结果
    assert isinstance(result, AdaptionResult)
    assert result.success
    assert result.error is None
    assert result.result is not None
    
    # 验证命令
    cmd = result.result
    assert cmd["device_id"] == device_id
    assert cmd["function"] == "set_temperature"
    assert cmd["parameters"]["temperature"] == 26
    
    # 验证调用
    llm_service.understand_command.assert_called_once_with(
        command,
        agent.device_schema
    )

@pytest.mark.asyncio
async def test_adapt_command_failure(agent, llm_service):
    """测试命令适配失败场景"""
    # 配置mock抛出异常
    llm_service.understand_command.side_effect = ValueError("Cannot understand command")
    
    # 执行测试
    result = await agent.adapt_command("ac_001", "未知命令", {})
    
    # 验证结果
    assert isinstance(result, AdaptionResult)
    assert not result.success
    assert result.error is not None
    assert result.result is None

@pytest.mark.asyncio
async def test_validate_command_params_success(agent):
    """测试命令参数验证成功场景"""
    # 准备测试数据
    function = "set_temperature"
    params = {"temperature": 26}
    schema = {
        "set_temperature": {
            "type": "number",
            "range": [16, 30],
            "description": "设置温度"
        }
    }
    
    # 执行测试
    validated = await agent._validate_command_params(function, params, schema)
    
    # 验证结果
    assert validated["temperature"] == 26

@pytest.mark.asyncio
async def test_validate_command_params_failure(agent):
    """测试命令参数验证失败场景"""
    # 准备测试数据
    function = "set_temperature"
    params = {"temperature": 35}  # 超出范围
    schema = {
        "set_temperature": {
            "type": "number",
            "range": [16, 30],
            "description": "设置温度"
        }
    }
    
    # 验证异常
    with pytest.raises(ValueError) as exc:
        await agent._validate_command_params(function, params, schema)
    assert "greater than maximum" in str(exc.value) 