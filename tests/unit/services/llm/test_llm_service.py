import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import test_utils, web, ClientSession
from src.services.llm.llm_service import llm_service
from src.services.llm.prompt_manager import PromptTemplate
from src.services.llm.function_call import registry

class MockStreamResponse:
    """模拟的流式响应"""
    def __init__(self, status=200, content=None, text=None):
        self.status = status
        self._content = content or []
        self._text = text
        self.content = self  # Make content property point to self for streaming

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def __aiter__(self):
        for item in self._content:
            yield item

    async def text(self):
        return self._text

class MockClientSession:
    """模拟的HTTP客户端会话"""
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    def post(self, *args, **kwargs):
        """返回一个异步上下文管理器"""
        return self.response

@pytest.fixture
def service():
    """创建 llm_service 实例的 fixture"""
    return llm_service()

@pytest.fixture
def sample_template():
    """创建示例模板"""
    return PromptTemplate(
        name="test_template",
        version="1.0.0",
        description="Test template",
        template="Test prompt: {user_input}",
        parameters={"user_input": {"type": "string", "description": "User input"}},
        tags=["test"],
        category="test"
    )

@pytest.fixture
def example_function():
    """创建示例函数的 fixture"""
    @registry.register(
        description="Test function",
        category="test",
        tags=["test"]
    )
    async def test_func(text: str) -> str:
        """测试函数，将文本转换为大写"""
        return text.upper()
    return test_func

@pytest.mark.asyncio
async def test_chat_stream_basic(service):
    """测试基本的流式对话功能"""
    content = [
        json.dumps({"message": {"content": "Hello"}}).encode(),
        json.dumps({"done": True}).encode()
    ]
    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream("Hi", "test_session"):
            responses.append(response)

    assert len(responses) > 0
    assert "Hello" in "".join(responses)

@pytest.mark.asyncio
async def test_chat_stream_with_template(service, sample_template):
    """测试使用模板的流式对话功能"""
    service.prompt_manager.add_template(sample_template)
    
    content = [
        json.dumps({"message": {"content": "Hello from template"}}).encode(),
        json.dumps({"done": True}).encode()
    ]
    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream(
            "Hi",
            "test_session",
            template_name="test_template",
            template_params={"user_input": "value"}
        ):
            responses.append(response)

    assert len(responses) > 0
    assert "Hello from template" in "".join(responses)

@pytest.mark.asyncio
async def test_chat_stream_with_function(service, example_function):
    """测试使用函数调用的流式对话功能"""
    service.register_function(example_function)
    
    content = [
        json.dumps({"message": {"content": """Let me help you with that:

        <function>
        name: test_func
        parameters:
          text: hello
        </function>
        """}}).encode(),
        json.dumps({"done": True}).encode()
    ]
    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream(
            "Convert this to uppercase: hello",
            "test_session",
            functions=[example_function.__name__]
        ):
            responses.append(response)

    assert len(responses) > 0
    assert "HELLO" in "".join(responses)

@pytest.mark.asyncio
async def test_chat_stream_with_invalid_function(service):
    """测试使用无效函数的流式对话功能"""
    content = [
        json.dumps({"message": {"content": """Let me try that:

        <function>
        name: non_existent_func
        parameters:
          text: hello
        </function>
        """}}).encode(),
        json.dumps({"done": True}).encode()
    ]
    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream(
            "Try an invalid function",
            "test_session",
            functions=["non_existent_func"]
        ):
            responses.append(response)

    assert len(responses) > 0
    assert "函数执行失败" in "".join(responses)

@pytest.mark.asyncio
async def test_chat_stream_api_error(service):
    """测试API错误处理"""
    mock_response = MockStreamResponse(status=500, text="Internal Server Error")
    mock_session = MockClientSession(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream("Hello", "test_session"):
            responses.append(response)

    assert len(responses) == 1
    assert "API调用失败" in responses[0]

@pytest.mark.asyncio
async def test_conversation_management(service):
    """测试会话管理功能"""
    # 测试创建新会话
    conversation = service._get_or_create_conversation("test_session")
    assert conversation is not None
    assert len(conversation) == 0

    # 测试获取已存在的会话
    same_conversation = service._get_or_create_conversation("test_session")
    assert same_conversation is conversation

    # 测试清除会话
    service.clear_conversation("test_session")
    new_conversation = service._get_or_create_conversation("test_session")
    assert new_conversation is not conversation
    assert len(new_conversation) == 0

@pytest.mark.asyncio
async def test_function_registration(service, example_function):
    """测试函数注册功能"""
    # 测试注册函数
    service.register_function(example_function)
    assert example_function.__name__ in service.functions

    # 测试注销函数
    service.unregister_function(example_function.__name__)
    assert example_function.__name__ not in service.functions

def test_remove_think_tags(service):
    """测试移除思考标签功能"""
    # 测试基本标签移除
    text = "Hello <think>thinking</think> World"
    result = service._remove_think_tags(text)
    assert result == "Hello  World"

    # 测试嵌套标签移除
    text = "Hello <think>outer <think>inner</think> text</think> World"
    result = service._remove_think_tags(text)
    assert result == "Hello  World"

    # 测试多行标签移除
    text = """Hello
    <think>
    thinking
    more thinking
    </think>
    World"""
    result = service._remove_think_tags(text)
    assert result == """Hello
    
    World""" 