from typing import Dict, Any, List
from ..core.entity import Entity, EntityCategory, EntityState, ServiceCall
import logging

logger = logging.getLogger(__name__)

class LightEntity(Entity):
    """智能灯实体"""
    
    def __init__(self, entity_id: str, name: str):
        """初始化智能灯实体
        
        Args:
            entity_id: 实体ID
            name: 实体名称
        """
        super().__init__(
            entity_id=entity_id,
            name=name,
            category=EntityCategory.LIGHT,
            supported_features=["turn_on", "turn_off", "brightness"]
        )
        self._is_on = False
        self._brightness = 100
        
    async def update(self) -> None:
        """更新实体状态"""
        self._state.state = "on" if self._is_on else "off"
        self._state.attributes.update({
            "brightness": self._brightness,
            "is_on": self._is_on
        })
        
    def get_service_schema(self) -> Dict[str, Any]:
        """获取服务定义"""
        return {
            "turn_on": {
                "description": "打开灯",
                "fields": {}
            },
            "turn_off": {
                "description": "关闭灯",
                "fields": {}
            },
            "set_brightness": {
                "description": "设置亮度",
                "fields": {
                    "brightness": {
                        "description": "亮度值(0-100)",
                        "type": "integer",
                        "min": 0,
                        "max": 100
                    }
                }
            }
        }
        
    async def call_service(self, call: ServiceCall) -> None:
        """调用服务
        
        Args:
            call: 服务调用信息
        """
        if call.service == "turn_on":
            self._is_on = True
            await self.update()
            
        elif call.service == "turn_off":
            self._is_on = False
            await self.update()
            
        elif call.service == "set_brightness":
            brightness = call.data.get("brightness", 100)
            if not 0 <= brightness <= 100:
                raise ValueError("亮度必须在0-100之间")
            self._brightness = brightness
            self._is_on = brightness > 0
            await self.update()
            
        else:
            raise ValueError(f"不支持的服务: {call.service}")
            
def setup_platform(registry, config: Dict[str, Any]) -> None:
    """设置智能灯平台
    
    Args:
        registry: 实体注册表
        config: 配置信息
    """
    # 从配置创建实体
    for device_config in config.get("devices", []):
        try:
            entity = LightEntity(
                entity_id=device_config["id"],
                name=device_config["name"]
            )
            registry.register(entity)
            logger.info(f"注册智能灯实体: {entity.entity_id}")
        except Exception as e:
            logger.error(f"注册智能灯实体失败: {str(e)}") 