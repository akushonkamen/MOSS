"""设备发现服务

提供设备自动发现和注册功能。支持多种发现协议：
1. mDNS/DNS-SD (默认启用)
2. 网络扫描 (默认禁用)
"""
import asyncio
import logging
import socket
import json
from typing import Dict, Set, Optional, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime
import aiohttp
from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange
from zeroconf.asyncio import AsyncZeroconf
import netifaces
import async_timeout
import os

from ..device_registry_server import DeviceInfo, DeviceStatus
from ...events.event_bus import event_bus, EventType
from ...agents.scout.scout_agent import LLMScoutAgent
from ...agents.dispatch.agent_dispatch_center import agent_dispatch_center
from core.config import settings
from ..managers.unified_device_manager import unified_device_manager

logger = logging.getLogger(__name__)

@dataclass
class PortInfo:
    """端口信息"""
    address: str
    port: int
    endpoints_data: Dict[str, Any] = None
    last_scan: datetime = None
    is_analyzed: bool = False

@dataclass
class DiscoveredDevice:
    """发现的设备信息"""
    device_id: str
    device_type: str
    name: str
    address: str
    port: int
    protocol: str
    capabilities: List[str]
    metadata: Dict[str, Any]
    discovery_time: datetime
    last_seen: datetime

class DiscoveryProtocol:
    """发现协议类型"""
    MDNS = "mdns"
    SCAN = "scan"  # 默认禁用

