"""设备发现服务

使用 zeroconf 实现设备自动发现功能
"""
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser
from typing import Dict, Any, Optional, Set, Callable
import socket
import json
import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    name: str
    type: str
    host: str
    port: int
    properties: Dict[str, Any]
    last_seen: datetime

class DeviceDiscoveryService:
    """设备发现服务"""
    
    SERVICE_TYPE = "_moss-device._tcp.local."
    
    def __init__(self):
        """初始化设备发现服务"""
        self.zeroconf = Zeroconf()
        self.devices: Dict[str, DeviceInfo] = {}
        self.device_callbacks: Set[Callable[[str, DeviceInfo], None]] = set()
        
    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        port: int,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """注册设备服务
        
        Args:
            device_id: 设备ID
            name: 设备名称
            device_type: 设备类型
            port: 设备服务端口
            properties: 设备属性
        """
        properties = properties or {}
        properties.update({
            "device_id": device_id,
            "type": device_type
        })
        
        # 获取本机IP
        hostname = socket.gethostname()
        host = socket.gethostbyname(hostname)
        
        # 创建服务信息
        info = ServiceInfo(
            self.SERVICE_TYPE,
            f"{device_id}.{self.SERVICE_TYPE}",
            addresses=[socket.inet_aton(host)],
            port=port,
            properties=properties,
            server=f"{hostname}.local."
        )
        
        # 注册服务
        self.zeroconf.register_service(info)
        logger.info(f"设备已注册: {device_id} ({device_type}) at {host}:{port}")
        
    def start_discovery(self) -> None:
        """启动设备发现"""
        self.browser = ServiceBrowser(
            self.zeroconf,
            self.SERVICE_TYPE,
            handlers=[self._on_service_state_change]
        )
        logger.info("设备发现服务已启动")
        
    def stop_discovery(self) -> None:
        """停止设备发现"""
        self.zeroconf.close()
        logger.info("设备发现服务已停止")
        
    def add_device_callback(
        self,
        callback: Callable[[str, DeviceInfo], None]
    ) -> None:
        """添加设备回调函数
        
        Args:
            callback: 回调函数，接收事件类型和设备信息作为参数
        """
        self.device_callbacks.add(callback)
        
    def remove_device_callback(
        self,
        callback: Callable[[str, DeviceInfo], None]
    ) -> None:
        """移除设备回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        self.device_callbacks.discard(callback)
        
    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: str
    ) -> None:
        """服务状态变更处理
        
        Args:
            zeroconf: Zeroconf实例
            service_type: 服务类型
            name: 服务名称
            state_change: 状态变更类型
        """
        info = zeroconf.get_service_info(service_type, name)
        if not info:
            return
            
        # 解析设备信息
        try:
            host = socket.inet_ntoa(info.addresses[0])
            properties = {
                k.decode(): v.decode() if isinstance(v, bytes) else v
                for k, v in info.properties.items()
            }
            device_id = properties.get("device_id", "")
            device_type = properties.get("type", "")
            
            device_info = DeviceInfo(
                device_id=device_id,
                name=name.replace(f".{service_type}", ""),
                type=device_type,
                host=host,
                port=info.port,
                properties=properties,
                last_seen=datetime.now()
            )
            
            # 更新设备列表
            if state_change == "Added" or state_change == "Updated":
                self.devices[device_id] = device_info
                event = "added" if state_change == "Added" else "updated"
            else:  # Removed
                self.devices.pop(device_id, None)
                event = "removed"
                
            # 触发回调
            for callback in self.device_callbacks:
                try:
                    callback(event, device_info)
                except Exception as e:
                    logger.error(f"设备回调执行失败: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"处理设备信息失败: {e}", exc_info=True)
            
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[DeviceInfo]: 设备信息，如果设备不存在则返回None
        """
        return self.devices.get(device_id)
        
    def get_devices(self, device_type: Optional[str] = None) -> Dict[str, DeviceInfo]:
        """获取所有设备
        
        Args:
            device_type: 设备类型过滤器
            
        Returns:
            Dict[str, DeviceInfo]: 设备信息字典
        """
        if device_type:
            return {
                device_id: info
                for device_id, info in self.devices.items()
                if info.type == device_type
            }
        return self.devices.copy() 