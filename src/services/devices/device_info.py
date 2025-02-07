"""设备信息类"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from .function_definitions import get_device_functions

@dataclass
class DeviceParameter:
    """设备参数"""
    type: str
    description: str
    current_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: Optional[List[str]] = None
    unit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            Dict[str, Any]: 参数字典
        """
        return {
            "type": self.type,
            "description": self.description,
            "current_value": self.current_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "enum_values": self.enum_values,
            "unit": self.unit
        }

@dataclass
class DeviceInfo:
    """设备信息"""
    id: str
    name: str
    type: str
    location: str
    capabilities: List[str]
    parameters: Dict[str, DeviceParameter]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            Dict[str, Any]: 设备信息字典
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "location": self.location,
            "capabilities": self.capabilities,
            "parameters": {
                name: param.to_dict()
                for name, param in self.parameters.items()
            }
        }
        
    def get_functions(self) -> List[Dict[str, Any]]:
        """获取设备可用的控制函数
        
        Returns:
            List[Dict[str, Any]]: 函数列表
        """
        return get_device_functions(self.type) 