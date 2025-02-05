import pytest
from src.services.function_calling import setup_function_calling, FunctionParser
from src.services.core.entity import registry as entity_registry, ServiceCall
from src.services.devices.light_entity import LightEntity
from src.services.devices.ac_entity import ACEntity
from src.services.devices.curtain_entity import CurtainEntity

@pytest.fixture
async def setup_devices():
    """设置测试设备"""
    # 注册测试设备
    light = LightEntity("light.test", "测试灯")
    ac = ACEntity("ac.test", "测试空调")
    curtain = CurtainEntity("curtain.test", "测试窗帘")
    
    # 初始化设备状态
    await light.call_service(ServiceCall(
        domain="light",
        service="turn_off",
        entity_id="light.test",
        data={}
    ))
    await ac.call_service(ServiceCall(
        domain="climate",
        service="turn_off",
        entity_id="ac.test",
        data={}
    ))
    await curtain.call_service(ServiceCall(
        domain="cover",
        service="turn_off",
        entity_id="curtain.test",
        data={}
    ))
    
    entity_registry.register(light)
    entity_registry.register(ac)
    entity_registry.register(curtain)
    
    # 初始化函数调用系统
    await setup_function_calling()
    
    yield {
        "light": light,
        "ac": ac,
        "curtain": curtain
    }
    
    # 清理
    entity_registry.unregister("light.test")
    entity_registry.unregister("ac.test")
    entity_registry.unregister("curtain.test")

@pytest.mark.asyncio
async def test_light_control(setup_devices):
    """测试灯光控制"""
    devices = setup_devices
    
    # 测试开灯
    text = """
    打开测试灯
    
    <function>
    name: light_control
    parameters:
      entity_id: light.test
      state: on
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "已将测试灯切换为on状态" in results[0]["result"]
    assert devices["light"].state.state == "on"
    
    # 测试设置亮度
    text = """
    将测试灯调到50%亮度
    
    <function>
    name: light_set_brightness
    parameters:
      entity_id: light.test
      brightness: 50
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "已将测试灯的亮度设置为50%" in results[0]["result"]
    assert devices["light"].state.attributes["brightness"] == 50

@pytest.mark.asyncio
async def test_ac_control(setup_devices):
    """测试空调控制"""
    devices = setup_devices
    
    # 测试开空调
    text = """
    打开测试空调
    
    <function>
    name: ac_control
    parameters:
      entity_id: ac.test
      state: on
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "已将测试空调切换为on状态" in results[0]["result"]
    assert devices["ac"].state.state == "on"
    
    # 测试设置温度
    text = """
    将测试空调温度调到26度
    
    <function>
    name: ac_set_temperature
    parameters:
      entity_id: ac.test
      temperature: 26
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "已将测试空调的温度设置为26°C" in results[0]["result"]
    assert devices["ac"].state.attributes["temperature"] == 26
    
    # 测试设置模式
    text = """
    将测试空调设置为制冷模式
    
    <function>
    name: ac_set_mode
    parameters:
      entity_id: ac.test
      mode: cool
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "已将测试空调切换到制冷模式" in results[0]["result"]
    assert devices["ac"].state.attributes["mode"] == "cool"

@pytest.mark.asyncio
async def test_curtain_control(setup_devices):
    """测试窗帘控制"""
    devices = setup_devices
    
    # 测试打开窗帘
    text = """
    打开测试窗帘
    
    <function>
    name: curtain_control
    parameters:
      entity_id: curtain.test
      state: on
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "正在打开测试窗帘" in results[0]["result"]
    assert devices["curtain"].state.state == "on"
    
    # 测试设置位置
    text = """
    将测试窗帘打开到60%
    
    <function>
    name: curtain_set_position
    parameters:
      entity_id: curtain.test
      position: 60
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "正在将测试窗帘调整到60%的位置" in results[0]["result"]
    assert devices["curtain"].state.attributes["position"] == 60

@pytest.mark.asyncio
async def test_device_query(setup_devices):
    """测试设备查询"""
    devices = setup_devices
    
    # 测试查询单个设备状态
    text = """
    查询测试灯的状态
    
    <function>
    name: get_device_status
    parameters:
      entity_id: light.test
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "测试灯当前状态" in results[0]["result"]
    
    # 测试列出所有设备
    text = """
    列出所有设备
    
    <function>
    name: list_devices
    parameters: {}
    </function>
    """
    
    response, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 1
    assert "result" in results[0]
    assert "测试灯" in results[0]["result"]
    assert "测试空调" in results[0]["result"]
    assert "测试窗帘" in results[0]["result"] 