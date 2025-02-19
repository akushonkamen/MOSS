"""服务注册表

提供服务的注册、发现和生命周期管理。
"""
import logging
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    service: Any
    status: str
    start_time: datetime
    metadata: Dict[str, Any]

class ServiceRegistry:
    """服务注册表"""
    
    def __init__(self):
        """初始化服务注册表"""
        self.logger = logging.getLogger("ServiceRegistry")
        self._services: Dict[str, ServiceInfo] = {}
        self._lock = asyncio.Lock()
        
    async def register(self, name: str, service: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """注册服务
        
        Args:
            name: 服务名称
            service: 服务实例
            metadata: 服务元数据
            
        Returns:
            bool: 是否注册成功
        """
        try:
            async with self._lock:
                if name in self._services:
                    self.logger.warning(f"服务 {name} 已注册")
                    return False
                    
                self._services[name] = ServiceInfo(
                    name=name,
                    service=service,
                    status="registered",
                    start_time=datetime.now(),
                    metadata=metadata or {}
                )
                
            self.logger.info(f"服务 {name} 注册成功")
            return True
            
        except Exception as e:
            self.logger.error(f"注册服务 {name} 失败: {str(e)}")
            return False
            
    async def unregister(self, name: str) -> bool:
        """注销服务
        
        Args:
            name: 服务名称
            
        Returns:
            bool: 是否注销成功
        """
        try:
            async with self._lock:
                if name not in self._services:
                    self.logger.warning(f"服务 {name} 未注册")
                    return False
                    
                del self._services[name]
                
            self.logger.info(f"服务 {name} 注销成功")
            return True
            
        except Exception as e:
            self.logger.error(f"注销服务 {name} 失败: {str(e)}")
            return False
            
    def get_service(self, name: str) -> Optional[Any]:
        """获取服务实例
        
        Args:
            name: 服务名称
            
        Returns:
            Optional[Any]: 服务实例
        """
        if name in self._services:
            return self._services[name].service
        return None
        
    def get_service_info(self, name: str) -> Optional[ServiceInfo]:
        """获取服务信息
        
        Args:
            name: 服务名称
            
        Returns:
            Optional[ServiceInfo]: 服务信息
        """
        return self._services.get(name)
        
    def list_services(self) -> List[ServiceInfo]:
        """获取所有服务
        
        Returns:
            List[ServiceInfo]: 服务列表
        """
        return list(self._services.values())
        
    async def start_service(self, name: str) -> bool:
        """启动服务
        
        Args:
            name: 服务名称
            
        Returns:
            bool: 是否启动成功
        """
        try:
            service_info = self._services.get(name)
            if not service_info:
                self.logger.warning(f"服务 {name} 未注册")
                return False
                
            service = service_info.service
            if hasattr(service, "start"):
                await service.start()
                
            service_info.status = "running"
            self.logger.info(f"服务 {name} 启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"启动服务 {name} 失败: {str(e)}")
            return False
            
    async def stop_service(self, name: str) -> bool:
        """停止服务
        
        Args:
            name: 服务名称
            
        Returns:
            bool: 是否停止成功
        """
        try:
            service_info = self._services.get(name)
            if not service_info:
                self.logger.warning(f"服务 {name} 未注册")
                return False
                
            service = service_info.service
            if hasattr(service, "stop"):
                await service.stop()
                
            service_info.status = "stopped"
            self.logger.info(f"服务 {name} 停止成功")
            return True
            
        except Exception as e:
            self.logger.error(f"停止服务 {name} 失败: {str(e)}")
            return False

# 创建全局服务注册表实例
service_registry = ServiceRegistry() 