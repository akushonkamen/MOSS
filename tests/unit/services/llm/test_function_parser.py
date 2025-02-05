import pytest
from src.services.llm.function_parser import FunctionParser
from src.services.llm.function_call import registry

@pytest.fixture
def example_functions():
    """注册示例函数"""
    @registry.register(
        description="Add two numbers",
        category="math",
        tags=["math"]
    )
    async def add(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
        
    @registry.register(
        description="Convert text to uppercase",
        category="text",
        tags=["text"]
    )
    async def upper(text: str) -> str:
        """Convert text to uppercase"""
        return text.upper()
        
    return [add, upper]

def test_parse_function_calls():
    """测试函数调用解析"""
    text = """
    Let me help you with that.
    
    <function>
    name: add
    parameters:
      a: 1
      b: 2
    </function>
    
    And also:
    
    <function>
    name: upper
    parameters:
      text: hello
    </function>
    """
    
    calls = FunctionParser.parse_function_calls(text)
    assert len(calls) == 2
    
    # 验证第一个调用
    name1, params1 = calls[0]
    assert name1 == "add"
    assert params1 == {"a": 1, "b": 2}
    
    # 验证第二个调用
    name2, params2 = calls[1]
    assert name2 == "upper"
    assert params2 == {"text": "hello"}

def test_parse_invalid_function_calls():
    """测试无效函数调用解析"""
    # 缺少函数名
    text1 = """
    <function>
    parameters:
      a: 1
    </function>
    """
    calls = FunctionParser.parse_function_calls(text1)
    assert len(calls) == 0
    
    # 无效的YAML
    text2 = """
    <function>
    invalid: yaml:
    </function>
    """
    calls = FunctionParser.parse_function_calls(text2)
    assert len(calls) == 0

@pytest.mark.asyncio
async def test_execute_function_calls(example_functions):
    """测试函数调用执行"""
    text = """
    Let me calculate that for you:
    
    <function>
    name: add
    parameters:
      a: 1
      b: 2
    </function>
    
    And convert this to uppercase:
    
    <function>
    name: upper
    parameters:
      text: hello
    </function>
    """
    
    processed_text, results = await FunctionParser.execute_function_calls(text)
    
    # 验证结果数量
    assert len(results) == 2
    
    # 验证第一个结果
    assert results[0]["function"] == "add"
    assert results[0]["parameters"] == {"a": 1, "b": 2}
    assert results[0]["result"] == 3
    
    # 验证第二个结果
    assert results[1]["function"] == "upper"
    assert results[1]["parameters"] == {"text": "hello"}
    assert results[1]["result"] == "HELLO"
    
    # 验证文本替换
    assert "[函数 add 的执行结果: 3]" in processed_text
    assert "[函数 upper 的执行结果: HELLO]" in processed_text

@pytest.mark.asyncio
async def test_execute_invalid_function_calls():
    """测试执行无效的函数调用"""
    text = """
    Let me try an invalid function:
    
    <function>
    name: non_existent
    parameters:
      x: 1
    </function>
    """
    
    processed_text, results = await FunctionParser.execute_function_calls(text)
    assert len(results) == 0
    assert "执行失败" in processed_text

def test_extract_function_calls():
    """测试提取函数调用"""
    text = """
    Some text before
    
    <function>
    name: test1
    parameters:
      a: 1
    </function>
    
    Some text in between
    
    <function>
    name: test2
    parameters:
      b: 2
    </function>
    
    Some text after
    """
    
    extracted = FunctionParser.extract_function_calls(text)
    assert "<function>" in extracted
    assert "test1" in extracted
    assert "test2" in extracted
    assert "Some text before" not in extracted
    assert "Some text in between" not in extracted
    assert "Some text after" not in extracted

def test_validate_function_call(example_functions):
    """测试函数调用验证"""
    # 验证有效调用
    valid, error = FunctionParser.validate_function_call("add", {"a": 1, "b": 2})
    assert valid is True
    assert error is None
    
    # 验证缺少参数
    valid, error = FunctionParser.validate_function_call("add", {"a": 1})
    assert valid is False
    assert "缺少必需参数" in error
    
    # 验证类型错误
    valid, error = FunctionParser.validate_function_call("add", {"a": "1", "b": 2})
    assert valid is False
    assert "必须是整数类型" in error
    
    # 验证不存在的函数
    valid, error = FunctionParser.validate_function_call("non_existent", {})
    assert valid is False
    assert "未找到函数" in error 