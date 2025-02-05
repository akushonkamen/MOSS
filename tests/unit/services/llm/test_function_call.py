import pytest
from typing import List
from src.services.llm.function_call import registry, FunctionDefinition, FunctionParameter

@pytest.fixture
def example_function():
    """创建示例函数"""
    @registry.register(
        description="Test function",
        category="test",
        tags=["test"]
    )
    async def test_func(a: int, b: str = "default") -> str:
        """Test function"""
        return f"{a} - {b}"
    return test_func

def test_function_registration(example_function):
    """测试函数注册"""
    definition = registry.get_definition("test_func")
    assert definition is not None
    assert definition.name == "test_func"
    assert definition.description == "Test function"
    assert definition.category == "test"
    assert "test" in definition.tags
    
    # 验证参数
    params = {p.name: p for p in definition.parameters}
    assert "a" in params
    assert params["a"].type == "integer"
    assert params["a"].required is True
    
    assert "b" in params
    assert params["b"].type == "string"
    assert params["b"].required is False

def test_function_listing():
    """测试函数列表"""
    # 注册多个函数
    @registry.register(category="math", tags=["math"])
    async def add(a: int, b: int) -> int:
        return a + b
        
    @registry.register(category="text", tags=["text"])
    async def upper(text: str) -> str:
        return text.upper()
        
    # 测试无过滤
    all_funcs = registry.list_functions()
    assert len(all_funcs) >= 2
    
    # 测试按分类过滤
    math_funcs = registry.list_functions(category="math")
    assert len(math_funcs) >= 1
    assert all(f.category == "math" for f in math_funcs)
    
    # 测试按标签过滤
    text_funcs = registry.list_functions(tag="text")
    assert len(text_funcs) >= 1
    assert all("text" in f.tags for f in text_funcs)

@pytest.mark.asyncio
async def test_function_execution(example_function):
    """测试函数执行"""
    func = registry.get_function("test_func")
    assert func is not None
    
    # 测试必需参数
    result = await func(a=1)
    assert result == "1 - default"
    
    # 测试可选参数
    result = await func(a=1, b="test")
    assert result == "1 - test"

def test_prompt_generation():
    """测试提示词生成"""
    # 注册测试函数
    @registry.register(
        description="Add two numbers",
        category="math",
        tags=["math"]
    )
    async def add(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
        
    # 生成提示词
    prompt = registry.to_prompt(["add"])
    assert "add" in prompt
    assert "Add two numbers" in prompt
    assert "a: integer" in prompt
    assert "b: integer" in prompt
    
    # 测试函数过滤
    prompt = registry.to_prompt(["non_existent"])
    assert prompt == "你可以使用以下函数：\n\n"

def test_parameter_validation():
    """测试参数验证"""
    # 注册带有枚举值的函数
    @registry.register
    async def select_color(color: str = "red") -> str:
        """Select a color"""
        return color
        
    definition = registry.get_definition("select_color")
    assert definition is not None
    
    # 验证参数类型
    param = definition.parameters[0]
    assert param.name == "color"
    assert param.type == "string"
    assert param.required is False

def test_function_documentation():
    """测试函数文档"""
    @registry.register(
        description="Test function with detailed docs",
        category="test",
        tags=["test", "docs"]
    )
    async def documented_func(
        text: str,
        count: int = 1,
        options: List[str] = None
    ) -> str:
        """
        A test function with detailed documentation
        
        Args:
            text: Input text
            count: Number of repetitions
            options: Optional settings
            
        Returns:
            str: Processed text
        """
        return text * count
        
    definition = registry.get_definition("documented_func")
    assert definition is not None
    assert definition.description == "Test function with detailed docs"
    assert len(definition.parameters) == 3
    
    # 验证参数
    params = {p.name: p for p in definition.parameters}
    assert "text" in params
    assert params["text"].type == "string"
    assert params["text"].required is True
    
    assert "count" in params
    assert params["count"].type == "integer"
    assert params["count"].required is False
    
    assert "options" in params
    assert params["options"].type == "array"
    assert params["options"].required is False 