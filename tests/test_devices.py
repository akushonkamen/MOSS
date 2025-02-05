"""设备测试用例"""
import pytest
from src.services.devices.ac_client import SmartACClient
from src.services.devices.ac_entity import ACEntity
from src.services.devices.base import DeviceError, registry

@pytest.fixture
def ac_client():
    """空调客户端"""
    client = SmartACClient("test_ac")
    registry.register("test_ac", client)
    yield client
    registry.unregister("test_ac")
    
@pytest.fixture
def ac_entity(ac_client):
    """空调实体"""
    return ACEntity("test_ac", "测试空调")

@pytest.mark.asyncio
async def test_ac_status(ac_client, ac_entity):
    """测试空调状态"""
    # 初始状态
    status = await ac_client.get_status()
    assert status["is_on"] is False
    assert status["temperature"] == 26
    assert status["mode"] == "auto"
    
    # 更新状态
    await ac_client.update_state({
        "is_on": True,
        "temperature": 24,
        "mode": "cool"
    })
    
    status = await ac_client.get_status()
    assert status["is_on"] is True
    assert status["temperature"] == 24
    assert status["mode"] == "cool"
    
@pytest.mark.asyncio
async def test_ac_commands(ac_client):
    """测试空调命令"""
    # 打开空调
    result = await ac_client.execute_command("turn_on")
    assert result is True
    status = await ac_client.get_status()
    assert status["is_on"] is True
    
    # 设置温度
    result = await ac_client.execute_command(
        "set_temperature",
        temperature=25
    )
    assert result is True
    status = await ac_client.get_status()
    assert status["temperature"] == 25
    assert status["is_on"] is True
    
    # 设置模式
    result = await ac_client.execute_command(
        "set_mode",
        mode="cool"
    )
    assert result is True
    status = await ac_client.get_status()
    assert status["mode"] == "cool"
    assert status["is_on"] is True
    
    # 关闭空调
    result = await ac_client.execute_command("turn_off")
    assert result is True
    status = await ac_client.get_status()
    assert status["is_on"] is False
    
@pytest.mark.asyncio
async def test_ac_validation(ac_client):
    """测试参数验证"""
    # 无效温度
    with pytest.raises(DeviceError, match="温度必须在16-30之间"):
        await ac_client.execute_command(
            "set_temperature",
            temperature=15
        )
    with pytest.raises(DeviceError, match="温度必须在16-30之间"):
        await ac_client.execute_command(
            "set_temperature",
            temperature=31
        )
    with pytest.raises(DeviceError, match="温度必须是数字"):
        await ac_client.execute_command(
            "set_temperature",
            temperature="25"
        )
    with pytest.raises(DeviceError, match="缺少温度参数"):
        await ac_client.execute_command("set_temperature")
        
    # 无效模式
    with pytest.raises(DeviceError, match="不支持的模式"):
        await ac_client.execute_command(
            "set_mode",
            mode="invalid"
        )
    with pytest.raises(DeviceError, match="模式必须是字符串"):
        await ac_client.execute_command(
            "set_mode",
            mode=123
        )
    with pytest.raises(DeviceError, match="缺少模式参数"):
        await ac_client.execute_command("set_mode")
        
    # 无效命令
    with pytest.raises(DeviceError, match="不支持的命令"):
        await ac_client.execute_command("invalid_command")
        
@pytest.mark.asyncio
async def test_ac_entity_services(ac_entity):
    """测试空调实体服务"""
    # 打开空调
    await ac_entity.call_service({
        "service": "turn_on"
    })
    assert ac_entity._is_on is True
    
    # 设置温度
    await ac_entity.call_service({
        "service": "set_temperature",
        "data": {"temperature": 25}
    })
    assert ac_entity._is_on is True
    assert ac_entity._temperature == 25
    
    # 设置模式
    await ac_entity.call_service({
        "service": "set_mode",
        "data": {"mode": "cool"}
    })
    assert ac_entity._is_on is True
    assert ac_entity._mode == "cool"
    
    # 关闭空调
    await ac_entity.call_service({
        "service": "turn_off"
    })
    assert ac_entity._is_on is False
    
    # 无效服务
    with pytest.raises(ValueError, match="不支持的服务"):
        await ac_entity.call_service({
            "service": "invalid_service"
        })
        
    # 无效温度
    with pytest.raises(ValueError, match="温度必须在16-30之间"):
        await ac_entity.call_service({
            "service": "set_temperature",
            "data": {"temperature": 15}
        })
        
    # 无效模式
    with pytest.raises(ValueError, match="不支持的模式"):
        await ac_entity.call_service({
            "service": "set_mode",
            "data": {"mode": "invalid"}
        }) 