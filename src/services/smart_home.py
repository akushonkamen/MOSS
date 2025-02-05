"""智能家居控制器"""
from typing import List, Dict, Any, Optional
import logging
from .llm.decoderAgent import DecoderAgent
from .llm.intent import DeviceIntent
from .llm.expertAgent import ExpertAgent, ActionResponse
from .devices.base import DeviceInfo
from .function_calling.registry import FunctionRegistry
from .devices.functions import register_device_functions
from .llm.example_functions import register_example_functions

logger = logging.getLogger(__name__)

class SmartHomeController:
    """智能家居控制器"""
    
    def __init__(
        self,
        api_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3.1:latest"
    ):
        """初始化智能家居控制器
        
        Args:
            api_url: LLM API地址
            model_name: LLM模型名称
        """
        self.decoder = DecoderAgent()
        self.expert = ExpertAgent(api_url=api_url, model_name=model_name)
        self.function_registry = FunctionRegistry()
        self.devices: Dict[str, DeviceInfo] = {}
        
        # 注册设备控制函数
        register_device_functions(self.function_registry)
        # 注册示例函数
        register_example_functions(self.function_registry)
        
    def register_device(self, device: DeviceInfo) -> None:
        """注册设备
        
        Args:
            device: 设备信息
        """
        self.devices[device.id] = device
        logger.info(f"注册设备: {device.id} ({device.name})")
        
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[DeviceInfo]: 设备信息
        """
        return self.devices.get(device_id)
        
    def list_devices(self) -> List[DeviceInfo]:
        """获取所有设备列表
        
        Returns:
            List[DeviceInfo]: 设备列表
        """
        return list(self.devices.values())
        
    async def process_command(self, user_input: str) -> str:
        """处理用户命令
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: 处理结果
        """
        try:
            # 获取可用设备列表
            devices = self.list_devices()
            if not devices:
                return "当前没有可用的设备"
                
            # 理解用户意图
            intent = await self.decoder.understand_intent(user_input, devices)
            logger.info(f"识别到的意图: {intent}")
            
            # 如果意图未知，返回错误信息
            if intent.intent_type == "unknown":
                return "无法理解命令"
                
            # 获取目标设备
            device = self.get_device(intent.device_id)
            if not device:
                return f"未找到设备"
                
            # 获取可用函数列表
            available_functions = []
            for func in self.function_registry.list_functions():
                func_info = {
                    "name": func.name,
                    "description": func.description,
                    "parameters": {}
                }
                if func.parameters:
                    for param_name, param_info in func.parameters.items():
                        func_info["parameters"][param_name] = {
                            "type": param_info["type"],
                            "description": param_info["description"],
                            "required": param_info.get("required", True),
                            "default": param_info.get("default"),
                            "enum_values": param_info.get("enum_values")
                        }
                available_functions.append(func_info)
                
            # 生成控制动作
            action = await self.expert.generate_actions(
                intent.dict(),
                device.to_dict(),
                available_functions
            )
            logger.info(f"生成的动作: {action}")
            
            # 执行函数调用
            results = []
            for call in action.function_calls:
                func_def = self.function_registry.get_function(call.name)
                if func_def:
                    logger.info(f"执行函数: {call.name}，参数: {call.parameters}")
                    try:
                        result = await func_def.implementation(**call.parameters)
                        logger.info(f"函数执行结果: {result}")
                        results.append(result)
                    except ValueError as e:
                        # 参数验证错误
                        error_msg = str(e)
                        if "温度" in error_msg:
                            return "温度超出范围"
                        elif "亮度" in error_msg:
                            return "亮度超出范围"
                        elif "位置" in error_msg:
                            return "位置超出范围"
                        return error_msg
                    except Exception as e:
                        logger.error(f"执行函数失败: {str(e)}")
                        return f"执行命令失败: {str(e)}"
                else:
                    logger.warning(f"未找到函数: {call.name}")
                    return f"不支持的操作: {call.name}"
                    
            # 返回执行结果
            if results:
                return "\n".join(results)
            return action.explanation
            
        except Exception as e:
            logger.error(f"处理命令失败: {str(e)}")
            error_msg = str(e)
            if "未找到设备" in error_msg:
                return "未找到设备"
            elif "无法理解" in error_msg:
                return "无法理解命令"
            return "抱歉，处理您的命令时出错了" 