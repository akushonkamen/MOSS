from typing import Dict, Any, List, Tuple, Optional, Set
import re
import yaml
import logging
from ..core.service_registry import registry as service_registry
from ..core.event_bus import bus, Event
import asyncio

logger = logging.getLogger(__name__)

class FunctionParser:
    """函数调用解析器"""
    
    @staticmethod
    def parse_function_calls(text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        解析文本中的函数调用
        
        Args:
            text: 包含函数调用的文本
            
        Returns:
            List[Tuple[str, str, Dict[str, Any]]]: 函数调用列表，每个元素是(域, 服务名, 参数字典)的元组
        """
        pattern = r'<function>(.*?)</function>'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        calls = []
        for match in matches:
            try:
                # 预处理YAML文本
                yaml_text = match.group(1)
                yaml_text = re.sub(r'\((.*?)\)', '', yaml_text)
                
                # 解析YAML格式的函数调用
                function_data = yaml.safe_load(yaml_text)
                
                if not isinstance(function_data, dict):
                    continue
                    
                # 解析域和服务名
                full_name = function_data.get('name', '')
                if '.' in full_name:
                    domain, service = full_name.split('.', 1)
                else:
                    continue
                    
                parameters = function_data.get('parameters', {})
                
                # 统一参数格式为字典
                if isinstance(parameters, list):
                    param_dict = {}
                    for item in parameters:
                        if isinstance(item, dict):
                            param_dict.update(item)
                    parameters = param_dict
                elif not isinstance(parameters, dict):
                    parameters = {}
                
                # 确保所有参数值不是列表
                parameters = {k: v[0] if isinstance(v, list) else v 
                            for k, v in parameters.items()}
                
                logger.info(f"解析到函数调用: {domain}.{service}, 参数: {parameters}")
                calls.append((domain, service, parameters))
            except Exception as e:
                logger.error(f"解析函数调用失败: {str(e)}")
                continue
                
        return calls
    
    @staticmethod
    async def execute_function_calls(
        text: str,
        available_domains: Optional[Set[str]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        执行文本中的所有函数调用，并生成自然的语音响应
        
        Args:
            text: 包含函数调用的文本
            available_domains: 可用的服务域集合
            
        Returns:
            Tuple[str, List[Dict[str, Any]]]: 处理后的文本和函数调用结果列表
        """
        calls = FunctionParser.parse_function_calls(text)
        results = []
        
        # 如果没有函数调用，直接返回原文本
        if not calls:
            return text, results

        # 移除所有函数调用标记，保留纯文本部分
        clean_text = text
        for domain, service, _ in calls:
            pattern = r'<function>.*?name: ' + f"{domain}.{service}" + r'.*?</function>'
            clean_text = re.sub(pattern, '', clean_text, flags=re.DOTALL)
        
        # 串行执行所有函数调用
        for domain, service, parameters in calls:
            try:
                # 检查域是否可用
                if available_domains is not None and domain not in available_domains:
                    logger.warning(f"服务域 {domain} 不可用")
                    results.append({"error": f"服务域 {domain} 不可用"})
                    continue
                    
                # 调用服务
                result = await service_registry.call_service(domain, service, parameters)
                logger.info(f"函数执行结果: {result}")
                
                # 等待一小段时间确保状态更新
                await asyncio.sleep(1.0)
                results.append({"result": result})
                
            except Exception as e:
                logger.error(f"执行函数 {domain}.{service} 时出错: {str(e)}")
                results.append({"error": str(e)})
                continue
        
        # 处理执行结果
        response_parts = []
        
        # 添加原始文本（去除函数调用标记后的）
        clean_text = clean_text.strip()
        if clean_text:
            response_parts.append(clean_text)
        
        # 添加执行结果的自然语言描述
        for result in results:
            if "error" in result:
                if "服务域不可用" in result["error"]:
                    response_parts.append(f"抱歉，我暂时无法执行这个操作。")
                else:
                    response_parts.append(f"在执行操作时遇到了一些问题：{result['error']}")
            else:
                response = result.get("result", "操作已完成")
                if isinstance(response, str):
                    response_parts.append(response)
        
        # 将所有部分组合成自然的响应
        final_text = " ".join(response_parts)
        
        return final_text, results
    
    @staticmethod
    def extract_function_calls(text: str) -> str:
        """
        从文本中提取所有函数调用
        
        Args:
            text: 包含函数调用的文本
            
        Returns:
            str: 只包含函数调用的文本
        """
        pattern = r'<function>.*?</function>'
        matches = re.finditer(pattern, text, re.DOTALL)
        return '\n'.join(match.group(0) for match in matches)
    
    @staticmethod
    def validate_function_call(name: str, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        验证函数调用参数
        
        Args:
            name: 函数名
            parameters: 参数字典
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        func_def = registry.get_definition(name)
        if not func_def:
            return False, "未找到函数定义"
            
        required_params = {
            param.name
            for param in func_def.parameters
            if param.required
        }
        
        # 检查必需参数
        missing_params = required_params - set(parameters.keys())
        if missing_params:
            return False, f"缺少必需参数: {', '.join(missing_params)}"
            
        return True, None 