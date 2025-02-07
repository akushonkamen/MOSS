"""意图理解模型"""
from typing import List, Dict, Any, Optional
import aiohttp
import json
import logging
import re
from dataclasses import dataclass
from src.services.devices.device_info import DeviceInfo
from .intent import DeviceIntent, IntentParameter, IntentType
from datetime import datetime
from src.services.agents.base import BaseAgent, AgentType, AgentStatus, AgentCapability

logger = logging.getLogger(__name__)

class DecoderAgent(BaseAgent):
    """意图理解模型"""
    
    def __init__(self, agent_id: str, api_url: str, model_name: str):
        """初始化意图理解模型
        
        Args:
            agent_id: 代理ID
            api_url: LLM API地址
            model_name: 模型名称
        """
        super().__init__(agent_id, AgentType.DECODER)
        self.api_url = api_url
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """初始化智能体"""
        try:
            # 注册基础能力
            await self.register_base_capabilities()
            self.logger.info(f"Decoder agent {self.id} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize decoder agent {self.id}: {str(e)}")
            raise
            
    async def register_base_capabilities(self):
        """注册基础能力"""
        capabilities = [
            AgentCapability(
                name="intent_understanding",
                description="理解用户自然语言输入，识别控制意图",
                parameters={
                    "input_type": "text",
                    "output_type": "json",
                    "supported_intents": [
                        "control",
                        "query",
                        "scene",
                        "unknown"
                    ]
                },
                version="1.0.0"
            ),
            AgentCapability(
                name="parameter_extraction",
                description="从用户输入中提取设备控制参数",
                parameters={
                    "input_type": "text",
                    "output_type": "json",
                    "supported_parameters": [
                        "operation",
                        "direction",
                        "target_value",
                        "current_value"
                    ]
                },
                version="1.0.0"
            ),
            AgentCapability(
                name="device_matching",
                description="匹配用户提到的设备与系统中的实际设备",
                parameters={
                    "input_type": "text",
                    "output_type": "json",
                    "matching_methods": [
                        "exact",
                        "fuzzy",
                        "context"
                    ]
                },
                version="1.0.0"
            )
        ]
        
        for capability in capabilities:
            await self.register_capability(capability)
        
    def _build_prompt(self, user_input: str, devices: List[DeviceInfo]) -> str:
        """构建提示词
        
        Args:
            user_input: 用户输入
            devices: 可用设备列表
            
        Returns:
            str: 提示词
        """
        # 构建设备列表JSON
        devices_json = []
        for device in devices:
            device_info = {
                "id": device.id,
                "name": device.name,
                "type": device.type,
                "location": device.location,
                "capabilities": device.capabilities,
                "parameters": {
                    name: param.to_dict()
                    for name, param in device.parameters.items()
                }
            }
            devices_json.append(device_info)
            
        prompt = """你是一个智能家居意图理解专家。你的任务是理解用户的自然语言输入，识别用户想要控制的设备和具体意图。

【上下文隔离声明】
1. 你只能使用我提供的设备列表中的信息
2. 不得使用任何外部知识或历史对话信息
3. 只能基于当前的用户输入进行理解
4. 不得主动添加或推测未提供的信息

【设备列表】
{devices}

【用户输入】
{user_input}

【输出要求】
你必须返回一个JSON对象，格式如下：

{{
    "intent_type": "意图类型",
    "device": {{
        "id": "设备ID",
        "name": "设备名称",
        "type": "设备类型"
    }},
    "parameters": {{
        "operation": "具体操作",
        "direction": "调节方向",
        "target_value": "目标值",
        "current_value": "当前值",
        "reason": "操作原因"
    }}
}}

【严格约束】
1. 你必须且只能返回上述格式的JSON对象
2. 不要返回任何其他内容，如代码、注释或说明
3. 不要使用JSON代码块标记(```)
4. 所有字段必须使用双引号
5. 数值字段必须是具体的数字，不能是表达式
6. 必须从设备列表中选择匹配的设备
7. 如果找不到匹配的设备，返回intent_type为"unknown"
8. 所有可选字段如果无法识别，使用null
9. 不得添加任何额外的字段
10. 不得修改字段名称

【字段规范】
1. intent_type: 必须是以下值之一：
   - "control": 控制设备
   - "query": 查询状态
   - "scene": 场景控制
   - "unknown": 未知意图
2. direction: 必须是以下值之一：
   - "increase": 增加
   - "decrease": 减少
   - "maintain": 保持
   - null: 无方向
3. operation: 必须是设备支持的操作之一
4. target_value: 必须在设备参数的有效范围内
5. current_value: 必须是当前实际值
6. reason: 必须是对用户意图的简要描述

【处理流程】
1. 仔细分析用户输入
2. 在设备列表中查找匹配的设备
3. 确定具体的意图类型
4. 提取操作参数
5. 生成规范的JSON响应
6. 确保所有字段符合规范"""

        return prompt.format(
            devices=json.dumps(devices_json, indent=2, ensure_ascii=False),
            user_input=user_input
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
            # 如果找不到代码块，直接查找第一个完整的JSON对象
            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
            if not match:
                raise ValueError("未找到JSON内容")
            json_str = match.group(0)
            
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
        
        # 确保所有属性名都用双引号括起来
        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        return json_str
        
    def _validate_input(self, user_input: str, devices: List[DeviceInfo]) -> bool:
        """验证输入数据的有效性
        
        Args:
            user_input: 用户输入的文本
            devices: 设备列表
            
        Returns:
            bool: 输入是否有效
        """
        try:
            # 验证用户输入
            if not isinstance(user_input, str) or not user_input.strip():
                self.logger.error("Invalid user input: empty or wrong type")
                return False
                
            # 验证设备列表
            if not isinstance(devices, list):
                self.logger.error("Invalid devices: not a list")
                return False
                
            # 验证每个设备对象
            for device in devices:
                if not isinstance(device, DeviceInfo):
                    self.logger.error(f"Invalid device object: {device}")
                    return False
                    
                # 验证必要属性
                required_attrs = ["id", "name", "type"]
                if not all(hasattr(device, attr) for attr in required_attrs):
                    self.logger.error(f"Device missing required attributes: {required_attrs}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Input validation error: {str(e)}")
            return False
            
    async def understand_intent(self, user_input: str, devices: List[DeviceInfo]) -> Dict[str, Any]:
        """理解用户意图
        
        Args:
            user_input: 用户输入的文本
            devices: 设备列表
            
        Returns:
            Dict[str, Any]: 意图理解结果
        """
        try:
            # 输入验证
            if not self._validate_input(user_input, devices):
                return {
                    "intent_type": "unknown",
                    "device": None,
                    "parameters": {
                        "operation": None,
                        "direction": None,
                        "target_value": None,
                        "current_value": None,
                        "reason": "Invalid input data"
                    }
                }
                
            # 记录处理开始
            self.logger.info(f"Processing intent for input: {user_input}")
            start_time = datetime.now()
            
            # 构建提示词
            prompt = self._build_prompt(user_input, devices)
            
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
                        self.logger.error(f"意图理解失败: {error_text}")
                        return {
                            "intent_type": "unknown",
                            "device": None,
                            "parameters": {
                                "operation": None,
                                "direction": None,
                                "target_value": None,
                                "current_value": None,
                                "reason": f"Error: {error_text}"
                            }
                        }
                        
                    result = await response.json()
                    content = result["message"]["content"]
                    self.logger.debug(f"收到API响应: {content}")
                    
                    # 解析响应
                    try:
                        intent = self._parse_response(content)
                        self.logger.debug(f"解析到的意图数据: {intent}")
                        return intent
                    except Exception as e:
                        self.logger.error(f"解析意图响应失败: {str(e)}")
                        return {
                            "intent_type": "unknown",
                            "device": None,
                            "parameters": {
                                "operation": None,
                                "direction": None,
                                "target_value": None,
                                "current_value": None,
                                "reason": f"Error: {str(e)}"
                            }
                        }
                        
        except Exception as e:
            self.logger.error(f"意图理解失败: {str(e)}")
            return {
                "intent_type": "unknown",
                "device": None,
                "parameters": {
                    "operation": None,
                    "direction": None,
                    "target_value": None,
                    "current_value": None,
                    "reason": f"Error: {str(e)}"
                }
            }
        
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应
        
        Args:
            response: LLM的响应文本
            
        Returns:
            Dict[str, Any]: 解析后的意图数据
        """
        try:
            # 清理响应文本
            cleaned_response = self._clean_json_content(response)
            
            # 解析JSON
            result = json.loads(cleaned_response)
            
            # 验证必要字段
            required_fields = ["intent_type", "device", "parameters"]
            if not all(field in result for field in required_fields):
                raise ValueError("Missing required fields in response")
                
            # 验证intent_type
            valid_intent_types = ["control", "query", "scene", "unknown"]
            if result["intent_type"] not in valid_intent_types:
                raise ValueError(f"Invalid intent_type: {result['intent_type']}")
                
            # 验证direction
            if result["parameters"].get("direction"):
                valid_directions = ["increase", "decrease", "maintain", None]
                if result["parameters"]["direction"] not in valid_directions:
                    raise ValueError(f"Invalid direction: {result['parameters']['direction']}")
                    
            return result
            
        except Exception as e:
            self.logger.error(f"Response parsing error: {str(e)}")
            return {
                "intent_type": "unknown",
                "device": None,
                "parameters": {
                    "operation": None,
                    "direction": None,
                    "target_value": None,
                    "current_value": None,
                    "reason": f"Parsing error: {str(e)}"
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

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入数据
        
        Args:
            input_data: 包含用户输入和设备列表的字典
            
        Returns:
            Dict[str, Any]: 意图理解结果
        """
        try:
            # 验证输入数据
            if not isinstance(input_data, dict):
                raise ValueError("Input data must be a dictionary")
                
            required_fields = ["user_input", "devices"]
            if not all(field in input_data for field in required_fields):
                raise ValueError(f"Input data missing required fields: {required_fields}")
                
            # 验证字段类型
            if not isinstance(input_data["user_input"], str):
                raise ValueError("user_input must be a string")
            if not isinstance(input_data["devices"], list):
                raise ValueError("devices must be a list")
            if not all(isinstance(device, DeviceInfo) for device in input_data["devices"]):
                raise ValueError("all devices must be DeviceInfo objects")
                
            # 更新状态
            self.status = AgentStatus.PROCESSING
            
            # 记录开始时间
            start_time = self.get_current_time()
            
            # 调用意图理解
            result = await self.understand_intent(
                user_input=input_data["user_input"],
                devices=input_data["devices"]
            )
            
            # 更新状态
            self.status = AgentStatus.IDLE
            
            # 更新指标
            end_time = self.get_current_time()
            self.update_metrics(
                success=result["intent_type"] != "unknown",
                processing_time=end_time - start_time
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in process: {str(e)}")
            self.status = AgentStatus.ERROR
            return {
                "intent_type": "unknown",
                "device": None,
                "parameters": {
                    "operation": None,
                    "direction": None,
                    "target_value": None,
                    "current_value": None,
                    "reason": f"Processing error: {str(e)}"
                }
            } 