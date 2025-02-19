"""位置管理器

负责管理特定位置的设备。
"""
from typing import Dict, List, Optional
import logging
from ..base.device_base import Device

class LocationManager:
    """位置管理器"""
    
    def __init__(self, location: str):
        """初始化位置管理器
        
        Args:
            location: 位置名称
        """
        self.location = location
        self._devices: Dict[str, Device] = {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{location}")
        
    def register_device(self, device: Device) -> bool:
        """注册设备
        
        Args:
            device: 设备实例
            
        Returns:
            bool: 是否注册成功
        """
        try:
            device_id = device.device_id
            
            # 检查设备位置是否匹配
            if device.location != self.location:
                self.logger.error(f"设备位置不匹配: {device.location} != {self.location}")
                return False
                
            # 检查设备是否已注册
            if device_id in self._devices:
                self.logger.warning(f"设备已注册: {device_id}")
                return False
                
            # 添加到设备列表
            self._devices[device_id] = device
            self.logger.info(f"设备 {device.name} 注册到位置 {self.location}")
            return True
            
        except Exception as e:
            self.logger.error(f"注册设备失败: {str(e)}")
            return False
            
    def get_device(self, device_id: str) -> Optional[Device]:
        """获取设备实例
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Device]: 设备实例
        """
        return self._devices.get(device_id)
        
    def get_all_devices(self) -> List[Device]:
        """获取所有设备
        
        Returns:
            List[Device]: 设备列表
        """
        return list(self._devices.values())
        
    def get_devices_by_type(self, device_type: str) -> List[Device]:
        """获取指定类型的设备
        
        Args:
            device_type: 设备类型
            
        Returns:
            List[Device]: 设备列表
        """
        return [
            device for device in self._devices.values()
            if device.__class__.__name__ == device_type
        ]
        
    def get_device_count(self) -> int:
        """获取设备数量
        
        Returns:
            int: 设备数量
        """
        return len(self._devices)
        
    def remove_device(self, device_id: str) -> bool:
        """移除设备
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 是否移除成功
        """
        try:
            if device_id in self._devices:
                device = self._devices.pop(device_id)
                self.logger.info(f"设备 {device.name} 从位置 {self.location} 移除")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"移除设备失败: {str(e)}")
            return False 