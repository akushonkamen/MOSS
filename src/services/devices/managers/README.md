# 设备管理器

本目录包含设备管理系统的核心管理器实现，负责设备的生命周期管理、状态管理和统一控制。

## 组件说明

- `device_manager.py`: 设备管理器
  - 设备注册和注销
  - 设备发现
  - 设备分组管理
  - 设备事件处理

- `state_manager.py`: 状态管理器
  - 状态存储和验证
  - 状态变更通知
  - 状态历史记录
  - 状态持久化

- `unified_device_manager.py`: 统一设备管理器
  - 提供统一的设备管理接口
  - 设备注册和发现
  - 设备状态管理
  - 设备分组管理
  - 设备事件处理

## 使用说明

1. 所有管理器都实现为单例模式
2. 通过全局实例访问管理器功能
3. 支持异步操作
4. 提供事件订阅机制

## 示例

```python
from devices.managers import (
    device_manager,
    state_manager,
    unified_device_manager
)

# 注册设备
await unified_device_manager.register_device(device)

# 获取设备状态
state = await state_manager.get_state(device_id)

# 创建设备分组
await device_manager.create_group("客厅设备")
``` 