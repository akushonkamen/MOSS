import pytest
import asyncio
from src.services.function_calling.registry import registry, FunctionCategory
from src.services.function_calling.parser import FunctionParser

# 注册测试函数
@registry.register(
    description="测试函数",
    category=FunctionCategory.UTILITY,
    tags=["test"],
    examples=[{
        "description": "测试示例",
        "parameters": {
            "message": "Hello"
        }
    }]
)
async def helper_test_function(message: str) -> str:  # 重命名以避免与pytest冲突
    """测试函数
    
    Args:
        message: 测试消息
    """
    return f"收到消息: {message}"

@pytest.mark.asyncio
async def test_function_registration():
    """测试函数注册"""
    # 验证函数注册
    assert "helper_test_function" in registry._functions
    
    # 验证函数定义
    func_def = registry.get_definition("helper_test_function")
    assert func_def is not None
    assert func_def.name == "helper_test_function"
    assert func_def.category == FunctionCategory.UTILITY
    assert "test" in func_def.tags
    
    # 验证参数定义
    assert len(func_def.parameters) == 1
    param = func_def.parameters[0]
    assert param.name == "message"
    assert param.type == "string"
    assert param.required is True

@pytest.mark.asyncio
async def test_function_parsing():
    """测试函数解析"""
    text = """
    测试函数调用
    
    <function>
    name: helper_test_function
    parameters:
      message: Hello World
    </function>
    """
    
    # 解析函数调用
    calls = FunctionParser.parse_function_calls(text)
    assert len(calls) == 1
    
    name, params = calls[0]
    assert name == "helper_test_function"
    assert params == {"message": "Hello World"}

@pytest.mark.asyncio
async def test_function_execution():
    """测试函数执行"""
    text = """
    测试函数调用
    
    <function>
    name: helper_test_function
    parameters:
      message: Hello World
    </function>
    """
    
    # 执行函数调用
    response, results = await FunctionParser.execute_function_calls(text)
    
    # 验证结果
    assert len(results) == 1
    assert "result" in results[0]
    assert results[0]["result"] == "收到消息: Hello World"
    
    # 验证响应文本
    assert "测试函数调用" in response
    assert "收到消息: Hello World" in response

@pytest.mark.asyncio
async def test_multiple_functions():
    """测试多个函数调用"""
    # 注册另一个测试函数
    @registry.register(
        description="第二个测试函数",
        category=FunctionCategory.UTILITY,
        tags=["test"]
    )
    async def another_test_function(value: int) -> str:
        return f"数值: {value}"
    
    text = """
    测试多个函数调用
    
    <function>
    name: helper_test_function
    parameters:
      message: First Call
    </function>
    
    <function>
    name: another_test_function
    parameters:
      value: 42
    </function>
    """
    
    # 执行函数调用
    response, results = await FunctionParser.execute_function_calls(text)
    
    # 验证结果
    assert len(results) == 2
    assert results[0]["result"] == "收到消息: First Call"
    assert results[1]["result"] == "数值: 42"
    
    # 验证响应文本
    assert "测试多个函数调用" in response
    assert "收到消息: First Call" in response
    assert "数值: 42" in response

@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    text = """
    测试错误处理
    
    <function>
    name: non_existent_function
    parameters:
      param: value
    </function>
    
    <function>
    name: helper_test_function
    parameters:
      wrong_param: value
    </function>
    """
    
    # 执行函数调用
    response, results = await FunctionParser.execute_function_calls(text)
    
    # 验证结果
    assert len(results) == 2
    assert "error" in results[0]
    assert "error" in results[1]
    
    # 验证错误消息
    assert "未找到函数" in results[0]["error"]
    assert "unexpected keyword argument" in results[1]["error"]
    
    # 验证响应文本
    assert "测试错误处理" in response
    assert "操作失败" in response 