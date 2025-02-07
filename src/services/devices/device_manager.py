"""设备管理器"""
import logging
from typing import List, Dict, Any, Optional
from .device_info import DeviceInfo
from .smart_light import SmartLightClient
from .smart_ac import SmartACClient
from .smart_curtain import SmartCurtainClient

class DeviceManager:
    """设备管理器"""
    
    def __init__(self):
        """初始化设备管理器"""
        self.logger = logging.getLogger(__name__)
        self.devices = []
        
    async def initialize(self):
        """初始化设备管理器"""
        try:
            # 创建设备客户端
            self.devices = [
                SmartLightClient("light.001", "客厅灯", 8001),
                SmartLightClient("light.002", "卧室灯", 8002),
                SmartACClient("ac.001", "客厅空调", 8003),
                SmartCurtainClient("curtain.001", "卧室窗帘", 8004)
            ]
            
            # 初始化所有设备
            for device in self.devices:
                await device.initialize()
                
            self.logger.info(f"设备管理器初始化完成，共注册 {len(self.devices)} 个设备")
            
        except Exception as e:
            self.logger.error(f"设备管理器初始化失败: {str(e)}")
            raise
            
    async def get_all_devices(self) -> List[Any]:
        """获取所有设备
        
        Returns:
            List[Any]: 设备列表
        """
        return self.devices
        
    async def get_device(self, device_id: str) -> Optional[Any]:
        """获取指定设备
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[Any]: 设备对象，如果不存在则返回None
        """
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None 