class DiscoveryService:
    """设备发现服务"""
    
    def __init__(self):
        """初始化发现服务"""
        self._mdns = None
        self._is_running = False
        self._lock = asyncio.Lock()
        self._known_ports: Set[int] = set()
        self._port_scan_task: Optional[asyncio.Task] = None
        self._analyzed_ports: Dict[int, datetime] = {}
        self._known_devices: Set[str] = set()
        self._aiozc: Optional[AsyncZeroconf] = None
        self._scan_task = None
        self._enable_port_scan = False
        self._mdns_browser = None
        self._discovered_ports: Dict[str, PortInfo] = {}
        self._port_scan_lock = asyncio.Lock()
        self._batch_size = 1000
        self._endpoints_to_probe = [
            "/docs",
            "/openapi.json",
            "/info",
            "/api/info",
            "/api/v1/info",
            "/status",
            "/api/status",
            "/device",
            "/api/device"
        ]
        
        # 设置日志系统
        self._logger = logging.getLogger(__name__)
        self._setup_logging()
        self._logger.info("Device discovery service initialized")
        
    def _setup_logging(self):
        """配置日志系统"""
        # 确保日志目录存在
        os.makedirs(os.path.dirname(settings.SCAN_LOG_FILE), exist_ok=True)
        
        # 创建文件处理器
        scan_handler = logging.FileHandler(settings.SCAN_LOG_FILE)
        scan_handler.setLevel(logging.INFO)
        scan_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
        
        discovery_handler = logging.FileHandler(settings.DISCOVERY_LOG_FILE)
        discovery_handler.setLevel(logging.INFO)
        discovery_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
        
        # 配置日志器
        scan_logger = logging.getLogger("port_scanner")
        scan_logger.setLevel(logging.INFO)
        scan_logger.addHandler(scan_handler)
        scan_logger.propagate = False  # 防止扫描日志传播到终端
        
        discovery_logger = logging.getLogger("device_discovery")
        discovery_logger.setLevel(logging.INFO)
        discovery_logger.addHandler(discovery_handler)
        discovery_logger.propagate = True  # 允许设备发现日志显示在终端
        
        self.scan_logger = scan_logger
        self.discovery_logger = discovery_logger
        
    async def start(self, enable_port_scan: bool = False):
        """启动发现服务
        
        Args:
            enable_port_scan: 是否启用端口扫描
        """
        if self._is_running:
            return
            
        try:
            self._is_running = True
            
            # 启动mDNS发现
            await self._start_mdns_discovery()
            
            # 启动端口扫描（如果启用）
            if enable_port_scan:
                local_ip = self._get_local_ip()
                self._port_scan_task = asyncio.create_task(self._scan_ports(local_ip))
                self._logger.info("端口扫描已启用")
            
            self._logger.info("设备发现服务已启动")
            
        except Exception as e:
            self._is_running = False
            self._logger.error(f"启动发现服务失败: {str(e)}")
            raise
        
    async def stop(self):
        """停止发现服务"""
        if not self._is_running:
            return
            
        try:
            self._is_running = False
            
            # 停止端口扫描任务
            if self._port_scan_task:
                self._port_scan_task.cancel()
                try:
                    await self._port_scan_task
                except asyncio.CancelledError:
                    pass
                self._port_scan_task = None
        
        # 停止mDNS发现
            if self._mdns:
                self._mdns.close()
                self._mdns = None
            
            self._logger.info("设备发现服务已停止")
            
        except Exception as e:
            self._logger.error(f"停止发现服务失败: {str(e)}")
            raise
        
    async def _start_mdns_discovery(self):
        """启动mDNS服务发现"""
        self._logger.info("Starting mDNS discovery")
        self._aiozc = AsyncZeroconf()
        
        # 监听智能设备服务
        services = ['_http._tcp.local.', '_device._tcp.local.']
        for service in services:
            ServiceBrowser(
                self._aiozc.zeroconf,
                service,
                handlers=[self._on_service_state_change]
            )
            
    async def _on_service_state_change(self, zeroconf: Zeroconf, service_type: str,
                                     name: str, state_change: ServiceStateChange):
        """处理mDNS服务状态变化
        
        Args:
            zeroconf: Zeroconf实例
            service_type: 服务类型
            name: 服务名称
            state_change: 状态变化
        """
        if state_change is ServiceStateChange.Added:
            info = await self._aiozc.async_get_service_info(service_type, name)
            if info:
                device_info = self._parse_mdns_info(info)
                if device_info:
                    # 如果有 LLMScoutAgent，进行深入分析
                    if self._scout_agent:
                        try:
                            # 构建分析上下文
                            analysis_context = {
                                "address": device_info["metadata"]["address"],
                                "port": device_info["metadata"]["port"],
                                "protocol": "mdns",
                                "service_info": {
                                    "type": service_type,
                                    "name": name,
                                    "properties": device_info["metadata"]["properties"]
                                }
                            }
                            
                            # 使用 LLMScoutAgent 分析设备
                            analysis = await self._scout_agent._analyze_device(analysis_context)
                            
                            if analysis.get("is_device", False):
                                # 使用分析结果增强设备信息
                                device_info.update({
                                    "device_type": analysis.get("device_type", device_info["device_type"]),
                                    "capabilities": analysis.get("capabilities", device_info["capabilities"]),
                                    "metadata": {
                                        **device_info["metadata"],
                                        "analysis": analysis
                                    }
                                })
                        except Exception as e:
                            self._logger.error(f"设备分析失败: {e}")
                        finally:
                            await self._register_device(device_info)
                    else:
                        await self._register_device(device_info)
                    
        elif state_change is ServiceStateChange.Removed:
            # 处理设备离线
            device_id = f"mdns_{name}"
            await event_bus.publish(
                EventType.DEVICE,
                "device_lost",
                {
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

    def _get_local_ip(self) -> str:
        """获取本机IP地址"""
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if not ip.startswith('127.'):
                        return ip
        return '127.0.0.1'
        
    async def _scan_ports(self, local_ip: str):
        """扫描端口
        
        Args:
            local_ip: 本地IP地址
        """
        try:
            self._logger.info(f"开始扫描端口 ({local_ip})")
            start_port, end_port = settings.PORT_SCAN_RANGE
            batch_size = settings.PORT_SCAN_BATCH_SIZE
            
            while self._is_running:
                for port in range(start_port, end_port + 1, batch_size):
                    if not self._is_running:
                        break
                        
                    batch_end = min(port + batch_size, end_port + 1)
                    tasks = []
                    
                    for p in range(port, batch_end):
                        # 检查端口是否已经分析过
                        if p in self._analyzed_ports:
                            last_scan = self._analyzed_ports[p]
                            if (datetime.now() - last_scan).total_seconds() < settings.PORT_SCAN_INTERVAL:
                                continue
                                
                        tasks.append(self._check_port(local_ip, p))
                        
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        open_ports = [p for p, is_open in zip(range(port, batch_end), results) if is_open and not isinstance(is_open, Exception)]
                        
                        for open_port in open_ports:
                            if open_port not in self._known_ports:
                                self._known_ports.add(open_port)
                                port_info = PortInfo(
                                    address=local_ip,
                                    port=open_port,
                                    last_scan=datetime.now()
                                )
                                # 在后台收集端口数据
                                asyncio.create_task(self._collect_port_data(port_info))
                                
                    # 短暂暂停，避免占用过多资源
                    await asyncio.sleep(0.1)
                    
                # 完成一轮扫描后，等待指定间隔再开始下一轮
                await asyncio.sleep(settings.PORT_SCAN_INTERVAL)
                
        except Exception as e:
            self._logger.error(f"端口扫描失败: {str(e)}")
            
        finally:
            self._logger.info("端口扫描已停止")
        
    async def _check_port(self, ip: str, port: int) -> bool:
        """检查单个端口
        
        Args:
            ip: IP地址
            port: 端口号
            
        Returns:
            bool: 端口是否开放
        """
        try:
            # 创建socket连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception as e:
            self.scan_logger.error(f"检查端口 {port} 失败: {str(e)}")
            return False
        
    async def _probe_device(self, ip: str, port: int) -> Optional[Dict[str, Any]]:
        """基本设备探测
        
        Args:
            ip: 设备IP地址
            port: 设备端口
            
        Returns:
            Optional[Dict[str, Any]]: 设备信息
        """
        try:
            self._logger.debug(f"正在探测设备 {ip}:{port}")
            device_info = {
                "address": ip,
                "port": port,
                "endpoints": {},
                "available_endpoints": [],
                "api_url": None  # 添加api_url字段
            }
            
            # 尝试获取设备API文档
            async with async_timeout.timeout(5):
                async with aiohttp.ClientSession() as session:
                    # 首先尝试获取OpenAPI文档
                    for path in ['/docs', '/openapi.json', '/swagger.json']:
                        try:
                            url = f"http://{ip}:{port}{path}"
                            self._logger.debug(f"尝试访问: {url}")
                            async with session.get(url) as response:
                                if response.status == 200:
                                    self._logger.info(f"成功获取API文档: {url}")
                                    content_type = response.headers.get('Content-Type', '')
                                    content = await response.text()
                                    device_info["endpoints"][path] = {
                                        "url": url,
                                        "content_type": content_type,
                                        "content": content,
                                        "status_code": response.status
                                    }
                                    device_info["available_endpoints"].append(path)
                                    # 优先使用 OpenAPI/Swagger 文档作为 API URL
                                    if path in ['/openapi.json', '/swagger.json'] or not device_info["api_url"]:
                                        device_info["api_url"] = url
                        except Exception as e:
                            self._logger.debug(f"访问 {url} 失败: {e}")
                            device_info["endpoints"][path] = {
                                "url": url,
                                "error": str(e)
                            }
                    
                    # 尝试获取其他设备信息端点
                    for path in ['/info', '/device', '/about', '/status', '/api']:
                        try:
                            url = f"http://{ip}:{port}{path}"
                            self._logger.debug(f"尝试访问: {url}")
                            async with session.get(url) as response:
                                content = await response.text()
                                device_info["endpoints"][path] = {
                                    "url": url,
                                    "content_type": response.headers.get('Content-Type', ''),
                                    "content": content,
                                    "status_code": response.status
                                }
                                if response.status == 200:
                                    self._logger.info(f"成功获取设备信息: {url}")
                                    device_info["available_endpoints"].append(path)
                                    # 如果还没有找到API文档，也设置为api_url
                                    if not device_info["api_url"]:
                                        device_info["api_url"] = url
                        except Exception as e:
                            self._logger.debug(f"访问 {url} 失败: {e}")
                            device_info["endpoints"][path] = {
                                "url": url,
                                "error": str(e)
                            }
            
            # 添加元数据
            device_info["metadata"] = {
                "address": ip,
                "port": port,
                "discovery_time": datetime.now().isoformat(),
                "total_endpoints": len(device_info["endpoints"]),
                "available_endpoints": len(device_info["available_endpoints"])
            }
            
            # 只有当找到至少一个可用端点时才返回设备信息
            if device_info["available_endpoints"]:
                self._logger.info(f"设备探测成功 {ip}:{port}, API URL: {device_info['api_url']}")
                return device_info
            return None
                        
        except Exception as e:
            self._logger.debug(f"探测设备 {ip}:{port} 失败: {e}")
            return None
        
    def _parse_device_info(self, api_doc: Dict[str, Any], ip: str, port: int) -> Dict[str, Any]:
        """从API文档解析设备信息
        
        Args:
            api_doc: API文档
            ip: 设备IP地址
            port: 设备端口
            
        Returns:
            Dict[str, Any]: 设备信息
        """
        try:
            info = api_doc.get("info", {})
            paths = api_doc.get("paths", {})
            
            # 提取设备能力
            capabilities = []
            if "/power" in paths or "/power/on" in paths or "/power/off" in paths:
                capabilities.append("power_control")
            if "/status" in paths:
                capabilities.append("status_query")
            if "/command" in paths:
                capabilities.append("command_execution")
                
            return {
                "device_id": f"device_{ip}_{port}",
                "device_type": info.get("title", "unknown").lower().replace(" ", "_"),
                "name": info.get("title", f"Device at {ip}:{port}"),
                "capabilities": capabilities,
                "metadata": {
                    "address": ip,
                    "port": port,
                    "version": info.get("version", "unknown"),
                    "description": info.get("description", "")
                }
            }
            
        except Exception as e:
            self._logger.error(f"Error parsing API doc: {e}")
            return None
            
    def _parse_mdns_info(self, info: Any) -> Optional[Dict[str, Any]]:
        """解析mDNS服务信息
        
        Args:
            info: mDNS服务信息
            
        Returns:
            Optional[Dict[str, Any]]: 设备信息
        """
        try:
            # 获取设备地址和端口
            addresses = [f"{socket.inet_ntoa(addr)}" for addr in info.addresses]
            if not addresses:
                return None
                
            address = addresses[0]
            port = info.port
            
            # 解析设备信息
            properties = {}
            if info.properties:
                for key, value in info.properties.items():
                    if isinstance(value, bytes):
                        properties[key.decode('utf-8')] = value.decode('utf-8')
                    else:
                        properties[key] = value
                        
            device_id = properties.get('id', f"mdns_{info.name}")
            device_type = properties.get('type', 'unknown')
            name = properties.get('name', info.name)
            capabilities = properties.get('capabilities', '').split(',')
            
            return {
                "device_id": device_id,
                "device_type": device_type,
                "name": name,
                "capabilities": [cap for cap in capabilities if cap],
                "metadata": {
                    "address": address,
                    "port": port,
                    "protocol": "mdns",
                    "service_type": info.type,
                    "properties": properties
                }
            }
                    
        except Exception as e:
            self._logger.error(f"Error parsing mDNS info: {e}")
            return None

    async def _register_device(self, device_info: Dict[str, Any]) -> None:
        """注册设备
        
        Args:
            device_info: 设备信息
        """
        try:
            # 验证设备信息
            validation_result = self._validator.validate_device_info(device_info)
            if not validation_result.is_valid:
                error_messages = [f"{e.field}: {e.message}" for e in validation_result.errors]
                self._logger.warning(f"设备信息验证失败: {'; '.join(error_messages)}")
                return

            # 注册设备
            device = await unified_device_manager.register_device(device_info)
            
            # 打印详细的设备状态
            self._logger.info("发现并注册新设备:")
            self._logger.info(f"  设备ID: {device.device_id}")
            self._logger.info(f"  名称: {device.name}")
            self._logger.info(f"  类型: {device.device_type}")
            self._logger.info(f"  状态: {device.status}")
            self._logger.info(f"  能力: {', '.join(device.capabilities)}")
            if device.metadata:
                self._logger.info("  元数据:")
                for key, value in device.metadata.items():
                    self._logger.info(f"    {key}: {value}")
                
            # 发布设备发现事件，确保包含完整的设备信息
            event_data = {
                        "device_id": device.device_id,
                "name": device.name,
                        "device_type": device.device_type,
                "capabilities": device.capabilities,
                "status": device.status,
                "metadata": device.metadata,
                "api_url": device_info.get("api_url"),  # 包含API URL
                "endpoints": device_info.get("endpoints", {}),  # 包含端点信息
                "available_endpoints": device_info.get("available_endpoints", []),  # 包含可用端点
                "response_data": device_info  # 包含原始响应数据
            }
            
            await event_bus.publish(EventType.DEVICE, "device_discovered", event_data)
            
            self._logger.info(f"Device registered: {device.device_id}")
            
        except Exception as e:
            self._logger.error(f"Failed to register device: {e}")
            
    async def _collect_port_data(self, port_info: PortInfo) -> None:
        """收集端口数据
        
        Args:
            port_info: 端口信息
        """
        try:
            # 探测设备
            response_data = await self._probe_device(port_info.address, port_info.port)
            if response_data:
                port_info.endpoints_data = response_data
                port_info.last_scan = datetime.now()
                
                # 将端口信息存储到discovered_ports
                port_key = f"{port_info.address}:{port_info.port}"
                self._discovered_ports[port_key] = port_info
                
                self._logger.info(f"成功收集端口 {port_info.address}:{port_info.port} 的数据")
                
                # 触发端口分析
                await self._analyze_collected_ports()
            
        except Exception as e:
            self._logger.error(f"收集端口数据失败: {str(e)}")
            
    async def _analyze_collected_ports(self) -> None:
        """分析收集到的端口数据"""
        try:
            # 获取未分析的端口
            unanalyzed_ports = [
                port_info for port_info in self._discovered_ports.values()
                if not port_info.is_analyzed and port_info.endpoints_data
            ]
            
            if not unanalyzed_ports:
                return
                
            self._logger.info(f"正在分析 {len(unanalyzed_ports)} 个端口")
            
            # 创建分析任务
            for port_info in unanalyzed_ports:
                # 准备分析上下文
                context = {
                    "port": port_info.port,
                    "response_data": port_info.endpoints_data
                }
                
                # 创建处理管道
                pipeline_id = f"analyze_port_{port_info.port}"
                await agent_dispatch_center.create_pipeline({
                    "pipeline_id": pipeline_id,
                    "agents": ["scout"]
                })
                
                self._logger.info(f"\n[ScoutAgent输入] 端口 {port_info.port}:")
                self._logger.info(f"输入数据: {json.dumps(context, indent=2, ensure_ascii=False)}")
                
                # 调用分析管道
                result = await agent_dispatch_center.dispatch({
                    "pipeline_id": pipeline_id,
                    "context": context
                })
                
                self._logger.info(f"\n[ScoutAgent输出] 端口 {port_info.port}:")
                self._logger.info(f"分析结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # 如果分析结果表明这是一个设备，发布设备发现事件
                if result.get("is_device", False):
                    device_info = {
                        "device_id": f"{result.get('device_type', 'device')}_{port_info.port}",
                        "name": result.get("device_name", ""),
                        "device_type": result.get("device_type", "unknown"),
                        "capabilities": result.get("capabilities", []),
                        "status": "online",
                        "metadata": {
                            "address": port_info.endpoints_data["address"],
                            "port": port_info.port,
                            "discovery_time": datetime.now().isoformat(),
                            "analysis": result
                        },
                        "api_url": port_info.endpoints_data.get("api_url"),  # 从端口数据中获取API URL
                        "endpoints": port_info.endpoints_data.get("endpoints", {}),
                        "available_endpoints": port_info.endpoints_data.get("available_endpoints", []),
                        "response_data": port_info.endpoints_data
                    }
                    await event_bus.publish(EventType.DEVICE, "device_discovered", device_info)
                    self._logger.info(f"设备发现事件已发布:  ({device_info['device_id']})")

                port_info.is_analyzed = True
                
        except Exception as e:
            self._logger.error(f"分析端口数据失败: {str(e)}")

# 创建发现服务实例
discovery_service = DiscoveryService() 