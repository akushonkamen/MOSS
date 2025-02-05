"""智能灯服务器"""
from .device_server import DeviceServer
import asyncio

class SmartLightServer(DeviceServer):
    """智能灯服务器"""
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化智能灯服务器"""
        super().__init__("SmartLight", device_id, name, port=port)
        self.status = {
            "is_on": False,
            "brightness": 100
        }
        
    async def handle_turn_on(self) -> str:
        """处理打开命令"""
        self.status["is_on"] = True
        return f"已打开{self.name}"
        
    async def handle_turn_off(self) -> str:
        """处理关闭命令"""
        self.status["is_on"] = False
        return f"已关闭{self.name}"
        
    async def handle_set_brightness(self, brightness: int) -> str:
        """处理设置亮度命令"""
        if not 0 <= brightness <= 100:
            raise ValueError("亮度必须在0-100之间")
        self.status["brightness"] = brightness
        return f"已将{self.name}的亮度设置为{brightness}%"

    async def handle_set_power(self, power: bool) -> str:
        """处理设置电源状态命令
        
        Args:
            power: 电源状态
            
        Returns:
            str: 操作结果
        """
        self.status["is_on"] = power
        state = "打开" if power else "关闭"
        return f"已{state}{self.name}"

def main():
    """启动服务器"""
    import argparse
    parser = argparse.ArgumentParser(description="智能灯服务器")
    parser.add_argument("--id", required=True, help="设备ID")
    parser.add_argument("--name", required=True, help="设备名称")
    parser.add_argument("--port", type=int, required=True, help="服务器端口")
    args = parser.parse_args()
    
    server = SmartLightServer(args.id, args.name, args.port)
    server.run()
    
if __name__ == "__main__":
    main() 