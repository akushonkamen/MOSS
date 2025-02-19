"""意图模型

定义意图的数据结构和相关操作。
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Intent:
    """意图数据类"""
    
    device_name: str
    """设备名称"""
    
    action: str
    """动作名称"""
    
    parameters: Dict[str, Any]
    """参数字典"""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['Intent']:
        """从字典创建意图对象
        
        Args:
            data: 字典数据
            
        Returns:
            Optional[Intent]: 意图对象
        """
        try:
            return cls(
                device_name=data["device_name"],
                action=data["action"],
                parameters=data.get("parameters", {})
            )
        except (KeyError, TypeError):
            return None
            
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            Dict[str, Any]: 字典数据
        """
        return {
            "device_name": self.device_name,
            "action": self.action,
            "parameters": self.parameters
        } 