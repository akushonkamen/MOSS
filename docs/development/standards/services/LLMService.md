# LLM服务标准

**版本**: v1.0.0
**更新时间**: 2024-02-12
**相关文档**: 
- [核心服务标准](../core/CoreService.md)
- [代理模块标准](../agents/AgentModule.md)
- [代理调度标准](../agents/AgentDispatch.md)
- [安全策略标准](../core/SecurityPolicy.md)
- [错误码标准](../core/ErrorCodes.md)

## 1. 设计目标

- **智能理解**：准确理解用户意图和命令语义
- **一致性**：保持对话上下文的连贯性和一致性
- **可扩展性**：支持多种语言模型和服务接入
- **高性能**：确保快速响应和处理能力

---

## 2. 基本原则

### 2.1 服务配置
```python
@dataclass
class LLMConfig:
    """LLM服务配置"""
    api_url: str = "http://localhost:11434/api/generate"  # API地址
    model_name: str = "llama3.1:latest"                           # 模型名称
    temperature: float = 0.7                             # 温度参数
    max_tokens: int = 1000                               # 最大token数
    timeout: int = 30                                    # 超时时间
```

### 2.2 提示词模板
```python
class PromptTemplate:
    """提示词模板基类"""
    def build_prompt(self, **kwargs) -> str:
        """构建提示词"""
        pass

    def parse_response(self, response: str) -> Dict[str, Any]:
        """解析响应"""
        pass
```

### 2.3 意图模型
```python
@dataclass
class Intent:
    """意图模型"""
    device_name: str           # 设备名称
    action: str               # 动作名称
    parameters: Dict[str, Any] # 参数
    confidence: float         # 置信度
```

---

## 3. 开发规范

### 3.1 LLM服务接口
```python
class LLMService:
    async def initialize(self) -> None:
        """初始化服务"""
        pass

    async def chat(self, prompt: str) -> Optional[str]:
        """对话接口"""
        pass

    async def classify_device_type(
        self,
        device_info: Dict[str, Any],
        supported_types: List[str]
    ) -> Optional[str]:
        """设备类型识别"""
        pass

    async def map_device_functions(
        self,
        source_functions: Dict[str, Any],
        target_schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """设备功能映射"""
        pass

    async def understand_command(
        self,
        command: str,
        device_schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """命令理解"""
        pass
```

### 3.2 提示词管理
```python
class PromptManager:
    def get_prompt(self, prompt_type: str) -> PromptTemplate:
        """获取提示词模板"""
        pass

    def register_prompt(self, prompt_type: str, template: PromptTemplate) -> None:
        """注册提示词模板"""
        pass

    def remove_prompt(self, prompt_type: str) -> None:
        """移除提示词模板"""
        pass
```

---

## 4. 提示词工程

### 4.1 基本规范
- 清晰的指令说明
- 结构化的输出格式
- 适当的约束条件
- 必要的示例说明

### 4.2 模板示例
```python
COMMAND_UNDERSTANDING_PROMPT = """
请理解以下用户命令，并提取关键信息：

命令: {command}

请以JSON格式返回以下信息：
- device_name: 设备名称
- action: 动作名称
- parameters: 参数对象

示例输出：
{
    "device_name": "客厅灯",
    "action": "turn_on",
    "parameters": {
        "brightness": 80
    }
}
"""
```

---

## 5. 错误处理

### 5.1 错误类型
```python
class LLMError(BaseError):
    """LLM服务错误基类"""
    def __init__(self, code: int, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code, message, details)

class APIError(LLMError):
    """API调用错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(70000, message, details)  # 使用标准错误码

class ParseError(LLMError):
    """解析错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(50001, message, details)  # 使用标准错误码

class TimeoutError(LLMError):
    """超时错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(30002, message, details)  # 使用标准错误码
```

### 5.2 错误恢复
1. 重试机制
2. 降级策略
3. 超时处理

---

## 6. 性能优化

### 6.1 响应优化
- 流式处理
- 并发控制
- 缓存机制
- 批量处理

### 6.2 资源管理
- Token限制
- 并发限制
- 内存管理
- 超时控制

---

## 7. 测试规范

### 7.1 单元测试
- API调用测试
- 提示词测试
- 解析测试
- 错误处理测试

### 7.2 集成测试
- 端到端测试
- 性能测试
- 稳定性测试
- 并发测试

### 7.3 提示词测试
- 有效性测试
- 鲁棒性测试
- 边界测试
- 多样性测试

---

## 8. 日志规范

### 8.1 日志级别
- ERROR: 服务错误
- WARNING: 处理警告
- INFO: 状态变更
- DEBUG: 详细信息

### 8.2 日志格式
```python
{
    "timestamp": "ISO8601",
    "service": "llm",
    "event": "string",
    "level": "string",
    "message": "string",
    "details": {
        "prompt": "string",
        "response": "string",
        "processing_time": float
    }
}
```

---

## 9. 监控指标

### 9.1 性能指标
- 响应时间
- 处理成功率
- Token使用量
- API调用量

### 9.2 质量指标
- 理解准确率
- 解析成功率
- 错误率统计
- 超时率统计

---

## 10. 安全规范

### 10.1 数据安全
- 敏感信息过滤
- 数据脱敏
- 访问控制
- 日志脱敏

### 10.2 模型安全
- 输入验证
- 输出过滤
- 注入防护
- 越权防护

## 11. 版本历史

### v1.0.0 (2024-02-12)
- 初始版本
- 定义服务接口
- 实现提示词管理
- 建立错误处理
- 引入错误码标准
- 完善监控指标

### v0.9.0 (2024-02-07)
- 预发布版本
- 完成服务设计
- 实现基础功能
- 添加性能优化

### v0.8.0 (2024-02-06)
- 草稿版本
- 开始服务标准化
- 定义基本接口
- 设计数据结构