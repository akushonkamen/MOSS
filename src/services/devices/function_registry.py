"""设备控制函数注册器"""
from typing import Dict, Any, List
from .base import registry as device_registry
from .device_client import SmartLightClient, SmartACClient, SmartCurtainClient
from ..llm.function_call import registry as function_registry

def register_device_functions():
    """注册所有设备控制函数"""
    
    # 注册智能灯控制函数
    @function_registry.register(
        description="打开指定的智能灯。device_id可选值：light_001(客厅灯), light_002(卧室灯)",
        category="device_control",
        tags=["light", "control"]
    )
    async def light_turn_on(device_id: str) -> str:
        """打开智能灯
        
        Args:
            device_id: 设备ID，可选值：light_001(客厅灯), light_002(卧室灯)
            
        Returns:
            str: 操作结果描述
        """
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartLightClient):
            return "未找到指定的智能灯设备"
        await device.turn_on()
        return f"已打开{device.name}"
        
    @function_registry.register(
        description="关闭指定的智能灯。device_id可选值：light_001(客厅灯), light_002(卧室灯)",
        category="device_control",
        tags=["light", "control"]
    )
    async def light_turn_off(device_id: str) -> str:
        """关闭智能灯"""
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartLightClient):
            return "未找到指定的智能灯设备"
        await device.turn_off()
        return f"已关闭{device.name}"
        
    @function_registry.register(
        description="设置智能灯亮度。device_id可选值：light_001(客厅灯), light_002(卧室灯)",
        category="device_control",
        tags=["light", "control"]
    )
    async def light_set_brightness(device_id: str, brightness: int) -> str:
        """设置智能灯亮度
        
        Args:
            device_id: 设备ID，可选值：light_001(客厅灯), light_002(卧室灯)
            brightness: 亮度值(0-100)
        """
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartLightClient):
            return "未找到指定的智能灯设备"
        await device.set_brightness(brightness)
        return f"已将{device.name}的亮度设置为{brightness}%"
        
    # 注册空调控制函数
    @function_registry.register(
        description="打开指定的空调。device_id可选值：ac_001(客厅空调)",
        category="device_control",
        tags=["ac", "control"]
    )
    async def ac_turn_on(device_id: str) -> str:
        """打开空调"""
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartACClient):
            return "未找到指定的空调设备"
        await device.turn_on()
        return f"已打开{device.name}"
        
    @function_registry.register(
        description="关闭指定的空调。device_id可选值：ac_001(客厅空调)",
        category="device_control",
        tags=["ac", "control"]
    )
    async def ac_turn_off(device_id: str) -> str:
        """关闭空调"""
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartACClient):
            return "未找到指定的空调设备"
        await device.turn_off()
        return f"已关闭{device.name}"
        
    @function_registry.register(
        description="设置空调温度。device_id可选值：ac_001(客厅空调)",
        category="device_control",
        tags=["ac", "control"]
    )
    async def ac_set_temperature(device_id: str, temperature: float) -> str:
        """设置空调温度
        
        Args:
            device_id: 设备ID，可选值：ac_001(客厅空调)
            temperature: 目标温度(16-30)
        """
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartACClient):
            return "未找到指定的空调设备"
        await device.set_temperature(temperature)
        return f"已将{device.name}的温度设置为{temperature}°C"
        
    @function_registry.register(
        description="设置空调模式。device_id可选值：ac_001(客厅空调)。mode可选值：cool(制冷), heat(制热), auto(自动)",
        category="device_control",
        tags=["ac", "control"]
    )
    async def ac_set_mode(device_id: str, mode: str) -> str:
        """设置空调模式
        
        Args:
            device_id: 设备ID，可选值：ac_001(客厅空调)
            mode: 运行模式，可选值：cool(制冷), heat(制热), auto(自动)
        """
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartACClient):
            return "未找到指定的空调设备"
        if not await device.set_mode(mode):
            return f"不支持的模式: {mode}"
        return f"已将{device.name}切换到{mode}模式"
        
    # 注册窗帘控制函数
    @function_registry.register(
        description="打开指定的窗帘。device_id可选值：curtain_001(卧室窗帘)",
        category="device_control",
        tags=["curtain", "control"]
    )
    async def curtain_open(device_id: str) -> str:
        """打开窗帘"""
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartCurtainClient):
            return "未找到指定的窗帘设备"
        await device.turn_on()
        return f"正在打开{device.name}"
        
    @function_registry.register(
        description="关闭指定的窗帘。device_id可选值：curtain_001(卧室窗帘)",
        category="device_control",
        tags=["curtain", "control"]
    )
    async def curtain_close(device_id: str) -> str:
        """关闭窗帘"""
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartCurtainClient):
            return "未找到指定的窗帘设备"
        await device.turn_off()
        return f"正在关闭{device.name}"
        
    @function_registry.register(
        description="设置窗帘位置。device_id可选值：curtain_001(卧室窗帘)",
        category="device_control",
        tags=["curtain", "control"]
    )
    async def curtain_set_position(device_id: str, position: int) -> str:
        """设置窗帘位置
        
        Args:
            device_id: 设备ID，可选值：curtain_001(卧室窗帘)
            position: 位置百分比(0-100)
        """
        device = device_registry.get_device(device_id)
        if not device or not isinstance(device, SmartCurtainClient):
            return "未找到指定的窗帘设备"
        await device.set_position(position)
        return f"正在将{device.name}调整到{position}%的位置"
        
    # 注册设备状态查询函数
    @function_registry.register(
        description="查询设备状态",
        category="device_control",
        tags=["query", "status"]
    )
    async def get_device_status(device_id: str) -> Dict[str, Any]:
        """查询设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            Dict[str, Any]: 设备状态信息
        """
        device = device_registry.get_device(device_id)
        if not device:
            return {"error": "未找到指定的设备"}
        status = await device.get_status()
        return {
            "device_id": device.device_id,
            "name": device.name,
            "type": device.__class__.__name__,
            "status": status
        }
        
    @function_registry.register(
        description="列出所有设备",
        category="device_control",
        tags=["query", "list"]
    )
    async def list_all_devices() -> List[Dict[str, str]]:
        """列出所有已注册的设备
        
        Returns:
            List[Dict[str, str]]: 设备列表
        """
        devices = device_registry.list_devices()
        return [
            {
                "device_id": device.device_id,
                "name": device.name,
                "type": device.__class__.__name__
            }
            for device in devices.values()
        ] 