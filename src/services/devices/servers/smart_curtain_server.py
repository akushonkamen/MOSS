"""智能窗帘服务器实现"""
import json
from typing import Dict, Any, List
from ..base import DeviceServer, DeviceError, DeviceParameter, DeviceInfo

class CurtainServer(DeviceServer):
    """智能窗帘服务器"""
    
    def __init__(self, device_id: str, name: str, location: str, port: int):
        """初始化智能窗帘服务器
        
        Args:
            device_id: 设备ID
            name: 设备名称
            location: 设备位置
            port: 服务器端口
        """
        super().__init__(device_id, name, location, port)
        
    async def get_initial_state(self) -> Dict[str, Any]:
        """获取初始状态"""
        return {
            "is_on": True,  # 窗帘总是在线
            "position": 0   # 0表示完全关闭，100表示完全打开
        }
        
    async def _validate_state(self, state: Dict[str, Any]) -> None:
        """验证状态
        
        Args:
            state: 要验证的状态
            
        Raises:
            DeviceError: 状态无效
        """
        if "position" in state:
            position = state["position"]
            if not isinstance(position, (int, float)):
                raise DeviceError("位置必须是数字")
            if not 0 <= position <= 100:
                raise DeviceError("位置必须在0-100之间")
                
    async def get_capabilities(self) -> List[str]:
        """获取设备能力列表"""
        return [
            "position_control"
        ]
        
    async def _handle_command(self, command: str) -> str:
        """处理命令
        
        Args:
            command: 命令字符串
            
        Returns:
            str: 响应字符串
        """
        try:
            # 解析命令
            cmd_data = json.loads(command)
            cmd_type = cmd_data.get("type")
            params = cmd_data.get("params", {})
            
            if cmd_type == "get_state":
                # 获取状态
                state = await self.get_state()
                return json.dumps({
                    "success": True,
                    "state": state
                })
                
            elif cmd_type == "set_state":
                # 设置状态
                if "state" not in cmd_data:
                    raise DeviceError("缺少state参数")
                    
                success = await self.set_state(cmd_data["state"])
                return json.dumps({
                    "success": success
                })
                
            elif cmd_type == "set_position":
                # 设置位置
                if "position" not in params:
                    raise DeviceError("缺少position参数")
                    
                success = await self.set_state({
                    "position": params["position"]
                })
                return json.dumps({
                    "success": success
                })
                
            else:
                raise DeviceError(f"不支持的命令类型: {cmd_type}")
                
        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": "无效的JSON格式"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }) 