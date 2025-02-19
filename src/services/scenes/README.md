# 场景管理

此目录包含了智能工业AI场景管理相关的功能实现。

## 目录结构

- `scene_manager.py`: 场景管理器
- `scene_executor.py`: 场景执行器
- `scene_validator.py`: 场景验证器
- `models/`: 场景相关数据模型
  - `scene.py`: 场景定义
  - `condition.py`: 条件定义
  - `action.py`: 动作定义
  - `trigger.py`: 触发器定义

## 功能说明

1. 场景定义
   - 支持多设备联动
   - 支持条件触发
   - 支持定时执行
   - 支持手动触发

2. 场景执行
   - 并发执行控制
   - 执行状态跟踪
   - 错误处理和恢复
   - 执行日志记录

3. 场景验证
   - 设备可用性检查
   - 参数有效性验证
   - 循环依赖检测
   - 权限检查

## 使用示例

```python
from scenes.models import Scene, Condition, Action
from scenes.scene_manager import scene_manager

# 创建场景
scene = Scene(
    name="回家模式",
    conditions=[
        Condition("time", "after", "18:00"),
        Condition("location", "enter", "home")
    ],
    actions=[
        Action("light.living_room", "turn_on"),
        Action("ac.living_room", "set_temperature", {"temperature": 26})
    ]
)

# 注册场景
scene_manager.register_scene(scene)
``` 