# 设备服务器实现

本目录包含所有具体设备的服务器实现。每个服务器类负责处理设备的实际控制逻辑，并提供设备状态管理。

## 设备列表

- `smart_light_server.py`: 智能灯服务器
  - 处理开关控制命令
  - 处理亮度调节命令
  - 维护设备状态
  - 提供状态查询接口

- `smart_ac_server.py`: 智能空调服务器
  - 处理开关控制命令
  - 处理温度调节命令
  - 处理模式切换命令
  - 处理风速调节命令
  - 维护设备状态
  - 提供状态查询接口

- `smart_curtain_server.py`: 智能窗帘服务器
  - 处理开关控制命令
  - 处理位置调节命令
  - 维护设备状态
  - 提供状态查询接口

## 使用说明

1. 所有服务器都继承自 `DeviceServer` 基类
2. 每个服务器实现特定设备的控制逻辑
3. 提供统一的命令处理接口
4. 支持事件通知机制
5. 实现状态持久化

## 示例

```python
from devices.servers import SmartLightServer

# 创建智能灯服务器
server = SmartLightServer(
    device_id="light.001",
    name="客厅灯",
    location="客厅",
    port=8001
)

# 初始化服务器
await server.initialize()

# 启动服务
await server.start()
``` 