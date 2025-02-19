"""服务发现模块

提供服务注册、发现和管理功能。
"""
import asyncio
import logging
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .port_manager import port_manager, PortAllocationError
from ...services.events.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)

@dataclass
class ServiceRegistration:
    """服务注册信息"""
    service_id: str          # 服务ID
    service_type: str        # 服务类型
    name: str               # 服务名称
    location: Optional[str]  # 位置标识
    capabilities: List[str]  # 服务能力
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceInfo:
    """服务信息"""
    registration: ServiceRegistration
    port: int
    status: str
    last_heartbeat: datetime
    token: str = field(default_factory=lambda: str(uuid.uuid4()))

class ServiceRegistrationError(Exception):
    """服务注册错误"""
    pass

class ServiceDiscovery:
    """服务发现"""
    
    def __init__(self):
        """初始化服务发现"""
        self._services: Dict[str, ServiceInfo] = {}
        self._locations: Dict[str, Set[str]] = {}  # location -> service_ids
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """启动服务发现"""
        logger.info("Starting service discovery")
        # 启动端口管理器
        await port_manager.start()
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_services())
        
    async def stop(self):
        """停止服务发现"""
        logger.info("Stopping service discovery")
        # 停止清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        # 停止端口管理器
        await port_manager.stop()
        
    async def register_service(
        self,
        registration: ServiceRegistration
    ) -> ServiceInfo:
        """注册服务
        
        Args:
            registration: 服务注册信息
            
        Returns:
            ServiceInfo: 服务信息
            
        Raises:
            ServiceRegistrationError: 注册失败
        """
        try:
            async with self._lock:
                # 检查服务是否已注册
                if registration.service_id in self._services:
                    raise ServiceRegistrationError(
                        f"Service already registered: {registration.service_id}"
                    )
                    
                # 分配端口
                port = await port_manager.allocate_port(
                    registration.service_id,
                    registration.service_type,
                    registration.location
                )
                
                # 创建服务信息
                service_info = ServiceInfo(
                    registration=registration,
                    port=port,
                    status="active",
                    last_heartbeat=datetime.now()
                )
                
                # 保存服务信息
                self._services[registration.service_id] = service_info
                
                # 更新位置映射
                if registration.location:
                    if registration.location not in self._locations:
                        self._locations[registration.location] = set()
                    self._locations[registration.location].add(
                        registration.service_id
                    )
                    
                # 发布服务注册事件
                await event_bus.publish(
                    EventType.SYSTEM,
                    "service_registered",
                    {
                        "service_id": registration.service_id,
                        "service_type": registration.service_type,
                        "name": registration.name,
                        "location": registration.location,
                        "port": port,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                logger.info(
                    f"Service registered: {registration.name} "
                    f"({registration.service_id}) at port {port}"
                )
                return service_info
                
        except PortAllocationError as e:
            raise ServiceRegistrationError(f"Port allocation failed: {str(e)}")
        except Exception as e:
            raise ServiceRegistrationError(f"Registration failed: {str(e)}")
            
    async def unregister_service(self, service_id: str) -> None:
        """注销服务
        
        Args:
            service_id: 服务ID
            
        Raises:
            KeyError: 服务不存在
        """
        async with self._lock:
            if service_id not in self._services:
                raise KeyError(f"Service not found: {service_id}")
                
            service_info = self._services[service_id]
            
            # 释放端口
            await port_manager.release_port(service_id)
            
            # 更新位置映射
            location = service_info.registration.location
            if location and location in self._locations:
                self._locations[location].discard(service_id)
                if not self._locations[location]:
                    del self._locations[location]
                    
            # 删除服务信息
            del self._services[service_id]
            
            # 发布服务注销事件
            await event_bus.publish(
                EventType.SYSTEM,
                "service_unregistered",
                {
                    "service_id": service_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Service unregistered: {service_id}")
            
    async def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        """获取服务信息
        
        Args:
            service_id: 服务ID
            
        Returns:
            Optional[ServiceInfo]: 服务信息
        """
        return self._services.get(service_id)
        
    async def list_services(
        self,
        service_type: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[ServiceInfo]:
        """列出服务
        
        Args:
            service_type: 服务类型过滤
            location: 位置过滤
            
        Returns:
            List[ServiceInfo]: 服务列表
        """
        services = list(self._services.values())
        
        if service_type:
            services = [
                s for s in services 
                if s.registration.service_type == service_type
            ]
            
        if location:
            services = [
                s for s in services 
                if s.registration.location == location
            ]
            
        return services
        
    async def update_heartbeat(self, service_id: str) -> None:
        """更新服务心跳
        
        Args:
            service_id: 服务ID
            
        Raises:
            KeyError: 服务不存在
        """
        if service_id not in self._services:
            raise KeyError(f"Service not found: {service_id}")
            
        self._services[service_id].last_heartbeat = datetime.now()
        await port_manager.update_heartbeat(service_id)
        
    async def _cleanup_expired_services(self):
        """清理过期的服务"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                now = datetime.now()
                expired_services = []
                
                async with self._lock:
                    for service_id, info in self._services.items():
                        # 如果超过5分钟没有心跳，认为服务已失效
                        if (now - info.last_heartbeat).seconds > 300:
                            expired_services.append(service_id)
                            
                    # 注销过期的服务
                    for service_id in expired_services:
                        try:
                            await self.unregister_service(service_id)
                            logger.warning(
                                f"Unregistered expired service: {service_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error unregistering expired service: {e}"
                            )
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in service cleanup: {e}")
                await asyncio.sleep(5)  # 发生错误时等待短暂时间

# 创建服务发现实例
service_discovery = ServiceDiscovery() 