"""智能窗帘客户端实现"""
from typing import Dict, Any, List
from ..base import DeviceClient, DeviceError, DeviceParameter, DeviceInfo

class CurtainClient(DeviceClient):
    """智能窗帘客户端"""
    
    def __init__(self, device_id: str, name: str, location: str, port: int):
        """初始化智能窗帘客户端
        
        Args:
            device_id: 设备ID
            name: 设备名称
            location: 设备位置
            port: 设备端口
        """
        super().__init__(device_id, name, location, port)
        
    async def get_initial_state(self) -> Dict[str, Any]:
        """获取初始状态"""
        return {
            "is_on": True,  # 窗帘总是在线
            "position": 0   # 0表示完全关闭，100表示完全打开
        }
        
    async def _validate_state(self, state: Dict[str, Any]) -> None:
        """验证状态
        
        Args:
            state: 要验证的状态
            
        Raises:
            DeviceError: 状态无效
        """
        if "position" in state:
            position = state["position"]
            if not isinstance(position, (int, float)):
                raise DeviceError("位置必须是数字")
            if not 0 <= position <= 100:
                raise DeviceError("位置必须在0-100之间")
                
    async def get_capabilities(self) -> List[str]:
        """获取设备能力列表"""
        return [
            "position_control"
        ]
        
    def get_device_info(self) -> DeviceInfo:
        """获取设备信息"""
        # 获取当前状态
        state = self._state
        
        # 构建参数列表
        parameters = {
            "position": DeviceParameter(
                name="position",
                type="number",
                description="窗帘位置",
                current_value=state.get("position", 0),
                min_value=0,
                max_value=100,
                unit="%"
            )
        }
        
        return DeviceInfo(
            id=self.device_id,
            name=self.name,
            type="Curtain",
            location=self.location,
            status=self.status,
            parameters=parameters,
            capabilities=self.get_capabilities()
        )
        
    # 设备特定的控制方法
    async def set_position(self, position: int) -> bool:
        """设置窗帘位置
        
        Args:
            position: 目标位置(0-100)
            
        Returns:
            bool: 是否设置成功
        """
        return await self.set_state({
            "position": position
        }) 