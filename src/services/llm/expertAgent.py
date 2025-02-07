"""动作生成智能体"""
from typing import List, Dict, Any, Optional
import aiohttp
import json
import logging
import re
from dataclasses import dataclass
from src.services.devices.device_info import DeviceInfo
from .intent import DeviceIntent, IntentParameter, IntentType
from ..agents import BaseAgent, AgentType, AgentStatus, AgentCapability, AgentMetrics
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class FunctionCall:
    """函数调用"""
    name: str
    parameters: Dict[str, Any]

@dataclass
class ActionResponse:
    """动作响应"""
    function_calls: List[FunctionCall]
    explanation: str

class ExpertAgent(BaseAgent):
    """动作生成智能体"""
    
    def __init__(self, agent_id: str, api_url: str = "http://localhost:11434/api/chat", model_name: str = "llama3.1:latest"):
        """初始化动作生成智能体
        
        Args:
            agent_id: 智能体ID
            api_url: LLM API地址
            model_name: 模型名称
        """
        super().__init__(agent_id, AgentType.EXPERT)
        self.api_url = api_url
        self.model_name = model_name
        self._initialized = False
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """异步初始化"""
        if not self._initialized:
            await self.register_base_capabilities()
            self._initialized = True
            
    async def register_base_capabilities(self):
        """注册基础能力
        
        注册代理的基础能力，包括：
        1. 动作生成能力
        2. 设备控制能力
        3. 场景控制能力
        """
        try:
            # 注册动作生成能力
            await self.register_capability(
                AgentCapability(
                    name="action_generation",
                    description="Generate device control actions based on user intent",
                    parameters={
                        "intent": "User intent data",
                        "device": "Device information"
                    },
                    returns={
                        "actions": "List of control actions",
                        "response": "Response information"
                    }
                )
            )
            
            # 注册设备控制能力
            await self.register_capability(
                AgentCapability(
                    name="device_control",
                    description="Control devices with specific commands",
                    parameters={
                        "device_id": "Target device ID",
                        "command": "Control command",
                        "parameters": "Command parameters"
                    },
                    returns={
                        "success": "Whether the control was successful",
                        "message": "Control result message"
                    }
                )
            )
            
            # 注册场景控制能力
            await self.register_capability(
                AgentCapability(
                    name="scene_control",
                    description="Control multiple devices in a scene",
                    parameters={
                        "scene_id": "Target scene ID",
                        "actions": "List of scene actions"
                    },
                    returns={
                        "success": "Whether the scene control was successful",
                        "message": "Scene control result message"
                    }
                )
            )
            
            self.logger.info("Base capabilities registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register base capabilities: {str(e)}")
            return False
        
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入数据
        
        Args:
            input_data: 输入数据，包含用户意图和设备信息
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 验证输入数据
            if not isinstance(input_data, dict):
                raise ValueError("Input data must be a dictionary")
                
            required_fields = ["intent", "device"]
            if not all(field in input_data for field in required_fields):
                raise ValueError(f"Input data missing required fields: {required_fields}")
                
            # 更新状态
            self.status = AgentStatus.PROCESSING
            
            # 记录开始时间
            start_time = self.get_current_time()
            
            # 生成控制指令
            result = await self.generate_actions(
                intent=input_data["intent"],
                device=input_data["device"]
            )
            
            # 更新状态
            self.status = AgentStatus.IDLE
            
            # 更新指标
            end_time = self.get_current_time()
            self.update_metrics(
                success=True if result["actions"] else False,
                processing_time=end_time - start_time
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in process: {str(e)}")
            self.status = AgentStatus.ERROR
            return {
                "actions": [],
                "response": {
                    "type": "error",
                    "content": f"Processing error: {str(e)}",
                    "status": "failed"
                }
            }
            
    async def learn(self, feedback_data: Dict[str, Any]) -> bool:
        """从反馈中学习
        
        Args:
            feedback_data: 反馈数据，包含执行结果和用户反馈
            
        Returns:
            bool: 学习是否成功
        """
        try:
            # 验证反馈数据
            if not isinstance(feedback_data, dict):
                raise ValueError("Feedback data must be a dictionary")
                
            required_fields = ["execution_result", "user_feedback"]
            if not all(field in feedback_data for field in required_fields):
                raise ValueError(f"Feedback data missing required fields: {required_fields}")
                
            # 更新状态
            self.status = AgentStatus.LEARNING
            
            # 记录开始时间
            start_time = self.get_current_time()
            
            # TODO: 实现学习逻辑
            # 1. 分析执行结果
            # 2. 评估用户反馈
            # 3. 更新内部模型
            # 4. 优化决策策略
            
            # 更新状态
            self.status = AgentStatus.IDLE
            
            # 更新指标
            end_time = self.get_current_time()
            self.update_metrics(
                success=True,
                processing_time=end_time - start_time
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in learn: {str(e)}")
            self.status = AgentStatus.ERROR
            return False
            
    async def evolve(self, evolution_data: Dict[str, Any]) -> bool:
        """进化能力
        
        Args:
            evolution_data: 进化数据，包含性能指标和优化目标
            
        Returns:
            bool: 进化是否成功
        """
        try:
            # 验证进化数据
            if not isinstance(evolution_data, dict):
                raise ValueError("Evolution data must be a dictionary")
                
            required_fields = ["performance_metrics", "optimization_goals"]
            if not all(field in evolution_data for field in required_fields):
                raise ValueError(f"Evolution data missing required fields: {required_fields}")
                
            # 更新状态
            self.status = AgentStatus.EVOLVING
            
            # 记录开始时间
            start_time = self.get_current_time()
            
            # TODO: 实现进化逻辑
            # 1. 分析性能指标
            # 2. 确定优化方向
            # 3. 调整内部参数
            # 4. 验证改进效果
            
            # 更新状态
            self.status = AgentStatus.IDLE
            
            # 更新指标
            end_time = self.get_current_time()
            self.update_metrics(
                success=True,
                processing_time=end_time - start_time
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in evolve: {str(e)}")
            self.status = AgentStatus.ERROR
            return False

    def _build_prompt(self, intent: Dict[str, Any], device: DeviceInfo) -> str:
        """构建提示词
        
        Args:
            intent: 用户意图
            device: 目标设备
            
        Returns:
            str: 提示词
        """
        # 获取设备可用的控制函数
        functions = self._get_device_functions(device)
        
        # 构建设备信息字符串，将 DeviceParameter 对象转换为字典
        parameters = {}
        for name, param in device.parameters.items():
            parameters[name] = {
                "type": param.type,
                "description": param.description,
                "current_value": param.current_value
            }
            if hasattr(param, "min_value") and param.min_value is not None:
                parameters[name]["min_value"] = param.min_value
            if hasattr(param, "max_value") and param.max_value is not None:
                parameters[name]["max_value"] = param.max_value
            if hasattr(param, "unit") and param.unit is not None:
                parameters[name]["unit"] = param.unit
            if hasattr(param, "enum_values") and param.enum_values is not None:
                parameters[name]["enum_values"] = param.enum_values
                
        device_info = {
            "id": device.id,
            "name": device.name,
            "type": device.type,
            "parameters": parameters,
            "functions": functions
        }
        
        prompt = """你是一个智能家居控制专家。你的任务是根据用户意图生成具体的设备控制指令。

【上下文隔离声明】
1. 你只能使用我提供的设备信息和用户意图
2. 不得使用任何外部知识或历史对话信息
3. 只能基于当前的输入生成控制指令
4. 不得主动添加或推测未提供的信息

【设备信息】
{device_info}

【用户意图】
{intent}

【可用函数】
{functions}

【输出要求】
你必须返回一个JSON对象，格式如下：

{{
    "function_calls": [
        {{
            "name": "函数名称",
            "parameters": {{
                "param1": "value1",
                "param2": "value2"
            }}
        }}
    ],
    "explanation": "对执行动作的解释说明"
}}

请确保：
1. function_calls 中的函数名称必须来自【可用函数】列表
2. parameters 必须与函数定义中的参数完全匹配
3. explanation 应该用中文解释将要执行的操作
"""
        
        return prompt.format(
            device_info=json.dumps(device_info, ensure_ascii=False, indent=2),
            intent=json.dumps(intent, ensure_ascii=False, indent=2),
            functions=json.dumps(functions, ensure_ascii=False, indent=2)
        )
        
    def _clean_json_content(self, content: str) -> str:
        """清理JSON内容
        
        Args:
            content: 原始JSON字符串
            
        Returns:
            str: 清理后的JSON字符串
        """
        # 首先尝试查找JSON代码块
        match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
        if match:
            json_str = match.group(1)
        else:
            # 如果找不到代码块，尝试查找最外层的完整JSON对象
            json_str = content.strip()
            # 确保它是一个有效的JSON对象
            if not (json_str.startswith('{') and json_str.endswith('}')):
                raise ValueError("未找到有效的JSON对象")
            
        # 移除单行注释
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        
        # 移除多行注释
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # 移除每行开头的空格和空行
        lines = []
        for line in json_str.split('\n'):
            line = line.strip()
            if line:
                lines.append(line)
        
        # 合并所有行
        json_str = ''.join(lines)
        
        # 替换中文引号为英文引号
        json_str = json_str.replace('"', '"').replace('"', '"')
        
        # 确保所有属性名都用双引号括起来
        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        return json_str
        
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            Dict[str, Any]: 解析后的动作数据
        """
        try:
            # 提取JSON字符串
            json_str = response.strip()
            if json_str.startswith("```") and json_str.endswith("```"):
                json_str = json_str[3:-3].strip()
                
            # 解析JSON
            result = json.loads(json_str)
            
            # 验证必要字段
            if not isinstance(result, dict):
                raise ValueError("Response must be a dictionary")
                
            required_fields = ["function_calls", "explanation"]
            if not all(field in result for field in required_fields):
                raise ValueError(f"Response missing required fields: {required_fields}")
                
            # 验证function_calls格式
            if not isinstance(result["function_calls"], list):
                raise ValueError("function_calls must be a list")
                
            for call in result["function_calls"]:
                if not isinstance(call, dict):
                    raise ValueError("Each function call must be a dictionary")
                    
                required_call_fields = ["name", "parameters"]
                if not all(field in call for field in required_call_fields):
                    raise ValueError(f"Function call missing required fields: {required_call_fields}")
                    
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {str(e)}")
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            self.logger.error(f"响应解析错误: {str(e)}")
            raise ValueError(f"Response parsing error: {str(e)}")
        
    def _get_device_functions(self, device: DeviceInfo) -> List[Dict[str, Any]]:
        """获取设备可用的控制函数
        
        Args:
            device: 设备信息对象
            
        Returns:
            List[Dict[str, Any]]: 函数列表
        """
        try:
            # 根据设备类型获取可用函数
            device_type = device.type
            functions = []
            
            # 基础控制函数
            functions.append({
                "name": f"{device_type}.set_power",
                "description": "设置设备电源状态",
                "parameters": {
                    "device_id": "设备ID",
                    "power": "电源状态(true/false)"
                }
            })
            
            # 根据设备类型添加特定函数
            if device_type == "light":
                functions.extend([
                    {
                        "name": f"{device_type}.set_brightness",
                        "description": "设置灯光亮度",
                        "parameters": {
                            "device_id": "设备ID",
                            "brightness": "亮度值(0-100)"
                        }
                    },
                    {
                        "name": f"{device_type}.set_color",
                        "description": "设置灯光颜色",
                        "parameters": {
                            "device_id": "设备ID",
                            "color": "颜色值(hex)"
                        }
                    }
                ])
            elif device_type == "airconditioner":
                functions.extend([
                    {
                        "name": f"{device_type}.set_temperature",
                        "description": "设置空调温度",
                        "parameters": {
                            "device_id": "设备ID",
                            "temperature": "温度值(16-30)"
                        }
                    },
                    {
                        "name": f"{device_type}.set_mode",
                        "description": "设置空调模式",
                        "parameters": {
                            "device_id": "设备ID",
                            "mode": "工作模式(cool/heat/auto/dry/fan)"
                        }
                    },
                    {
                        "name": f"{device_type}.set_fan_speed",
                        "description": "设置风速",
                        "parameters": {
                            "device_id": "设备ID",
                            "speed": "风速(low/medium/high/auto)"
                        }
                    }
                ])
            elif device_type == "curtain":
                functions.extend([
                    {
                        "name": f"{device_type}.set_position",
                        "description": "设置窗帘位置",
                        "parameters": {
                            "device_id": "设备ID",
                            "position": "位置(0-100)"
                        }
                    }
                ])
                
            return functions
            
        except Exception as e:
            self.logger.error(f"获取设备函数失败: {str(e)}")
            return []

    def _validate_input(self, intent: Dict[str, Any], device: DeviceInfo) -> bool:
        """验证输入数据的有效性
        
        Args:
            intent: 用户意图数据
            device: 设备信息对象
            
        Returns:
            bool: 输入是否有效
        """
        try:
            # 验证意图数据
            if not isinstance(intent, dict):
                self.logger.error("Invalid intent: not a dict")
                return False
                
            required_intent_fields = ["intent_type", "parameters"]
            if not all(field in intent for field in required_intent_fields):
                self.logger.error(f"Invalid intent: missing required fields {required_intent_fields}")
                return False
                
            # 验证设备数据
            if not isinstance(device, DeviceInfo):
                self.logger.error("Invalid device: not a DeviceInfo object")
                return False
                
            # 验证设备必要属性
            required_device_attrs = ["id", "type", "parameters"]
            if not all(hasattr(device, attr) for attr in required_device_attrs):
                self.logger.error(f"Invalid device: missing required attributes {required_device_attrs}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Input validation error: {str(e)}")
            return False
            
    async def generate_actions(self, intent: Dict[str, Any], device: DeviceInfo) -> Dict[str, Any]:
        """生成控制动作
        
        Args:
            intent: 用户意图
            device: 目标设备
            
        Returns:
            Dict[str, Any]: 动作数据，包含 function_calls 和 explanation 字段
        """
        try:
            # 输入验证
            if not self._validate_input(intent, device):
                return {
                    "function_calls": [],
                    "explanation": "输入数据无效"
                }
                
            # 记录处理开始
            self.logger.info(f"Generating actions for intent: {intent}")
            start_time = self.get_current_time()
            
            # 构建提示词
            prompt = self._build_prompt(intent, device)
            
            # 调用LLM API
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "temperature": 0.1
                }
                
                async with session.post(self.api_url, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"生成动作失败: {error_text}")
                        return {
                            "function_calls": [],
                            "explanation": f"生成动作失败: {error_text}"
                        }
                        
                    result = await response.json()
                    content = result["message"]["content"]
                    self.logger.debug(f"收到API响应: {content}")
                    
                    # 解析响应
                    try:
                        actions = self._parse_response(content)
                        self.logger.debug(f"解析到的动作数据: {actions}")
                        return actions
                    except Exception as e:
                        self.logger.error(f"解析动作响应失败: {str(e)}")
                        return {
                            "function_calls": [],
                            "explanation": f"解析动作响应失败: {str(e)}"
                        }
                        
        except Exception as e:
            self.logger.error(f"生成动作失败: {str(e)}")
            return {
                "function_calls": [],
                "explanation": f"生成动作失败: {str(e)}"
            } 