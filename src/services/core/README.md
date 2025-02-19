# 核心服务组件

此目录包含了系统的核心服务组件，提供基础设施和核心功能支持。

## 组件说明

- `smart_home.py`: 智能工业AI核心逻辑
  - 设备控制流程
  - 场景管理
  - 状态同步

- `entity.py`: 实体定义
  - 基础实体类型
  - 实体属性管理
  - 实体关系定义

- `event_bus.py`: 事件总线
  - 事件发布/订阅
  - 事件路由
  - 异步事件处理

- `service_registry.py`: 服务注册表
  - 服务注册和发现
  - 服务生命周期管理
  - 服务依赖管理

## 开发规范

1. 核心组件应该保持高内聚、低耦合
2. 提供清晰的接口定义和文档
3. 实现完整的错误处理和日志记录
4. 支持异步操作和并发处理
5. 遵循依赖注入原则

## 使用示例

```python
from core.event_bus import event_bus
from core.service_registry import service_registry

# 注册服务
@service_registry.register("my_service")
class MyService:
    def __init__(self):
        # 订阅事件
        event_bus.subscribe("device.state_changed", self.handle_state_change)
        
    async def handle_state_change(self, event):
        # 处理状态变更事件
        pass
``` 