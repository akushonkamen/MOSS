"""设备服务器基类

提供设备服务器的基础功能，包括：
1. 设备状态管理
2. 设备操作处理
3. 事件通知
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
import asyncio
import logging
from .device_base import Device, DeviceStatus, DeviceError

class DeviceServer(Device):
    """设备服务器基类"""
    
    def __init__(self, device_id: str, name: str, location: str, port: int):
        """初始化设备服务器
        
        Args:
            device_id: 设备ID
            name: 设备名称
            location: 设备位置
            port: 服务器端口
        """
        super().__init__(device_id, name, location)
        self.port = port
        self._state: Dict[str, Any] = {}
        self._handlers: Dict[str, List[Callable]] = {}
        self._server = None
        
    async def initialize(self) -> None:
        """初始化服务器"""
        try:
            # 获取初始状态
            self._state = await self.get_initial_state()
            
            # 注册到统一设备管理器
            from ..managers.unified_device_manager import unified_device_manager
            if await unified_device_manager.register_device(self):
                # 启动服务器
                await self.start()
                self.status = DeviceStatus.ONLINE
                self.logger.info(f"设备服务器 {self.name} 初始化完成")
            else:
                raise DeviceError(f"设备 {self.name} 注册失败")
                
        except Exception as e:
            self.status = DeviceStatus.ERROR
            self.logger.error(f"设备服务器 {self.name} 初始化失败: {str(e)}")
            raise DeviceError(f"初始化失败: {str(e)}")
            
    async def start(self) -> None:
        """启动服务器"""
        try:
            # 创建服务器
            self._server = await asyncio.start_server(
                self._handle_client,
                '0.0.0.0',  # 监听所有网络接口
                self.port
            )
            
            # 启动服务器
            asyncio.create_task(self._server.serve_forever())
            self.logger.info(f"设备服务器 {self.name} 启动成功，监听端口 {self.port}")
            
        except Exception as e:
            self.logger.error(f"设备服务器 {self.name} 启动失败: {str(e)}")
            raise DeviceError(f"启动失败: {str(e)}")
            
    async def stop(self) -> None:
        """停止服务器"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self.status = DeviceStatus.OFFLINE
            self.logger.info(f"设备服务器 {self.name} 已停止")
            
    async def get_state(self) -> Dict[str, Any]:
        """获取设备状态"""
        return self._state.copy()
        
    async def set_state(self, state: Dict[str, Any]) -> bool:
        """设置设备状态
        
        Args:
            state: 新的状态
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 验证状态
            await self._validate_state(state)
            
            # 更新状态
            old_state = self._state.copy()
            self._state.update(state)
            
            # 通知状态变更
            await self._notify_state_change(old_state, self._state)
            
            return True
            
        except Exception as e:
            self.logger.error(f"设置设备 {self.name} 状态失败: {str(e)}")
            return False
            
    @abstractmethod
    async def get_initial_state(self) -> Dict[str, Any]:
        """获取初始状态"""
        pass
        
    @abstractmethod
    async def _validate_state(self, state: Dict[str, Any]) -> None:
        """验证状态
        
        Args:
            state: 要验证的状态
            
        Raises:
            DeviceError: 状态无效
        """
        pass
        
    async def _notify_state_change(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> None:
        """通知状态变更
        
        Args:
            old_state: 旧状态
            new_state: 新状态
        """
        # 更新设备状态
        from ..managers.unified_device_manager import unified_device_manager
        await unified_device_manager.update_device_state(
            self.device_id,
            new_state
        )
        
        # 调用状态变更处理器
        handlers = self._handlers.get("state_change", [])
        for handler in handlers:
            try:
                await handler(old_state, new_state)
            except Exception as e:
                self.logger.error(f"调用状态变更处理器失败: {str(e)}")
                
    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """处理客户端连接
        
        Args:
            reader: 读取器
            writer: 写入器
        """
        try:
            while True:
                # 读取命令
                data = await reader.read(1024)
                if not data:
                    break
                    
                # 解析命令
                command = data.decode()
                self.logger.debug(f"收到命令: {command}")
                
                # 处理命令
                response = await self._handle_command(command)
                
                # 发送响应
                writer.write(response.encode())
                await writer.drain()
                
        except Exception as e:
            self.logger.error(f"处理客户端连接失败: {str(e)}")
        finally:
            writer.close()
            await writer.wait_closed()
            
    @abstractmethod
    async def _handle_command(self, command: str) -> str:
        """处理命令
        
        Args:
            command: 命令字符串
            
        Returns:
            str: 响应字符串
        """
        pass
        
    def add_handler(self, event: str, handler: Callable) -> None:
        """添加事件处理器
        
        Args:
            event: 事件名称
            handler: 处理器函数
        """
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
        
    def remove_handler(self, event: str, handler: Callable) -> None:
        """移除事件处理器
        
        Args:
            event: 事件名称
            handler: 处理器函数
        """
        if event in self._handlers:
            self._handlers[event].remove(handler)