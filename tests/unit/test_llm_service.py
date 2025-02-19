"""LLMService 单元测试"""
import pytest
from unittest.mock import Mock, AsyncMock
import aiohttp
from datetime import datetime

from src.services.llm.llm_service import LLMService, LLMConfig

@pytest.fixture
def config():
    """创建LLM配置"""
    return LLMConfig(
        api_url="http://localhost:11434/api/chat",
        model_name="llama2:latest",
        temperature=0.7,
        max_tokens=1000,
        timeout=30
    )

@pytest.fixture
async def mock_session():
    """创建mock session"""
    session = Mock(spec=aiohttp.ClientSession)
    session.post = AsyncMock()
    session.close = AsyncMock()
    return session

@pytest.fixture
async def service(config, mock_session):
    """创建LLMService实例"""
    service = LLMService(config)
    service._session = mock_session
    return service

@pytest.mark.asyncio
async def test_initialize(service, mock_session):
    """测试初始化"""
    await service.initialize()
    assert service._session is not None

@pytest.mark.asyncio
async def test_close(service, mock_session):
    """测试关闭服务"""
    await service.close()
    mock_session.close.assert_called_once()

@pytest.mark.asyncio
async def test_classify_device_type_success(service, mock_session):
    """测试设备类型识别成功场景"""
    # 准备测试数据
    device_info = {
        "device_name": "XiaoMi.AirConditioner.v3",
        "functions": {
            "setPower": {"type": "boolean"},
            "setTemperature": {"type": "number", "range": [16, 32]},
            "setMode": {"type": "enum", "values": ["cool", "heat", "auto"]}
        }
    }
    supported_types = ["SmartAC", "SmartLight", "SmartCurtain"]
    
    # 配置mock响应
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "message": {"content": "SmartAC"}
    })
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    # 执行测试
    result = await service.classify_device_type(device_info, supported_types)
    
    # 验证结果
    assert result == "SmartAC"
    mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_classify_device_type_failure(service, mock_session):
    """测试设备类型识别失败场景"""
    # 配置mock响应
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "message": {"content": "UnknownType"}
    })
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    # 验证异常
    with pytest.raises(ValueError) as exc:
        await service.classify_device_type(
            {"device_name": "Unknown.Device"},
            ["SmartAC", "SmartLight"]
        )
    assert "Unsupported device type" in str(exc.value)

@pytest.mark.asyncio
async def test_map_device_functions_success(service, mock_session):
    """测试功能映射成功场景"""
    # 准备测试数据
    source_functions = {
        "setPower": {"type": "boolean"},
        "setTemperature": {"type": "number", "range": [16, 32]}
    }
    target_schema = {
        "set_power": {
            "type": "boolean",
            "description": "控制电源开关"
        },
        "set_temperature": {
            "type": "number",
            "range": [16, 30],
            "description": "设置温度"
        }
    }
    
    # 配置mock响应
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "message": {
            "content": '''
            {
                "set_power": {
                    "type": "boolean",
                    "description": "控制电源开关"
                },
                "set_temperature": {
                    "type": "number",
                    "range": [16, 30],
                    "description": "设置温度"
                }
            }
            '''
        }
    })
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    # 执行测试
    result = await service.map_device_functions(source_functions, target_schema)
    
    # 验证结果
    assert "set_power" in result
    assert "set_temperature" in result
    assert result["set_power"]["type"] == "boolean"
    assert result["set_temperature"]["type"] == "number"
    mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_understand_command_success(service, mock_session):
    """测试命令理解成功场景"""
    # 准备测试数据
    command = "设置温度到26度"
    device_schema = {
        "SmartAC": {
            "functions": {
                "set_temperature": {
                    "type": "number",
                    "range": [16, 30],
                    "description": "设置温度"
                }
            }
        }
    }
    
    # 配置mock响应
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "message": {
            "content": '''
            {
                "device_type": "SmartAC",
                "function": "set_temperature"
            }
            '''
        }
    })
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    # 执行测试
    result = await service.understand_command(command, device_schema)
    
    # 验证结果
    assert result["device_type"] == "SmartAC"
    assert result["function"] == "set_temperature"
    mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_understand_command_failure(service, mock_session):
    """测试命令理解失败场景"""
    # 配置mock响应
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "message": {
            "content": '''
            {
                "device_type": "UnknownType",
                "function": "unknown_function"
            }
            '''
        }
    })
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    # 验证异常
    with pytest.raises(ValueError) as exc:
        await service.understand_command(
            "未知命令",
            {"SmartAC": {"functions": {}}}
        )
    assert "Unknown device type" in str(exc.value)

@pytest.mark.asyncio
async def test_call_llm_error(service, mock_session):
    """测试LLM调用错误场景"""
    # 配置mock响应
    mock_response = Mock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    # 验证异常
    with pytest.raises(RuntimeError) as exc:
        await service._call_llm("test prompt")
    assert "LLM request failed with status 500" in str(exc.value) 