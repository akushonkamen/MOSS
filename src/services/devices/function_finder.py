"""函数查找器

负责查找和管理设备的控制函数。
"""
import logging
from typing import Dict, Any, List, Optional
from .managers.unified_device_manager import unified_device_manager

class FunctionFinder:
    """函数查找器类"""
    
    @staticmethod
    async def find_device_by_name(device_name: str) -> Optional[str]:
        """根据设备名称查找设备ID
        
        Args:
            device_name: 设备名称
            
        Returns:
            Optional[str]: 设备ID
        """
        try:
            # 获取所有设备
            devices = await unified_device_manager.get_all_devices()
            
            # 查找匹配的设备
            for device_id, device in devices.items():
                if device.get("name") == device_name:
                    return device_id
                    
            return None
            
        except Exception as e:
            logging.getLogger("function_finder").error(f"查找设备失败: {str(e)}")
            return None
            
    @staticmethod
    async def get_device_functions(device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备的控制函数
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Dict[str, Any]]: 函数字典
        """
        try:
            # 获取设备信息
            device = await unified_device_manager.get_device(device_id)
            if not device:
                return None
                
            # 返回设备的函数列表
            return device.get("functions", {})
            
        except Exception as e:
            logging.getLogger("function_finder").error(f"获取设备函数失败: {str(e)}")
            return None
            
    @staticmethod
    async def get_all_device_names() -> List[str]:
        """获取所有设备名称
        
        Returns:
            List[str]: 设备名称列表
        """
        try:
            # 获取所有设备
            devices = await unified_device_manager.get_all_devices()
            
            # 提取设备名称
            return [device.get("name", "") for device in devices.values()]
            
        except Exception as e:
            logging.getLogger("function_finder").error(f"获取设备名称失败: {str(e)}")
            return [] 