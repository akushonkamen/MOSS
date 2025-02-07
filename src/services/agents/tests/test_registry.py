"""Agent注册中心测试"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from ..base import BaseAgent, AgentType, AgentStatus, AgentCapability
from ..registry import AgentRegistry, AgentRegistration

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

@pytest.fixture
def registry():
    """创建注册中心实例"""
    return AgentRegistry()

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

@pytest.mark.asyncio
async def test_agent_registration(registry, test_agent):
    """测试Agent注册"""
    # 测试基本注册
    await registry.register(test_agent)
    assert registry.get_agent(test_agent.id) == test_agent
    
    # 测试重复注册
    with pytest.raises(ValueError):
        await registry.register(test_agent)
    
    # 测试带依赖和元数据的注册
    agent2 = TestAgent("test_002", AgentType.EXPERT)
    metadata = {"version": "1.0.0", "description": "Test agent"}
    await registry.register(agent2, dependencies=[test_agent.id], metadata=metadata)
    
    # 验证依赖关系
    deps = registry.get_dependencies("test_002")
    assert len(deps) == 1
    assert deps[0] == test_agent
    
    # 验证元数据
    info = registry.get_agent_info("test_002")
    assert info["metadata"] == metadata

@pytest.mark.asyncio
async def test_agent_unregistration(registry, test_agents):
    """测试Agent注销"""
    # 注册所有测试智能体
    for agent in test_agents:
        await registry.register(agent)
    
    # 测试基本注销
    await registry.unregister(test_agents[0].id)
    assert registry.get_agent(test_agents[0].id) is None
    
    # 测试注销有依赖的Agent
    await registry.register(
        test_agents[0],
        dependencies=[test_agents[1].id]
    )
    with pytest.raises(ValueError):
        await registry.unregister(test_agents[1].id)

@pytest.mark.asyncio
async def test_agent_type_indexing(registry, test_agents):
    """测试Agent类型索引"""
    # 注册不同类型的Agent
    await registry.register(test_agents[0])  # DECODER
    await registry.register(
        TestAgent("expert_001", AgentType.EXPERT)
    )
    await registry.register(
        TestAgent("memory_001", AgentType.MEMORY)
    )
    
    # 验证类型索引
    decoder_agents = registry.get_agents_by_type(AgentType.DECODER)
    assert len(decoder_agents) == 1
    assert decoder_agents[0].id == test_agents[0].id
    
    expert_agents = registry.get_agents_by_type(AgentType.EXPERT)
    assert len(expert_agents) == 1
    assert expert_agents[0].id == "expert_001"

@pytest.mark.asyncio
async def test_agent_capability_indexing(registry, test_agent):
    """测试Agent能力索引"""
    # 注册带能力的Agent
    capability = AgentCapability(
        name="test_capability",
        description="Test capability",
        parameters={"param1": "value1"},
        version="1.0.0"
    )
    await test_agent.register_capability(capability)
    await registry.register(test_agent)
    
    # 验证能力索引
    agents = registry.get_agents_by_capability("test_capability")
    assert len(agents) == 1
    assert agents[0] == test_agent

@pytest.mark.asyncio
async def test_agent_status_update(registry, test_agent):
    """测试Agent状态更新"""
    await registry.register(test_agent)
    
    # 更新状态
    await registry.update_agent_status(test_agent.id, False)
    info = registry.get_agent_info(test_agent.id)
    assert not info["is_active"]
    
    # 验证活跃Agent列表
    active_agents = registry.get_active_agents()
    assert test_agent not in active_agents
    
    # 恢复状态
    await registry.update_agent_status(test_agent.id, True)
    active_agents = registry.get_active_agents()
    assert test_agent in active_agents

@pytest.mark.asyncio
async def test_agent_metadata_update(registry, test_agent):
    """测试Agent元数据更新"""
    initial_metadata = {"version": "1.0.0"}
    await registry.register(test_agent, metadata=initial_metadata)
    
    # 更新元数据
    new_metadata = {"description": "Updated test agent"}
    await registry.update_agent_metadata(test_agent.id, new_metadata)
    
    # 验证元数据
    info = registry.get_agent_info(test_agent.id)
    assert info["metadata"]["version"] == "1.0.0"
    assert info["metadata"]["description"] == "Updated test agent"

@pytest.mark.asyncio
async def test_agent_dependency_management(registry, test_agents):
    """测试Agent依赖管理"""
    # 注册带依赖关系的Agent
    await registry.register(test_agents[0])
    await registry.register(test_agents[1])
    await registry.register(
        test_agents[2],
        dependencies=[test_agents[0].id, test_agents[1].id]
    )
    
    # 验证依赖关系
    deps = registry.get_dependencies(test_agents[2].id)
    assert len(deps) == 2
    assert test_agents[0] in deps
    assert test_agents[1] in deps
    
    # 验证反向依赖
    dependents = registry.get_dependents(test_agents[0].id)
    assert len(dependents) == 1
    assert test_agents[2] in dependents

@pytest.mark.asyncio
async def test_concurrent_operations(registry, test_agents):
    """测试并发操作"""
    # 并发注册
    tasks = [
        registry.register(agent)
        for agent in test_agents
    ]
    await asyncio.gather(*tasks)
    
    # 验证注册结果
    all_agents = registry.get_all_agents()
    assert len(all_agents) == len(test_agents)
    assert all(agent in all_agents for agent in test_agents)
    
    # 并发状态更新
    tasks = [
        registry.update_agent_status(agent.id, False)
        for agent in test_agents
    ]
    await asyncio.gather(*tasks)
    
    # 验证状态更新
    active_agents = registry.get_active_agents()
    assert len(active_agents) == 0 