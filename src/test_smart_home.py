"""智能家居测试客户端"""
import asyncio
import sys
import os
import logging
from tabulate import tabulate
from unittest.mock import AsyncMock
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from src.services.llm.llm_service import llm_service
from src.services.devices.device_client import SmartLightClient, SmartACClient, SmartCurtainClient
from src.services.devices.functions import register_device_functions
from src.services.function_calling.registry import registry as function_registry, FunctionParameter
from src.services.devices.base import registry as device_registry
from src.services.core.entity import registry as entity_registry
from src.services.devices.light_entity import LightEntity
from src.services.devices.ac_entity import ACEntity
from src.services.devices.curtain_entity import CurtainEntity
from src.services.function_calling.parser import FunctionParser
from src.services.function_calling.registry import FunctionDefinition
from src.services.devices.device_info import DeviceInfo, DeviceParameter

async def setup_devices():
    """设置测试设备"""
    # 创建设备客户端
    living_room_light = SmartLightClient("light.living_room", "客厅灯", 8001)
    bedroom_light = SmartLightClient("light.bedroom", "卧室灯", 8002)
    living_room_ac = SmartACClient("ac.living_room", "客厅空调", 8003)
    bedroom_curtain = SmartCurtainClient("curtain.bedroom", "卧室窗帘", 8004)
    
    # 注册设备客户端到设备注册表中
    device_registry.register(living_room_light)
    device_registry.register(bedroom_light)
    device_registry.register(living_room_ac)
    device_registry.register(bedroom_curtain)
    
    # 创建并注册实体
    living_room_light_entity = LightEntity("light.living_room", "客厅灯")
    bedroom_light_entity = LightEntity("light.bedroom", "卧室灯")
    living_room_ac_entity = ACEntity("ac.living_room", "客厅空调")
    bedroom_curtain_entity = CurtainEntity("curtain.bedroom", "卧室窗帘")
    
    entity_registry.register(living_room_light_entity)
    entity_registry.register(bedroom_light_entity)
    entity_registry.register(living_room_ac_entity)
    entity_registry.register(bedroom_curtain_entity)
    
    logger.info("设备注册完成")
    
    return {
        "living_room_light": living_room_light,
        "bedroom_light": bedroom_light,
        "living_room_ac": living_room_ac,
        "bedroom_curtain": bedroom_curtain,
        "living_room_light_entity": living_room_light_entity,
        "bedroom_light_entity": bedroom_light_entity,
        "living_room_ac_entity": living_room_ac_entity,
        "bedroom_curtain_entity": bedroom_curtain_entity
    }

async def setup_service():
    """设置LLM服务"""
    service = llm_service()
    
    # 创建设备客户端
    ac = SmartACClient("ac.001", "客厅空调", 8003)
    light = SmartLightClient("light.001", "客厅灯", 8001)
    curtain = SmartCurtainClient("curtain.001", "卧室窗帘", 8004)
    
    # 注册空调控制函数
    service.register_function(
        ac.set_power,
        description="控制空调电源",
        parameters={
            "power": {
                "name": "power",
                "type": "boolean",
                "description": "电源状态",
                "required": True
            }
        }
    )
    logger.info("已注册函数: ac.set_power")
    
    service.register_function(
        ac.set_temperature,
        description="设置空调温度",
        parameters={
            "temperature": {
                "name": "temperature",
                "type": "number",
                "description": "目标温度",
                "required": True,
                "min_value": 16,
                "max_value": 30
            }
        }
    )
    logger.info("已注册函数: ac.set_temperature")
    
    service.register_function(
        ac.set_mode,
        description="设置空调运行模式",
        parameters={
            "mode": {
                "name": "mode",
                "type": "string",
                "description": "运行模式",
                "required": True,
                "enum_values": ["auto", "cool", "heat", "dry", "fan"]
            }
        }
    )
    logger.info("已注册函数: ac.set_mode")
    
    # 注册灯光控制函数
    service.register_function(
        light.set_power,
        description="控制灯光电源",
        parameters={
            "power": {
                "name": "power",
                "type": "boolean",
                "description": "电源状态",
                "required": True
            }
        }
    )
    logger.info("已注册函数: light.set_power")
    
    service.register_function(
        light.set_brightness,
        description="设置灯光亮度",
        parameters={
            "brightness": {
                "name": "brightness",
                "type": "number",
                "description": "亮度百分比",
                "required": True,
                "min_value": 0,
                "max_value": 100
            }
        }
    )
    logger.info("已注册函数: light.set_brightness")
    
    # 注册窗帘控制函数
    service.register_function(
        curtain.set_position,
        description="设置窗帘位置",
        parameters={
            "device_id": {
                "name": "device_id",
                "type": "string",
                "description": "设备ID",
                "required": True
            },
            "position": {
                "name": "position",
                "type": "number",
                "description": "位置百分比",
                "required": True,
                "min_value": 0,
                "max_value": 100
            }
        }
    )
    logger.info("已注册函数: curtain.set_position")
    
    return service

