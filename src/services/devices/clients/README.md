# 设备客户端实现

此目录包含了所有具体设备的客户端实现。每个设备客户端都继承自 `base.DeviceClient` 类，并实现了特定设备的控制逻辑。

## 目录结构

- `smart_light_client.py`: 智能灯具客户端实现
- `smart_curtain_client.py`: 智能窗帘客户端实现

## 开发规范

1. 命名规范
   - 文件名使用小写字母，单词之间用下划线连接
   - 类名使用 PascalCase，例如 `SmartLightClient`
   - 方法名使用小写字母，单词之间用下划线连接

2. 代码结构
   - 每个客户端类都应该继承自 `base.DeviceClient`
   - 必须实现所有抽象方法
   - 应该提供完整的类型注解
   - 必须包含详细的文档字符串

3. 错误处理
   - 使用 `DeviceError` 处理设备相关错误
   - 所有可能的异常都应该被适当处理
   - 错误信息应该清晰明确

4. 状态管理
   - 使用 `DeviceState` 管理设备状态
   - 状态变化应该触发相应的事件
   - 保持状态同步和一致性

## 示例

```python
from ..base import DeviceClient
from ..models import DeviceState, DeviceError

class ExampleClient(DeviceClient):
    """示例设备客户端"""
    
    def get_initial_state(self) -> DeviceState:
        """获取初始状态"""
        pass
        
    def _validate_state(self, state: dict) -> None:
        """验证状态有效性"""
        pass
``` 