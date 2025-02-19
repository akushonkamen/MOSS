"""函数查询器
用于从统一设备管理器获取设备的控制函数
"""
import logging
from typing import List, Dict, Any, Optional
from src.services.devices.managers.unified_device_manager import unified_device_manager
from src.services.devices.base import DeviceInfo

logger = logging.getLogger(__name__)

class FunctionFinder:
    """函数查询器"""
    
    @staticmethod
    async def get_device_functions(device_id: str) -> List[Dict[str, Any]]:
        """获取设备的控制函数
        
        Args:
            device_id: 设备ID
            
        Returns:
            List[Dict[str, Any]]: 控制函数列表
        """
        try:
            # 从统一设备管理器获取设备信息
            device_info = unified_device_manager.get_device_info(device_id)
            if not device_info:
                logger.error(f"未找到设备: {device_id}")
                return []
                
            # 获取设备类型
            device_type = device_info.type
            
            # 构建函数列表
            functions = []
            
            # 根据设备类型添加通用函数
            if "power" in device_info.parameters:
                functions.append({
                    "name": f"{device_type}.set_power",
                    "description": "控制设备电源",
                    "parameters": {
                        "power": {
                            "type": "boolean",
                            "description": "电源状态",
                            "required": True
                        }
                    }
                })
                
            # 根据设备参数添加特定函数
            if "brightness" in device_info.parameters:
                functions.append({
                    "name": f"{device_type}.set_brightness",
                    "description": "设置设备亮度",
                    "parameters": {
                        "brightness": {
                            "type": "integer",
                            "description": "亮度值",
                            "required": True,
                            "minimum": 0,
                            "maximum": 100
                        }
                    }
                })
                
            if "temperature" in device_info.parameters:
                functions.append({
                    "name": f"{device_type}.set_temperature",
                    "description": "设置设备温度",
                    "parameters": {
                        "temperature": {
                            "type": "integer",
                            "description": "温度值",
                            "required": True,
                            "minimum": 16,
                            "maximum": 30
                        }
                    }
                })
                
            if "mode" in device_info.parameters:
                functions.append({
                    "name": f"{device_type}.set_mode",
                    "description": "设置设备模式",
                    "parameters": {
                        "mode": {
                            "type": "string",
                            "description": "运行模式",
                            "required": True,
                            "enum_values": ["auto", "cool", "heat", "dry", "fan"]
                        }
                    }
                })
                
            if "position" in device_info.parameters:
                functions.append({
                    "name": f"{device_type}.set_position",
                    "description": "设置设备位置",
                    "parameters": {
                        "position": {
                            "type": "integer",
                            "description": "位置值",
                            "required": True,
                            "minimum": 0,
                            "maximum": 100
                        }
                    }
                })
                
            logger.debug(f"设备 {device_id} 的可用函数: {functions}")
            return functions
            
        except Exception as e:
            logger.error(f"获取设备 {device_id} 的控制函数失败: {str(e)}")
            return [] 