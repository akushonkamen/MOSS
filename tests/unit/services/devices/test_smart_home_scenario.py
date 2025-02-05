"""智能家居场景测试"""
import pytest
import json
import asyncio
from unittest.mock import patch
from src.services.llm.llm_service import llm_service
from src.services.devices.smart_devices import SmartLight, SmartAC, SmartCurtain
from src.services.devices.base import registry as device_registry
from src.services.devices.function_registry import register_device_functions
from src.services.llm.function_call import registry as function_registry
from tests.unit.services.llm.test_llm_service import MockStreamResponse, MockClientSession

@pytest.fixture
def service():
    """创建 llm_service 实例"""
    service = llm_service()
    # 注册设备控制函数
    register_device_functions()
    # 将所有注册的函数添加到 llm_service 中
    for func_def in function_registry.list_functions():
        service.register_function(function_registry.get_function(func_def.name))
    return service

@pytest.fixture
def devices():
    """创建测试设备"""
    # 创建测试设备
    living_room_light = SmartLight("light_001", "客厅灯")
    bedroom_light = SmartLight("light_002", "卧室灯")
    living_room_ac = SmartAC("ac_001", "客厅空调")
    bedroom_curtain = SmartCurtain("curtain_001", "卧室窗帘")
    
    # 注册设备
    device_registry.register_device(living_room_light)
    device_registry.register_device(bedroom_light)
    device_registry.register_device(living_room_ac)
    device_registry.register_device(bedroom_curtain)
    
    return {
        "living_room_light": living_room_light,
        "bedroom_light": bedroom_light,
        "living_room_ac": living_room_ac,
        "bedroom_curtain": bedroom_curtain
    }

@pytest.mark.asyncio
async def test_morning_scene(service, devices):
    """测试早晨场景"""
    content = [
        json.dumps({"message": {"content": "好的，我来帮您准备早晨的场景。"}}).encode(),
        json.dumps({"message": {"content": """
        让我帮您打开窗帘：
        <function>
        name: curtain_open
        parameters:
          device_id: curtain_001
        </function>
        
        现在调整灯光：
        <function>
        name: light_turn_on
        parameters:
          device_id: light_002
        </function>
        <function>
        name: light_set_brightness
        parameters:
          device_id: light_002
          brightness: 70
        </function>
        """}}).encode(),
        json.dumps({"done": True}).encode()
    ]
    
    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream(
            "帮我准备早晨场景，打开卧室窗帘，开灯并调整到合适亮度",
            "test_session",
            functions=["curtain_open", "light_turn_on", "light_set_brightness"]
        ):
            responses.append(response)
            print(f"收到响应: {response}")
            
    # 验证设备状态
    curtain_status = await devices["bedroom_curtain"].get_status()
    assert curtain_status["is_open"] is True
    assert curtain_status["position"] == 100
    
    light_status = await devices["bedroom_light"].get_status()
    assert light_status["is_on"] is True
    assert light_status["brightness"] == 70
    
    # 验证响应的自然性
    full_response = " ".join(responses)
    assert "好的，我来帮您准备早晨的场景" in full_response
    assert "正在打开卧室窗帘" in full_response
    assert "已打开卧室灯" in full_response
    assert "已将卧室灯的亮度设置为70%" in full_response

@pytest.mark.asyncio
async def test_evening_scene(service, devices):
    """测试晚上回家场景"""
    content = [
        json.dumps({"message": {"content": "好的，我来帮您准备舒适的回家环境。"}}).encode(),
        json.dumps({"message": {"content": """
        首先打开客厅灯：
        <function>
        name: light_turn_on
        parameters:
          device_id: light_001
        </function>
        <function>
        name: light_set_brightness
        parameters:
          device_id: light_001
          brightness: 60
        </function>
        
        调整空调：
        <function>
        name: ac_turn_on
        parameters:
          device_id: ac_001
        </function>
        <function>
        name: ac_set_temperature
        parameters:
          device_id: ac_001
          temperature: 26
        </function>
        <function>
        name: ac_set_mode
        parameters:
          device_id: ac_001
          mode: auto
        </function>
        """}}).encode(),
        json.dumps({"done": True}).encode()
    ]
    
    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream(
            "我到家了，帮我打开客厅的灯和空调，调整到舒适的温度",
            "test_session",
            functions=["light_turn_on", "light_set_brightness", "ac_turn_on", "ac_set_temperature", "ac_set_mode"]
        ):
            responses.append(response)
            print(f"收到响应: {response}")
            
    # 验证设备状态
    light_status = await devices["living_room_light"].get_status()
    assert light_status["is_on"] is True
    assert light_status["brightness"] == 60
    
    ac_status = await devices["living_room_ac"].get_status()
    assert ac_status["is_on"] is True
    assert ac_status["temperature"] == 26
    assert ac_status["mode"] == "auto"
    
    # 验证响应的自然性
    full_response = " ".join(responses)
    assert "好的，我来帮您准备舒适的回家环境" in full_response
    assert "已打开客厅灯" in full_response
    assert "已将客厅灯的亮度设置为60%" in full_response
    assert "已打开客厅空调" in full_response
    assert "已将客厅空调的温度设置为26°C" in full_response
    assert "已将客厅空调切换到auto模式" in full_response

@pytest.mark.asyncio
async def test_sleep_scene(service, devices):
    """测试睡眠场景"""
    content = [
        json.dumps({"message": {"content": "好的，我来帮您准备睡眠环境。"}}).encode(),
        json.dumps({"message": {"content": """
        关闭所有灯光：
        <function>
        name: light_turn_off
        parameters:
          device_id: light_001
        </function>
        <function>
        name: light_turn_off
        parameters:
          device_id: light_002
        </function>
        
        关闭窗帘：
        <function>
        name: curtain_close
        parameters:
          device_id: curtain_001
        </function>
        
        调整空调：
        <function>
        name: ac_set_temperature
        parameters:
          device_id: ac_001
          temperature: 24
        </function>
        <function>
        name: ac_set_mode
        parameters:
          device_id: ac_001
          mode: auto
        </function>
        """}}).encode(),
        json.dumps({"done": True}).encode()
    ]
    
    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream(
            "我准备睡觉了，帮我关闭所有灯，关窗帘，调整空调到睡眠模式",
            "test_session",
            functions=["light_turn_off", "curtain_close", "ac_set_temperature", "ac_set_mode"]
        ):
            responses.append(response)
            print(f"收到响应: {response}")
            
    # 验证设备状态
    living_room_light_status = await devices["living_room_light"].get_status()
    bedroom_light_status = await devices["bedroom_light"].get_status()
    assert living_room_light_status["is_on"] is False
    assert bedroom_light_status["is_on"] is False
    
    curtain_status = await devices["bedroom_curtain"].get_status()
    assert curtain_status["is_open"] is False
    assert curtain_status["position"] == 0
    
    ac_status = await devices["living_room_ac"].get_status()
    assert ac_status["temperature"] == 24
    assert ac_status["mode"] == "auto"
    
    # 验证响应的自然性
    full_response = " ".join(responses)
    assert "好的，我来帮您准备睡眠环境" in full_response
    assert "已关闭客厅灯" in full_response
    assert "已关闭卧室灯" in full_response
    assert "正在关闭卧室窗帘" in full_response
    assert "已将客厅空调的温度设置为24°C" in full_response
    assert "已将客厅空调切换到auto模式" in full_response 