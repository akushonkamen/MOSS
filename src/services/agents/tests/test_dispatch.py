import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta
from ..base import BaseAgent, AgentType, AgentStatus
from ..dispatch import AgentDispatchCenter, PipelineConfig

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

@pytest.mark.asyncio
async def test_agent_registration():
    """测试智能体注册"""
    center = AgentDispatchCenter()
    agent = TestAgent("test_001", AgentType.DECODER)
    
    await center.register_agent(agent)
    assert "test_001" in center.agents
    assert center.get_agent("test_001") == agent
    
    await center.unregister_agent("test_001")
    assert "test_001" not in center.agents
    assert center.get_agent("test_001") is None

@pytest.mark.asyncio
async def test_pipeline_management():
    """测试管道管理"""
    center = AgentDispatchCenter()
    
    # 注册测试智能体
    agents = [
        TestAgent(f"agent_{i}", AgentType.DECODER)
        for i in range(3)
    ]
    for agent in agents:
        await center.register_agent(agent)
    
    # 测试管道创建
    await center.create_pipeline(
        "test_pipeline",
        ["agent_0", "agent_1", "agent_2"],
        "Test pipeline"
    )
    
    pipeline = center.get_pipeline("test_pipeline")
    assert pipeline is not None
    assert pipeline.id == "test_pipeline"
    assert pipeline.agent_ids == ["agent_0", "agent_1", "agent_2"]
    
    # 测试管道移除
    await center.remove_pipeline("test_pipeline")
    assert center.get_pipeline("test_pipeline") is None

@pytest.mark.asyncio
async def test_pipeline_execution():
    """测试管道执行"""
    center = AgentDispatchCenter()
    
    # 注册测试智能体
    agents = [
        TestAgent(f"agent_{i}", AgentType.DECODER)
        for i in range(3)
    ]
    for agent in agents:
        await center.register_agent(agent)
    
    # 创建测试管道
    await center.create_pipeline(
        "test_pipeline",
        ["agent_0", "agent_1", "agent_2"]
    )
    
    # 执行管道
    input_data = {"test": "data"}
    result = await center.process("test_pipeline", input_data)
    
    # 验证执行结果
    assert result["result"] == "processed_by_agent_2"
    assert all(agent.process_called for agent in agents)
    
    # 验证执行顺序
    assert agents[0].input_history == [input_data]
    assert len(agents[1].input_history) == 1
    assert len(agents[2].input_history) == 1

@pytest.mark.asyncio
async def test_pipeline_metrics():
    """测试管道度量指标"""
    center = AgentDispatchCenter()
    
    # 注册测试智能体
    agent = TestAgent("test_agent", AgentType.DECODER, delay=0.1)
    await center.register_agent(agent)
    
    # 创建测试管道
    await center.create_pipeline("test_pipeline", ["test_agent"])
    
    # 执行管道并检查度量指标
    await center.process("test_pipeline", {"test": "data"})
    
    pipeline = center.get_pipeline("test_pipeline")
    assert pipeline.execution_count == 1
    assert pipeline.success_rate == 1.0
    assert pipeline.avg_execution_time >= 0.1

@pytest.mark.asyncio
async def test_learning_loop():
    """测试学习循环"""
    center = AgentDispatchCenter()
    
    # 注册测试智能体
    agent = TestAgent("test_agent", AgentType.DECODER)
    await center.register_agent(agent)
    
    # 启动学习循环
    await center.start_learning_loop(interval=0.1)
    
    # 等待一段时间让学习循环执行
    await asyncio.sleep(0.2)
    
    # 停止调度中心
    await center.stop()
    
    # 验证学习是否执行
    assert agent.learn_called
    assert agent.metrics.learning_progress > 0

@pytest.mark.asyncio
async def test_evolution_loop():
    """测试进化循环"""
    center = AgentDispatchCenter()
    
    # 注册测试智能体
    agent = TestAgent("test_agent", AgentType.DECODER)
    await center.register_agent(agent)
    
    # 启动进化循环
    await center.start_evolution_loop(interval=0.1)
    
    # 等待一段时间让进化循环执行
    await asyncio.sleep(0.2)
    
    # 停止调度中心
    await center.stop()
    
    # 验证进化是否执行
    assert agent.evolve_called
    assert agent.metrics.evolution_score > 0

@pytest.mark.asyncio
async def test_concurrent_pipeline_execution():
    """测试并发管道执行"""
    center = AgentDispatchCenter()
    
    # 注册测试智能体
    agents = [
        TestAgent(f"agent_{i}", AgentType.DECODER, delay=0.1)
        for i in range(3)
    ]
    for agent in agents:
        await center.register_agent(agent)
    
    # 创建多个测试管道
    for i in range(3):
        await center.create_pipeline(
            f"pipeline_{i}",
            [f"agent_{i}"]
        )
    
    # 并发执行管道
    tasks = [
        center.process(f"pipeline_{i}", {"test": f"data_{i}"})
        for i in range(3)
    ]
    results = await asyncio.gather(*tasks)
    
    # 验证执行结果
    for i, result in enumerate(results):
        assert result["result"] == f"processed_by_agent_{i}"
        assert result["input"]["test"] == f"data_{i}"

@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    center = AgentDispatchCenter()
    
    class ErrorAgent(TestAgent):
        async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            raise ValueError("Test error")
    
    # 注册错误智能体
    agent = ErrorAgent("error_agent", AgentType.DECODER)
    await center.register_agent(agent)
    
    # 创建测试管道
    await center.create_pipeline("error_pipeline", ["error_agent"])
    
    # 执行管道并验证错误处理
    with pytest.raises(ValueError):
        await center.process("error_pipeline", {"test": "data"})
    
    # 验证智能体状态
    assert agent.status == AgentStatus.ERROR
    
    # 验证管道度量指标
    pipeline = center.get_pipeline("error_pipeline")
    assert pipeline.execution_count == 1
    assert pipeline.success_rate == 0.0

