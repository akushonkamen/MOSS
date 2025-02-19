# 设备工具函数

本目录包含设备管理系统使用的工具函数和辅助功能。

## 组件说明

- `function_definitions.py`: 功能定义
  - 设备功能注册
  - 功能参数定义
  - 功能验证规则

- `registry.py`: 注册表
  - 功能注册和查询
  - 设备类型注册
  - 验证器注册

## 使用说明

1. 工具函数应该是无状态的
2. 提供清晰的函数签名和文档
3. 实现错误处理和日志记录
4. 支持单元测试

## 示例

```python
from devices.utils import (
    register_function,
    get_function,
    list_functions
)

# 注册设备功能
register_function(
    name="set_brightness",
    description="设置设备亮度",
    parameters={
        "brightness": {
            "type": "number",
            "description": "亮度值",
            "min": 0,
            "max": 100
        }
    }
)

# 获取功能定义
function = get_function("set_brightness")

# 列出所有功能
functions = list_functions()
``` 