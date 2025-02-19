from typing import Dict, Any, Optional, List, Callable, Set
from pydantic import BaseModel, Field
import json
import inspect
from functools import wraps

class FunctionParameter(BaseModel):
    """函数参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型")
    description: str = Field("", description="参数描述")
    required: bool = Field(True, description="是否必需")
    default: Any = Field(None, description="默认值")
    enum: Optional[List[str]] = Field(None, description="可选值列表")

class FunctionDefinition(BaseModel):
    """函数定义"""
    name: str = Field(..., description="函数名称")
    description: str = Field("", description="函数描述")
    implementation: Callable = Field(..., description="函数实现")
    parameters: Optional[Dict[str, Any]] = Field(None, description="参数定义")

class FunctionRegistry:
    """函数注册表"""
    
    def __init__(self):
        """初始化函数注册表"""
        self._functions: Dict[str, FunctionDefinition] = {}
        
    def register_function(
        self,
        name: str,
        description: str,
        implementation: Callable,
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """注册函数
        
        Args:
            name: 函数名称
            description: 函数描述
            implementation: 函数实现
            parameters: 函数参数定义
        """
        self._functions[name] = FunctionDefinition(
            name=name,
            description=description,
            implementation=implementation,
            parameters=parameters
        )
        
    def get_function(self, name: str) -> Optional[FunctionDefinition]:
        """获取函数定义
        
        Args:
            name: 函数名称
            
        Returns:
            Optional[FunctionDefinition]: 函数定义
        """
        return self._functions.get(name)
        
    def list_functions(self) -> List[FunctionDefinition]:
        """获取所有函数定义
        
        Returns:
            List[FunctionDefinition]: 函数定义列表
        """
        return list(self._functions.values())
        
    def clear(self) -> None:
        """清空注册表"""
        self._functions.clear()

# 创建全局函数注册表实例
registry = FunctionRegistry() 