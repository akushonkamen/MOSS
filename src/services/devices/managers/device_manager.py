"""设备管理器

提供统一的设备管理接口。
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod

from ..validators import DeviceValidator, ValidationResult
from ..device_registry_server import DeviceInfo, DeviceStatus
from .state_manager import state_manager

logger = logging.getLogger(__name__)

class DeviceOperation:
    """设备操作类型"""
    QUERY = "query"           # 查询操作
    CONTROL = "control"       # 控制操作
    CONFIG = "config"         # 配置操作
    UPGRADE = "upgrade"       # 升级操作
    REBOOT = "reboot"         # 重启操作
    RESET = "reset"           # 重置操作

@dataclass
class OperationResult:
    """操作结果"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[int] = None

class DeviceManager(ABC):
    """设备管理器基类"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化管理器"""
        pass
        
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭管理器"""
        pass
        
    @abstractmethod
    async def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息"""
        pass
        
    @abstractmethod
    async def list_devices(self, 
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[DeviceInfo]:
        """列出设备"""
        pass
        
    @abstractmethod
    async def add_device(self, device_info: Dict[str, Any]) -> DeviceInfo:
        """添加设备"""
        pass
        
    @abstractmethod
    async def remove_device(self, device_id: str) -> None:
        """移除设备"""
        pass
        
    @abstractmethod
    async def update_device(self, device_id: str, updates: Dict[str, Any]) -> DeviceInfo:
        """更新设备信息"""
        pass
        
    @abstractmethod
    async def execute_operation(self,
        device_id: str,
        operation: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> OperationResult:
        """执行设备操作"""
        pass
        
    @abstractmethod
    async def get_device_status(self, device_id: str) -> str:
        """获取设备状态"""
        pass
        
    @abstractmethod
    async def set_device_status(self, device_id: str, status: str) -> None:
        """设置设备状态"""
        pass
        
    @abstractmethod
    async def get_device_metrics(self, device_id: str) -> Dict[str, Any]:
        """获取设备指标"""
        pass
        
    @abstractmethod
    async def validate_operation(self,
        device_id: str,
        operation: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """验证操作"""
        pass

class UnifiedDeviceManager(DeviceManager):
    """统一设备管理器实现"""
    
    def __init__(self):
        self._devices: Dict[str, DeviceInfo] = {}
        self._lock = asyncio.Lock()
        self._validator = DeviceValidator()
        self._metrics: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self) -> None:
        """初始化管理器"""
        logger.info("Initializing device manager")
        # TODO: 加载持久化的设备信息
        # TODO: 启动监控任务
        
    async def shutdown(self) -> None:
        """关闭管理器"""
        logger.info("Shutting down device manager")
        # TODO: 保存设备状态
        # TODO: 清理资源
        
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
        status: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[DeviceInfo]:
        """列出设备
        
        Args:
            device_type: 设备类型过滤
            status: 状态过滤
            location: 位置过滤
            
        Returns:
            List[DeviceInfo]: 设备列表
        """
        devices = list(self._devices.values())
        
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
        if status:
            devices = [d for d in devices if d.status == status]
        if location:
            devices = [d for d in devices if d.metadata.get("location") == location]
            
        return devices
        
    async def add_device(self, device_info: Dict[str, Any]) -> DeviceInfo:
        """添加设备
        
        Args:
            device_info: 设备信息
            
        Returns:
            DeviceInfo: 设备信息
            
        Raises:
            ValueError: 设备信息无效
        """
        # 验证设备信息
        validation_result = self._validator.validate_device_info(device_info)
        if not validation_result.is_valid:
            error_messages = [f"{e.field}: {e.message}" for e in validation_result.errors]
            raise ValueError(f"Invalid device information: {'; '.join(error_messages)}")
            
        device_id = device_info.get("device_id")
        if device_id:
            async with self._lock:
                if device_id in self._devices:
                    raise ValueError(f"Device ID already exists: {device_id}")
                    
        device = DeviceInfo(
            device_id=device_id or str(uuid.uuid4()),
            device_type=device_info["device_type"],
            name=device_info["name"],
            capabilities=device_info["capabilities"],
            status=DeviceStatus.REGISTERING,
            last_seen=datetime.now(),
            metadata=device_info.get("metadata", {})
        )
        
        async with self._lock:
            self._devices[device.device_id] = device
            device.status = DeviceStatus.ONLINE
            
        logger.info(f"Device added: {device.name} ({device.device_id})")
        return device
        
    async def remove_device(self, device_id: str) -> None:
        """移除设备
        
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
            if device_id in self._metrics:
                del self._metrics[device_id]
                
        logger.info(f"Device removed: {device_id}")
        
    async def update_device(self, device_id: str, updates: Dict[str, Any]) -> DeviceInfo:
        """更新设备信息
        
        Args:
            device_id: 设备ID
            updates: 更新信息
            
        Returns:
            DeviceInfo: 更新后的设备信息
            
        Raises:
            KeyError: 设备不存在
            ValueError: 更新信息无效
        """
        async with self._lock:
            if device_id not in self._devices:
                raise KeyError(f"Device not found: {device_id}")
                
            device = self._devices[device_id]
            
            # 验证更新字段
            if "name" in updates:
                result = self._validator.validate_device_name(updates["name"])
                if not result.is_valid:
                    raise ValueError(f"Invalid name: {result.errors[0].message}")
                device.name = updates["name"]
                
            if "capabilities" in updates:
                result = self._validator.validate_capabilities(
                    device.device_type,
                    updates["capabilities"]
                )
                if not result.is_valid:
                    raise ValueError(f"Invalid capabilities: {result.errors[0].message}")
                device.capabilities = updates["capabilities"]
                
            if "metadata" in updates:
                device.metadata.update(updates["metadata"])
                
            device.last_seen = datetime.now()
            
        logger.info(f"Device updated: {device_id}")
        return device
        
    async def execute_operation(self,
        device_id: str,
        operation: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> OperationResult:
        """执行设备操作
        
        Args:
            device_id: 设备ID
            operation: 操作类型
            parameters: 操作参数
            
        Returns:
            OperationResult: 操作结果
            
        Raises:
            KeyError: 设备不存在
            ValueError: 操作无效
        """
        # 验证操作
        validation_result = await self.validate_operation(device_id, operation, parameters)
        if not validation_result.is_valid:
            return OperationResult(
                success=False,
                message=validation_result.errors[0].message,
                error_code=400
            )
            
        try:
            # 获取设备信息和当前状态
            device = self._devices[device_id]
            current_state = await state_manager.get_state(device_id)
            
            # 导入专家代理（避免循环导入）
            from ...agents.expert_agent import expert_agent
            
            # 委托给专家代理执行操作
            operation_result = await expert_agent.execute_device_operation(
                device_id=device_id,
                device_type=device.device_type,
                operation=operation,
                parameters=parameters,
                current_state=current_state
            )
            
            if operation_result.success:
                # 更新设备状态
                await state_manager.update_state(
                    device_id=device_id,
                    new_state=operation_result.data["new_state"],
                    metadata={
                        "operation": operation,
                        "parameters": parameters,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
            return operation_result
            
        except Exception as e:
            logger.error(f"Error executing operation: {e}")
            return OperationResult(
                success=False,
                message=f"Operation execution failed: {str(e)}",
                error_code=500
            )
        
    async def get_device_status(self, device_id: str) -> str:
        """获取设备状态
        
        Args:
            device_id: 设备ID
            
        Returns:
            str: 设备状态
            
        Raises:
            KeyError: 设备不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"Device not found: {device_id}")
        return self._devices[device_id].status
        
    async def set_device_status(self, device_id: str, status: str) -> None:
        """设置设备状态
        
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
        
    async def get_device_metrics(self, device_id: str) -> Dict[str, Any]:
        """获取设备指标
        
        Args:
            device_id: 设备ID
            
        Returns:
            Dict[str, Any]: 设备指标
            
        Raises:
            KeyError: 设备不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"Device not found: {device_id}")
        return self._metrics.get(device_id, {})
        
    async def validate_operation(self,
        device_id: str,
        operation: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """验证操作
        
        Args:
            device_id: 设备ID
            operation: 操作类型
            parameters: 操作参数
            
        Returns:
            ValidationResult: 验证结果
        """
        if device_id not in self._devices:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="device_id",
                    message="Device not found",
                    details={"device_id": device_id}
                )]
            )
            
        if operation not in vars(DeviceOperation).values():
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="operation",
                    message="Invalid operation",
                    details={
                        "operation": operation,
                        "supported_operations": list(vars(DeviceOperation).values())
                    }
                )]
            )
            
        device = self._devices[device_id]
        if device.status != DeviceStatus.ONLINE:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="status",
                    message="Device is not online",
                    details={"current_status": device.status}
                )]
            )
            
        # TODO: 实现具体的操作参数验证逻辑
        return ValidationResult(is_valid=True)

# 创建管理器实例
device_manager = UnifiedDeviceManager() 