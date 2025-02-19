"""LLM语言模型服务

注意：我们使用的是 llama3.2-vision:latest 模型。
这是因为我们需要一个支持函数调用的模型，而 llama3.2-vision 在这方面表现良好。

主要功能：
1. 支持流式对话
2. 支持函数调用
3. 支持会话历史
4. 支持提示词模板
5. 支持自定义系统提示词
"""
import json
from typing import AsyncGenerator, Optional, List, Dict, Set, Any, Callable
import aiohttp
import re
from src.services.llm.interface import LLMService
from src.services.llm.prompt_manager import PromptManager
from src.services.llm.function_call import registry
from src.services.llm.function_parser import FunctionParser
from src.services.devices.base import registry as device_registry
import asyncio
import logging
from tabulate import tabulate
from src.services.devices.device_client import SmartLightClient, SmartACClient, SmartCurtainClient
from ..function_calling.registry import FunctionDefinition
from ..core.entity import registry as entity_registry
from .decoderAgent import DecoderAgent
from .expertAgent import ExpertAgent
from .intent import DeviceIntent, IntentParameter, IntentType
from ..devices.device_info import DeviceInfo
from ..devices.unified_device_manager import unified_device_manager

logger = logging.getLogger(__name__)

class LLMServiceImpl(LLMService):
    """LLM语言模型服务
    
    我们使用 llama3.2-vision:latest 模型进行对话。
    这是因为 llama3.2-vision 模型在函数调用方面有很好的支持。
    
    主要特性：
    - 支持流式输出
    - 支持函数调用
    - 支持会话历史管理
    - 支持提示词模板
    - 支持自定义系统提示词
    """
    
    def __init__(self):
        """初始化服务
        
        设置：
        - API地址：默认为 localhost:11434
        - 默认模型：llama3.2-vision:latest
        - 会话历史：使用字典存储，key为会话ID
        - 提示词管理：使用 PromptManager
        - 函数注册：使用 Set 存储可用函数
        """
        self.api_url = "http://localhost:11434/api"  # Ollama API地址
        self.model_name = "llama3.2-vision:latest"  # 使用 llama3.2-vision 模型
        self.conversations: Dict[str, List[Dict[str, str]]] = {}  # 会话历史
        self.prompt_manager = PromptManager()  # 初始化提示词管理器
        self.functions: Dict[str, Dict[str, Any]] = {}  # 可用函数集合
        
        # 初始化两个Agent
        self.decoder = DecoderAgent(
            api_url="http://localhost:11434/api/chat",
            model_name="llama3.2-vision:latest"
        )
        self.expert = ExpertAgent(
            agent_id="expert_001",
            api_url="http://localhost:11434/api/chat",
            model_name="llama3.1:latest"
        )
        
        # 会话历史
        self.session_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # 初始化标志
        self._initialized = False
        
        # 初始化logger
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def initialize(self):
        """异步初始化"""
        if not self._initialized:
            await self.decoder.initialize()
            await self.expert.initialize()
            self._initialized = True
        
    def register_function(self, func: Callable, description: str = "", **kwargs):
        """注册函数
        
        Args:
            func: 函数对象
            description: 函数描述
            **kwargs: 其他参数
        """
        if not hasattr(func, "__name__"):
            raise ValueError("函数对象必须有__name__属性")
            
        # 根据设备类型和函数名构造完整的函数名
        device_type = func.__self__.__class__.__name__.replace("Client", "").lower()
        full_name = f"{device_type}.{func.__name__}"
            
        self.functions[full_name] = {
            "name": full_name,
            "description": description,
            "implementation": func,
            **kwargs
        }
        logger.debug(f"注册函数: {full_name}")
        
    def unregister_function(self, name: str) -> None:
        """取消注册函数"""
        if name in self.functions:
            del self.functions[name]
        
    def _get_or_create_conversation(self, session_id: str) -> List[Dict[str, str]]:
        """获取或创建会话历史"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]
        
    def _remove_think_tags(self, text: str) -> str:
        """移除<think>标签及其内容"""
        # 使用非贪婪模式匹配<think>标签及其内容
        pattern = r'<think>.*?</think>'
        return re.sub(pattern, '', text, flags=re.DOTALL)
        
    async def chat_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """流式对话
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            temperature: 温度参数
            
        Yields:
            str: 模型响应片段
        """
        try:
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # 使用专家代理进行对话
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.model_name,
                    "messages": messages,
                    "stream": True,
                    "temperature": temperature
                }
                
                async with session.post(f"{self.api_url}/chat", json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"调用LLM API失败: {error_text}")
                        yield ""
                        return
                        
                    async for line in response.content:
                        if line:
                            try:
                                line_str = line.decode('utf-8').strip()
                                if line_str:
                                    data = json.loads(line_str)
                                    if "message" in data:
                                        content = data["message"].get("content", "")
                                        if content:
                                            yield content
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                self.logger.error(f"解析响应失败: {str(e)}")
                                yield ""
                                continue
                                
        except Exception as e:
            self.logger.error(f"流式对话失败: {str(e)}")
            yield ""

    def clear_conversation(self, session_id: str):
        """清除指定会话的历史记录"""
        if session_id in self.conversations:
            del self.conversations[session_id]

    async def chat_stream_old(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        使用Ollama API进行流式对话
        """
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "你是一个有帮助的AI助手。"},
                {"role": "user", "content": prompt}
            ],
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/chat", json=data) as response:
                async for line in response.content:
                    if line:
                        try:
                            json_line = json.loads(line)
                            if "message" in json_line and "content" in json_line["message"]:
                                yield json_line["message"]["content"]
                        except json.JSONDecodeError:
                            continue 

    async def identify_target_device(
        self, 
        user_input: str,
        available_devices: List[DeviceInfo]
    ) -> Dict[str, Any]:
        """识别用户意图中的目标设备
        
        Args:
            user_input: 用户输入
            available_devices: 可用设备列表
            
        Returns:
            Dict[str, Any]: 意图识别结果
        """
        try:
            # 构建设备列表
            devices_json = []
            for device in available_devices:
                device_json = {
                    "id": device.id,
                    "name": device.name,
                    "type": device.type,
                    "location": device.location,
                    "capabilities": device.capabilities,
                    "parameters": {
                        name: {
                            "type": param.type,
                            "description": param.description,
                            "current_value": param.current_value,
                            "min_value": param.min_value,
                            "max_value": param.max_value,
                            "enum_values": param.enum_values,
                            "unit": param.unit
                        }
                        for name, param in device.parameters.items()
                    }
                }
                devices_json.append(device_json)
            
            # 构建系统提示词
            system_prompt = """你是一个智能工业AI系统的意图理解器。
你的任务是理解用户的自然语言输入，提取其中的意图、目标设备和相关参数。

可用设备列表如下：
{devices}

你需要分析用户输入中的以下要素：
1. 核心意图：用户想要执行什么操作（如调节温度、改变亮度等）
2. 目标设备：用户想要控制哪个设备
3. 具体参数：操作需要的具体参数值
4. 意图原因：用户为什么要执行这个操作（如感觉热、感觉闷等）

你需要返回一个JSON格式的理解结果，包含以下字段：
{
    "intent": {
        "name": "意图名称",
        "description": "意图的详细描述",
        "reason": "用户执行这个操作的原因",
        "confidence": 0.95
    },
    "target_device": {
        "device_id": "设备ID",
        "device_name": "设备名称",
        "device_type": "设备类型",
        "confidence": 0.95
    },
    "parameters": {
        "operation": "具体操作类型",
        "direction": "调节方向(increase/decrease)",
        "target_value": "目标值",
        "current_value": "当前值(如果已知)"
    }
}

意图名称应该是标准化的操作类型，比如：
- adjust_temperature: 调节温度
- change_brightness: 调节亮度
- power_control: 开关控制
- change_mode: 改变模式
- adjust_position: 调节位置

示例1：
输入："我觉得有点热，帮我把温度调低一点"
输出：{
    "intent": {
        "name": "adjust_temperature",
        "description": "降低空调温度",
        "reason": "用户感觉热",
        "confidence": 0.95
    },
    "target_device": {
        "device_id": "ac.living_room",
        "device_name": "客厅空调",
        "device_type": "ac",
        "confidence": 0.95
    },
    "parameters": {
        "operation": "decrease_temperature",
        "direction": "decrease",
        "target_value": -2,
        "current_value": null
    }
}

示例2：
输入："好闷，开一下空调"
输出：{
    "intent": {
        "name": "power_control",
        "description": "打开空调并调节到合适温度",
        "reason": "用户感觉闷热",
        "confidence": 0.95
    },
    "target_device": {
        "device_id": "ac.living_room",
        "device_name": "客厅空调",
        "device_type": "ac",
        "confidence": 0.95
    },
    "parameters": {
        "operation": "turn_on",
        "direction": "decrease",
        "target_value": 24,
        "current_value": null
    }
}

请注意：
1. 当用户表达不适感（如热、冷、闷）时，应该理解其潜在意图
2. 温度调节应该根据用户的感受来决定方向
3. 设备选择应该考虑上下文和场景
4. 参数值应该在合理范围内
5. 如果用户输入不够明确，可以选择最合理的默认值"""
            
            devices_str = "\n".join([
                f"- {dev['name']} (ID: {dev['id']}, 类型: {dev['type']})"
                for dev in devices_json
            ])
            
            # 构建完整的提示词
            prompt = system_prompt.format(devices=devices_str)
            prompt += f"\n\n用户输入: {user_input}"
            logger.info(f"意图理解提示词: {prompt}")
            
            # 调用LLM API进行意图理解
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": prompt}
                    ],
                    "stream": False,
                    "temperature": 0.1  # 使用较低的温度以获得更确定的输出
                }
                logger.info(f"发送到LLM API的数据: {json.dumps(data, indent=2)}")
                
                async with session.post(f"{self.api_url}/chat", json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"意图理解API调用失败: {error_text}")
                        return {"error": "意图理解失败"}
                        
                    result = await response.json()
                    logger.info(f"收到LLM API响应: {json.dumps(result, indent=2)}")
                    content = result["message"]["content"]
                    logger.info(f"提取的响应内容: {content}")
                    
                    try:
                        # 清理并解析JSON响应
                        content = re.sub(r'```json\s*|\s*```', '', content)
                        logger.info(f"清理后的响应内容: {content}")
                        intent_result = json.loads(content)
                        logger.info(f"解析后的意图结果: {json.dumps(intent_result, indent=2)}")
                        
                        # 验证响应格式
                        required_fields = ["intent", "target_device", "parameters"]
                        if not all(field in intent_result for field in required_fields):
                            missing_fields = [f for f in required_fields if f not in intent_result]
                            error_msg = f"响应缺少必要字段: {', '.join(missing_fields)}"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                            
                        return intent_result
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"解析意图响应失败: {str(e)}\n响应内容: {content}")
                        return {"error": "意图解析失败"}
                    except ValueError as e:
                        logger.error(f"意图响应格式错误: {str(e)}")
                        return {"error": "意图格式错误"}
                        
        except Exception as e:
            logger.error(f"意图理解失败: {str(e)}")
            return {"error": "意图理解失败"}
        
    async def generate_function_calls(
        self,
        user_input: str,
        intent_result: Dict[str, Any],
        available_functions: List[FunctionDefinition]
    ) -> str:
        """第二个LLM Agent: 专家系统
        
        这个Agent负责：
        1. 根据理解到的意图选择合适的控制函数
        2. 将意图参数转换为函数参数
        3. 生成正确的函数调用序列
        
        Args:
            user_input: 原始用户输入
            intent_result: 第一个Agent的意图理解结果
            available_functions: 可用的设备控制函数列表
            
        Returns:
            str: 包含函数调用的响应文本
        """
        # 构建系统提示词
        system_prompt = """你是一个智能工业AI控制专家系统。
你的任务是根据理解到的用户意图，生成正确的设备控制函数调用序列。

用户意图：
{intent}

可用的控制函数：
{functions}

你需要：
1. 根据意图选择合适的控制函数
2. 将意图参数转换为函数参数
3. 确保函数调用的顺序正确
4. 生成友好的响应消息

注意：
- 某些意图可能需要多个函数调用才能完成
- 参数值需要在合理范围内
- 函数调用顺序可能会影响最终效果"""
        
        intent = intent_result["intent"]
        target_device = intent_result["target_device"]
        parameters = intent_result["parameters"]
        
        functions_str = "\n".join([
            f"- {func.name}: {func.description}"
            for func in available_functions
        ])
        
        # 构建完整的提示词
        prompt = system_prompt.format(
            intent=json.dumps(intent_result, indent=2),
            functions=functions_str
        )
        logger.info(f"函数调用生成提示词: {prompt}")
        
        try:
            # 调用LLM API生成函数调用
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_input}
                    ],
                    "stream": False,
                    "temperature": 0.1
                }
                logger.info(f"发送到LLM API的数据: {json.dumps(data, indent=2)}")
                
                async with session.post(f"{self.api_url}/chat", json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"生成函数调用失败: {error_text}")
                        return "抱歉，生成控制方案时出错"
                        
                    result = await response.json()
                    logger.info(f"收到LLM API响应: {json.dumps(result, indent=2)}")
                    content = result["message"]["content"]
                    logger.info(f"提取的响应内容: {content}")
                    
                    try:
                        # 清理并解析响应
                        content = re.sub(r'```json\s*|\s*```', '', content)
                        logger.info(f"清理后的响应内容: {content}")
                        action_data = json.loads(content)
                        logger.info(f"解析后的动作数据: {json.dumps(action_data, indent=2)}")
                        
                        # 验证响应格式
                        if not isinstance(action_data, dict):
                            error_msg = "响应不是一个有效的JSON对象"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        if "function_calls" not in action_data:
                            error_msg = "响应中缺少function_calls字段"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        if "explanation" not in action_data:
                            error_msg = "响应中缺少explanation字段"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                            
                        # 验证每个函数调用
                        for i, call in enumerate(action_data["function_calls"]):
                            logger.info(f"验证函数调用 {i+1}: {json.dumps(call, indent=2)}")
                            if "name" not in call or "parameters" not in call:
                                error_msg = f"函数调用 {i+1} 格式错误: 缺少name或parameters字段"
                                logger.error(error_msg)
                                raise ValueError(error_msg)
                                
                        return action_data["explanation"]
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"解析函数调用响应失败: {str(e)}\n响应内容: {content}")
                        return "抱歉，生成控制方案时出错"
                    except ValueError as e:
                        logger.error(f"函数调用响应格式错误: {str(e)}")
                        return "抱歉，生成控制方案时出错"
                        
        except Exception as e:
            logger.error(f"生成函数调用失败: {str(e)}")
            return "抱歉，生成控制方案时出错"

    async def execute_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """执行用户意图
        
        Args:
            user_input: 用户输入
            
        Returns:
            Optional[Dict[str, Any]]: 执行结果
        """
        try:
            self.logger.info(f"开始执行意图解析，用户输入: {user_input}")
            
            # 1. 使用decoderAgent理解用户意图
            self.logger.info("调用解码代理解析意图...")
            intent = await self.decoder.understand_intent(user_input)
            self.logger.info(f"解码结果: {intent}")
            
            if not intent or intent.intent_type == "unknown":
                self.logger.warning("未能理解用户意图")
                return None
                
            # 2. 将DeviceIntent转换为字典格式
            intent_dict = {
                "device_id": intent.device_id,
                "device_name": intent.device_name,
                "device_type": intent.device_type,
                "intent_type": intent.intent_type,
                "parameters": intent.parameters.__dict__,
                "confidence": intent.confidence
            }
            self.logger.info(f"转换后的意图数据: {intent_dict}")
                
            # 3. 使用expertAgent执行意图
            self.logger.info("调用专家代理执行意图...")
            result = await self.expert.execute_intent(intent_dict)
            self.logger.info(f"执行结果: {result}")
            
            if not result:
                self.logger.warning("执行意图失败")
                return None
                
            return result
            
        except Exception as e:
            self.logger.error(f"执行意图失败: {str(e)}")
            import traceback
            self.logger.error(f"错误详情:\n{traceback.format_exc()}")
            return None

def llm_service() -> LLMService:
    """获取LLM服务实例
    
    Returns:
        LLMService: LLM服务实例
    """
    return LLMServiceImpl() 