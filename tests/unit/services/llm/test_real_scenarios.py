"""真实场景测试用例"""
import pytest
import json
import asyncio
from unittest.mock import patch
from src.services.llm.llm_service import llm_service
from src.services.llm.function_call import registry
from tests.unit.services.llm.test_llm_service import MockStreamResponse, MockClientSession

@pytest.fixture
def service():
    """创建 llm_service 实例"""
    return llm_service()

@pytest.fixture
def music_functions():
    """创建音乐相关的函数"""
    @registry.register(
        description="播放音乐",
        category="music",
        tags=["music", "control"]
    )
    async def play_music(genre: str = "classical", volume: int = 50) -> str:
        await asyncio.sleep(0.5)  # 模拟播放延迟
        return f"Playing {genre} music at volume {volume}"

    @registry.register(
        description="调整音量",
        category="music",
        tags=["music", "control"]
    )
    async def set_volume(level: int) -> str:
        await asyncio.sleep(0.2)  # 模拟设置延迟
        return f"Volume set to {level}"

    @registry.register(
        description="获取当前播放信息",
        category="music",
        tags=["music", "query"]
    )
    async def get_current_track() -> str:
        await asyncio.sleep(0.1)  # 模拟查询延迟
        return "Now playing: Moonlight Sonata by Beethoven"

    return [play_music, set_volume, get_current_track]

@pytest.mark.asyncio
async def test_music_control_scenario(service, music_functions):
    """测试音乐控制场景"""
    # 注册所有音乐相关函数
    for func in music_functions:
        service.register_function(func)

    # 模拟用户请求：播放音乐并调整音量
    content = [
        json.dumps({"message": {"content": "好的，我来帮您播放音乐。"}}).encode(),
        json.dumps({"message": {"content": """
        首先，让我为您播放一些轻音乐：
        <function>
        name: play_music
        parameters:
          genre: classical
          volume: 40
        </function>
        
        现在，我来调整音量：
        <function>
        name: set_volume
        parameters:
          level: 60
        </function>
        
        让我查看一下当前播放的音乐：
        <function>
        name: get_current_track
        parameters: {}
        </function>
        """}}).encode(),
        json.dumps({"done": True}).encode()
    ]

    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream(
            "播放一些轻音乐，把音量调大一点，然后告诉我现在播放的是什么",
            "test_session",
            functions=[func.__name__ for func in music_functions]
        ):
            responses.append(response)
            print(f"收到响应: {response}")  # 用于调试

    # 验证响应的自然性
    full_response = " ".join(responses)
    assert "好的，我来帮您播放音乐" in full_response
    assert "已经开始播放" in full_response
    assert "设置已更新" in full_response
    assert "现在播放的是" in full_response
    assert "Moonlight Sonata" in full_response

@pytest.mark.asyncio
async def test_error_handling_scenario(service, music_functions):
    """测试错误处理场景"""
    # 只注册部分函数，模拟某些功能不可用的情况
    service.register_function(music_functions[0])  # 只注册 play_music

    content = [
        json.dumps({"message": {"content": "让我帮您处理这些请求。"}}).encode(),
        json.dumps({"message": {"content": """
        首先播放音乐：
        <function>
        name: play_music
        parameters:
          genre: jazz
          volume: 50
        </function>
        
        现在尝试调整音量：
        <function>
        name: set_volume
        parameters:
          level: 70
        </function>
        """}}).encode(),
        json.dumps({"done": True}).encode()
    ]

    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        async for response in service.chat_stream(
            "播放爵士乐，音量调到70",
            "test_session",
            functions=[func.__name__ for func in music_functions]
        ):
            responses.append(response)
            print(f"收到响应: {response}")  # 用于调试

    # 验证响应的自然性
    full_response = " ".join(responses)
    assert "让我帮您处理这些请求" in full_response
    assert "已经开始播放" in full_response
    assert "抱歉，我暂时无法执行这个操作" in full_response  # set_volume 不可用

@pytest.mark.asyncio
async def test_parallel_operations_scenario(service, music_functions):
    """测试并行操作场景"""
    # 注册所有音乐相关函数
    for func in music_functions:
        service.register_function(func)

    content = [
        json.dumps({"message": {"content": "正在处理您的请求..."}}).encode(),
        json.dumps({"message": {"content": "音乐马上就来了，"}}).encode(),
        json.dumps({"message": {"content": """同时我会调整音量：
        <function>
        name: play_music
        parameters:
          genre: classical
          volume: 40
        </function>
        <function>
        name: set_volume
        parameters:
          level: 60
        </function>
        """}}).encode(),
        json.dumps({"done": True}).encode()
    ]

    mock_response = MockStreamResponse(status=200, content=content)
    mock_session = MockClientSession(mock_response)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        responses = []
        start_time = asyncio.get_event_loop().time()
        async for response in service.chat_stream(
            "播放古典音乐，把音量调到60",
            "test_session",
            functions=[func.__name__ for func in music_functions]
        ):
            responses.append(response)
            print(f"收到响应: {response}")  # 用于调试
        end_time = asyncio.get_event_loop().time()

    # 验证响应的自然性和并行性
    full_response = " ".join(responses)
    assert "正在处理您的请求" in full_response
    assert "音乐马上就来了" in full_response
    assert "已经开始播放" in full_response
    assert "设置已更新" in full_response

    # 验证总执行时间是否符合并行操作的预期
    # 如果是串行执行，总时间应该超过 0.7 秒 (0.5 + 0.2)
    # 如果是并行执行，总时间应该接近 0.5 秒（最长的单个操作时间）
    execution_time = end_time - start_time
    assert execution_time < 0.7, "操作可能没有并行执行" 