"""智能灯客户端实现"""
from typing import Dict, Any, List
from ..base import DeviceClient, DeviceError, DeviceParameter, DeviceInfo

class SmartLightClient(DeviceClient):
    """智能灯客户端"""
    
    def __init__(self, device_id: str, name: str, location: str, port: int):
        """初始化智能灯客户端
        
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
            "is_on": False,
            "brightness": 50
        }
        
    async def _validate_state(self, state: Dict[str, Any]) -> None:
        """验证状态
        
        Args:
            state: 要验证的状态
            
        Raises:
            DeviceError: 状态无效
        """
        if "brightness" in state:
            brightness = state["brightness"]
            if not isinstance(brightness, (int, float)):
                raise DeviceError("亮度必须是数字")
            if not 0 <= brightness <= 100:
                raise DeviceError("亮度必须在0-100之间")
                
    async def get_capabilities(self) -> List[str]:
        """获取设备能力列表"""
        return [
            "power_control",
            "brightness_control"
        ]
        
    def get_device_info(self) -> DeviceInfo:
        """获取设备信息"""
        # 获取当前状态
        state = self._state
        
        # 构建参数列表
        parameters = {
            "power": DeviceParameter(
                name="power",
                type="boolean",
                description="电源状态",
                current_value=state.get("is_on", False)
            ),
            "brightness": DeviceParameter(
                name="brightness",
                type="number",
                description="亮度设置",
                current_value=state.get("brightness", 50),
                min_value=0,
                max_value=100,
                unit="%"
            )
        }
        
        return DeviceInfo(
            id=self.device_id,
            name=self.name,
            type="Light",
            location=self.location,
            status=self.status,
            parameters=parameters,
            capabilities=self.get_capabilities()
        )
        
    # 设备特定的控制方法
    async def set_brightness(self, brightness: int) -> bool:
        """设置亮度
        
        Args:
            brightness: 目标亮度(0-100)
            
        Returns:
            bool: 是否设置成功
        """
        return await self.set_state({
            "brightness": brightness,
            "is_on": brightness > 0  # 亮度为0时自动关闭
        }) 