"""设备控制函数"""
from typing import Dict, Any, List
from ..function_calling.registry import registry as global_registry, FunctionCategory, FunctionRegistry
from ..core.entity import registry as entity_registry, ServiceCall
from .light_entity import LightEntity
from .ac_entity import ACEntity
from .curtain_entity import CurtainEntity

def register_device_functions(registry: FunctionRegistry = None):
    """注册设备控制函数
    
    Args:
        registry: 函数注册表，如果为None则使用全局注册表
    """
    if registry is None:
        registry = global_registry
    
    # 注册灯光控制函数
    registry.register_function(
        name="light_control",
        description="控制智能灯开关",
        implementation=light_control,
        parameters={
            "entity_id": {
                "type": "string",
                "description": "实体ID",
                "required": True
            },
            "state": {
                "type": "string",
                "description": "目标状态(on/off)",
                "required": True,
                "enum_values": ["on", "off"]
            }
        }
    )
    
    registry.register_function(
        name="light_set_brightness",
        description="设置智能灯亮度",
        implementation=light_set_brightness,
        parameters={
            "entity_id": {
                "type": "string",
                "description": "实体ID",
                "required": True
            },
            "brightness": {
                "type": "integer",
                "description": "亮度值(0-100)",
                "required": True,
                "min_value": 0,
                "max_value": 100
            }
        }
    )
    
    # 注册空调控制函数
    registry.register_function(
        name="ac_control",
        description="控制空调开关",
        implementation=ac_control,
        parameters={
            "entity_id": {
                "type": "string",
                "description": "实体ID",
                "required": True
            },
            "state": {
                "type": "string",
                "description": "目标状态(on/off)",
                "required": True,
                "enum_values": ["on", "off"]
            }
        }
    )
    
    registry.register_function(
        name="ac_set_temperature",
        description="设置空调温度",
        implementation=ac_set_temperature,
        parameters={
            "entity_id": {
                "type": "string",
                "description": "实体ID",
                "required": True
            },
            "temperature": {
                "type": "number",
                "description": "目标温度(16-30)",
                "required": True,
                "min_value": 16,
                "max_value": 30
            }
        }
    )
    
    registry.register_function(
        name="ac_set_mode",
        description="设置空调模式",
        implementation=ac_set_mode,
        parameters={
            "entity_id": {
                "type": "string",
                "description": "实体ID",
                "required": True
            },
            "mode": {
                "type": "string",
                "description": "运行模式(cool/heat/auto)",
                "required": True,
                "enum_values": ["cool", "heat", "auto"]
            }
        }
    )
    
    # 注册窗帘控制函数
    registry.register_function(
        name="curtain_control",
        description="控制窗帘开关",
        implementation=curtain_control,
        parameters={
            "entity_id": {
                "type": "string",
                "description": "实体ID",
                "required": True
            },
            "state": {
                "type": "string",
                "description": "目标状态(on/off)",
                "required": True,
                "enum_values": ["on", "off"]
            }
        }
    )
    
    registry.register_function(
        name="curtain_set_position",
        description="设置窗帘位置",
        implementation=curtain_set_position,
        parameters={
            "entity_id": {
                "type": "string",
                "description": "实体ID",
                "required": True
            },
            "position": {
                "type": "integer",
                "description": "位置百分比(0-100)",
                "required": True,
                "min_value": 0,
                "max_value": 100
            }
        }
    )
    
    # 注册查询函数
    registry.register_function(
        name="get_device_status",
        description="查询设备状态",
        implementation=get_device_status,
        parameters={
            "entity_id": {
                "type": "string",
                "description": "实体ID",
                "required": True
            }
        }
    )
    
    registry.register_function(
        name="list_devices",
        description="列出所有设备",
        implementation=list_devices
    )

async def light_control(entity_id: str, state: str) -> str:
    """控制智能灯开关状态
    
    Args:
        entity_id: 实体ID
        state: 目标状态(on/off)
    """
    entity = entity_registry.get(entity_id)
    if not entity or not isinstance(entity, LightEntity):
        return f"未找到智能灯实体: {entity_id}"
        
    # 确保状态值为布尔值
    is_on = state.lower() == "on"
    service = "turn_on" if is_on else "turn_off"
    
    # 更新设备状态
    entity._state.state = "on" if is_on else "off"
    entity._state.attributes["power"] = is_on
    
    await entity.call_service(ServiceCall(
        domain="light",
        service=service,
        entity_id=entity_id,
        data={}
    ))
    
    await entity.update()  # 确保状态已更新
    state_name = "on" if is_on else "off"
    return f"已将{entity.name}切换为{state_name}状态"
    
async def light_set_brightness(entity_id: str, brightness: int) -> str:
    """设置智能灯亮度
    
    Args:
        entity_id: 实体ID
        brightness: 亮度值(0-100)
    """
    entity = entity_registry.get(entity_id)
    if not entity or not isinstance(entity, LightEntity):
        return f"未找到智能灯实体: {entity_id}"
        
    # 验证亮度范围
    if brightness < 0 or brightness > 100:
        return f"亮度值必须在0-100之间，当前值: {brightness}"
        
    # 更新设备状态
    entity._state.attributes["brightness"] = brightness
    if brightness > 0:
        entity._state.state = "on"
        entity._state.attributes["power"] = True
    else:
        entity._state.state = "off"
        entity._state.attributes["power"] = False
    
    await entity.call_service(ServiceCall(
        domain="light",
        service="set_brightness",
        entity_id=entity_id,
        data={"brightness": brightness}
    ))
    
    await entity.update()  # 确保状态已更新
    return f"已将{entity.name}的亮度设置为{brightness}%"
    
