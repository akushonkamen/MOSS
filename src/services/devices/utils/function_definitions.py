"""设备函数定义

此模块定义了各种设备类型的控制函数。
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def get_device_functions(device_type: str) -> List[Dict[str, Any]]:
    """获取设备可用的控制函数
    
    Args:
        device_type: 设备类型
        
    Returns:
        List[Dict[str, Any]]: 函数列表
    """
    logger.debug(f"正在获取设备类型 {device_type} 的函数定义")
    
    # 基础控制函数
    function_name = f"{device_type}.set_power"
    logger.debug(f"构建电源控制函数名称: {function_name}")
    
    functions = [{
        "name": function_name,
        "description": "设置设备电源状态",
        "parameters": {
            "device_id": {
                "type": "string",
                "description": "设备ID"
            },
            "power": {
                "type": "boolean",
                "description": "电源状态(true/false)"
            }
        }
    }]
    
    # 根据设备类型添加特定函数
    if device_type == "SmartLight":
        brightness_function = f"{device_type}.set_brightness"
        logger.debug(f"添加亮度控制函数: {brightness_function}")
        functions.extend([
            {
                "name": brightness_function,
                "description": "设置灯光亮度",
                "parameters": {
                    "device_id": {
                        "type": "string",
                        "description": "设备ID"
                    },
                    "brightness": {
                        "type": "integer",
                        "description": "亮度值(0-100)",
                        "minimum": 0,
                        "maximum": 100
                    }
                }
            }
        ])
    elif device_type == "SmartAC":
        temp_function = f"{device_type}.set_temperature"
        mode_function = f"{device_type}.set_mode"
        logger.debug(f"添加温度控制函数: {temp_function}")
        logger.debug(f"添加模式控制函数: {mode_function}")
        functions.extend([
            {
                "name": temp_function,
                "description": "设置空调温度",
                "parameters": {
                    "device_id": {
                        "type": "string",
                        "description": "设备ID"
                    },
                    "temperature": {
                        "type": "integer",
                        "description": "温度值(16-30)",
                        "minimum": 16,
                        "maximum": 30
                    }
                }
            },
            {
                "name": mode_function,
                "description": "设置空调模式",
                "parameters": {
                    "device_id": {
                        "type": "string",
                        "description": "设备ID"
                    },
                    "mode": {
                        "type": "string",
                        "description": "工作模式",
                        "enum": ["cool", "heat", "auto", "dry", "fan"]
                    }
                }
            }
        ])
    elif device_type == "SmartCurtain":
        position_function = f"{device_type}.set_position"
        logger.debug(f"添加位置控制函数: {position_function}")
        functions.extend([
            {
                "name": position_function,
                "description": "设置窗帘位置",
                "parameters": {
                    "device_id": {
                        "type": "string",
                        "description": "设备ID"
                    },
                    "position": {
                        "type": "integer",
                        "description": "位置(0-100)",
                        "minimum": 0,
                        "maximum": 100
                    }
                }
            }
        ])
    
    logger.debug(f"设备类型 {device_type} 的所有函数: {[f['name'] for f in functions]}")
    return functions 