@pytest.mark.asyncio
async def test_pipeline_pause_resume():
    """测试管道暂停和恢复"""
    center = AgentDispatchCenter()
    agent = TestAgent("test_agent", AgentType.DECODER)
    await center.register_agent(agent)
    await center.create_pipeline("test_pipeline", ["test_agent"])
    
    # 测试暂停
    assert await center.pause_pipeline("test_pipeline")
    with pytest.raises(RuntimeError, match="Pipeline test_pipeline is paused"):
        await center.process("test_pipeline", {"test": "data"})
    
    # 测试恢复
    assert await center.resume_pipeline("test_pipeline")
    result = await center.process("test_pipeline", {"test": "data"})
    assert result["result"] == "processed_by_test_agent"

@pytest.mark.asyncio
async def test_metrics_cache():
    """测试度量指标缓存"""
    center = AgentDispatchCenter()
    agent = TestAgent("test_agent", AgentType.DECODER)
    await center.register_agent(agent)
    await center.create_pipeline("test_pipeline", ["test_agent"])
    
    # 执行管道生成度量指标
    await center.process("test_pipeline", {"test": "data"})
    
    # 获取管道度量指标
    metrics1 = await center.get_pipeline_metrics("test_pipeline")
    assert metrics1 is not None
    assert metrics1["execution_count"] == 1
    
    # 再次获取应该使用缓存
    metrics2 = await center.get_pipeline_metrics("test_pipeline")
    assert metrics2 == metrics1
    
    # 获取智能体度量指标
    agent_metrics1 = await center.get_agent_metrics("test_agent")
    assert agent_metrics1 is not None
    assert agent_metrics1["processing_count"] == 1
    
    # 再次获取应该使用缓存
    agent_metrics2 = await center.get_agent_metrics("test_agent")
    assert agent_metrics2 == agent_metrics1

@pytest.mark.asyncio
async def test_execution_history():
    """测试执行历史记录"""
    center = AgentDispatchCenter()
    agent = TestAgent("test_agent", AgentType.DECODER)
    await center.register_agent(agent)
    await center.create_pipeline("test_pipeline", ["test_agent"])
    
    # 执行管道
    await center.process("test_pipeline", {"test": "data1"})
    await center.process("test_pipeline", {"test": "data2"})
    
    # 获取管道度量指标和历史
    metrics = await center.get_pipeline_metrics("test_pipeline")
    assert metrics is not None
    assert len(metrics["execution_history"]) == 2
    
    # 验证历史记录内容
    history = metrics["execution_history"]
    assert all(
        set(entry.keys()) == {"timestamp", "execution_time", "success", "details"}
        for entry in history
    )
    assert all(entry["success"] for entry in history)
    assert all(
        len(entry["details"]["agent_results"]) == 1
        for entry in history
    )

@pytest.mark.asyncio
async def test_error_history():
    """测试错误历史记录"""
    center = AgentDispatchCenter()
    
    class ErrorAgent(TestAgent):
        async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            raise ValueError("Test error")
    
    agent = ErrorAgent("error_agent", AgentType.DECODER)
    await center.register_agent(agent)
    await center.create_pipeline("error_pipeline", ["error_agent"])
    
    # 执行管道（会失败）
    with pytest.raises(ValueError):
        await center.process("error_pipeline", {"test": "data"})
    
    # 获取管道度量指标和历史
    metrics = await center.get_pipeline_metrics("error_pipeline")
    assert metrics is not None
    assert len(metrics["execution_history"]) == 1
    
    # 验证错误记录
    history = metrics["execution_history"][0]
    assert not history["success"]
    assert len(history["details"]["errors"]) == 1
    error = history["details"]["errors"][0]
    assert error["agent_id"] == "error_agent"
    assert error["error"] == "Test error"
    assert "timestamp" in error

@pytest.mark.asyncio
async def test_cache_expiration():
    """测试缓存过期"""
    center = AgentDispatchCenter()
    center._cache_ttl = 0.1  # 设置较短的缓存时间用于测试
    
    agent = TestAgent("test_agent", AgentType.DECODER)
    await center.register_agent(agent)
    await center.create_pipeline("test_pipeline", ["test_agent"])
    
    # 执行管道并获取度量指标
    await center.process("test_pipeline", {"test": "data"})
    metrics1 = await center.get_pipeline_metrics("test_pipeline")
    
    # 等待缓存过期
    await asyncio.sleep(0.2)
    
    # 再次获取度量指标，应该重新计算
    metrics2 = await center.get_pipeline_metrics("test_pipeline")
    assert metrics2 is not None
    assert metrics2 == metrics1  # 内容应该相同，但是是重新计算的

@pytest.mark.asyncio
async def test_cache_cleanup():
    """测试缓存清理"""
    center = AgentDispatchCenter()
    agent = TestAgent("test_agent", AgentType.DECODER)
    await center.register_agent(agent)
    await center.create_pipeline("test_pipeline", ["test_agent"])
    
    # 生成并缓存度量指标
    await center.process("test_pipeline", {"test": "data"})
    await center.get_pipeline_metrics("test_pipeline")
    await center.get_agent_metrics("test_agent")
    
    # 验证缓存存在
    assert len(center._metrics_cache) == 2
    assert len(center._last_cache_update) == 2
    
    # 停止调度中心
    await center.stop()
    
    # 验证缓存被清理
    assert len(center._metrics_cache) == 0
    assert len(center._last_cache_update) == 0 