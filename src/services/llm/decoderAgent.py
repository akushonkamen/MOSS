"""意图理解模型"""
from typing import List, Dict, Any, Optional
import aiohttp
import json
import logging
import re
from dataclasses import dataclass
from src.services.devices.device_info import DeviceInfo
from .intent import DeviceIntent, IntentParameter, IntentType

logger = logging.getLogger(__name__)

class decoderAgent:
    """意图理解模型"""
    
    def __init__(self):
        """初始化意图理解模型"""
        self.api_url = "http://localhost:11434/api/chat"
        self.model_name = "llama3.2-vision:latest"
        
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

当前可用的设备列表：
{devices}

用户输入：
{user_input}

请分析用户输入，从设备列表中识别目标设备，并提取用户意图。你必须返回一个JSON对象，格式如下：

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

严格要求：
1. 你必须且只能返回上述格式的JSON对象
2. 不要返回任何其他内容，如代码、注释或说明
3. 不要使用JSON代码块标记(```)
4. 所有字段必须使用双引号
5. 数值字段必须是具体的数字，不能是表达式
6. 必须从设备列表中选择匹配的设备
7. 如果找不到匹配的设备，返回intent_type为"unknown"
8. 所有可选字段如果无法识别，使用null

字段说明：
1. intent_type: 必须是以下值之一：
   - "control": 控制设备
   - "query": 查询状态
   - "scene": 场景控制
   - "unknown": 未知意图
2. direction: 
   - increase: 增加
   - decrease: 减少
   - maintain: 保持
3. operation: 根据设备支持的操作选择
4. target_value: 根据设备参数的取值范围设置
5. current_value: 从设备当前状态获取
6. reason: 用自然语言描述用户的意图原因"""

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
        
    def _parse_response(self, content: str) -> DeviceIntent:
        """解析响应内容
        
        Args:
            content: 原始响应内容
            
        Returns:
            DeviceIntent: 意图对象
        """
        # 清理并解析JSON
        json_str = self._clean_json_content(content)
        data = json.loads(json_str)
        
        # 创建参数对象
        parameters = IntentParameter(
            operation=data["parameters"].get("operation"),
            direction=data["parameters"].get("direction"),
            target_value=data["parameters"].get("target_value"),
            current_value=data["parameters"].get("current_value"),
            reason=data["parameters"].get("reason")
        )
        
        # 创建意图对象
        intent = DeviceIntent(
            device_id=data["device"]["id"],
            device_name=data["device"]["name"],
            device_type=data["device"]["type"],
            intent_type=data["intent_type"],
            parameters=parameters,
            confidence=1.0
        )
        
        return intent
        
    async def understand_intent(self, user_input: str, devices: List[DeviceInfo]) -> DeviceIntent:
        """理解用户意图
        
        Args:
            user_input: 用户输入
            devices: 可用设备列表
            
        Returns:
            DeviceIntent: 意图对象
        """
        # 构建提示词
        prompt = self._build_prompt(user_input, devices)
        
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
                        logger.error(f"意图理解失败: {error_text}")
                        return DeviceIntent(
                            device_id="",
                            device_name="",
                            device_type="",
                            intent_type=IntentType.UNKNOWN,
                            parameters=IntentParameter(),
                            confidence=0.0
                        )
                        
                    result = await response.json()
                    content = result["message"]["content"]
                    logger.debug(f"收到API响应: {content}")
                    
                    # 解析响应
                    try:
                        intent = self._parse_response(content)
                        logger.debug(f"解析到的意图数据: {intent}")
                        return intent
                    except Exception as e:
                        logger.error(f"解析意图响应失败: {str(e)}")
                        return DeviceIntent(
                            device_id="",
                            device_name="",
                            device_type="",
                            intent_type=IntentType.UNKNOWN,
                            parameters=IntentParameter(),
                            confidence=0.0
                        )
                        
        except Exception as e:
            logger.error(f"意图理解失败: {str(e)}")
            return DeviceIntent(
                device_id="",
                device_name="",
                device_type="",
                intent_type=IntentType.UNKNOWN,
                parameters=IntentParameter(),
                confidence=0.0
            ) 