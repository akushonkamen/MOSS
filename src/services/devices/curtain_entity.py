from typing import Dict, Any
from ..core.entity import Entity, EntityCategory, ServiceCall

class CurtainEntity(Entity):
    """窗帘实体"""
    
    def __init__(self, entity_id: str, name: str):
        """初始化窗帘实体
        
        Args:
            entity_id: 实体ID
            name: 实体名称
        """
        super().__init__(
            entity_id=entity_id,
            name=name,
            category=EntityCategory.COVER,
            supported_features=["turn_on", "turn_off", "position"]
        )
        self._is_on = False
        self._position = 0  # 0: 完全关闭, 100: 完全打开
        
    async def update(self) -> None:
        """更新实体状态"""
        self._state.state = "on" if self._is_on else "off"
        self._state.attributes.update({
            "position": self._position,
            "is_on": self._is_on
        })
        
    def get_service_schema(self) -> Dict[str, Any]:
        """获取服务定义"""
        return {
            "turn_on": {
                "description": "打开窗帘",
                "fields": {}
            },
            "turn_off": {
                "description": "关闭窗帘",
                "fields": {}
            },
            "set_position": {
                "description": "设置位置",
                "fields": {
                    "position": {
                        "description": "位置百分比(0-100)",
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
            self._position = 100
            await self.update()
            
        elif call.service == "turn_off":
            self._is_on = False
            self._position = 0
            await self.update()
            
        elif call.service == "set_position":
            position = call.data.get("position", 0)
            if not 0 <= position <= 100:
                raise ValueError("位置必须在0-100之间")
            self._position = position
            self._is_on = position > 0
            await self.update()
            
        else:
            raise ValueError(f"不支持的服务: {call.service}") 