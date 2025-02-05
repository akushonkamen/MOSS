"""设备服务器

每个设备作为独立的FastAPI服务运行
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Dict, Any, Optional
import asyncio
import json
import logging
import sys
from .device_discovery import DeviceDiscoveryService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DeviceStatus(BaseModel):
    """设备状态基类"""
    device_id: str
    name: str
    type: str
    status: Dict[str, Any]

class DeviceCommand(BaseModel):
    """设备命令"""
    command: str
    parameters: Dict[str, Any]

class DeviceServer:
    """设备服务器基类"""
    
    def __init__(self, device_type: str, device_id: str, name: str, host: str = "127.0.0.1", port: int = 8000):
        """初始化设备服务器
        
        Args:
            device_type: 设备类型
            device_id: 设备ID
            name: 设备名称
            host: 服务器主机地址
            port: 服务器端口
        """
        self.device_type = device_type
        self.device_id = device_id
        self.name = name
        self.host = host
        self.port = port
        self.status: Dict[str, Any] = {}
        self.logger = logging.getLogger(f"{__name__}.{device_type}.{device_id}")
        
        # 创建FastAPI应用
        self.app = FastAPI(title=f"{name} API", description=f"{device_type} 设备服务器")
        self.setup_routes()
        
        # 初始化设备发现服务
        self.discovery = DeviceDiscoveryService()
        
        self.logger.info(f"设备初始化完成，初始状态: {self.status}")
        
    def setup_routes(self):
        """设置API路由"""
        
        @self.app.get("/status")
        async def get_status() -> DeviceStatus:
            """获取设备状态"""
            self.logger.info(f"收到状态查询请求")
            response = DeviceStatus(
                device_id=self.device_id,
                name=self.name,
                type=self.device_type,
                status=self.status
            )
            self.logger.info(f"返回状态: {response.dict()}")
            return response
            
        @self.app.post("/command")
        async def execute_command(command: DeviceCommand) -> Dict[str, Any]:
            """执行设备命令"""
            try:
                self.logger.info(f"收到命令: {command.command}, 参数: {command.parameters}")
                self.logger.info(f"命令执行前状态: {self.status}")
                
                handler = getattr(self, f"handle_{command.command}")
                result = await handler(**command.parameters)
                
                self.logger.info(f"命令执行结果: {result}")
                self.logger.info(f"命令执行后状态: {self.status}")
                
                return {
                    "success": True,
                    "result": result,
                    "error": None
                }
            except AttributeError:
                error = f"不支持的命令: {command.command}"
                self.logger.error(error)
                return {
                    "success": False,
                    "result": None,
                    "error": error
                }
            except Exception as e:
                error = str(e)
                self.logger.error(f"执行命令出错: {error}", exc_info=True)
                return {
                    "success": False,
                    "result": None,
                    "error": error
                }
                
    def run(self):
        """启动设备服务器"""
        # 注册设备服务
        self.discovery.register_device(
            device_id=self.device_id,
            name=self.name,
            device_type=self.device_type,
            port=self.port,
            properties={"status": json.dumps(self.status)}
        )
        
        self.logger.info(f"服务器启动于 {self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True
        )
        
    def __del__(self):
        """清理资源"""
        self.discovery.stop_discovery()
        
    async def handle_turn_on(self) -> str:
        """处理打开命令"""
        raise NotImplementedError()
        
    async def handle_turn_off(self) -> str:
        """处理关闭命令"""
        raise NotImplementedError()

    async def handle_set_power(self, power: bool) -> str:
        """处理设置电源状态命令
        
        Args:
            power: 电源状态
            
        Returns:
            str: 操作结果
        """
        if power:
            return await self.handle_turn_on()
        else:
            return await self.handle_turn_off() 