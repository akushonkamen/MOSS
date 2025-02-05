"""动作生成模型"""
from typing import List, Dict, Any, Optional
import aiohttp
import json
import logging
import re
from dataclasses import dataclass
from src.services.devices.device_info import DeviceInfo
from .intent import DeviceIntent, IntentParameter, IntentType

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

class ExpertAgent:
    """动作生成模型"""
    
    def __init__(self):
        """初始化动作生成模型"""
        self.api_url = "http://localhost:11434/api/chat"
        self.model_name = "llama3.1:latest"
        
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
        
        prompt = """你是一个智能家居控制专家。你的任务是根据用户意图和设备状态，生成精确的设备控制指令。

用户意图：
{intent}

设备信息：
{device_info}

可用的控制函数：
{functions}

请注意：
1. 用户意图中的 target_value 表示目标状态，如果为 true 表示要打开设备，false 表示要关闭设备
2. 用户意图中的 current_value 表示当前状态，不要与目标状态混淆
3. 如果用户说"开灯"，应该将设备打开（power=true）
4. 如果用户说"关灯"，应该将设备关闭（power=false）
5. 在调整亮度、温度等参数时，应该先确保设备是开启状态

你必须且只能返回一个JSON对象，格式如下：

{{
    "function_calls": [
        {{
            "name": "函数名称",
            "parameters": {{
                "参数名": "参数值"
            }}
        }}
    ],
    "explanation": "执行计划说明"
}}

严格要求：
1. 你必须且只能返回上述格式的JSON对象
2. 不要返回任何其他内容，如代码、注释或说明
3. 不要使用JSON代码块标记(```)
4. 所有字段必须使用双引号
5. 数值字段必须是具体的数字，不能是表达式
6. 必须从可用函数列表中选择函数
7. 参数必须符合函数定义的要求
8. 如果需要多个函数调用，请按照正确的顺序排列
9. 确保所有必需的参数都被设置
10. explanation字段应该用自然语言描述执行的操作"""

        return prompt.format(
            intent=json.dumps(intent, indent=2, ensure_ascii=False),
            device_info=json.dumps(device.to_dict(), indent=2, ensure_ascii=False),
            functions=json.dumps(functions, indent=2, ensure_ascii=False)
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
        
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """解析响应内容
        
        Args:
            content: 原始响应内容
            
        Returns:
            Dict[str, Any]: 动作数据
        """
        # 清理并解析JSON
        try:
            json_str = self._clean_json_content(content)
            logger.debug(f"清理后的JSON字符串: {json_str}")
            
            data = json.loads(json_str)
            logger.debug(f"解析后的JSON数据: {data}")
            
            # 验证响应格式
            if "function_calls" not in data:
                logger.error(f"响应缺少function_calls字段: {data}")
                raise ValueError("响应缺少function_calls字段")
                
            if not isinstance(data["function_calls"], list):
                logger.error(f"function_calls必须是数组: {data['function_calls']}")
                raise ValueError("function_calls必须是数组")
                
            for call in data["function_calls"]:
                if "name" not in call:
                    logger.error(f"函数调用缺少name字段: {call}")
                    raise ValueError("函数调用缺少name字段")
                if "parameters" not in call:
                    logger.error(f"函数调用缺少parameters字段: {call}")
                    raise ValueError("函数调用缺少parameters字段")
                    
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}, 原始内容: {content}")
            raise ValueError(f"JSON解析失败: {str(e)}")
        except Exception as e:
            logger.error(f"解析响应失败: {str(e)}, 原始内容: {content}")
            raise
        
    def _get_device_functions(self, device: DeviceInfo) -> List[Dict[str, Any]]:
        """获取设备可用的控制函数
        
        Args:
            device: 设备信息
            
        Returns:
            List[Dict[str, Any]]: 函数列表
        """
        device_type = device.type.lower()
        functions = []
        
        if device_type == "smartlight":
            functions = [
                {
                    "name": "smartlight.set_power",
                    "description": "控制灯光开关",
                    "parameters": {
                        "power": {
                            "type": "boolean",
                            "description": "开关状态"
                        }
                    }
                },
                {
                    "name": "smartlight.set_brightness",
                    "description": "设置灯光亮度",
                    "parameters": {
                        "brightness": {
                            "type": "integer",
                            "description": "亮度值(0-100)",
                            "minimum": 0,
                            "maximum": 100
                        }
                    }
                }
            ]
        elif device_type == "smartac":
            functions = [
                {
                    "name": "smartac.set_power",
                    "description": "控制空调开关",
                    "parameters": {
                        "power": {
                            "type": "boolean",
                            "description": "开关状态"
                        }
                    }
                },
                {
                    "name": "smartac.set_temperature",
                    "description": "设置空调温度",
                    "parameters": {
                        "temperature": {
                            "type": "number",
                            "description": "温度值(16-30)",
                            "minimum": 16,
                            "maximum": 30
                        }
                    }
                },
                {
                    "name": "smartac.set_mode",
                    "description": "设置空调模式",
                    "parameters": {
                        "mode": {
                            "type": "string",
                            "description": "运行模式",
                            "enum": ["cool", "heat", "auto"]
                        }
                    }
                }
            ]
        elif device_type == "smartcurtain":
            functions = [
                {
                    "name": "smartcurtain.set_position",
                    "description": "设置窗帘位置",
                    "parameters": {
                        "position": {
                            "type": "integer",
                            "description": "位置值(0-100)",
                            "minimum": 0,
                            "maximum": 100
                        }
                    }
                }
            ]
            
        return functions

    async def generate_actions(self, intent: DeviceIntent, device: DeviceInfo) -> Dict[str, Any]:
        """生成控制动作
        
        Args:
            intent: 用户意图
            device: 目标设备
            
        Returns:
            Dict[str, Any]: 动作数据
        """
        # 构建提示词
        prompt = self._build_prompt(intent, device)
        logger.debug(f"生成的提示词: {prompt}")
        
        try:
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
                        logger.error(f"生成动作失败: {error_text}")
                        return {
                            "function_calls": [],
                            "explanation": "生成动作失败",
                            "error": error_text
                        }
                        
                    result = await response.json()
                    content = result["message"]["content"]
                    logger.debug(f"收到API响应: {content}")
                    
                    # 解析响应
                    try:
                        actions = self._parse_response(content)
                        logger.debug(f"解析到的动作数据: {actions}")
                        return actions
                    except Exception as e:
                        logger.error(f"解析动作响应失败: {str(e)}")
                        return {
                            "function_calls": [],
                            "explanation": "解析动作响应失败",
                            "error": str(e)
                        }
                        
        except Exception as e:
            logger.error(f"生成动作失败: {str(e)}")
            return {
                "function_calls": [],
                "explanation": "生成动作失败",
                "error": str(e)
            } 