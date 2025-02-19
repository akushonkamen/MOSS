"""自定义错误类

定义系统中使用的自定义错误类。
"""

class MossError(Exception):
    """Moss系统基础错误类"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AdaptorError(MossError):
    """适配器错误"""
    pass

class ValidationError(MossError):
    """验证错误"""
    pass

class APIGenerationError(MossError):
    """API生成错误"""
    pass

class DeviceError(MossError):
    """设备错误"""
    pass

class ConfigError(MossError):
    """配置错误"""
    pass

class NetworkError(MossError):
    """网络错误"""
    pass

class AuthenticationError(MossError):
    """认证错误"""
    pass

class AuthorizationError(MossError):
    """授权错误"""
    pass

class DatabaseError(MossError):
    """数据库错误"""
    pass

class CacheError(MossError):
    """缓存错误"""
    pass

class EventError(MossError):
    """事件错误"""
    pass

class TimeoutError(MossError):
    """超时错误"""
    pass

class ResourceNotFoundError(MossError):
    """资源未找到错误"""
    pass

class ResourceExistsError(MossError):
    """资源已存在错误"""
    pass

class InvalidOperationError(MossError):
    """无效操作错误"""
    pass 