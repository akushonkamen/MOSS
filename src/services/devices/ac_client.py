"""空调设备客户端"""
from typing import Dict, Any
from .base import DeviceClient, DeviceError

class SmartACClient(DeviceClient):
    """智能空调客户端"""
    
    def __init__(self, device_id: str):
        """初始化空调客户端
        
        Args:
            device_id: 设备ID
        """
        super().__init__(device_id)
        # 初始化默认状态
        self.state = {
            "is_on": False,
            "temperature": 26,
            "mode": "auto"
        }
        
    def _validate_temperature(self, temp: Any) -> None:
        """验证温度
        
        Args:
            temp: 温度值
            
        Raises:
            DeviceError: 温度无效
        """
        if not isinstance(temp, (int, float)):
            raise DeviceError("温度必须是数字")
        if not 16 <= temp <= 30:
            raise DeviceError("温度必须在16-30之间")
            
    def _validate_mode(self, mode: Any) -> None:
        """验证模式
        
        Args:
            mode: 运行模式
            
        Raises:
            DeviceError: 模式无效
        """
        if not isinstance(mode, str):
            raise DeviceError("模式必须是字符串")
        if mode not in ["cool", "heat", "auto"]:
            raise DeviceError("不支持的模式")
        
    async def _make_request(self, method: str, **kwargs) -> Dict[str, Any]:
        """发送请求
        
        Args:
            method: 请求方法
            **kwargs: 请求参数
            
        Returns:
            Dict[str, Any]: 响应数据
            
        Raises:
            DeviceError: 设备操作异常
        """
        try:
            if method == "get_status":
                return self.state.copy()
                
            elif method == "update_state":
                new_state = kwargs.get("state", {})
                # 验证状态
                if "temperature" in new_state:
                    self._validate_temperature(new_state["temperature"])
                        
                if "mode" in new_state:
                    self._validate_mode(new_state["mode"])
                        
                # 更新状态
                self.state.update(new_state)
                return {"success": True}
                
            elif method == "execute":
                command = kwargs.get("command")
                params = kwargs.get("params", {})
                
                if command == "turn_on":
                    self.state["is_on"] = True
                    return {"success": True}
                    
                elif command == "turn_off":
                    self.state["is_on"] = False
                    return {"success": True}
                    
                elif command == "set_power":
                    power = params.get("power")
                    if power is None:
                        raise DeviceError("缺少power参数")
                    self.state["is_on"] = power
                    return {"success": True}
                    
                elif command == "set_temperature":
                    temp = params.get("temperature")
                    if temp is None:
                        raise DeviceError("缺少温度参数")
                    self._validate_temperature(temp)
                    self.state["temperature"] = temp
                    self.state["is_on"] = True
                    return {"success": True}
                    
                elif command == "set_mode":
                    mode = params.get("mode")
                    if mode is None:
                        raise DeviceError("缺少模式参数")
                    self._validate_mode(mode)
                    self.state["mode"] = mode
                    self.state["is_on"] = True
                    return {"success": True}
                    
                else:
                    raise DeviceError(f"不支持的命令: {command}")
                    
            else:
                raise DeviceError(f"不支持的方法: {method}")
                
        except DeviceError:
            raise
        except Exception as e:
            raise DeviceError(f"设备操作失败: {str(e)}")

    async def turn_on(self) -> Dict[str, Any]:
        """打开空调"""
        result = await self.execute_command("turn_on")
        return result
        
    async def turn_off(self) -> Dict[str, Any]:
        """关闭空调"""
        result = await self.execute_command("turn_off")
        return result
        
    async def set_temperature(self, temperature: int) -> Dict[str, Any]:
        """设置温度
        
        Args:
            temperature: 温度值(16-30)
        """
        if not 16 <= temperature <= 30:
            raise ValueError(f"温度值必须在16-30之间")
        result = await self.execute_command(
            "set_temperature",
            {"temperature": temperature}
        )
        return result
        
    async def set_mode(self, mode: str) -> Dict[str, Any]:
        """设置模式
        
        Args:
            mode: 运行模式
        """
        if mode not in ["cool", "heat", "auto"]:
            raise ValueError(f"无效的模式: {mode}")
        result = await self.execute_command(
            "set_mode",
            {"mode": mode}
        )
        return result
        
    async def set_power(self, power: bool) -> Dict[str, Any]:
        """设置电源状态
        
        Args:
            power: 电源状态
        """
        result = await self.execute_command(
            "set_power",
            {"power": power}
        )
        return result 