"""空调服务器"""
from .device_server import DeviceServer
import asyncio
import logging

logger = logging.getLogger(__name__)

class SmartACServer(DeviceServer):
    """空调服务器"""
    
    def __init__(self, device_id: str, name: str, port: int):
        """初始化空调服务器"""
        super().__init__("SmartAC", device_id, name, port=port)
        self.status = {
            "is_on": False,
            "temperature": 26.0,
            "mode": "cool"
        }
        self.logger.info(f"空调初始化完成: {self.status}")
        
    async def handle_turn_on(self) -> str:
        """处理打开命令"""
        self.logger.info(f"处理打开命令，当前状态: {self.status}")
        self.status["is_on"] = True
        self.logger.info(f"空调已打开，更新后状态: {self.status}")
        return f"已打开{self.name}"
        
    async def handle_turn_off(self) -> str:
        """处理关闭命令"""
        self.logger.info(f"处理关闭命令，当前状态: {self.status}")
        self.status["is_on"] = False
        self.logger.info(f"空调已关闭，更新后状态: {self.status}")
        return f"已关闭{self.name}"
        
    async def handle_set_temperature(self, temperature: float) -> str:
        """处理设置温度命令"""
        self.logger.info(f"处理设置温度命令: {temperature}°C，当前状态: {self.status}")
        if not 16 <= temperature <= 30:
            error = f"温度必须在16-30度之间，收到的温度: {temperature}"
            self.logger.error(error)
            raise ValueError(error)
        self.status["temperature"] = temperature
        self.logger.info(f"温度已设置，更新后状态: {self.status}")
        return f"已将{self.name}的温度设置为{temperature}°C"
        
    async def handle_set_mode(self, mode: str) -> str:
        """处理设置模式命令"""
        self.logger.info(f"处理设置模式命令: {mode}，当前状态: {self.status}")
        if mode not in ["cool", "heat", "auto"]:
            error = f"不支持的模式: {mode}"
            self.logger.error(error)
            raise ValueError(error)
        self.status["mode"] = mode
        self.logger.info(f"模式已设置，更新后状态: {self.status}")
        return f"已将{self.name}切换到{mode}模式"
        
    async def handle_set_power(self, power: bool) -> str:
        """处理设置电源命令
        
        Args:
            power: 电源状态
            
        Returns:
            str: 处理结果
        """
        self.logger.info(f"处理设置电源命令: {power}，当前状态: {self.status}")
        self.status["is_on"] = power
        self.logger.info(f"电源状态已设置，更新后状态: {self.status}")
        return f"已将{self.name}的电源设置为{'开启' if power else '关闭'}"

def main():
    """启动服务器"""
    import argparse
    parser = argparse.ArgumentParser(description="空调服务器")
    parser.add_argument("--id", required=True, help="设备ID")
    parser.add_argument("--name", required=True, help="设备名称")
    parser.add_argument("--port", type=int, required=True, help="服务器端口")
    args = parser.parse_args()
    
    logger.info(f"启动空调服务器: id={args.id}, name={args.name}, port={args.port}")
    server = SmartACServer(args.id, args.name, args.port)
    server.run()
    
if __name__ == "__main__":
    main() 