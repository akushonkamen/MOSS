from typing import Dict, List, Any, Optional, Tuple, Callable, Awaitable
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field
from .base import BaseAgent, AgentStatus, AgentType
from .registry import registry

logger = logging.getLogger(__name__)

@dataclass
class PipelineConfig:
    """管道配置"""
    id: str
    agent_ids: List[str]
    description: str = ""
    paused: bool = False
    execution_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_execution_time: Optional[datetime] = None
    last_execution_duration: float = 0.0
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        return self.success_count / self.execution_count if self.execution_count > 0 else 0.0
    
    @property
    def avg_execution_time(self) -> float:
        """计算平均执行时间"""
        if not self.execution_history:
            return 0.0
        times = [entry["execution_time"] for entry in self.execution_history]
        return sum(times) / len(times)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "agent_ids": self.agent_ids,
            "description": self.description,
            "paused": self.paused,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "avg_execution_time": self.avg_execution_time,
            "last_execution_time": self.last_execution_time.isoformat() if self.last_execution_time else None,
            "last_execution_duration": self.last_execution_duration,
            "execution_history": self.execution_history
        }

class AgentDispatchCenter:
    """智能体调度中心"""
    
    def __init__(self):
        self.pipelines: Dict[str, PipelineConfig] = {}
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, asyncio.Task] = {}
        self._metrics_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl: float = 60.0  # 缓存有效期（秒）
        self._last_cache_update: Dict[str, float] = {}
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取智能体"""
        return registry.get_agent(agent_id)
    
    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineConfig]:
        """获取管道配置"""
        return self.pipelines.get(pipeline_id)
    
    async def register_agent(self, agent: BaseAgent) -> None:
        """注册智能体"""
        await registry.register(agent)
    
    async def unregister_agent(self, agent_id: str) -> None:
        """注销智能体"""
        await registry.unregister(agent_id)
    
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
                if not registry.get_agent(agent_id):
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
    
    async def process(self, pipeline_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行处理管道"""
        pipeline = self.pipelines.get(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        if pipeline.paused:
            raise RuntimeError(f"Pipeline {pipeline_id} is paused")
        
        start_time = datetime.now()
        result = input_data
        agent_results = []
        errors = []
        
        try:
            for agent_id in pipeline.agent_ids:
                agent = registry.get_agent(agent_id)
                if not agent:
                    raise ValueError(f"Agent {agent_id} not found")
                
                if agent.status == AgentStatus.ERROR:
                    raise RuntimeError(f"Agent {agent_id} is in error state")
                
                try:
                    result = await agent.process(result)
                    agent_results.append({
                        "agent_id": agent_id,
                        "output": result
                    })
                except Exception as e:
                    agent.status = AgentStatus.ERROR
                    errors.append({
                        "agent_id": agent_id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    raise
            
            pipeline.success_count += 1
            success = True
            
        except Exception as e:
            pipeline.error_count += 1
            success = False
            raise
            
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            pipeline.execution_count += 1
            pipeline.last_execution_time = end_time
            pipeline.last_execution_duration = duration
            
            # 更新执行历史
            history_entry = {
                "timestamp": start_time.isoformat(),
                "execution_time": duration,
                "success": success,
                "details": {
                    "agent_results": agent_results,
                    "errors": errors
                }
            }
            pipeline.execution_history.append(history_entry)
            
            # 限制历史记录数量
            if len(pipeline.execution_history) > 100:
                pipeline.execution_history = pipeline.execution_history[-100:]
        
        return result
    
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
                    for agent in registry.get_active_agents():
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
        agent = registry.get_agent(agent_id)
        if agent:
            return agent.to_dict()["metrics"]
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
        # 取消所有任务
        for task in self._tasks.values():
            task.cancel()
        
        # 等待任务完成
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        
        # 清理缓存
        self._metrics_cache.clear()
        self._last_cache_update.clear()
        
        logger.info("Stopped dispatch center") 