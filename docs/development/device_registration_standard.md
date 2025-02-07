# MOSS 设备注册标准

## 1. 设备注册流程

### 1.1 基本流程
1. 设备发现
2. 能力声明
3. 状态初始化
4. 注册确认
5. 开始服务

### 1.2 智能体交互流程
1. 向AgentDispatchCenter注册设备能力
2. 获取设备控制智能体
3. 建立设备状态监听
4. 配置处理管道
5. 启动服务

## 2. 设备能力声明

### 2.1 基本信息
```json
{
    "device_id": "string",
    "device_name": "string",
    "device_type": "string",
    "manufacturer": "string",
    "model": "string",
    "firmware_version": "string"
}
```

### 2.2 智能体交互能力
```json
{
    "agent_capabilities": {
        "decoder_support": true,
        "expert_support": true,
        "memory_support": false,
        "learner_support": false,
        "supported_pipelines": [
            "basic_control",
            "status_query",
            "scene_control"
        ],
        "custom_agents": []
    }
}
```

### 2.3 控制能力
```json
{
    "control_capabilities": {
        "operations": [
            {
                "name": "string",
                "description": "string",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ],
        "states": [
            {
                "name": "string",
                "type": "string",
                "readable": true,
                "writable": true
            }
        ]
    }
}
```

## 3. 设备注册接口

### 3.1 注册请求
```http
POST /api/v1/devices/register
Content-Type: application/json

{
    "basic_info": {},
    "agent_capabilities": {},
    "control_capabilities": {}
}
```

### 3.2 注册响应
```json
{
    "success": true,
    "device_token": "string",
    "assigned_agents": [
        {
            "agent_id": "string",
            "agent_type": "string",
            "pipeline_id": "string"
        }
    ],
    "error": null
}
```

## 4. 设备状态管理

### 4.1 状态上报
```json
{
    "device_id": "string",
    "timestamp": "string",
    "states": {},
    "metrics": {}
}
```

### 4.2 智能体状态同步
```json
{
    "device_id": "string",
    "agent_states": [
        {
            "agent_id": "string",
            "status": "string",
            "metrics": {}
        }
    ]
}
```

## 5. 设备控制标准

### 5.1 控制请求
```json
{
    "device_id": "string",
    "operation": "string",
    "parameters": {},
    "pipeline_id": "string"
}
```

### 5.2 控制响应
```json
{
    "success": true,
    "result": {},
    "error": null,
    "agent_feedback": [
        {
            "agent_id": "string",
            "feedback": {}
        }
    ]
}
```

## 6. 错误处理

### 6.1 错误码定义
- 1000: 注册失败
- 1001: 能力不支持
- 1002: 智能体不可用
- 1003: 管道配置失败
- 1004: 状态同步失败

### 6.2 错误响应格式
```json
{
    "error_code": "number",
    "error_message": "string",
    "error_details": {},
    "recovery_suggestion": "string"
}
```

## 7. 安全要求

### 7.1 认证要求
- 设备身份认证
- 通信加密
- 令牌管理
- 权限控制

### 7.2 数据安全
- 数据加密
- 隐私保护
- 访问控制
- 审计日志

## 8. 性能要求

### 8.1 响应时间
- 注册响应: < 1s
- 状态同步: < 100ms
- 控制执行: < 200ms
- 错误恢复: < 500ms

### 8.2 并发处理
- 支持多设备并发
- 支持多管道并发
- 支持多智能体并发
- 负载均衡

## 9. 可靠性要求

### 9.1 故障恢复
- 自动重连
- 状态恢复
- 管道重建
- 智能体重启

### 9.2 监控要求
- 心跳检测
- 性能监控
- 错误监控
- 状态监控

## 10. 版本管理

### 10.1 版本兼容性
- 向后兼容
- 版本协商
- 能力降级
- 平滑升级

### 10.2 升级流程
1. 版本检查
2. 能力协商
3. 配置更新
4. 重新注册
5. 服务迁移

## 11. 测试要求

### 11.1 注册测试
- 基本流程测试
- 异常流程测试
- 性能测试
- 安全测试

### 11.2 智能体测试
- 能力验证
- 管道测试
- 并发测试
- 恢复测试

## 12. 文档要求

### 12.1 设备文档
- 能力说明
- 接口文档
- 示例代码
- 故障排除

### 12.2 集成文档
- 集成指南
- 测试用例
- 最佳实践
- 常见问题 