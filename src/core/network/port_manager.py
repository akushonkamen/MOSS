"""端口管理器

提供统一的端口分配和管理功能。
"""
import asyncio
import logging
from typing import Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PortAssignment:
    """端口分配信息"""
    port: int
    service_id: str
    service_type: str
    location: Optional[str]
    assigned_time: datetime
    last_heartbeat: Optional[datetime] = None

class PortAllocationError(Exception):
    """端口分配错误"""
    pass

class PortManager:
    """端口管理器"""
    
    # 固定端口 (9000-9019)
    CORE_SERVICE_PORT = 9000      # 核心服务（必需）
    DEVICE_REGISTRY_PORT = 9001   # 设备注册服务（必需）
    UNIFIED_MANAGER_PORT = 9002   # 统一设备管理器（必需）
    
    # 动态端口范围
    LOCATION_PORT_RANGE = (9020, 9099)    # 位置服务端口范围
    PROXY_PORT_RANGE = (9100, 9199)       # 代理服务端口范围
    DEVICE_PORT_RANGE = (9200, 9299)      # 设备服务端口范围
    STATE_PORT_RANGE = (9300, 9399)       # 状态服务端口范围
    
    def __init__(self):
        """初始化端口管理器"""
        self._used_ports: Set[int] = set([
            self.CORE_SERVICE_PORT,
            self.DEVICE_REGISTRY_PORT,
            self.UNIFIED_MANAGER_PORT
        ])
        self._assignments: Dict[str, PortAssignment] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """启动端口管理器"""
        logger.info("Starting port manager")
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_ports())
        
    async def stop(self):
        """停止端口管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Port manager stopped")
        
    def _get_port_range(self, service_type: str) -> Optional[Tuple[int, int]]:
        """获取服务类型对应的端口范围"""
        return {
            "location": self.LOCATION_PORT_RANGE,
            "proxy": self.PROXY_PORT_RANGE,
            "device": self.DEVICE_PORT_RANGE,
            "state": self.STATE_PORT_RANGE
        }.get(service_type)
        
    async def allocate_port(self,
        service_id: str,
        service_type: str,
        location: Optional[str] = None
    ) -> int:
        """分配端口
        
        Args:
            service_id: 服务ID
            service_type: 服务类型
            location: 位置标识（可选）
            
        Returns:
            int: 分配的端口号
            
        Raises:
            PortAllocationError: 端口分配失败
        """
        async with self._lock:
            # 检查服务是否已分配端口
            if service_id in self._assignments:
                return self._assignments[service_id].port
                
            # 获取端口范围
            port_range = self._get_port_range(service_type)
            if not port_range:
                raise PortAllocationError(f"Unknown service type: {service_type}")
                
            # 查找可用端口
            for port in range(port_range[0], port_range[1] + 1):
                if port not in self._used_ports:
                    self._used_ports.add(port)
                    assignment = PortAssignment(
                        port=port,
                        service_id=service_id,
                        service_type=service_type,
                        location=location,
                        assigned_time=datetime.now()
                    )
                    self._assignments[service_id] = assignment
                    
                    logger.info(
                        f"Port {port} allocated to service {service_id} "
                        f"({service_type})"
                    )
                    return port
                    
            raise PortAllocationError(
                f"No available ports for {service_type} in range "
                f"{port_range[0]}-{port_range[1]}"
            )
            
    async def release_port(self, service_id: str) -> None:
        """释放端口
        
        Args:
            service_id: 服务ID
        """
        async with self._lock:
            if service_id in self._assignments:
                assignment = self._assignments[service_id]
                self._used_ports.remove(assignment.port)
                del self._assignments[service_id]
                
                logger.info(
                    f"Port {assignment.port} released from service {service_id}"
                )
                
    async def get_port(self, service_id: str) -> Optional[int]:
        """获取服务的端口号
        
        Args:
            service_id: 服务ID
            
        Returns:
            Optional[int]: 端口号，未分配则返回None
        """
        assignment = self._assignments.get(service_id)
        return assignment.port if assignment else None
        
    async def update_heartbeat(self, service_id: str) -> None:
        """更新服务心跳
        
        Args:
            service_id: 服务ID
        """
        if service_id in self._assignments:
            self._assignments[service_id].last_heartbeat = datetime.now()
            
    async def _cleanup_expired_ports(self):
        """清理过期的端口分配"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                now = datetime.now()
                expired_services = []
                
                async with self._lock:
                    for service_id, assignment in self._assignments.items():
                        # 如果超过5分钟没有心跳，认为服务已失效
                        if (assignment.last_heartbeat and 
                            (now - assignment.last_heartbeat).seconds > 300):
                            expired_services.append(service_id)
                            
                    # 释放过期的端口
                    for service_id in expired_services:
                        await self.release_port(service_id)
                        logger.warning(
                            f"Released expired port for service {service_id}"
                        )
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in port cleanup: {e}")
                await asyncio.sleep(5)  # 发生错误时等待短暂时间

# 创建端口管理器实例
port_manager = PortManager() 