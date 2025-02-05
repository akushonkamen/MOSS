from typing import Dict, Any, List, Tuple, Optional
from .registry import registry
import re
import yaml
import logging
import asyncio

logger = logging.getLogger(__name__)

class FunctionParser:
    """函数调用解析器"""
    
    @staticmethod
    def parse_function_calls(text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """解析文本中的函数调用
        
        Args:
            text: 包含函数调用的文本
            
        Returns:
            List[Tuple[str, Dict[str, Any]]]: 函数调用列表
        """
        pattern = r'<function>(.*?)</function>'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        calls = []
        for match in matches:
            try:
                yaml_text = match.group(1)
                function_data = yaml.safe_load(yaml_text)
                
                if not isinstance(function_data, dict):
                    continue
                    
                name = function_data.get('name', '')
                parameters = function_data.get('parameters', {})
                
                if isinstance(parameters, list):
                    parameters = {
                        item["name"]: item["value"] 
                        for item in parameters 
                        if isinstance(item, dict)
                    }
                
                # 确保状态值为字符串
                if "state" in parameters:
                    state = str(parameters["state"]).lower()
                    if state == "true":
                        state = "on"
                    elif state == "false":
                        state = "off"
                    parameters["state"] = state
                
                calls.append((name, parameters))
                
            except Exception as e:
                logger.error(f"解析函数调用失败: {str(e)}")
                continue
                
        return calls
        
    @staticmethod
    async def execute_function_calls(text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """执行函数调用
        
        Args:
            text: 包含函数调用的文本
            
        Returns:
            Tuple[str, List[Dict[str, Any]]]: 处理后的文本和执行结果
        """
        calls = FunctionParser.parse_function_calls(text)
        results = []
        
        # 移除函数调用标记
        clean_text = re.sub(r'<function>.*?</function>', '', text, flags=re.DOTALL)
        
        # 执行函数调用
        for name, parameters in calls:
            try:
                func = registry.get_function(name)
                if not func:
                    results.append({
                        "error": f"未找到函数: {name}"
                    })
                    continue
                    
                # 检查是否是异步函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(**parameters)
                else:
                    result = func(**parameters)
                    
                results.append({
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"执行函数 {name} 失败: {str(e)}")
                results.append({
                    "error": str(e)
                })
                
        # 生成响应文本
        response_parts = []
        if clean_text.strip():
            response_parts.append(clean_text.strip())
            
        for result in results:
            if "error" in result:
                response_parts.append(f"操作失败: {result['error']}")
            else:
                response = result["result"]
                if isinstance(response, str):
                    response_parts.append(response)
                    
        return " ".join(response_parts), results 