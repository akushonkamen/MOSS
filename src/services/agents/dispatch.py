from typing import Dict, List, Any, Optional, Tuple, Callable, Awaitable
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from .base import BaseAgent, AgentStatus, AgentType

logger = logging.getLogger(__name__)

@dataclass
class PipelineConfig:
    """管道配置"""
    id: str
    agent_ids: List[str]
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    execution_count: int = 0
    avg_execution_time: float = 0.0
    success_rate: float = 0.0
    paused: bool = False
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    max_history_size: int = 100

    def update_metrics(self, execution_time: float, success: bool, details: Dict[str, Any] = None) -> None:
        """更新管道度量指标"""
        self.execution_count += 1
        self.last_used = datetime.now()
        
        # 使用增量更新方式计算平均值
        self.avg_execution_time += (
            (execution_time - self.avg_execution_time) / self.execution_count
        )
        
        # 使用增量更新方式计算成功率
        self.success_rate += (
            (float(success) - self.success_rate) / self.execution_count
        )
        
        # 记录执行历史
        history_entry = {
            "timestamp": self.last_used.isoformat(),
            "execution_time": execution_time,
            "success": success,
            "details": details or {}
        }
        
        self.execution_history.append(history_entry)
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "agent_ids": self.agent_ids,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
            "execution_count": self.execution_count,
            "avg_execution_time": self.avg_execution_time,
            "success_rate": self.success_rate,
            "paused": self.paused,
            "execution_history": self.execution_history
        }

