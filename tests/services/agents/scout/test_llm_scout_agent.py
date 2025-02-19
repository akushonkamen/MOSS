"""LLM增强的设备侦察智能体测试

测试LLMScoutAgent的各项功能，包括：
1. 端口探测
2. 设备分析
3. LLM集成
4. 学习能力
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.agents.scout.scout_agent import LLMScoutAgent, DetectionContext
from src.services.events.event_bus import Event, EventType

# 测试数据
MOCK_PORT_INFO = {
    "port": 8080,
    "status": "opened",
    "address": "192.168.1.100",
    "protocol": "tcp"
}

MOCK_RESPONSE_DATA = {
    "device": {
        "type": "smart_light",
        "name": "Living Room Light",
        "capabilities": ["on_off", "brightness", "color"]
    },
    "api_version": "1.0",
    "endpoints": [
        "/status",
        "/control",
        "/capabilities"
    ]
}

MOCK_LLM_ANALYSIS = {
    "is_device": True,
    "confidence": 0.95,
    "device_type": "smart_light",
    "capabilities": ["on_off", "brightness", "color"],
    "reasoning": "Response contains typical smart light device characteristics"
}

MOCK_PROBE_STRATEGY = {
    "endpoints": ["/status", "/info", "/api"],
    "methods": ["GET"],
    "headers": {"Accept": "application/json"},
    "fallback_strategies": ["try_upnp", "try_mdns"]
}

@pytest.fixture
def mock_llm_service():
    """创建模拟的LLM服务"""
    mock_service = AsyncMock()
    mock_service.generate = AsyncMock()
    return mock_service

@pytest.fixture
async def agent(mock_llm_service):
    """创建测试用的LLMScoutAgent实例"""
    agent = LLMScoutAgent("test_scout", mock_llm_service)
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_initialize(agent):
    """测试智能体初始化"""
    assert agent.agent_id == "test_scout"
    assert agent._known_ports == set()
    assert isinstance(agent._detection_cache, dict)
    assert agent._prompts is not None

@pytest.mark.asyncio
async def test_generate_probe_strategy(agent, mock_llm_service):
    """测试生成探测策略"""
    mock_llm_service.generate.return_value = json.dumps(MOCK_PROBE_STRATEGY)
    
    context = DetectionContext(port_info=MOCK_PORT_INFO)
    strategy = await agent._generate_probe_strategy(context)
    
    assert strategy == MOCK_PROBE_STRATEGY
    assert "endpoints" in strategy
    assert "methods" in strategy
    assert "headers" in strategy
    
    # 测试异常处理
    mock_llm_service.generate.side_effect = Exception("LLM error")
    fallback_strategy = await agent._generate_probe_strategy(context)
    assert isinstance(fallback_strategy, dict)
    assert "/docs" in fallback_strategy["endpoints"]

@pytest.mark.asyncio
async def test_analyze_with_llm(agent, mock_llm_service):
    """测试LLM分析功能"""
    mock_llm_service.generate.return_value = json.dumps(MOCK_LLM_ANALYSIS)
    
    context = DetectionContext(
        port_info=MOCK_PORT_INFO,
        response_data=MOCK_RESPONSE_DATA
    )
    
    analysis = await agent._analyze_with_llm(context)
    
    assert analysis == MOCK_LLM_ANALYSIS
    assert analysis["is_device"] is True
    assert analysis["confidence"] > 0.9
    assert "device_type" in analysis
    
    # 测试无响应数据的情况
    context.response_data = None
    analysis = await agent._analyze_with_llm(context)
    assert analysis["is_device"] is False
    assert analysis["confidence"] == 0.0

@pytest.mark.asyncio
async def test_execute_probe_strategy(agent):
    """测试执行探测策略"""
    with patch("aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_RESPONSE_DATA)
        mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response
        
        result = await agent._execute_probe_strategy(
            "192.168.1.100",
            8080,
            MOCK_PROBE_STRATEGY
        )
        
        assert result["success"] is True
        assert result["response_data"] == MOCK_RESPONSE_DATA
        
        # 测试请求失败的情况
        mock_response.status = 404
        result = await agent._execute_probe_strategy(
            "192.168.1.100",
            8080,
            MOCK_PROBE_STRATEGY
        )
        assert result["success"] is False

@pytest.mark.asyncio
async def test_on_port_change(agent, mock_llm_service):
    """测试端口变化事件处理"""
    # 模拟成功的设备发现
    mock_llm_service.generate.side_effect = [
        json.dumps(MOCK_PROBE_STRATEGY),
        json.dumps(MOCK_LLM_ANALYSIS),
        "{}"  # 学习结果
    ]
    
    with patch.object(agent, "_execute_probe_strategy") as mock_execute:
        mock_execute.return_value = {
            "success": True,
            "response_data": MOCK_RESPONSE_DATA
        }
        
        event = Event(
            event_type=EventType.SYSTEM,
            event_name="port_change",
            data=MOCK_PORT_INFO
        )
        
        await agent._on_port_change(event)
        
        # 验证端口被记录
        assert MOCK_PORT_INFO["port"] in agent._known_ports
        
        # 测试端口关闭
        closed_event = Event(
            event_type=EventType.SYSTEM,
            event_name="port_change",
            data={**MOCK_PORT_INFO, "status": "closed"}
        )
        
        await agent._on_port_change(closed_event)
        assert MOCK_PORT_INFO["port"] not in agent._known_ports

@pytest.mark.asyncio
async def test_inspect_port(agent, mock_llm_service):
    """测试端口检查功能"""
    mock_llm_service.generate.side_effect = [
        json.dumps(MOCK_PROBE_STRATEGY),
        json.dumps(MOCK_LLM_ANALYSIS)
    ]
    
    with patch.object(agent, "_execute_probe_strategy") as mock_execute:
        mock_execute.return_value = {
            "success": True,
            "response_data": MOCK_RESPONSE_DATA
        }
        
        result = await agent._inspect_port({
            "address": "192.168.1.100",
            "port": 8080
        })
        
        assert result == MOCK_LLM_ANALYSIS
        assert result["is_device"] is True
        
        # 测试缓存
        cached_result = await agent._inspect_port({
            "address": "192.168.1.100",
            "port": 8080
        })
        assert cached_result == MOCK_LLM_ANALYSIS
        
        # 测试探测失败的情况
        mock_execute.return_value = {
            "success": False,
            "error": "Connection failed"
        }
        
        result = await agent._inspect_port({
            "address": "192.168.1.101",
            "port": 8081
        })
        
        assert result["is_device"] is False
        assert result["confidence"] == 0.0

@pytest.mark.asyncio
async def test_analyze_device(agent, mock_llm_service):
    """测试设备分析功能"""
    mock_llm_service.generate.return_value = json.dumps(MOCK_LLM_ANALYSIS)
    
    result = await agent._analyze_device({
        "address": "192.168.1.100",
        "port": 8080,
        "response_data": MOCK_RESPONSE_DATA
    })
    
    assert result == MOCK_LLM_ANALYSIS
    assert result["device_type"] == "smart_light"
    assert "capabilities" in result
    
    # 测试无响应数据的情况
    result = await agent._analyze_device({
        "address": "192.168.1.100",
        "port": 8080
    })
    assert "error" in result

@pytest.mark.asyncio
async def test_learn_from_detection(agent, mock_llm_service):
    """测试学习功能"""
    mock_llm_service.generate.return_value = json.dumps({
        "success_factors": ["Clear API structure", "Standard endpoints"],
        "improvement_areas": ["Add timeout retry", "Expand endpoint list"],
        "new_features": ["Protocol detection", "Service fingerprinting"],
        "strategy_adjustments": ["Increase timeout", "Add more fallbacks"]
    })
    
    detection_data = {
        "context": DetectionContext(
            port_info=MOCK_PORT_INFO,
            response_data=MOCK_RESPONSE_DATA,
            analysis_result=MOCK_LLM_ANALYSIS
        ),
        "probe_strategy": MOCK_PROBE_STRATEGY,
        "detection_result": {
            "success": True,
            "response_data": MOCK_RESPONSE_DATA
        },
        "final_analysis": MOCK_LLM_ANALYSIS
    }
    
    await agent._learn_from_detection(detection_data)
    mock_llm_service.generate.assert_called_once() 