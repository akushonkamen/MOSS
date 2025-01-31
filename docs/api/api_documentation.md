# MOSS API 文档

## 基础信息

- 基础URL: `http://localhost:8000`
- API版本: v1
- 认证方式: JWT Bearer Token

## 认证

### 获取访问令牌

```http
POST /api/v1/auth/token
```

请求体：
```json
{
  "username": "string",
  "password": "string"
}
```

响应：
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

## 语音识别 (STT)

### 上传音频文件进行识别

```http
POST /api/v1/stt
```

请求：
- Content-Type: `multipart/form-data`
- Body:
  - `audio_file`: 音频文件 (支持格式: wav, mp3, ogg)
  - `language`: 语言代码 (可选，默认: "zh")

响应：
```json
{
  "text": "识别出的文本",
  "confidence": 0.95,
  "language": "zh"
}
```

### 流式语音识别

```websocket
WS /ws/stt
```

消息格式：
```json
{
  "type": "audio_chunk",
  "data": "base64编码的音频数据",
  "language": "zh"
}
```

响应流：
```json
{
  "type": "partial_result",
  "text": "部分识别结果"
}
```

最终响应：
```json
{
  "type": "final_result",
  "text": "完整识别结果",
  "confidence": 0.95
}
```

## 语义理解

### 处理文本指令

```http
POST /api/v1/understand
```

请求体：
```json
{
  "text": "打开客厅的灯",
  "context": {
    "user_id": "string",
    "location": "string",
    "timestamp": "string"
  }
}
```

响应：
```json
{
  "action": "device_control",
  "target": {
    "type": "light",
    "location": "客厅"
  },
  "command": "on",
  "confidence": 0.95
}
```

## 设备控制

### 执行设备指令

```http
POST /api/v1/device/{device_id}/control
```

请求体：
```json
{
  "command": "on",
  "parameters": {
    "brightness": 80,
    "color": "warm"
  }
}
```

响应：
```json
{
  "status": "success",
  "device_id": "string",
  "state": {
    "power": "on",
    "brightness": 80,
    "color": "warm"
  }
}
```

### 获取设备状态

```http
GET /api/v1/device/{device_id}/status
```

响应：
```json
{
  "device_id": "string",
  "type": "light",
  "location": "客厅",
  "state": {
    "power": "on",
    "brightness": 80,
    "color": "warm"
  },
  "last_updated": "2024-01-30T12:00:00Z"
}
```

### 设备状态实时更新

```websocket
WS /ws/device-status
```

消息格式：
```json
{
  "type": "status_update",
  "device_id": "string",
  "state": {
    "power": "on",
    "brightness": 80
  }
}
```

## 语音合成 (TTS)

### 文本转语音

```http
POST /api/v1/tts
```

请求体：
```json
{
  "text": "要转换的文本",
  "voice_id": "string",
  "speed": 1.0,
  "pitch": 1.0
}
```

响应：
- Content-Type: `audio/wav`
- Body: 音频文件数据

### 流式语音合成

```websocket
WS /ws/tts
```

请求：
```json
{
  "text": "要转换的文本",
  "voice_id": "string",
  "speed": 1.0
}
```

响应流：
```json
{
  "type": "audio_chunk",
  "data": "base64编码的音频数据",
  "is_last": false
}
```

## 错误处理

所有API端点在发生错误时都会返回一个标准的错误响应：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {
      "field": "额外的错误信息"
    }
  }
}
```

### 常见错误代码

| 错误代码 | HTTP状态码 | 描述 |
|---------|-----------|------|
| UNAUTHORIZED | 401 | 未认证或token无效 |
| FORBIDDEN | 403 | 权限不足 |
| NOT_FOUND | 404 | 资源不存在 |
| VALIDATION_ERROR | 422 | 请求参数验证失败 |
| STT_ERROR | 500 | 语音识别失败 |
| TTS_ERROR | 500 | 语音合成失败 |
| DEVICE_ERROR | 500 | 设备控制失败 |

## 速率限制

- 默认限制：60次请求/分钟/IP
- 超出限制时返回429状态码
- 响应头包含：
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

## WebSocket连接管理

1. 建立连接时需要提供JWT token作为查询参数：
```
ws://localhost:8000/ws/stt?token=your_jwt_token
```

2. 心跳要求：
- 客户端需要每30秒发送一次ping
- 服务器会响应pong
- 60秒内未收到ping则断开连接

3. 重连策略：
- 指数退避重连
- 最大重试间隔：30秒
- 最大重试次数：5次

# 语音识别服务 API

## WebSocket 语音识别

### 端点
`ws://localhost:8000/ws/chat`

### 请求格式
```json
{
    "type": "audio",
    "data": "音频数据（十六进制字符串）",
    "temperature": 0.7
}
```

### 智能语音检测参数
录音器支持以下可配置参数：
- `silence_threshold`: 静音检测阈值（默认：0.03）
- `silence_duration`: 静音持续时间（默认：1.0秒）
- `max_duration`: 最大录音时间（默认：10.0秒）
- `min_duration`: 最小录音时间（默认：1.0秒）

### 响应格式
```json
{
    "type": "status",
    "content": "录音状态信息"
}
```
或
```json
{
    "type": "llm_response",
    "content": "语音识别结果"
}
```

### 错误处理
- 输入溢出：系统会自动跳过溢出的数据块并继续录音
- 设备错误：自动选择可用的音频输入设备
- 连接断开：支持自动重连机制

### 示例代码
```python
recorder = AudioRecorder(
    silence_threshold=0.03,    # 静音阈值
    silence_duration=1.0,      # 静音持续1秒后停止
    max_duration=10.0,         # 最长录音10秒
    min_duration=1.0           # 最短录音1秒
)
```

# 其他API文档 