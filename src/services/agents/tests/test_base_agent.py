import pytest
import asyncio
from typing import Dict, Any
from ..base import BaseAgent, AgentType, AgentStatus, AgentCapability

class TestAgent(BaseAgent):
    """测试用智能体实现"""
    
    def __init__(self, agent_id: str, agent_type: AgentType):
        super().__init__(agent_id, agent_type)
        self.process_called = False
        self.learn_called = False
        self.evolve_called = False
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self.process_called = True
        return {"result": "processed", "input": input_data}
    
    async def learn(self, experience: Dict[str, Any]) -> None:
        self.learn_called = True
        self.metrics.learning_progress += 0.1
    
    async def evolve(self) -> None:
        self.evolve_called = True
        self.metrics.evolution_score += 0.1

@pytest.mark.asyncio
async def test_agent_initialization():
    """测试智能体初始化"""
    agent = TestAgent("test_001", AgentType.DECODER)
    assert agent.id == "test_001"
    assert agent.type == AgentType.DECODER
    assert agent.status == AgentStatus.IDLE
    assert isinstance(agent.capabilities, dict)
    assert len(agent.capabilities) == 0

@pytest.mark.asyncio
async def test_agent_process():
    """测试处理功能"""
    agent = TestAgent("test_001", AgentType.DECODER)
    result = await agent.process({"test": "data"})
    assert agent.process_called
    assert result["result"] == "processed"
    assert result["input"] == {"test": "data"}

@pytest.mark.asyncio
async def test_agent_learn():
    """测试学习功能"""
    agent = TestAgent("test_001", AgentType.DECODER)
    initial_progress = agent.metrics.learning_progress
    await agent.learn({"experience": "test"})
    assert agent.learn_called
    assert agent.metrics.learning_progress > initial_progress

@pytest.mark.asyncio
async def test_agent_evolve():
    """测试进化功能"""
    agent = TestAgent("test_001", AgentType.DECODER)
    initial_score = agent.metrics.evolution_score
    await agent.evolve()
    assert agent.evolve_called
    assert agent.metrics.evolution_score > initial_score

@pytest.mark.asyncio
async def test_capability_management():
    """测试能力管理"""
    agent = TestAgent("test_001", AgentType.DECODER)
    
    # 测试能力注册
    capability = AgentCapability(
        name="test_capability",
        description="Test capability",
        parameters={"param1": "value1"},
        version="1.0.0"
    )
    await agent.register_capability(capability)
    assert agent.has_capability("test_capability")
    assert agent.get_capability("test_capability") == capability
    
    # 测试能力移除
    await agent.remove_capability("test_capability")
    assert not agent.has_capability("test_capability")
    assert agent.get_capability("test_capability") is None

@pytest.mark.asyncio
async def test_metrics_update():
    """测试度量指标更新"""
    agent = TestAgent("test_001", AgentType.DECODER)
    
    # 测试成功更新
    agent.update_metrics(success=True, response_time=0.1)
    assert agent.metrics.processing_count == 1
    assert agent.metrics.success_rate == 1.0
    assert agent.metrics.avg_response_time == 0.1
    
    # 测试失败更新
    agent.update_metrics(success=False, response_time=0.2)
    assert agent.metrics.processing_count == 2
    assert agent.metrics.success_rate == 0.5
    assert 0.15 - 0.001 <= agent.metrics.avg_response_time <= 0.15 + 0.001

@pytest.mark.asyncio
async def test_concurrent_capability_management():
    """测试并发能力管理"""
    agent = TestAgent("test_001", AgentType.DECODER)
    
    async def register_capability(name: str):
        capability = AgentCapability(
            name=name,
            description=f"Test capability {name}",
            parameters={},
            version="1.0.0"
        )
        await agent.register_capability(capability)
    
    # 并发注册多个能力
    tasks = [
        register_capability(f"capability_{i}")
        for i in range(5)
    ]
    await asyncio.gather(*tasks)
    
    # 验证所有能力都已正确注册
    for i in range(5):
        assert agent.has_capability(f"capability_{i}")
    
    # 测试并发移除
    tasks = [
        agent.remove_capability(f"capability_{i}")
        for i in range(5)
    ]
    await asyncio.gather(*tasks)
    
    # 验证所有能力都已正确移除
    for i in range(5):
        assert not agent.has_capability(f"capability_{i}")

def test_agent_serialization():
    """测试智能体序列化"""
    agent = TestAgent("test_001", AgentType.DECODER)
    capability = AgentCapability(
        name="test_capability",
        description="Test capability",
        parameters={"param1": "value1"},
        version="1.0.0"
    )
    asyncio.run(agent.register_capability(capability))
    
    data = agent.to_dict()
    assert data["id"] == "test_001"
    assert data["type"] == "decoder"
    assert data["status"] == "idle"
    assert "test_capability" in data["capabilities"]
    assert isinstance(data["metrics"], dict) 