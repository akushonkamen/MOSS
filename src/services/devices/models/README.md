# 设备数据模型

本目录包含设备管理系统使用的所有数据模型定义，使用 dataclasses 实现。

## 模型说明

- `device_info.py`: 设备信息模型
  - `DeviceInfo`: 设备基本信息
  - `DeviceParameter`: 设备参数定义

- `device_state.py`: 设备状态模型
  - `DeviceState`: 设备状态信息
  - `StateChange`: 状态变更记录

- `device_event.py`: 设备事件模型
  - `DeviceEvent`: 设备事件信息
  - `EventType`: 事件类型枚举

- `device_metrics.py`: 设备指标模型
  - `DeviceMetrics`: 设备运行指标
  - `MetricsType`: 指标类型定义

## 使用说明

1. 所有模型都使用 dataclasses 装饰器
2. 提供类型注解和文档字符串
3. 实现必要的序列化方法
4. 支持数据验证

## 示例

```python
from devices.models import DeviceInfo, DeviceParameter

# 创建设备参数
parameter = DeviceParameter(
    name="brightness",
    type="number",
    description="亮度设置",
    current_value=50,
    min_value=0,
    max_value=100,
    unit="%"
)

# 创建设备信息
info = DeviceInfo(
    id="light.001",
    name="客厅灯",
    type="Light",
    location="客厅",
    status="online",
    parameters={"brightness": parameter},
    capabilities=["power_control", "brightness_control"]
)
``` 