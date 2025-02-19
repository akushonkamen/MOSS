"""设备注册服务

提供设备注册、发现和管理功能。
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import aiohttp
from aiohttp import web
import uuid
import socket

from core.config import settings
from .validators import DeviceValidator, ValidationError as DeviceValidationError
from services.events.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)

# 心跳超时时间（秒）
HEARTBEAT_TIMEOUT = 30
# 心跳检查间隔（秒）
HEARTBEAT_CHECK_INTERVAL = 10

class DeviceStatus:
    """设备状态枚举"""
    REGISTERING = "registering"  # 注册中
    ONLINE = "online"           # 在线
    OFFLINE = "offline"         # 离线
    ERROR = "error"            # 错误
    DEREGISTERING = "deregistering" # 注销中

@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    device_type: str
    name: str
    capabilities: List[str]
    status: str = DeviceStatus.OFFLINE
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    heartbeat_count: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "name": self.name,
            "capabilities": self.capabilities,
            "status": self.status,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.metadata,
            "error_message": self.error_message
        }

class DeviceRegistry:
    """设备注册表"""
    def __init__(self):
        self._devices: Dict[str, DeviceInfo] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._validator = DeviceValidator()
        
    async def start(self):
        """启动注册表服务"""
        self._heartbeat_task = asyncio.create_task(self._check_heartbeats())
        logger.info("Device registry started")
        
    async def stop(self):
        """停止注册表服务"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("Device registry stopped")
        
    async def _check_heartbeats(self):
        """检查设备心跳"""
        while True:
            try:
                now = datetime.now()
                timeout_threshold = now - timedelta(seconds=HEARTBEAT_TIMEOUT)
                
                async with self._lock:
                    for device_id, device in self._devices.items():
                        if device.status == DeviceStatus.ONLINE:
                            if device.last_seen and device.last_seen < timeout_threshold:
                                device.status = DeviceStatus.OFFLINE
                                device.error_message = "Heartbeat timeout"
                                logger.warning(f"Device {device_id} went offline due to heartbeat timeout")
                
                await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Error in heartbeat check: {e}")
                await asyncio.sleep(1)
        
    async def register_device(self, device_info: Dict[str, Any]) -> DeviceInfo:
        """注册设备
        
        Args:
            device_info: 设备信息字典
            
        Returns:
            DeviceInfo: 注册的设备信息
            
        Raises:
            ValueError: 设备信息无效
        """
        # 验证设备信息
        validation_result = self._validator.validate_device_info(device_info)
        if not validation_result.is_valid:
            error_messages = [f"{e.field}: {e.message}" for e in validation_result.errors]
            raise ValueError(f"Invalid device information: {'; '.join(error_messages)}")
            
        device_id = device_info.get("device_id", str(uuid.uuid4()))
        
        # 如果提供了设备ID，验证其唯一性
        if "device_id" in device_info:
            async with self._lock:
                if device_id in self._devices:
                    raise ValueError(f"Device ID already exists: {device_id}")
        
        device = DeviceInfo(
            device_id=device_id,
            device_type=device_info["device_type"],
            name=device_info["name"],
            capabilities=device_info["capabilities"],
            status=DeviceStatus.REGISTERING,
            last_seen=datetime.now(),
            metadata=device_info.get("metadata", {})
        )
        
        async with self._lock:
            self._devices[device_id] = device
            device.status = DeviceStatus.ONLINE
            
        # 发布设备发现事件
        await event_bus.publish(
            EventType.DEVICE,
            "device_discovered",
            {
                "device_id": device.device_id,
                "device_type": device.device_type,
                "name": device.name,
                "capabilities": device.capabilities,
                "status": device.status,
                "metadata": device.metadata,
                "timestamp": datetime.now().isoformat()
            }
        )
            
        logger.info(f"Device registered: {device.name} ({device.device_id})")
        return device
        
    async def unregister_device(self, device_id: str) -> None:
        """注销设备
        
        Args:
            device_id: 设备ID
            
        Raises:
            KeyError: 设备不存在
        """
        async with self._lock:
            if device_id not in self._devices:
                raise KeyError(f"Device not found: {device_id}")
            device = self._devices[device_id]
            device.status = DeviceStatus.DEREGISTERING
            del self._devices[device_id]
        logger.info(f"Device unregistered: {device_id}")
        
    async def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[DeviceInfo]: 设备信息，不存在则返回None
        """
        return self._devices.get(device_id)
        
    async def list_devices(self, 
        device_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[DeviceInfo]:
        """列出设备
        
        Args:
            device_type: 设备类型过滤
            status: 状态过滤
            
        Returns:
            List[DeviceInfo]: 设备列表
        """
        devices = list(self._devices.values())
        
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
        if status:
            devices = [d for d in devices if d.status == status]
            
        return devices
        
    async def update_device_status(self, device_id: str, status: str) -> None:
        """更新设备状态
        
        Args:
            device_id: 设备ID
            status: 新状态
            
        Raises:
            KeyError: 设备不存在
            ValueError: 状态无效
        """
        if status not in vars(DeviceStatus).values():
            raise ValueError(f"Invalid status: {status}")
            
        async with self._lock:
            if device_id not in self._devices:
                raise KeyError(f"Device not found: {device_id}")
            device = self._devices[device_id]
            device.status = status
            device.last_seen = datetime.now()
            if status == DeviceStatus.ERROR:
                device.error_message = "Status manually set to ERROR"
            else:
                device.error_message = None
        logger.info(f"Device status updated: {device_id} -> {status}")
        
    async def heartbeat(self, device_id: str) -> None:
        """处理设备心跳
        
        Args:
            device_id: 设备ID
            
        Raises:
            KeyError: 设备不存在
        """
        async with self._lock:
            if device_id not in self._devices:
                raise KeyError(f"Device not found: {device_id}")
            device = self._devices[device_id]
            device.last_seen = datetime.now()
            device.heartbeat_count += 1
            if device.status == DeviceStatus.OFFLINE:
                device.status = DeviceStatus.ONLINE
                device.error_message = None
                logger.info(f"Device {device_id} is back online")

class RegistryServer:
    """注册服务器"""
    def __init__(self):
        self.registry = DeviceRegistry()
        self.app = web.Application()
        self.setup_routes()
        self._runner = None
        self._site = None
        
    def setup_routes(self):
        """设置路由"""
        self.app.router.add_post("/register", self.handle_register)
        self.app.router.add_post("/unregister", self.handle_unregister)
        self.app.router.add_get("/devices", self.handle_list_devices)
        self.app.router.add_get("/devices/{device_id}", self.handle_get_device)
        self.app.router.add_post("/devices/{device_id}/status", self.handle_update_status)
        self.app.router.add_post("/devices/{device_id}/heartbeat", self.handle_heartbeat)
        self.app.router.add_post("/devices/discover", self.handle_discover)
        
    async def handle_register(self, request: web.Request) -> web.Response:
        """处理注册请求"""
        try:
            data = await request.json()
            device = await self.registry.register_device(data)
            return web.json_response(device.to_dict())
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
            
    async def handle_unregister(self, request: web.Request) -> web.Response:
        """处理注销请求"""
        try:
            data = await request.json()
            device_id = data.get("device_id")
            if not device_id:
                return web.json_response({"error": "Missing device_id"}, status=400)
            
            await self.registry.unregister_device(device_id)
            return web.json_response({"status": "success"})
        except KeyError as e:
            return web.json_response({"error": str(e)}, status=404)
        except Exception as e:
            logger.error(f"Unregistration error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
            
    async def handle_list_devices(self, request: web.Request) -> web.Response:
        """处理设备列表请求"""
        try:
            device_type = request.query.get("type")
            status = request.query.get("status")
            
            devices = await self.registry.list_devices(device_type, status)
            return web.json_response([d.to_dict() for d in devices])
        except Exception as e:
            logger.error(f"List devices error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
            
    async def handle_get_device(self, request: web.Request) -> web.Response:
        """处理获取设备信息请求"""
        try:
            device_id = request.match_info["device_id"]
            device = await self.registry.get_device(device_id)
            
            if not device:
                return web.json_response({"error": "Device not found"}, status=404)
            return web.json_response(device.to_dict())
        except Exception as e:
            logger.error(f"Get device error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
            
    async def handle_update_status(self, request: web.Request) -> web.Response:
        """处理状态更新请求"""
        try:
            device_id = request.match_info["device_id"]
            data = await request.json()
            status = data.get("status")
            
            if not status:
                return web.json_response({"error": "Missing status"}, status=400)
                
            await self.registry.update_device_status(device_id, status)
            return web.json_response({"status": "success"})
        except KeyError as e:
            return web.json_response({"error": str(e)}, status=404)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Status update error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
            
    async def handle_heartbeat(self, request: web.Request) -> web.Response:
        """处理心跳请求"""
        try:
            device_id = request.match_info["device_id"]
            await self.registry.heartbeat(device_id)
            return web.json_response({"status": "success"})
        except KeyError as e:
            return web.json_response({"error": str(e)}, status=404)
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
            
    async def handle_discover(self, request: web.Request) -> web.Response:
        """处理设备发现请求"""
        try:
            data = await request.json()
            device_info = {
                "device_id": data["device_id"],
                "device_type": data["device_type"],
                "name": data["name"],
                "capabilities": data.get("capabilities", []),
                "metadata": {
                    "address": data["address"],
                    "port": data["port"]
                }
            }
            
            device = await self.registry.register_device(device_info)
            return web.json_response(device.to_dict())
        except KeyError as e:
            return web.json_response({"error": f"Missing required field: {str(e)}"}, status=400)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Device discovery error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
            
    async def start(self, host: str = '0.0.0.0', port: int = 9001):
        """启动服务器
        
        Args:
            host: 监听地址
            port: 监听端口
        """
        try:
            # 启动注册表
            await self.registry.start()
            
            # 启动HTTP服务器
            runner = web.AppRunner(
                self.app,
                access_log=logging.getLogger('aiohttp.access')
            )
            await runner.setup()
            self._runner = runner
            
            # 创建TCP服务器
            site = web.TCPSite(
                runner,
                host=host,
                port=port,
                shutdown_timeout=60.0,
                backlog=128,
                reuse_address=True,
                reuse_port=True
            )
            
            # 启动服务器
            await site.start()
            self._site = site
            
            # 等待服务器完全启动
            await asyncio.sleep(1)
            
            logger.info(f"Registry server started at http://{host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to start registry server: {str(e)}")
            # 清理资源
            if hasattr(self, '_site'):
                await self._site.stop()
            if hasattr(self, '_runner'):
                await self._runner.cleanup()
            await self.registry.stop()
            raise
            
    async def stop(self):
        """停止服务器"""
        try:
            if hasattr(self, '_site'):
                await self._site.stop()
            if hasattr(self, '_runner'):
                await self._runner.cleanup()
            await self.registry.stop()
            logger.info("Registry server stopped")
        except Exception as e:
            logger.error(f"Error stopping registry server: {str(e)}")
            raise

# 创建服务器实例
registry_server = RegistryServer() 