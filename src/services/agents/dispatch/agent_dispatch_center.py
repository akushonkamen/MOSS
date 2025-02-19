"""智能体调度中心

负责管理和调度所有智能体。
"""
import logging
from typing import Dict, Any, Optional, List, Set
import asyncio
from datetime import datetime

from ...events.event_bus import event_bus, EventType, Event
from ..base import BaseAgent
from ..adaptor import AdaptorAgent
from ..decoder.decoder_agent import DecoderAgent, DecoderConfig
from ..expert import ExpertAgent
from ..scout import LLMScoutAgent, ScoutAgentConfig
from core.config import settings

logger = logging.getLogger(__name__)

class AgentDispatchCenter:
    """智能体调度中心"""
    
    def __init__(self):
        """初始化调度中心"""
        self._agents: Dict[str, BaseAgent] = {}
        self._pipelines: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
        self._metrics: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self) -> None:
        """初始化调度中心"""
        logger.info("正在初始化智能体调度中心...")
        
        try:
            # 创建配置
            decoder_config = DecoderConfig(
                api_url=settings.OLLAMA_GENERATE_URL,
                model_name=settings.DEFAULT_MODEL,
                temperature=0.1,
                max_tokens=1000,
                timeout=30
            )
            
            scout_config = ScoutAgentConfig(
                api_url=settings.OLLAMA_GENERATE_URL,
                model_name=settings.DEFAULT_MODEL,
                temperature=0.1,
                max_tokens=1000,
                timeout=30
            )
            
            # 注册内置智能体
            await self.register_agent(AdaptorAgent("adaptor"))
            await self.register_agent(DecoderAgent("decoder", config=decoder_config))
            await self.register_agent(ExpertAgent("expert"))
            await self.register_agent(LLMScoutAgent("scout", config=scout_config))
            
            # 订阅设备发现事件
            event_bus.subscribe(
                EventType.DEVICE,
                self._on_device_discovered,
                "device_discovered"
            )
            
            logger.info("智能体调度中心初始化完成")
            
        except Exception as e:
            logger.error(f"初始化智能体调度中心失败: {str(e)}")
            raise
        
    async def stop(self) -> None:
        """停止调度中心"""
        logger.info("正在停止智能体调度中心...")
        
        # 停止所有智能体
        for agent in self._agents.values():
            await agent.stop()
            
        logger.info("智能体调度中心已停止")
        
    async def register_agent(self, agent: BaseAgent) -> bool:
        """注册智能体
        
        Args:
            agent: 智能体实例
            
        Returns:
            bool: 是否注册成功
        """
        try:
            async with self._lock:
                agent_id = agent.agent_id
                if agent_id in self._agents:
                    logger.warning(f"智能体 {agent_id} 已存在")
                    return False
                    
                self._agents[agent_id] = agent
                await agent.initialize()
                logger.info(f"智能体 {agent_id} 注册成功")
                return True
                
        except Exception as e:
            logger.error(f"注册智能体失败: {str(e)}")
            return False
            
    async def create_pipeline(self, config: Dict[str, Any]) -> str:
        """创建处理管道
        
        Args:
            config: 管道配置
            
        Returns:
            str: 管道ID
        """
        try:
            pipeline_id = config.get("pipeline_id", str(datetime.now().timestamp()))
            agent_sequence = config.get("agents", [])
            
            # 验证所有智能体是否存在
            for agent_id in agent_sequence:
                if agent_id not in self._agents:
                    raise ValueError(f"智能体 {agent_id} 不存在")
                    
            async with self._lock:
                self._pipelines[pipeline_id] = agent_sequence
                logger.info(f"创建处理管道 {pipeline_id}")
                return pipeline_id
                
        except Exception as e:
            logger.error(f"创建处理管道失败: {str(e)}")
            raise
            
    async def dispatch(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """调度请求
        
        Args:
            request: 请求参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            pipeline_id = request.get("pipeline_id")
            if not pipeline_id or pipeline_id not in self._pipelines:
                raise ValueError(f"处理管道 {pipeline_id} 不存在")
                
            context = request.get("context", {})
            agent_sequence = self._pipelines[pipeline_id]
            
            # 按顺序执行管道中的智能体
            for agent_id in agent_sequence:
                agent = self._agents[agent_id]
                context = await agent.process(context)
                
            return context
            
        except Exception as e:
            logger.error(f"调度请求失败: {str(e)}")
            raise
            
    async def _on_device_discovered(self, event: Event):
        """处理设备发现事件
        
        Args:
            event: 事件对象
        """
        try:
            device_info = event.data
            device_id = device_info.get("device_id", "")
            address = device_info.get("address", "")
            port = device_info.get("port", 8080)
            
            # 创建设备适配管道
            pipeline_config = {
                "pipeline_id": f"device_adapt_{device_id}",
                "agents": ["adaptor"]
            }
            pipeline_id = await self.create_pipeline(pipeline_config)
            
            # 构建适配请求上下文
            api_url = device_info.get("response_data", {}).get("api_url")
            if not api_url:
                logger.error(f"设备 {device_id} 缺少API URL")
                return

            context = {
                "device_id": device_id,
                "api_url": api_url,
                "response_data": device_info.get("response_data", {}),
                "action": "adapt_device"
            }
            
            # 调用适配管道
            request = {
                "pipeline_id": pipeline_id,
                "context": context
            }
            
            result = await self.dispatch(request)
            logger.info(f"设备 {device_id} 适配结果: {result}")
            
        except Exception as e:
            logger.error(f"处理设备发现事件失败: {str(e)}")

# 创建调度中心实例
agent_dispatch_center = AgentDispatchCenter() 