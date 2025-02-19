"""智能工业AI核心

提供智能工业AI系统的核心功能实现。
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from .event_bus import event_bus, Event
from .service_registry import service_registry
from ..devices import UnifiedDeviceManager, StateManager
from ..agents import DecoderAgent, ExpertAgent
from ..scenes import SceneManager, Scene
from ..llm import LLMService

class Industrial AI:
    """智能工业AI核心类"""
    
    def __init__(self):
        """初始化智能工业AI系统"""
        self.logger = logging.getLogger("Industrial AI")
        self._device_manager = UnifiedDeviceManager()
        self._state_manager = StateManager()
        self._scene_manager = SceneManager()
        self._llm_service = None
        self._decoder_agent = None
        self._expert_agent = None
        self._running = False
        
    async def initialize(self) -> None:
        """初始化系统"""
        self.logger.info("正在初始化智能工业AI系统...")
        
        try:
            # 初始化设备管理器
            await self._device_manager.initialize()
            
            # 初始化状态管理器
            await self._state_manager.initialize()
            
            # 初始化场景管理器
            await self._scene_manager.initialize()
            
            # 初始化LLM服务
            self._llm_service = LLMService()
            await self._llm_service.initialize()
            
            # 初始化智能代理
            self._decoder_agent = DecoderAgent("decoder", self._llm_service)
            self._expert_agent = ExpertAgent("expert", self._llm_service)
            await self._decoder_agent.initialize()
            await self._expert_agent.initialize()
            
            # 注册核心服务
            await self._register_core_services()
            
            # 订阅事件
            await self._subscribe_events()
            
            self.logger.info("智能工业AI系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            raise
            
    async def start(self) -> None:
        """启动系统"""
        if self._running:
            return
            
        self.logger.info("正在启动智能工业AI系统...")
        self._running = True
        
        try:
            # 启动所有服务
            services = service_registry.list_services()
            for service in services:
                await service_registry.start_service(service.name)
                
            self.logger.info("智能工业AI系统启动完成")
            
        except Exception as e:
            self._running = False
            self.logger.error(f"启动失败: {str(e)}")
            raise
            
    async def stop(self) -> None:
        """停止系统"""
        if not self._running:
            return
            
        self.logger.info("正在停止智能工业AI系统...")
        self._running = False
        
        try:
            # 停止所有服务
            services = service_registry.list_services()
            for service in services:
                await service_registry.stop_service(service.name)
                
            self.logger.info("智能工业AI系统已停止")
            
        except Exception as e:
            self.logger.error(f"停止失败: {str(e)}")
            raise
            
    async def process_command(self, command: str) -> bool:
        """处理用户命令
        
        Args:
            command: 用户命令
            
        Returns:
            bool: 是否处理成功
        """
        try:
            # 解码意图
            intent = await self._decoder_agent.decode(command)
            if not intent:
                self.logger.warning("无法理解用户意图")
                return False
                
            # 执行意图
            result = await self._expert_agent.execute_intent(intent)
            if not result:
                self.logger.warning("执行意图失败")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"处理命令失败: {str(e)}")
            return False
            
    async def _register_core_services(self) -> None:
        """注册核心服务"""
        # 注册设备管理器
        await service_registry.register(
            "device_manager",
            self._device_manager,
            {"type": "core", "description": "设备管理服务"}
        )
        
        # 注册状态管理器
        await service_registry.register(
            "state_manager",
            self._state_manager,
            {"type": "core", "description": "状态管理服务"}
        )
        
        # 注册场景管理器
        await service_registry.register(
            "scene_manager",
            self._scene_manager,
            {"type": "core", "description": "场景管理服务"}
        )
        
    async def _subscribe_events(self) -> None:
        """订阅事件"""
        # 订阅设备状态变更事件
        await event_bus.subscribe(
            "device_state_changed",
            self._handle_device_state_change
        )
        
        # 订阅场景触发事件
        await event_bus.subscribe(
            "scene_triggered",
            self._handle_scene_trigger
        )
        
    async def _handle_device_state_change(self, event: Event) -> None:
        """处理设备状态变更事件"""
        try:
            device_id = event.data["device_id"]
            new_state = event.data["new_state"]
            
            # 更新状态管理器
            await self._state_manager.update_state(device_id, new_state)
            
            # 检查场景触发
            await self._scene_manager.check_triggers(device_id, new_state)
            
        except Exception as e:
            self.logger.error(f"处理设备状态变更事件失败: {str(e)}")
            
    async def _handle_scene_trigger(self, event: Event) -> None:
        """处理场景触发事件"""
        try:
            scene_id = event.data["scene_id"]
            scene = self._scene_manager.get_scene(scene_id)
            if scene:
                await self._scene_manager.execute_scene(scene)
            
        except Exception as e:
            self.logger.error(f"处理场景触发事件失败: {str(e)}")

# 创建全局智能工业AI实例
smart_home = Industrial AI() 