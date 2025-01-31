# MOSS 系统架构设计文档

## 1. 项目结构
```
moss/
├── src/
│   ├── core/                    # 核心功能模块
│   │   ├── config.py           # 配置管理
│   │   ├── security.py         # 安全相关
│   │   └── exceptions.py       # 自定义异常
│   │
│   ├── api/                    # API 接口层
│   │   ├── v1/                # API版本1
│   │   │   ├── endpoints/     # API端点
│   │   │   └── dependencies/  # 依赖注入
│   │   └── websocket/        # WebSocket处理
│   │
│   ├── services/              # 业务服务层
│   │   ├── stt/              # 语音识别服务
│   │   ├── tts/              # 语音合成服务
│   │   ├── llm/              # LLM服务
│   │   └── device/           # 设备控制服务
│   │
│   ├── models/               # 数据模型
│   │   ├── domain/          # 领域模型
│   │   └── schemas/         # Pydantic模型
│   │
│   ├── db/                  # 数据库相关
│   │   ├── repositories/    # 数据访问层
│   │   └── migrations/      # 数据库迁移
│   │
│   └── utils/               # 工具函数
│
├── tests/                   # 测试目录
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   └── e2e/               # 端到端测试
│
├── docs/                   # 文档
│   ├── api/               # API文档
│   ├── development/       # 开发文档
│   └── deployment/        # 部署文档
│
├── scripts/               # 工具脚本
├── pyproject.toml        # 项目依赖配置
├── .env.example          # 环境变量示例
└── README.md             # 项目说明
```

## 2. 核心模块设计

### 2.1 语音识别模块 (STT)
- 接口定义：`src/services/stt/interface.py`
- 实现类：`src/services/stt/whisper_service.py`
- 职责：
  - 音频预处理
  - Whisper模型调用
  - 结果后处理

### 2.2 LLM推理模块
- 接口定义：`src/services/llm/interface.py`
- 实现类：`src/services/llm/deepseek_service.py`
- 职责：
  - Ollama API封装
  - 提示词管理
  - 结果解析

### 2.3 设备控制模块
- 接口定义：`src/services/device/interface.py`
- 实现类：
  - `src/services/device/mqtt_controller.py`
  - `src/services/device/http_controller.py`
- 职责：
  - 设备指令转换
  - 协议适配
  - 状态管理

### 2.4 语音合成模块 (TTS)
- 接口定义：`src/services/tts/interface.py`
- 实现类：`src/services/tts/coqui_service.py`
- 职责：
  - 文本预处理
  - TTS模型调用
  - 音频缓存管理

## 3. 接口设计

### 3.1 REST API
- 语音识别：`POST /api/v1/stt`
- 语音合成：`POST /api/v1/tts`
- 设备控制：`POST /api/v1/device/{device_id}/control`

### 3.2 WebSocket
- 实时状态更新：`/ws/device-status`
- 双向通信：`/ws/chat`

## 4. 数据模型

### 4.1 核心模型
```python
# 用户指令
class Command(BaseModel):
    action: str
    target: str
    parameters: Dict[str, Any]
    
# 设备状态
class DeviceState(BaseModel):
    device_id: str
    status: str
    last_updated: datetime
```

## 5. 安全设计

### 5.1 认证机制
- JWT token认证
- WebSocket连接验证
- API访问限制

### 5.2 数据安全
- 传输加密 (TLS)
- 敏感数据脱敏
- 审计日志

## 6. 性能优化

### 6.1 缓存策略
- Redis缓存层
- 模型预热
- 音频缓存

### 6.2 异步处理
- Celery任务队列
- 异步IO操作
- 并发控制

## 7. 测试策略

### 7.1 单元测试
- 模块隔离测试
- Mock外部依赖
- 参数边界测试

### 7.2 集成测试
- API端点测试
- 服务间交互测试
- 数据流测试

### 7.3 端到端测试
- 完整流程测试
- 性能测试
- 负载测试

## 8. 监控告警

### 8.1 系统监控
- 服务健康检查
- 资源使用监控
- 性能指标采集

### 8.2 业务监控
- 用户行为分析
- 错误率监控
- 响应时间监控

## 9. 部署方案

### 9.1 开发环境
- Docker Compose
- 本地开发配置
- 调试工具

### 9.2 生产环境
- Kubernetes集群
- 自动扩缩容
- 灾备方案 