async def print_device_status(devices: List[DeviceInfo]):
    """打印设备状态
    
    Args:
        devices: 设备列表
    """
    # 获取设备状态
    table_data = []
    headers = ["设备名称", "状态", "详细信息"]
    
    for device in devices:
        try:
            # 构造状态信息
            if device.type == "SmartLight":
                name = "🔌 " + device.name
                is_on = device.parameters["power"].current_value
                brightness = device.parameters["brightness"].current_value
                status = "🟢 开启" if is_on else "⚫️ 关闭"
                details = f"💡 亮度: {brightness}%"
            elif device.type == "SmartAC":
                name = "🎛️ " + device.name
                is_on = device.parameters["power"].current_value
                temperature = device.parameters["temperature"].current_value
                mode = device.parameters["mode"].current_value
                status = "🟢 开启" if is_on else "⚫️ 关闭"
                mode_icons = {
                    "cool": "❄️",
                    "heat": "🔥",
                    "auto": "🔄"
                }
                mode_icon = mode_icons.get(mode, "")
                details = f"🌡️ 温度: {temperature}°C, {mode_icon} 模式: {mode}"
            elif device.type == "SmartCurtain":
                name = "🪟 " + device.name
                is_open = device.parameters["power"].current_value
                position = device.parameters["position"].current_value
                status = "🟢 开启" if is_open else "⚫️ 关闭"
                details = f"📏 位置: {position}%"
            else:
                continue
                
            table_data.append([name, status, details])
            
        except Exception as e:
            logger.error(f"获取设备 {device.name} 状态失败: {str(e)}")
            table_data.append([f"❌ {device.name}", "错误", str(e)])
            
    logger.debug(f"表格数据: {table_data}")
    
    # 打印状态表格
    print("\n当前设备状态:")
    print("=" * 80)
    
    if not table_data:
        print("暂无设备状态信息")
        logger.warning("没有设备状态数据被添加到表格中")
    else:
        try:
            # 使用简单的表格格式，避免特殊字符问题
            table = tabulate(
                table_data,
                headers=headers,
                tablefmt="simple",
                stralign="left"
            )
            print(table)
        except Exception as e:
            logger.error(f"格式化设备状态表格失败: {str(e)}")
            # 使用最简单的格式打印
            print(f"{headers[0]:<30} {headers[1]:<15} {headers[2]}")
            print("-" * 80)
            for row in table_data:
                print(f"{row[0]:<30} {row[1]:<15} {row[2]}")
    
    print("=" * 80)

async def process_command(command: str, service: llm_service) -> bool:
    """处理用户指令"""
    logger.info(f"收到用户指令: {command}")
    
    # 特殊指令处理
    if command.lower() == "exit":
        logger.info("用户请求退出")
        return False
    elif command.lower() == "status":
        devices = await register_devices()
        await print_device_status(devices)
        return True
        
    print("\n正在处理您的指令...")
        
    # 通过LLM处理所有指令
    response = ""
    # 获取可用函数列表
    available_functions = []
    for func in function_registry.list_functions():
        func_info = FunctionDefinition(
            name=func.name,
            description=func.description,
            implementation=func.implementation,
            parameters=func.parameters
        )
        available_functions.append(func_info)
        
    # 获取最新设备状态
    devices = await register_devices()
        
    async for response_chunk in service.chat_stream(
        command,
        "test_session",
        functions=available_functions
    ):
        response += response_chunk
        print(response_chunk, end="", flush=True)
        
    print("\n")
    
    # 等待设备状态更新
    logger.info("等待设备状态更新...")
    await asyncio.sleep(1.0)
    
    # 获取最新设备状态
    devices = await register_devices()
    await print_device_status(devices)
    
    return True

