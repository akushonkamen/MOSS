# 设备状态管理系统设计文档

## 1. 系统概述

设备状态管理系统提供了一个统一的接口来管理智能设备的状态，包括状态存储、验证、转换和历史记录等功能。系统采用Redis作为后端存储，支持异步操作和事件通知机制。

### 1.1 主要功能

- 状态存储和查询
- 状态验证和类型检查
- 状态转换规则管理
- 状态历史记录
- 事件通知机制
- 并发状态更新

### 1.2 技术栈

- Python 3.10+
- Redis
- asyncio
- Pydantic
- pytest

## 2. 核心组件

### 2.1 状态管理器 (DeviceStateManager)

状态管理器是系统的核心组件，负责协调各个功能模块的工作。

```python
from src.services.devices.state_manager import DeviceStateManager

# 创建状态管理器实例
manager = DeviceStateManager(
    redis_url="redis://localhost",
    max_history=1000,
    state_ttl=86400,
    cache_ttl=60,  # 状态缓存时间
    sync_interval=1  # 状态同步间隔
)
```

主要方法：

- `get_state(device_id)`: 获取设备当前状态
- `set_state(device_id, device_type, state)`: 设置设备状态
- `get_history(device_id)`: 获取状态历史记录
- `register_validator(device_type, validator)`: 注册状态验证器
- `register_transition(device_type, transition)`: 注册状态转换规则
- `subscribe(device_id, callback)`: 订阅状态事件
- `unsubscribe(device_id, callback)`: 取消订阅
- `get_cached_state(device_id)`: 获取缓存的状态
- `update_cache(device_id, state)`: 更新状态缓存
- `sync_states()`: 同步所有设备状态

### 2.2 状态验证器 (StateValidator)

状态验证器负责检查设备状态的有效性，每种设备类型都有其特定的验证规则。

```python
from src.services.devices.validators import LightValidator

# 注册灯光设备验证器
manager.register_validator(
    "light",
    LightValidator(device_type="light", rules={})
)
```

内置验证器：

- `LightValidator`: 验证灯光设备状态
- `ACValidator`: 验证空调设备状态
- `CurtainValidator`: 验证窗帘设备状态

### 2.3 状态转换规则 (StateTransition)

状态转换规则定义了设备状态变化的合法性条件。

```python
from src.services.devices.transitions import StateTransition

# 注册状态转换规则
transition = StateTransition(
    from_state={"power": "off"},
    to_state={"power": "on"},
    conditions=[check_function],
    priority=1
)
manager.register_transition("light", transition)
```

## 3. 状态定义

### 3.1 灯光设备

```python
{
    "power": "on" | "off" | "dimming",
    "brightness": 0-100,
    "color_temp": 2700-6500,  # 可选
    "rgb": [0-255, 0-255, 0-255]  # 可选
}
```

### 3.2 空调设备

```python
{
    "power": true | false,
    "mode": "cool" | "heat" | "auto" | "dry" | "fan",
    "temperature": 16-30,
    "fan_speed": 1-5,  # 可选
    "swing": true | false  # 可选
}
```

### 3.3 窗帘设备

```python
{
    "state": "open" | "closed" | "opening" | "closing" | "stopped",
    "position": 0-100,
    "speed": 1-3  # 可选
}
```

## 4. 使用示例

### 4.1 基本使用

```python
# 设置设备状态
await manager.set_state(
    "light1",
    "light",
    {
        "power": "on",
        "brightness": 80
    }
)

# 获取设备状态
state = await manager.get_state("light1")

# 获取历史记录
history = await manager.get_history("light1")
```

### 4.2 事件订阅

```python
async def on_state_change(device_id, event, data):
    print(f"设备 {device_id} 状态变化: {event}")
    print(f"新状态: {data}")

# 订阅状态事件
manager.subscribe("light1", on_state_change)

# 取消订阅
manager.unsubscribe("light1", on_state_change)
```

## 5. 最佳实践

### 5.1 状态验证

- 始终为每种设备类型定义明确的状态验证规则
- 验证规则应包括：
  - 必需字段检查
  - 字段类型检查
  - 取值范围检查
  - 字段间关系检查
  - JSON序列化验证

### 5.2 状态转换

- 定义清晰的状态转换路径
- 为关键状态转换添加条件检查
- 使用优先级管理复杂的转换规则
- 避免循环转换
- 确保状态转换的原子性

### 5.3 错误处理

- 捕获并处理所有可能的异常
- 提供详细的错误信息
- 使用自定义异常类型
- 记录错误日志
- 实现错误恢复机制

### 5.4 性能优化

- 使用Redis pipeline减少网络往返
- 合理设置TTL避免数据无限增长
- 限制历史记录数量
- 使用异步操作提高并发性能
- 实现状态缓存机制
- 优化状态同步策略
- 使用批量操作减少开销

### 5.5 测试

- 编写完整的单元测试
- 测试异常情况
- 测试并发操作
- 测试性能和负载
- 测试状态同步机制
- 测试缓存一致性
- 测试错误恢复

## 6. 注意事项

1. Redis连接管理
   - 正确配置连接参数
   - 及时关闭不再使用的连接
   - 处理连接异常

2. 状态一致性
   - 使用事务确保原子性
   - 验证状态完整性
   - 处理并发冲突

3. 内存管理
   - 设置合理的TTL
   - 定期清理过期数据
   - 监控内存使用

4. 安全性
   - 验证输入数据
   - 限制状态大小
   - 保护敏感信息

## 7. 常见问题

### 7.1 状态验证失败

可能原因：
- 缺少必需字段
- 字段类型错误
- 值超出范围
- 字段间关系不符合要求
- JSON序列化失败

解决方法：
- 检查状态数据格式
- 查看验证器日志
- 确保所有必需字段都存在
- 检查字段值是否在有效范围内
- 验证JSON序列化结果

### 7.2 状态转换失败

可能原因：
- 当前状态不支持目标转换
- 转换条件不满足
- 状态冲突
- 并发更新冲突

解决方法：
- 检查转换规则定义
- 确保满足所有转换条件
- 避免并发更新冲突
- 实现乐观锁机制

### 7.3 性能问题

可能原因：
- 状态更新过于频繁
- 缓存失效率高
- 同步开销大
- 历史记录过多

解决方法：
- 优化更新频率
- 调整缓存策略
- 使用批量同步
- 清理过期数据

### 7.4 并发控制

可能原因：
- 多客户端同时更新
- 状态覆盖
- 死锁
- 数据不一致

解决方法：
- 使用乐观锁
- 实现原子操作
- 避免长时间锁定
- 定期状态校验

## 8. 未来改进

1. 功能增强
   - 支持更多设备类型
   - 添加批量操作接口
   - 实现状态回滚机制
   - 增加状态统计功能

2. 性能优化
   - 引入缓存机制
   - 优化并发处理
   - 实现分布式部署
   - 添加性能监控

3. 可用性提升
   - 增加健康检查
   - 完善错误处理
   - 添加监控告警
   - 优化日志系统

4. 开发体验
   - 提供更多示例代码
   - 完善开发文档
   - 添加调试工具
   - 简化配置过程 