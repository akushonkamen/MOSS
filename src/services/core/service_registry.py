from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field
import logging
from .event_bus import bus, Event

logger = logging.getLogger(__name__)

class ServiceSchema(BaseModel):
    """服务定义模型"""
    name: str = Field(..., description="服务名称")
    description: str = Field("", description="服务描述")
    fields: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="参数定义")
    target_domain: str = Field(..., description="目标域")
    supported_features: List[str] = Field(default_factory=list, description="支持的功能")

class Service:
    """服务类"""
    
    def __init__(
        self,
        schema: ServiceSchema,
        handler: Callable[[Dict[str, Any]], Any]
    ):
        """初始化服务
        
        Args:
            schema: 服务定义
            handler: 服务处理函数
        """
        self.schema = schema
        self.handler = handler

class ServiceRegistry:
    """服务注册表"""
    
    def __init__(self):
        """初始化服务注册表"""
        self._services: Dict[str, Dict[str, Service]] = {}
        
    def register(self, domain: str, service: Service) -> None:
        """注册服务
        
        Args:
            domain: 服务域
            service: 服务对象
        """
        if domain not in self._services:
            self._services[domain] = {}
            
        self._services[domain][service.schema.name] = service
        logger.info(f"注册服务: {domain}.{service.schema.name}")
        
        # 触发服务注册事件
        asyncio.create_task(bus.fire(Event(
            event_type="service_registered",
            data={
                "domain": domain,
                "service": service.schema.dict()
            },
            origin="service_registry"
        )))
        
    def unregister(self, domain: str, service_name: str) -> None:
        """注销服务
        
        Args:
            domain: 服务域
            service_name: 服务名称
        """
        if domain in self._services and service_name in self._services[domain]:
            del self._services[domain][service_name]
            if not self._services[domain]:
                del self._services[domain]
            logger.info(f"注销服务: {domain}.{service_name}")
            
            # 触发服务注销事件
            asyncio.create_task(bus.fire(Event(
                event_type="service_unregistered",
                data={
                    "domain": domain,
                    "service_name": service_name
                },
                origin="service_registry"
            )))
            
    def get_service(self, domain: str, service_name: str) -> Optional[Service]:
        """获取服务
        
        Args:
            domain: 服务域
            service_name: 服务名称
            
        Returns:
            Optional[Service]: 服务对象
        """
        return self._services.get(domain, {}).get(service_name)
        
    def list_services(self, domain: Optional[str] = None) -> Dict[str, List[ServiceSchema]]:
        """列出服务
        
        Args:
            domain: 可选的服务域过滤
            
        Returns:
            Dict[str, List[ServiceSchema]]: 服务列表，按域分组
        """
        result = {}
        domains = [domain] if domain else self._services.keys()
        
        for d in domains:
            if d in self._services:
                result[d] = [
                    service.schema
                    for service in self._services[d].values()
                ]
                
        return result
        
    async def call_service(
        self,
        domain: str,
        service_name: str,
        data: Dict[str, Any]
    ) -> Any:
        """调用服务
        
        Args:
            domain: 服务域
            service_name: 服务名称
            data: 服务参数
            
        Returns:
            Any: 服务执行结果
            
        Raises:
            ValueError: 服务不存在
            Exception: 服务执行错误
        """
        service = self.get_service(domain, service_name)
        if not service:
            raise ValueError(f"服务不存在: {domain}.{service_name}")
            
        try:
            # 触发服务调用事件
            await bus.fire(Event(
                event_type="service_called",
                data={
                    "domain": domain,
                    "service": service_name,
                    "data": data
                },
                origin="service_registry"
            ))
            
            # 调用服务处理函数
            if asyncio.iscoroutinefunction(service.handler):
                result = await service.handler(data)
            else:
                result = service.handler(data)
                
            # 触发服务完成事件
            await bus.fire(Event(
                event_type="service_completed",
                data={
                    "domain": domain,
                    "service": service_name,
                    "result": result
                },
                origin="service_registry"
            ))
            
            return result
        except Exception as e:
            logger.error(f"调用服务 {domain}.{service_name} 失败: {str(e)}")
            
            # 触发服务错误事件
            await bus.fire(Event(
                event_type="service_error",
                data={
                    "domain": domain,
                    "service": service_name,
                    "error": str(e)
                },
                origin="service_registry"
            ))
            
            raise

# 全局服务注册表
registry = ServiceRegistry() 