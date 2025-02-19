"""设备相关的工具函数"""

from .function_definitions import get_device_functions
from .registry import register_function, get_function, list_functions

__all__ = [
    'get_device_functions',
    'register_function',
    'get_function',
    'list_functions'
] 