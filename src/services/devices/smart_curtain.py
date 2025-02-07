"""智能窗帘设备"""
from typing import Dict, Any
from .base import DeviceClient

class SmartCurtainClient(DeviceClient):
    """智能窗帘设备客户端"""
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化智能窗帘设备
        
        Args:
            device_id: 设备ID
            name: 设备名称
            port: 设备端口
        """
        super().__init__(device_id, name, port)
        
    async def get_initial_state(self) -> Dict[str, Any]:
        """获取初始状态
        
        Returns:
            Dict[str, Any]: 初始状态
        """
        return {
            "is_open": False,
            "position": 0
        }
        
    async def get_state(self) -> Dict[str, Any]:
        """获取设备状态
        
        Returns:
            Dict[str, Any]: 设备状态
        """
        return await super().get_state()
        
    async def set_state(self, state: Dict[str, Any]) -> bool:
        """设置设备状态
        
        Args:
            state: 设备状态
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 验证状态
            if "is_open" in state:
                state["is_open"] = bool(state["is_open"])
            if "position" in state:
                position = int(state["position"])
                if not 0 <= position <= 100:
                    raise ValueError("位置必须在0-100之间")
                    
            # 更新状态
            return await super().set_state(state)
            
        except Exception as e:
            self.logger.error(f"设置设备 {self.name} 状态失败: {str(e)}")
            return False 