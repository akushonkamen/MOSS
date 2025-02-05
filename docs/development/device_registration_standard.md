# 智能家居设备注册标准

## 1. 设备标识

### 1.1 设备ID
- 格式: 只能包含字母、数字、下划线和连字符
- 长度: 建议不超过32个字符
- 唯一性: 在系统内必须唯一
- 示例: `light_001`, `ac_001`, `curtain_001`

### 1.2 设备名称
- 长度: 不超过32个字符
- 可读性: 应该具有描述性和可读性
- 示例: "客厅灯", "卧室空调"

## 2. 设备元数据

### 2.1 基本信息
```python
{
    "manufacturer": "制造商名称",
    "model": "设备型号",
    "firmware": "固件版本",
    "protocol": "通信协议版本"
}
```

### 2.2 设备能力
支持的能力类型：
- `power`: 电源控制
- `brightness`: 亮度控制
- `temperature`: 温度控制
- `mode`: 模式控制
- `position`: 位置控制
- `schedule`: 定时控制
- `scene`: 场景控制
- `voice`: 语音控制

## 3. 设备参数

### 3.1 参数定义
每个参数必须包含：
- `type`: 参数类型 (boolean/integer/float/string)
- `description`: 参数描述
- `current_value`: 当前值
- `min_value`: 最小值（可选）
- `max_value`: 最大值（可选）
- `unit`: 单位（可选）
- `enum_values`: 枚举值列表（可选）

### 3.2 标准参数范围
- 亮度: 0-100%
- 温度: 16-30°C
- 位置: 0-100%
- 端口: 1024-65535

## 4. 设备分组

### 4.1 分组信息
```python
{
    "group_id": "分组ID",
    "name": "分组名称",
    "location": "位置信息",
    "devices": ["设备ID列表"]
}
```

### 4.2 分组规则
- 一个设备可以属于一个分组
- 分组ID必须唯一
- 分组名称应具有描述性

## 5. 状态报告

### 5.1 状态信息
```python
{
    "timestamp": "状态更新时间",
    "online": true/false,
    "error": "错误信息（可选）",
    "parameters": {
        "参数名": "参数值"
    },
    "metrics": {
        "cpu_usage": "CPU使用率",
        "memory_usage": "内存使用率",
        "network_latency": "网络延迟",
        "signal_strength": "信号强度",
        "uptime": "运行时间"
    }
}
```

### 5.2 状态更新要求
- 定期更新: 建议每60秒更新一次
- 事件触发: 状态变化时立即更新
- 错误报告: 发生错误时必须更新状态

## 6. 安全要求

### 6.1 通信安全
- 必须使用TLS/SSL加密通信
- 支持设备认证机制
- 实现访问控制策略

### 6.2 数据安全
- 敏感数据加密存储
- 实现数据完整性校验
- 提供安全的配置管理

## 7. 注册流程

### 7.1 设备注册步骤
1. 准备设备信息
2. 验证设备参数
3. 注册设备到系统
4. 加入设备分组（可选）
5. 开始状态报告

### 7.2 注册验证
- 验证设备ID格式
- 验证设备名称长度
- 验证端口号范围
- 验证必要参数

## 8. 示例代码

### 8.1 设备注册
```python
registration = DeviceRegistrationValidation(
    device_id="light_001",
    name="客厅灯",
    type="light",
    port=8001,
    metadata=DeviceMetadata(
        manufacturer="智能家居公司",
        model="SL-001",
        firmware="1.0.0",
        protocol="1.0",
        capabilities=["power", "brightness"]
    )
)

device_info = await registry.register_device(registration)
```

### 8.2 状态更新
```python
status = DeviceStatusReport(
    timestamp=datetime.now(),
    online=True,
    parameters={
        "power": True,
        "brightness": 80
    },
    metrics=DeviceMetrics(
        cpu_usage=10.5,
        memory_usage=25.0,
        network_latency=50.0,
        signal_strength=-65,
        uptime=3600
    )
)

await registry.update_device_status("light_001", status)
```

## 9. 错误处理

### 9.1 错误类型
- 设备ID重复
- 参数验证失败
- 设备离线
- 通信超时
- 认证失败

### 9.2 错误响应
- 提供详细的错误信息
- 记录错误日志
- 实现错误恢复机制

## 10. 维护要求

### 10.1 日志记录
- 记录设备注册事件
- 记录状态变更
- 记录错误信息
- 记录安全事件

### 10.2 监控告警
- 设备离线告警
- 性能指标告警
- 安全事件告警
- 错误率监控 