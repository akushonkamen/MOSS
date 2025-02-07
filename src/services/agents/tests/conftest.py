import pytest
import asyncio
from typing import Dict, Any, List
from ..base import BaseAgent, AgentType, AgentStatus
from ..dispatch import AgentDispatchCenter

class TestAgent(BaseAgent):
    """测试用智能体实现"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, delay: float = 0):
        super().__init__(agent_id, agent_type)
        self.process_called = False
        self.learn_called = False
        self.evolve_called = False
        self.delay = delay
        self.input_history = []
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self.process_called = True
        self.input_history.append(input_data)
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return {"result": f"processed_by_{self.id}", "input": input_data}
    
    async def learn(self, experience: Dict[str, Any]) -> None:
        self.learn_called = True
        self.metrics.learning_progress += 0.1
        if self.delay > 0:
            await asyncio.sleep(self.delay)
    
    async def evolve(self) -> None:
        self.evolve_called = True
        self.metrics.evolution_score += 0.1
        if self.delay > 0:
            await asyncio.sleep(self.delay)

@pytest.fixture
def test_agent():
    """创建测试智能体"""
    return TestAgent("test_001", AgentType.DECODER)

@pytest.fixture
def test_agents():
    """创建多个测试智能体"""
    return [
        TestAgent(f"agent_{i}", AgentType.DECODER)
        for i in range(3)
    ]

@pytest.fixture
def dispatch_center():
    """创建调度中心"""
    return AgentDispatchCenter()

@pytest.fixture
async def setup_pipeline(dispatch_center, test_agents):
    """设置测试管道"""
    # 注册智能体
    for agent in test_agents:
        await dispatch_center.register_agent(agent)
    
    # 创建管道
    await dispatch_center.create_pipeline(
        "test_pipeline",
        [agent.id for agent in test_agents],
        "Test pipeline"
    )
    
    return dispatch_center, test_agents

@pytest.fixture
def error_agent():
    """创建会抛出错误的智能体"""
    class ErrorAgent(TestAgent):
        async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            raise ValueError("Test error")
    
    return ErrorAgent("error_agent", AgentType.DECODER) 