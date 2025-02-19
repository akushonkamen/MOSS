# 错误码标准

**版本**: v1.0.0
**更新时间**: 2024-02-12
**相关文档**: 
- [核心服务标准](CoreService.md)
- [网络架构标准](NetworkArchitecture.md)
- [安全策略标准](SecurityPolicy.md)

## 1. 错误码体系

### 1.1 错误码格式

错误码采用5位数字格式：`ABBCC`
- A: 错误类型(1-9)
- BB: 模块ID(00-99)
- CC: 具体错误码(00-99)

### 1.2 错误类型(A)
- 1xxxx: 系统错误
- 2xxxx: 业务错误
- 3xxxx: 网络错误
- 4xxxx: 安全错误
- 5xxxx: 数据错误
- 6xxxx: 配置错误
- 7xxxx: 第三方服务错误
- 8xxxx: 用户错误
- 9xxxx: 其他错误

### 1.3 模块ID(BB)
- 00: 核心服务
- 01: 设备管理
- 02: 状态同步
- 03: 场景管理
- 04: LLM服务
- 05: 语音服务
- 06: 代理服务
- 07: 安全服务
- 08-99: 预留

## 2. 标准错误码

### 2.1 系统错误(1xxxx)
- 10000: 系统内部错误
- 10001: 服务未初始化
- 10002: 资源不足
- 10003: 并发限制
- 10004: 超时

### 2.2 业务错误(2xxxx)
- 20100: 设备未找到
- 20101: 设备离线
- 20102: 设备类型无效
- 20103: 功能不支持
- 20104: 参数无效

### 2.3 网络错误(3xxxx)
- 30000: 网络连接失败
- 30001: 服务不可用
- 30002: 请求超时
- 30003: 响应格式错误

### 2.4 安全错误(4xxxx)
- 40000: 认证失败
- 40001: 未授权访问
- 40002: 令牌过期
- 40003: 签名无效

### 2.5 数据错误(5xxxx)
- 50000: 数据不存在
- 50001: 数据格式错误
- 50002: 数据冲突
- 50003: 数据已存在

## 3. 错误处理机制

### 3.1 错误基类
```python
@dataclass
class ErrorResponse:
    """错误响应"""
    code: int           # 错误码
    message: str        # 错误消息
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 追踪ID

class BaseError(Exception):
    """错误基类"""
    def __init__(
        self,
        code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)
        
    def to_response(self) -> ErrorResponse:
        """转换为错误响应"""
        return ErrorResponse(
            code=self.code,
            message=self.message,
            details=self.details
        )
```

### 3.2 错误处理流程

1. 错误捕获
```python
try:
    # 业务逻辑
    pass
except BaseError as e:
    # 处理已知错误
    response = e.to_response()
except Exception as e:
    # 处理未知错误
    response = ErrorResponse(
        code=10000,
        message=str(e)
    )
```

2. 错误日志
```python
{
    "timestamp": "ISO8601",
    "level": "ERROR",
    "error_code": 10000,
    "message": "错误描述",
    "trace_id": "xxx",
    "details": {
        "stack": "错误堆栈",
        "context": "错误上下文"
    }
}
```

## 4. 版本历史

### v1.0.0 (2024-02-12)
- 初始版本
- 定义错误码体系
- 实现标准错误码
- 统一错误处理机制

### v0.9.0 (2024-02-07)
- 预发布版本
- 完成错误码设计
- 实现基础错误类

### v0.8.0 (2024-02-06)
- 草稿版本
- 开始错误码规范化 