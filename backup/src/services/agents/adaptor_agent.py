"""设备适配代理

负责将不同设备的信息和命令转换为系统标准格式。
遵循 AgentDev 指南进行开发，确保：
1. 单一数据源：只处理上游输入
2. 行为确定性：相同输入产生相同输出
3. 安全隔离：不引入外部信息
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..llm.llm_service import LLMService
from ..devices.base import DeviceInfo, DeviceParameter

@dataclass
class AdaptorContext:
    """适配器上下文"""
    timestamp: datetime
    source_info: Dict[str, Any]
    device_schema: Dict[str, Any]
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class AdaptionResult:
    """适配结果"""
    success: bool
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    context: AdaptorContext
    
    def items(self):
        """返回结果字典的items视图
        
        Returns:
            Dict.items: 结果字典的items视图
        """
        if not self.result:
            return {}
        return self.result.items()

class AdaptorAgent:
    """设备适配代理"""
    
    # 设备类型映射表
    DEVICE_TYPE_MAPPING = {
        "MockACClient": "SmartAC",
        "MockLightClient": "SmartLight",
        "MockCurtainClient": "SmartCurtain"
    }
    
    # 功能映射表
    CAPABILITY_MAPPING = {
        "power_control": "set_power",
        "temperature_control": "set_temperature",
        "mode_control": "set_mode",
        "brightness_control": "set_brightness",
        "position_control": "set_position",
        "fan_speed_control": "set_fan_speed",
        "color_control": "set_color"
    }
    
    def __init__(self, llm_service: LLMService):
        """初始化适配器代理
        
        Args:
            llm_service: LLM服务实例
        """
        self.llm_service = llm_service
        self.logger = logging.getLogger(__name__)
        self.device_schema = self._load_device_schema()
        
    def _load_device_schema(self) -> Dict[str, Any]:
        """加载设备模式定义
        
        Returns:
            Dict[str, Any]: 设备模式定义
        """
        return {
            "SmartAC": {
                "capabilities": ["power_control", "temperature_control", "mode_control", "fan_speed_control"],
                "functions": {
                    "set_power": {
                        "type": "boolean",
                        "description": "控制电源开关"
                    },
                    "set_temperature": {
                        "type": "number",
                        "range": [16, 30],
                        "description": "设置温度"
                    },
                    "set_mode": {
                        "type": "enum",
                        "values": ["auto", "cool", "heat", "dry", "fan"],
                        "description": "设置运行模式"
                    },
                    "set_fan_speed": {
                        "type": "number",
                        "range": [1, 3],
                        "description": "设置风速"
                    }
                }
            },
            "SmartLight": {
                "capabilities": ["power_control", "brightness_control", "color_control"],
                "functions": {
                    "set_power": {
                        "type": "boolean",
                        "description": "控制电源开关"
                    },
                    "set_brightness": {
                        "type": "number",
                        "range": [0, 100],
                        "description": "设置亮度"
                    },
                    "set_color": {
                        "type": "string",
                        "description": "设置颜色"
                    }
                }
            },
            "SmartCurtain": {
                "capabilities": ["power_control", "position_control"],
                "functions": {
                    "set_power": {
                        "type": "boolean",
                        "description": "控制电源开关"
                    },
                    "set_position": {
                        "type": "number",
                        "range": [0, 100],
                        "description": "设置窗帘位置"
                    }
                }
            }
        }

    def _map_device_type(self, device_type: str) -> str:
        """映射设备类型
        
        Args:
            device_type: 原始设备类型
            
        Returns:
            str: 标准设备类型
        """
        return self.DEVICE_TYPE_MAPPING.get(device_type, device_type)

    def _map_capabilities(self, capabilities: List[str]) -> Dict[str, Any]:
        """映射设备功能
        
        Args:
            capabilities: 设备功能列表
            
        Returns:
            Dict[str, Any]: 标准功能映射
        """
        functions = {}
        for cap in capabilities:
            if cap in self.CAPABILITY_MAPPING:
                func_name = self.CAPABILITY_MAPPING[cap]
                functions[func_name] = {"type": "auto"}
        return functions

    def _build_parameters(
        self,
        device_type: str,
        functions: Dict[str, Any]
    ) -> Dict[str, DeviceParameter]:
        """构建设备参数列表
        
        Args:
            device_type: 设备类型
            functions: 设备功能
            
        Returns:
            Dict[str, DeviceParameter]: 参数列表
        """
        parameters = {}
        schema = self.device_schema[device_type]["functions"]
        
        for name, func in functions.items():
            if name not in schema:
                continue
                
            func_schema = schema[name]
            parameters[name] = DeviceParameter(
                name=name,
                type=func_schema["type"],
                description=func_schema["description"],
                current_value=None,  # 初始值为空
                min_value=func_schema.get("range", [None, None])[0],
                max_value=func_schema.get("range", [None, None])[1],
                enum_values=func_schema.get("values")
            )
            
        return parameters

    async def adapt_device(self, device_info: DeviceInfo) -> AdaptionResult:
        """适配设备信息
        
        Args:
            device_info: 设备信息
            
        Returns:
            AdaptionResult: 适配结果
        """
        try:
            # 创建上下文
            context = AdaptorContext(
                timestamp=datetime.now(),
                source_info=device_info.to_dict(),
                device_schema=self.device_schema
            )
            
            # 记录输入日志
            self.logger.info(f"[{context.trace_id}] Adapting device info: {device_info}")
            
            # 直接映射设备类型
            device_type = self._map_device_type(device_info.type)
            if device_type not in self.device_schema:
                raise ValueError(f"Unsupported device type: {device_type}")
            
            # 直接映射设备功能
            standard_functions = self._map_capabilities(device_info.capabilities)
            
            # 构建标准设备信息
            result = DeviceInfo(
                id=device_info.id,
                name=device_info.name,
                type=device_type,
                location=device_info.location,
                status=device_info.status,
                parameters=self._build_parameters(device_type, standard_functions),
                capabilities=self.device_schema[device_type]["capabilities"]
            )
            
            # 记录输出日志
            self.logger.info(f"[{context.trace_id}] Adapted device info: {result}")
            
            return AdaptionResult(
                success=True,
                result=result.to_dict(),
                error=None,
                context=context
            )
            
        except Exception as e:
            error_msg = f"Failed to adapt device info: {str(e)}"
            self.logger.error(f"[{context.trace_id}] {error_msg}")
            
            return AdaptionResult(
                success=False,
                result=None,
                error=error_msg,
                context=context
            )