class AgentDispatchCenter:
    """智能体调度中心"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.pipelines: Dict[str, PipelineConfig] = {}
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, asyncio.Task] = {}
        self._metrics_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: float = 60.0  # 缓存有效期（秒）
        self._last_cache_update: Dict[str, float] = {}
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取智能体"""
        return self.agents.get(agent_id)
    
    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineConfig]:
        """获取管道配置"""
        return self.pipelines.get(pipeline_id)
    
    async def register_agent(self, agent: BaseAgent) -> None:
        """注册智能体"""
        async with self._lock:
            if agent.id in self.agents:
                logger.warning(f"Agent {agent.id} already registered, updating...")
            self.agents[agent.id] = agent
            logger.info(f"Registered agent: {agent}")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """注销智能体"""
        async with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                # 清理包含该智能体的管道
                pipelines_to_remove = []
                for pipeline_id, config in self.pipelines.items():
                    if agent_id in config.agent_ids:
                        pipelines_to_remove.append(pipeline_id)
                for pipeline_id in pipelines_to_remove:
                    del self.pipelines[pipeline_id]
                # 清理缓存
                cache_key = f"agent_metrics_{agent_id}"
                self._metrics_cache.pop(cache_key, None)
                self._last_cache_update.pop(cache_key, None)
                logger.info(f"Unregistered agent: {agent_id}")
    
    async def create_pipeline(
        self, 
        pipeline_id: str, 
        agent_ids: List[str],
        description: str = ""
    ) -> None:
        """创建处理管道"""
        async with self._lock:
            # 验证所有智能体都已注册
            for agent_id in agent_ids:
                if agent_id not in self.agents:
                    raise ValueError(f"Agent {agent_id} not registered")
            
            if pipeline_id in self.pipelines:
                logger.warning(f"Pipeline {pipeline_id} already exists, updating...")
            
            self.pipelines[pipeline_id] = PipelineConfig(
                id=pipeline_id,
                agent_ids=agent_ids,
                description=description
            )
            logger.info(f"Created pipeline: {pipeline_id} with agents: {agent_ids}")
    
    async def remove_pipeline(self, pipeline_id: str) -> None:
        """移除处理管道"""
        async with self._lock:
            if pipeline_id in self.pipelines:
                del self.pipelines[pipeline_id]
                # 清理缓存
                cache_key = f"pipeline_metrics_{pipeline_id}"
                self._metrics_cache.pop(cache_key, None)
                self._last_cache_update.pop(cache_key, None)
                logger.info(f"Removed pipeline: {pipeline_id}")
    
    async def process(
        self, 
        pipeline_id: str, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行管道处理"""
        if pipeline_id not in self.pipelines:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        pipeline = self.pipelines[pipeline_id]
        if pipeline.paused:
            raise RuntimeError(f"Pipeline {pipeline_id} is paused")
        
        start_time = datetime.now()
        current_data = input_data
        success = True
        execution_details = {
            "agent_results": [],
            "errors": []
        }
        
        try:
            for agent_id in pipeline.agent_ids:
                agent = self.agents[agent_id]
                agent.status = AgentStatus.PROCESSING
                agent_start_time = datetime.now()
                
                try:
                    current_data = await agent.process(current_data)
                    agent.status = AgentStatus.IDLE
                    
                    # 更新智能体度量指标
                    agent.metrics.processing_count += 1
                    agent.metrics.success_count += 1
                    agent.metrics.last_processing_time = (
                        datetime.now() - agent_start_time
                    ).total_seconds()
                    
                    # 记录智能体执行结果
                    execution_details["agent_results"].append({
                        "agent_id": agent_id,
                        "execution_time": agent.metrics.last_processing_time,
                        "success": True
                    })
                    
                except Exception as e:
                    agent.status = AgentStatus.ERROR
                    success = False
                    error_msg = str(e)
                    logger.error(f"Error in agent {agent_id}: {error_msg}")
                    
                    # 更新智能体度量指标
                    agent.metrics.processing_count += 1
                    agent.metrics.error_count += 1
                    
                    # 记录错误信息
                    execution_details["errors"].append({
                        "agent_id": agent_id,
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    })
                    raise
        
        finally:
            execution_time = (datetime.now() - start_time).total_seconds()
            pipeline.update_metrics(execution_time, success, execution_details)
            
            # 更新缓存
            cache_key = f"pipeline_metrics_{pipeline_id}"
            self._metrics_cache[cache_key] = pipeline.to_dict()
            self._last_cache_update[cache_key] = datetime.now().timestamp()
        
        return current_data
    
    async def _run_loop(
        self,
        name: str,
        operation: Callable[[BaseAgent], Awaitable[None]],
        interval: float
    ) -> None:
        """通用循环执行器"""
        while True:
            try:
                async with self._lock:
                    for agent in self.agents.values():
                        if agent.status == AgentStatus.IDLE:
                            try:
                                await operation(agent)
                            except Exception as e:
                                logger.error(f"Error in {name} loop for agent {agent.id}: {e}")
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in {name} loop: {e}")
                await asyncio.sleep(10)
    
    async def start_learning_loop(self, interval: float = 3600.0) -> None:
        """启动学习循环"""
        async def learn_operation(agent: BaseAgent) -> None:
            agent.status = AgentStatus.LEARNING
            try:
                await agent.learn({"timestamp": datetime.now().isoformat()})
            finally:
                agent.status = AgentStatus.IDLE
        
        if "learning" not in self._tasks or self._tasks["learning"].done():
            self._tasks["learning"] = asyncio.create_task(
                self._run_loop("learning", learn_operation, interval)
            )
            logger.info("Started learning loop")
    
    async def start_evolution_loop(self, interval: float = 86400.0) -> None:
        """启动进化循环"""
        async def evolve_operation(agent: BaseAgent) -> None:
            agent.status = AgentStatus.EVOLVING
            try:
                await agent.evolve()
            finally:
                agent.status = AgentStatus.IDLE
        
        if "evolution" not in self._tasks or self._tasks["evolution"].done():
            self._tasks["evolution"] = asyncio.create_task(
                self._run_loop("evolution", evolve_operation, interval)
            )
            logger.info("Started evolution loop")
    
    async def get_pipeline_metrics(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """获取管道度量指标"""
        cache_key = f"pipeline_metrics_{pipeline_id}"
        current_time = datetime.now().timestamp()
        
        # 检查缓存
        if (
            cache_key in self._metrics_cache
            and current_time - self._last_cache_update.get(cache_key, 0) < self._cache_ttl
        ):
            return self._metrics_cache[cache_key]
        
        pipeline = self.pipelines.get(pipeline_id)
        if pipeline:
            metrics = pipeline.to_dict()
            self._metrics_cache[cache_key] = metrics
            self._last_cache_update[cache_key] = current_time
            return metrics
        return None
    
    async def get_agent_metrics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体度量指标"""
        cache_key = f"agent_metrics_{agent_id}"
        current_time = datetime.now().timestamp()
        
        # 检查缓存
        if (
            cache_key in self._metrics_cache
            and current_time - self._last_cache_update.get(cache_key, 0) < self._cache_ttl
        ):
            return self._metrics_cache[cache_key]
        
        agent = self.agents.get(agent_id)
        if agent:
            metrics = agent.to_dict()["metrics"]
            self._metrics_cache[cache_key] = metrics
            self._last_cache_update[cache_key] = current_time
            return metrics
        return None
    
    async def pause_pipeline(self, pipeline_id: str) -> bool:
        """暂停管道"""
        pipeline = self.pipelines.get(pipeline_id)
        if pipeline:
            pipeline.paused = True
            logger.info(f"Paused pipeline: {pipeline_id}")
            return True
        return False
    
    async def resume_pipeline(self, pipeline_id: str) -> bool:
        """恢复管道"""
        pipeline = self.pipelines.get(pipeline_id)
        if pipeline:
            pipeline.paused = False
            logger.info(f"Resumed pipeline: {pipeline_id}")
            return True
        return False
    
    async def stop(self) -> None:
        """停止调度中心"""
        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._tasks.clear()
        self._metrics_cache.clear()
        self._last_cache_update.clear()
        logger.info("Stopped dispatch center") 