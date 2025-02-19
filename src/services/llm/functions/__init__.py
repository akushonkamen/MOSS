"""函数调用系统

提供标准化的函数注册和调用机制，用于连接LLM自然语言处理和设备操作。
"""

from .registry import registry, FunctionCategory
from .parser import FunctionParser

__all__ = ['registry', 'FunctionCategory', 'FunctionParser']

async def setup_function_calling():
    """初始化函数调用系统"""
    # 导入并注册设备控制函数
    from ..devices.functions import register_device_functions
    register_device_functions()
    
    # 未来可以在这里添加更多的函数注册
    # 例如场景控制、自动化规则等 