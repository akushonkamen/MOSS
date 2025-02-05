"""示例函数"""
from typing import List, Dict, Any
from datetime import datetime
from .function_call import registry as global_registry, FunctionRegistry

def register_example_functions(registry: FunctionRegistry = None):
    """注册示例函数
    
    Args:
        registry: 函数注册表，如果为None则使用全局注册表
    """
    if registry is None:
        registry = global_registry
    
    # 注册时间相关函数
    registry.register_function(
        name="get_current_time",
        description="获取当前时间",
        implementation=get_current_time
    )
    
    # 注册数学相关函数
    registry.register_function(
        name="add_numbers",
        description="计算两个数的和",
        implementation=add_numbers,
        parameters={
            "a": {
                "type": "number",
                "description": "第一个数",
                "required": True
            },
            "b": {
                "type": "number",
                "description": "第二个数",
                "required": True
            }
        }
    )
    
    # 注册文本处理函数
    registry.register_function(
        name="to_upper",
        description="将文本转换为大写",
        implementation=to_upper,
        parameters={
            "text": {
                "type": "string",
                "description": "要转换的文本",
                "required": True
            }
        }
    )
    
    registry.register_function(
        name="select_option",
        description="从列表中选择一个选项",
        implementation=select_option,
        parameters={
            "options": {
                "type": "array",
                "description": "选项列表",
                "required": True,
                "items": {
                    "type": "string"
                }
            },
            "default": {
                "type": "string",
                "description": "默认选项",
                "required": False,
                "default": ""
            }
        }
    )
    
    registry.register_function(
        name="format_json",
        description="格式化JSON数据",
        implementation=format_json,
        parameters={
            "data": {
                "type": "object",
                "description": "JSON数据",
                "required": True
            },
            "indent": {
                "type": "integer",
                "description": "缩进空格数",
                "required": False,
                "default": 2
            }
        }
    )
    
    registry.register_function(
        name="random_number",
        description="生成一个范围内的随机数",
        implementation=random_number,
        parameters={
            "min_value": {
                "type": "integer",
                "description": "最小值",
                "required": False,
                "default": 0
            },
            "max_value": {
                "type": "integer",
                "description": "最大值",
                "required": False,
                "default": 100
            }
        }
    )
    
    registry.register_function(
        name="contains_keywords",
        description="检查文本是否包含特定关键词",
        implementation=contains_keywords,
        parameters={
            "text": {
                "type": "string",
                "description": "要检查的文本",
                "required": True
            },
            "keywords": {
                "type": "array",
                "description": "关键词列表",
                "required": True,
                "items": {
                    "type": "string"
                }
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "是否区分大小写",
                "required": False,
                "default": False
            }
        }
    )
    
    registry.register_function(
        name="join_list",
        description="将列表连接为字符串",
        implementation=join_list,
        parameters={
            "items": {
                "type": "array",
                "description": "要连接的列表",
                "required": True,
                "items": {
                    "type": "string"
                }
            },
            "separator": {
                "type": "string",
                "description": "分隔符",
                "required": False,
                "default": ", "
            }
        }
    )
    
    registry.register_function(
        name="text_statistics",
        description="计算文本的统计信息",
        implementation=text_statistics,
        parameters={
            "text": {
                "type": "string",
                "description": "要分析的文本",
                "required": True
            }
        }
    )
    
    registry.register_function(
        name="validate_email",
        description="验证邮箱地址格式",
        implementation=validate_email,
        parameters={
            "email": {
                "type": "string",
                "description": "要验证的邮箱地址",
                "required": True
            }
        }
    )

async def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def add_numbers(a: float, b: float) -> float:
    """计算两个数的和"""
    return a + b

async def to_upper(text: str) -> str:
    """将文本转换为大写"""
    return text.upper()

async def select_option(options: List[str], default: str = "") -> str:
    """
    从列表中选择一个选项
    
    Args:
        options: 选项列表
        default: 默认选项
    """
    if not options:
        return default
    return options[0]

async def format_json(data: Dict[str, Any], indent: int = 2) -> str:
    """
    格式化JSON数据
    
    Args:
        data: JSON数据
        indent: 缩进空格数
    """
    import json
    return json.dumps(data, indent=indent, ensure_ascii=False)

async def random_number(min_value: int = 0, max_value: int = 100) -> int:
    """
    生成一个范围内的随机数
    
    Args:
        min_value: 最小值
        max_value: 最大值
    """
    import random
    return random.randint(min_value, max_value)

async def contains_keywords(text: str, keywords: List[str], case_sensitive: bool = False) -> bool:
    """
    检查文本是否包含特定关键词
    
    Args:
        text: 要检查的文本
        keywords: 关键词列表
        case_sensitive: 是否区分大小写
    """
    if not case_sensitive:
        text = text.lower()
        keywords = [k.lower() for k in keywords]
    return any(k in text for k in keywords)

async def join_list(items: List[str], separator: str = ", ") -> str:
    """
    将列表连接为字符串
    
    Args:
        items: 要连接的列表
        separator: 分隔符
    """
    return separator.join(items)

async def text_statistics(text: str) -> Dict[str, int]:
    """
    计算文本的统计信息
    
    Args:
        text: 要分析的文本
    """
    return {
        "characters": len(text),
        "words": len(text.split()),
        "lines": len(text.splitlines()),
        "spaces": text.count(" ")
    }

async def validate_email(email: str) -> bool:
    """
    验证邮箱地址格式
    
    Args:
        email: 要验证的邮箱地址
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) 