async def register_devices() -> List[DeviceInfo]:
    """注册设备
    
    Returns:
        List[DeviceInfo]: 设备列表
    """
    # 创建设备客户端
    devices = [
        SmartLightClient("light.001", "客厅灯", 8001),
        SmartLightClient("light.002", "卧室灯", 8002),
        SmartACClient("ac.001", "客厅空调", 8003),
        SmartCurtainClient("curtain.001", "卧室窗帘", 8004)
    ]
    
    # 获取设备状态
    device_infos = []
    for device in devices:
        try:
            status = await device.get_status()
            logger.info(f"设备 {device.name} 类型: {device.__class__.__name__}")
            logger.info(f"{device.name}状态: {status}")
            
            # 构造设备信息
            parameters = {}
            if isinstance(device, SmartLightClient):
                parameters = {
                    "power": DeviceParameter(
                        type="boolean",
                        description="电源开关状态",
                        current_value=status["is_on"]
                    ),
                    "brightness": DeviceParameter(
                        type="integer",
                        description="亮度值",
                        current_value=status["brightness"],
                        min_value=0,
                        max_value=100,
                        unit="%"
                    )
                }
            elif isinstance(device, SmartACClient):
                parameters = {
                    "power": DeviceParameter(
                        type="boolean",
                        description="电源开关状态",
                        current_value=status["is_on"]
                    ),
                    "temperature": DeviceParameter(
                        type="integer",
                        description="温度值",
                        current_value=status["temperature"],
                        min_value=16,
                        max_value=30,
                        unit="°C"
                    ),
                    "mode": DeviceParameter(
                        type="string",
                        description="运行模式",
                        current_value=status["mode"],
                        enum_values=["auto", "cool", "heat", "dry", "fan"]
                    )
                }
            elif isinstance(device, SmartCurtainClient):
                parameters = {
                    "power": DeviceParameter(
                        type="boolean",
                        description="电源开关状态",
                        current_value=status["is_open"]
                    ),
                    "position": DeviceParameter(
                        type="integer",
                        description="位置值",
                        current_value=status["position"],
                        min_value=0,
                        max_value=100,
                        unit="%"
                    )
                }
                
            device_info = DeviceInfo(
                id=device.device_id,  # 直接使用设备的 ID
                name=device.name,
                type=device.__class__.__name__.replace("Client", ""),
                location="",
                capabilities=[],
                parameters=parameters
            )
            device_infos.append(device_info)
            
        except Exception as e:
            logger.error(f"获取设备 {device.name} 状态失败: {str(e)}")
            
    return device_infos

async def register_functions(llm_service: llm_service):
    """注册控制函数
    
    Args:
        llm_service: LLM服务
    """
    # 创建设备客户端
    ac = SmartACClient("ac.001", "客厅空调", 8003)
    light = SmartLightClient("light.001", "客厅灯", 8001)
    curtain = SmartCurtainClient("curtain.001", "卧室窗帘", 8004)
    
    # 注册空调控制函数
    llm_service.register_function(
        ac.set_power,
        description="控制空调电源",
        parameters={
            "power": {
                "name": "power",
                "type": "boolean",
                "description": "电源状态",
                "required": True
            }
        }
    )
    logger.info("已注册函数: ac.set_power")
    
    llm_service.register_function(
        ac.set_temperature,
        description="设置空调温度",
        parameters={
            "temperature": {
                "name": "temperature",
                "type": "number",
                "description": "目标温度",
                "required": True,
                "min_value": 16,
                "max_value": 30
            }
        }
    )
    logger.info("已注册函数: ac.set_temperature")
    
    llm_service.register_function(
        ac.set_mode,
        description="设置空调运行模式",
        parameters={
            "mode": {
                "name": "mode",
                "type": "string",
                "description": "运行模式",
                "required": True,
                "enum_values": ["auto", "cool", "heat", "dry", "fan"]
            }
        }
    )
    logger.info("已注册函数: ac.set_mode")
    
    # 注册灯光控制函数
    llm_service.register_function(
        light.set_power,
        description="控制灯光电源",
        parameters={
            "power": {
                "name": "power",
                "type": "boolean",
                "description": "电源状态",
                "required": True
            }
        }
    )
    logger.info("已注册函数: light.set_power")
    
    llm_service.register_function(
        light.set_brightness,
        description="设置灯光亮度",
        parameters={
            "brightness": {
                "name": "brightness",
                "type": "number",
                "description": "亮度百分比",
                "required": True,
                "min_value": 0,
                "max_value": 100
            }
        }
    )
    logger.info("已注册函数: light.set_brightness")
    
    # 注册窗帘控制函数
    llm_service.register_function(
        curtain.set_position,
        description="设置窗帘位置",
        parameters={
            "device_id": {
                "name": "device_id",
                "type": "string",
                "description": "设备ID",
                "required": True
            },
            "position": {
                "name": "position",
                "type": "integer",
                "description": "位置值",
                "required": True,
                "min_value": 0,
                "max_value": 100
            }
        }
    )
    logger.info("已注册函数: curtain.set_position")

async def main():
    """主函数"""
    try:
        # 创建LLM服务
        llm_service = await setup_service()
        
        # 注册设备
        devices = await register_devices()
        logger.info(f"获取到的设备列表: {[f'{d.name} ({d.type})' for d in devices]}")
        
        # 等待用户输入
        print("\n请输入指令: ", end="")
        user_input = input().strip()
        
        print("\n正在处理您的指令...")
        logger.info(f"收到用户指令: {user_input}")
        
        # 获取最新设备状态
        devices = await register_devices()
        
        # 处理用户指令
        try:
            # 生成控制动作
            result = await llm_service.execute_intent(user_input, devices)
            print(result)
            
            # 等待设备状态更新
            print("\n等待设备状态更新...")
            await asyncio.sleep(1)
            
            # 打印最新状态
            devices = await register_devices()
            await print_device_status(devices)
            
        except Exception as e:
            logger.error(f"处理指令时出错: {str(e)}")
            print(f"抱歉，处理您的指令时出现错误: {str(e)}")
            
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        print(f"程序运行出错: {str(e)}")
    finally:
        print("正在清理资源...")

if __name__ == "__main__":
    asyncio.run(main()) 