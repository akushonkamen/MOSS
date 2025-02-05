"""设备客户端"""
import aiohttp
from typing import Dict, Any, Optional, List, Callable
import logging
import sys
import asyncio
from datetime import datetime, timedelta
from .device_discovery import DeviceDiscoveryService, DeviceInfo

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DeviceClient:
    """设备客户端基类"""
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化设备客户端
        
        Args:
            device_id: 设备ID
            name: 设备名称
            port: 服务器端口
        """
        self.device_id = device_id
        self.id = device_id
        self.name = name
        self.port = port
        self.state = None
        self.last_update = None
        self.base_url = f"http://127.0.0.1:{port}"
        
        # 初始化设备发现服务
        self.discovery = DeviceDiscoveryService()
        self.discovery.start_discovery()
        self.discovery.add_device_callback(self._on_device_update)
        
    def _on_device_update(self, event: str, device_info: DeviceInfo) -> None:
        """设备更新回调
        
        Args:
            event: 事件类型 (added/updated/removed)
            device_info: 设备信息
        """
        if device_info.device_id == self.device_id:
            if event == "removed":
                logger.warning(f"设备 {self.device_id} 已离线")
            else:
                self.base_url = f"http://{device_info.host}:{device_info.port}"
                logger.info(f"设备 {self.device_id} 地址已更新: {self.base_url}")
                
    async def get_status(self) -> Dict[str, Any]:
        """获取设备状态
        
        Returns:
            Dict[str, Any]: 设备状态
        """
        try:
            # 尝试从设备发现服务获取最新地址
            device_info = self.discovery.get_device(self.device_id)
            if device_info:
                self.base_url = f"http://{device_info.host}:{device_info.port}"
                
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/status") as response:
                    if response.status != 200:
                        raise DeviceError(
                            "获取状态失败",
                            device_id=self.device_id,
                            status_code=response.status
                        )
                    data = await response.json()
                    self.state = data.get("status", {})
                    self.last_update = datetime.now()
                    return self.state
        except aiohttp.ClientError as e:
            raise DeviceError(
                f"连接设备失败: {str(e)}",
                device_id=self.device_id
            )
            
    async def execute_command(
        self,
        command: str,
        **parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行设备命令
        
        Args:
            command: 命令名称
            **parameters: 命令参数
            
        Returns:
            Dict[str, Any]: 命令执行结果，格式为:
            {
                "success": bool,
                "result": str,
                "error": Optional[str]
            }
            
        Raises:
            DeviceError: 设备操作异常
        """
        try:
            # 尝试从设备发现服务获取最新地址
            device_info = self.discovery.get_device(self.device_id)
            if device_info:
                self.base_url = f"http://{device_info.host}:{device_info.port}"
                
            # 构造请求数据
            data = {
                "command": command,
                "parameters": parameters
            }
            
            # 发送命令到设备服务器
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/command", json=data) as response:
                    if response.status != 200:
                        raise DeviceError(
                            "执行命令失败",
                            device_id=self.device_id,
                            status_code=response.status
                        )
                    result = await response.json()
                    
                    # 更新本地状态
                    if result.get("success"):
                        await self.get_status()
                        
                    return result
                    
        except aiohttp.ClientError as e:
            raise DeviceError(
                f"连接设备失败: {str(e)}",
                device_id=self.device_id
            )
        except Exception as e:
            raise DeviceError(
                f"执行命令失败: {str(e)}",
                device_id=self.device_id
            )
            
    def __del__(self):
        """清理资源"""
        self.discovery.stop_discovery()

class DeviceError(Exception):
    """设备操作异常"""
    
    def __init__(
        self,
        message: str,
        device_id: str,
        status_code: Optional[int] = None
    ):
        """初始化异常
        
        Args:
            message: 错误信息
            device_id: 设备ID
            status_code: HTTP状态码
        """
        super().__init__(message)
        self.device_id = device_id
        self.status_code = status_code

class SmartLightClient(DeviceClient):
    """智能灯客户端"""
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化智能灯客户端"""
        super().__init__(device_id, name, port)
        self.state = {
            "is_on": False,
            "brightness": 100
        }
        
    async def turn_on(self) -> Dict[str, Any]:
        """打开智能灯"""
        result = await self.execute_command("turn_on")
        return result
        
    async def turn_off(self) -> Dict[str, Any]:
        """关闭智能灯"""
        result = await self.execute_command("turn_off")
        return result
        
    async def set_brightness(self, brightness: int) -> Dict[str, Any]:
        """设置亮度
        
        Args:
            brightness: 亮度值(0-100)
        """
        if not 0 <= brightness <= 100:
            raise ValueError("亮度值必须在0-100之间")
        result = await self.execute_command(
            "set_brightness",
            brightness=brightness
        )
        return result
        
    async def set_power(self, power: bool) -> Dict[str, Any]:
        """设置电源状态
        
        Args:
            power: 电源状态
        """
        result = await self.execute_command(
            "set_power",
            power=power
        )
        return result

class SmartACClient(DeviceClient):
    """空调客户端"""
    
    VALID_MODES = {"cool", "heat", "auto"}
    MIN_TEMP = 16
    MAX_TEMP = 30
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化空调客户端"""
        super().__init__(device_id, name, port)
        self.state = {
            "is_on": False,
            "temperature": 26,
            "mode": "auto"
        }
        
    async def turn_on(self) -> Dict[str, Any]:
        """打开空调"""
        result = await self.execute_command("turn_on")
        return result
        
    async def turn_off(self) -> Dict[str, Any]:
        """关闭空调"""
        result = await self.execute_command("turn_off")
        return result
        
    async def set_temperature(self, temperature: int) -> Dict[str, Any]:
        """设置温度
        
        Args:
            temperature: 温度值(16-30)
        """
        if not self.MIN_TEMP <= temperature <= self.MAX_TEMP:
            raise ValueError(f"温度值必须在{self.MIN_TEMP}-{self.MAX_TEMP}之间")
        result = await self.execute_command(
            "set_temperature",
            temperature=temperature
        )
        return result
        
    async def set_mode(self, mode: str) -> Dict[str, Any]:
        """设置模式
        
        Args:
            mode: 运行模式
        """
        if mode not in self.VALID_MODES:
            raise ValueError(f"无效的模式: {mode}")
        result = await self.execute_command(
            "set_mode",
            mode=mode
        )
        return result
        
    async def set_power(self, power: bool) -> Dict[str, Any]:
        """设置电源状态
        
        Args:
            power: 电源状态
        """
        result = await self.execute_command(
            "set_power",
            power=power
        )
        return result

class SmartCurtainClient(DeviceClient):
    """窗帘客户端"""
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化窗帘客户端"""
        super().__init__(device_id, name, port)
        self.state = {
            "is_open": False,
            "position": 0
        }
        
    async def turn_on(self) -> Dict[str, Any]:
        """打开窗帘"""
        result = await self.execute_command("turn_on")
        return result
        
    async def turn_off(self) -> Dict[str, Any]:
        """关闭窗帘"""
        result = await self.execute_command("turn_off")
        return result
        
    async def set_position(self, position: int) -> Dict[str, Any]:
        """设置位置
        
        Args:
            position: 位置百分比(0-100)
        """
        if not 0 <= position <= 100:
            raise ValueError("位置值必须在0-100之间")
        result = await self.execute_command(
            "set_position",
            {"position": position}
        )
        return result 