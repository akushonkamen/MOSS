"""设备验证模块

提供设备信息的基本验证功能。
"""
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 验证规则常量
DEVICE_ID_PATTERN = r'^[a-z0-9][a-z0-9_-]{2,31}$'
DEVICE_NAME_MAX_LENGTH = 64
DEVICE_TYPE_PATTERN = r'^[a-z][a-z0-9_]{2,31}$'

@dataclass
class ValidationError:
    """验证错误"""
    field: str
    message: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)

class DeviceValidator:
    """设备验证器"""
    
    @staticmethod
    def validate_device_id(device_id: str) -> ValidationResult:
        """验证设备ID格式
        
        Args:
            device_id: 设备ID
            
        Returns:
            ValidationResult: 验证结果
        """
        if not re.match(DEVICE_ID_PATTERN, device_id):
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="device_id",
                    message="Invalid device ID format",
                    details={"pattern": DEVICE_ID_PATTERN}
                )]
            )
        return ValidationResult(is_valid=True)
    
    @staticmethod
    def validate_device_name(name: str) -> ValidationResult:
        """验证设备名称长度
        
        Args:
            name: 设备名称
            
        Returns:
            ValidationResult: 验证结果
        """
        if not name or len(name) > DEVICE_NAME_MAX_LENGTH:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="name",
                    message="Invalid device name length",
                    details={"max_length": DEVICE_NAME_MAX_LENGTH}
                )]
            )
        return ValidationResult(is_valid=True)
    
    @staticmethod
    def validate_device_type(device_type: str) -> ValidationResult:
        """验证设备类型格式
        
        Args:
            device_type: 设备类型
            
        Returns:
            ValidationResult: 验证结果
        """
        if not re.match(DEVICE_TYPE_PATTERN, device_type):
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="device_type",
                    message="Invalid device type format",
                    details={"pattern": DEVICE_TYPE_PATTERN}
                )]
            )
        return ValidationResult(is_valid=True)
    
    @classmethod
    def validate_device_info(cls, device_info: Dict[str, Any]) -> ValidationResult:
        """验证设备信息的基本格式
        
        Args:
            device_info: 设备信息字典
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        
        # 检查必需字段
        required_fields = {"device_type", "name", "capabilities"}
        missing_fields = required_fields - set(device_info.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="device_info",
                    message="Missing required fields",
                    details={"missing_fields": list(missing_fields)}
                )]
            )
            
        # 验证设备ID（如果提供）
        if "device_id" in device_info:
            result = cls.validate_device_id(device_info["device_id"])
            if not result.is_valid:
                errors.extend(result.errors)
                
        # 验证设备名称
        result = cls.validate_device_name(device_info["name"])
        if not result.is_valid:
            errors.extend(result.errors)
            
        # 验证设备类型格式
        result = cls.validate_device_type(device_info["device_type"])
        if not result.is_valid:
            errors.extend(result.errors)
                
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        ) 