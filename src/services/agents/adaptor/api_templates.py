"""API模板模块

提供API规范模板和分析提示词。
"""
import json
from typing import Dict, Any

def get_api_analysis_prompt(api_data: Dict[str, Any]) -> str:
    """生成API分析提示词
    
    Args:
        api_data: API数据
        
    Returns:
        str: 分析提示词
    """
    return f"""作为一个专业的设备API适配专家，请分析以下API信息并生成标准化的设备控制接口规范。

API端点信息:
{json.dumps(api_data.get('endpoints', {}), indent=2, ensure_ascii=False)}

可用端点列表:
{json.dumps(api_data.get('available_endpoints', []), indent=2, ensure_ascii=False)}

设备元数据:
{json.dumps(api_data.get('metadata', {}), indent=2, ensure_ascii=False)}

请生成一个标准化的API规范，包含以下部分：

1. device_info:
   - device_type: 设备类型
   - name: 设备名称
   - description: 设备描述
   - capabilities: 设备支持的功能列表
   - protocol: 通信协议
   - auth_required: 是否需要认证

2. api_mapping:
   - status: 状态查询相关端点
     - endpoint: 具体的API路径（必需）
     - method: HTTP方法（必需）
     - parameters: 参数定义
     - response_mapping: 响应字段映射
   - control: 控制相关端点
     - endpoint: 具体的API路径（必需）
     - method: HTTP方法（必需）
     - parameters: 参数定义
     - response_mapping: 响应字段映射

3. validation_rules:
   - parameters: 参数验证规则
   - response: 响应验证规则

请确保：
1. 每个端点都必须包含 endpoint 和 method 字段
2. endpoint 必须是有效的API路径
3. method 必须是有效的HTTP方法（GET, POST, PUT, DELETE）
4. 参数定义要完整
5. 响应映射要合理

请直接返回JSON格式的API规范，不要包含任何其他说明文字。"""

def create_api_spec_template() -> Dict[str, Any]:
    """创建基础API规范模板
    
    Returns:
        Dict[str, Any]: API规范模板
    """
    return {
        "device_info": {
            "device_type": "",
            "name": "",
            "description": "",
            "capabilities": [],
            "protocol": "http",
            "auth_required": False
        },
        "api_mapping": {
            "status": {
                "endpoint": "",
                "method": "GET",
                "parameters": {},
                "response_mapping": {}
            },
            "control": {
                "endpoint": "",
                "method": "POST",
                "parameters": {},
                "response_mapping": {}
            }
        },
        "validation_rules": {
            "parameters": {},
            "response": {}
        }
    }

def create_endpoint_spec(endpoint: str = "", method: str = "GET") -> Dict[str, Any]:
    """创建端点规范
    
    Args:
        endpoint: API端点路径
        method: HTTP方法
        
    Returns:
        Dict[str, Any]: 端点规范
    """
    return {
        "endpoint": endpoint,
        "method": method,
        "parameters": {},
        "response_mapping": {},
        "validation": {
            "required_params": [],
            "optional_params": [],
            "response_schema": {}
        }
    } 