"""窗帘服务器"""
from .device_server import DeviceServer
import asyncio

class SmartCurtainServer(DeviceServer):
    """窗帘服务器"""
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化窗帘服务器"""
        super().__init__("SmartCurtain", device_id, name, port=port)
        self.status = {
            "is_open": False,
            "position": 0
        }
        
    async def handle_turn_on(self) -> str:
        """处理打开命令"""
        self.status["is_open"] = True
        self.status["position"] = 100
        return f"正在打开{self.name}"
        
    async def handle_turn_off(self) -> str:
        """处理关闭命令"""
        self.status["is_open"] = False
        self.status["position"] = 0
        return f"正在关闭{self.name}"
        
    async def handle_set_position(self, position: int) -> str:
        """处理设置位置命令"""
        if not 0 <= position <= 100:
            raise ValueError("位置必须在0-100之间")
        self.status["position"] = position
        self.status["is_open"] = position > 0
        return f"正在将{self.name}调整到{position}%的位置"

def main():
    """启动服务器"""
    import argparse
    parser = argparse.ArgumentParser(description="窗帘服务器")
    parser.add_argument("--id", required=True, help="设备ID")
    parser.add_argument("--name", required=True, help="设备名称")
    parser.add_argument("--port", type=int, required=True, help="服务器端口")
    args = parser.parse_args()
    
    server = SmartCurtainServer(args.id, args.name, args.port)
    server.run()
    
if __name__ == "__main__":
    main() 