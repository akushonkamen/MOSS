# 设备基础类

本目录包含设备管理系统的基础类定义，为整个系统提供核心抽象和接口。

## 文件说明

- `device_base.py`: 设备基类定义
  - `Device`: 所有设备的抽象基类
  - `DeviceStatus`: 设备状态枚举
  - `DeviceError`: 设备异常类
  - `DeviceInfo`: 设备信息数据类
  - `DeviceParameter`: 设备参数数据类

- `client_base.py`: 设备客户端基类
  - `DeviceClient`: 所有设备客户端的基类
  - 提供与设备通信的基础功能
  - 实现状态管理和验证

- `server_base.py`: 设备服务器基类
  - `DeviceServer`: 所有设备服务器的基类
  - 提供设备服务器的基础功能
  - 实现命令处理和事件通知

## 使用说明

1. 所有具体的设备实现都应该继承这些基类
2. 必须实现基类中定义的抽象方法
3. 遵循基类定义的接口规范
4. 使用提供的异常类进行错误处理

## 示例

```python
from .device_base import Device, DeviceStatus

class MyDevice(Device):
    def __init__(self, device_id: str, name: str, location: str):
        super().__init__(device_id, name, location)
        
    async def initialize(self) -> None:
        # 实现设备初始化逻辑
        pass
``` 