async def ac_control(entity_id: str, state: str) -> str:
    """控制空调开关状态
    
    Args:
        entity_id: 实体ID
        state: 目标状态(on/off)
    """
    entity = entity_registry.get(entity_id)
    if not entity or not isinstance(entity, ACEntity):
        return f"未找到空调实体: {entity_id}"
        
    # 确保状态值为布尔值
    is_on = state.lower() == "on"
    service = "turn_on" if is_on else "turn_off"
    
    # 更新设备状态
    entity._state.state = "on" if is_on else "off"
    entity._state.attributes["power"] = is_on
    
    await entity.call_service(ServiceCall(
        domain="climate",
        service=service,
        entity_id=entity_id,
        data={}
    ))
    
    await entity.update()  # 确保状态已更新
    state_name = "on" if is_on else "off"
    return f"已将{entity.name}切换为{state_name}状态"
    
async def ac_set_temperature(entity_id: str, temperature: float) -> str:
    """设置空调温度
    
    Args:
        entity_id: 实体ID
        temperature: 目标温度(16-30)
    """
    entity = entity_registry.get(entity_id)
    if not entity or not isinstance(entity, ACEntity):
        return f"未找到空调实体: {entity_id}"
        
    # 验证温度范围
    if temperature < 16 or temperature > 30:
        return f"温度值必须在16-30之间，当前值: {temperature}"
        
    # 更新设备状态
    entity._state.attributes["temperature"] = temperature
    entity._state.state = "on"  # 设置温度时自动打开空调
    entity._state.attributes["power"] = True
    
    await entity.call_service(ServiceCall(
        domain="climate",
        service="set_temperature",
        entity_id=entity_id,
        data={"temperature": temperature}
    ))
    
    await entity.update()  # 确保状态已更新
    return f"已将{entity.name}的温度设置为{temperature}度"
    
async def ac_set_mode(entity_id: str, mode: str) -> str:
    """设置空调模式
    
    Args:
        entity_id: 实体ID
        mode: 运行模式(cool/heat/auto)
    """
    entity = entity_registry.get(entity_id)
    if not entity or not isinstance(entity, ACEntity):
        return f"未找到空调实体: {entity_id}"
        
    # 验证模式值
    valid_modes = ["cool", "heat", "auto"]
    if mode not in valid_modes:
        return f"无效的模式值，可选值: {', '.join(valid_modes)}"
        
    # 更新设备状态
    entity._state.attributes["mode"] = mode
    entity._state.state = "on"  # 设置模式时自动打开空调
    entity._state.attributes["power"] = True
    
    await entity.call_service(ServiceCall(
        domain="climate",
        service="set_mode",
        entity_id=entity_id,
        data={"mode": mode}
    ))
    
    await entity.update()  # 确保状态已更新
    return f"已将{entity.name}的模式设置为{mode}"
    
async def curtain_control(entity_id: str, state: str) -> str:
    """控制窗帘开关状态
    
    Args:
        entity_id: 实体ID
        state: 目标状态(on/off)
    """
    entity = entity_registry.get(entity_id)
    if not entity or not isinstance(entity, CurtainEntity):
        return f"未找到窗帘实体: {entity_id}"
        
    # 确保状态值为布尔值
    is_on = state.lower() == "on"
    service = "turn_on" if is_on else "turn_off"
    
    # 更新设备状态
    entity._state.state = "on" if is_on else "off"
    entity._state.attributes["power"] = is_on
    entity._state.attributes["position"] = 100 if is_on else 0
    
    await entity.call_service(ServiceCall(
        domain="cover",
        service=service,
        entity_id=entity_id,
        data={}
    ))
    
    await entity.update()  # 确保状态已更新
    state_name = "打开" if is_on else "关闭"
    return f"已将{entity.name}{state_name}"
    
async def curtain_set_position(entity_id: str, position: int) -> str:
    """设置窗帘位置
    
    Args:
        entity_id: 实体ID
        position: 位置百分比(0-100)
    """
    entity = entity_registry.get(entity_id)
    if not entity or not isinstance(entity, CurtainEntity):
        return f"未找到窗帘实体: {entity_id}"
        
    # 验证位置范围
    if position < 0 or position > 100:
        return f"位置值必须在0-100之间，当前值: {position}"
        
    # 更新设备状态
    entity._state.attributes["position"] = position
    entity._state.state = "on" if position > 0 else "off"
    entity._state.attributes["power"] = position > 0
    
    await entity.call_service(ServiceCall(
        domain="cover",
        service="set_position",
        entity_id=entity_id,
        data={"position": position}
    ))
    
    await entity.update()  # 确保状态已更新
    return f"已将{entity.name}的位置设置为{position}%"
    
async def get_device_status(entity_id: str) -> str:
    """查询设备状态
    
    Args:
        entity_id: 实体ID
    """
    entity = entity_registry.get(entity_id)
    if not entity:
        return f"未找到设备: {entity_id}"
        
    await entity.update()  # 确保状态已更新
    return f"{entity.name}的当前状态: {entity._state.dict()}"
    
async def list_devices() -> str:
    """列出所有设备"""
    devices = entity_registry.list_entities()
    if not devices:
        return "当前没有可用的设备"
        
    result = "可用设备列表:\n"
    for device in devices:
        result += f"- {device.name} ({device.entity_id})\n"
    return result 