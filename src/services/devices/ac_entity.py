from dataclasses import dataclass
from typing import Dict, Any, Optional
from ..core.entity import Entity, EntityCategory
from .base import registry as device_registry

@dataclass
class ServiceCall:
    """服务调用信息"""
    service: str
    data: Optional[Dict[str, Any]] = None

class ACEntity(Entity):
    """空调实体"""
    
    def __init__(self, entity_id: str, name: str):
        """初始化空调实体
        
        Args:
            entity_id: 实体ID
            name: 实体名称
        """
        super().__init__(
            entity_id=entity_id,
            name=name,
            category=EntityCategory.CLIMATE,
            supported_features=["turn_on", "turn_off", "temperature", "mode"]
        )
        self._is_on = False
        self._temperature = 26
        self._mode = "auto"
        
    async def update(self) -> None:
        """更新实体状态"""
        self._state.state = "on" if self._is_on else "off"
        self._state.attributes.update({
            "temperature": self._temperature,
            "mode": self._mode,
            "is_on": self._is_on
        })
        
        # 同步状态到设备客户端
        device = device_registry.get_device(self.entity_id)
        if device:
            await device.update_state({
                "is_on": self._is_on,
                "temperature": self._temperature,
                "mode": self._mode
            })
        
    def get_service_schema(self) -> Dict[str, Any]:
        """获取服务定义"""
        return {
            "turn_on": {
                "description": "打开空调",
                "fields": {}
            },
            "turn_off": {
                "description": "关闭空调",
                "fields": {}
            },
            "set_temperature": {
                "description": "设置温度",
                "fields": {
                    "temperature": {
                        "description": "目标温度(16-30)",
                        "type": "number",
                        "min": 16,
                        "max": 30
                    }
                }
            },
            "set_mode": {
                "description": "设置模式",
                "fields": {
                    "mode": {
                        "description": "运行模式",
                        "type": "string",
                        "enum": ["cool", "heat", "auto"]
                    }
                }
            }
        }
        
    async def call_service(self, call: Dict[str, Any]) -> None:
        """调用服务
        
        Args:
            call: 服务调用信息
        """
        # 转换为 ServiceCall 对象
        service_call = ServiceCall(
            service=call["service"],
            data=call.get("data", {})
        )
        
        if service_call.service == "turn_on":
            self._is_on = True
            await self.update()
            
        elif service_call.service == "turn_off":
            self._is_on = False
            await self.update()
            
        elif service_call.service == "set_temperature":
            temperature = service_call.data.get("temperature", self._temperature)
            if not 16 <= temperature <= 30:
                raise ValueError("温度必须在16-30之间")
            self._temperature = temperature
            self._is_on = True
            await self.update()
            
        elif service_call.service == "set_mode":
            mode = service_call.data.get("mode", self._mode)
            if mode not in ["cool", "heat", "auto"]:
                raise ValueError("不支持的模式")
            self._mode = mode
            self._is_on = True
            await self.update()
            
        else:
            raise ValueError(f"不支持的服务: {service_call.service}")

    async def set_mode(self, mode: str) -> bool:
        """设置模式
        
        Args:
            mode: 运行模式 (cool/heat/auto)
            
        Returns:
            bool: 是否设置成功
        """
        if mode not in ["cool", "heat", "auto"]:
            raise ValueError(f"不支持的模式: {mode}")
            
        # 获取当前状态
        device = device_registry.get_device(self.entity_id)
        if device:
            current_status = await device.get_status()
            current_temp = current_status["temperature"]
            
            # 设置新状态
            self._mode = mode
            self._is_on = True
            self._temperature = current_temp  # 保持当前温度
            
            # 更新状态
            await self.update()
            return True
            
        return False 