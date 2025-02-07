"""智能家居服务启动脚本"""
import os
import sys
import asyncio
import signal
from typing import Dict, Any, List, Optional
from loguru import logger
from tabulate import tabulate

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.services.audio.voice_interaction import VoiceInteractionManager, VoiceConfig
from src.services.audio.recorder_service import AudioConfig as RecorderConfig
from src.services.audio.player_service import AudioConfig as PlayerConfig
from src.services.llm.llm_service import llm_service
from src.services.devices.device_client import SmartLightClient, SmartACClient, SmartCurtainClient
from src.services.devices.functions import register_device_functions
from src.services.function_calling.registry import registry as function_registry, FunctionParameter
from src.services.devices.base import registry as device_registry
from src.services.core.entity import registry as entity_registry
from src.services.devices.light_entity import LightEntity
from src.services.devices.ac_entity import ACEntity
from src.services.devices.curtain_entity import CurtainEntity
from src.services.function_calling.parser import FunctionParser
from src.services.function_calling.registry import FunctionDefinition
from src.services.devices.device_info import DeviceInfo, DeviceParameter

class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        """初始化服务管理器"""
        self.voice_manager: Optional[VoiceInteractionManager] = None
        self.llm_service = llm_service()
        self.is_running = False
        
        # 配置日志
        os.makedirs("logs", exist_ok=True)
        logger.add(
            "logs/services.log",
            rotation="1 MB",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        
    async def init_voice_service(self):
        """初始化语音服务"""
        # 创建配置
        frame_duration = 0.03  # 30ms
        sample_rate = 16000
        chunk_size = int(sample_rate * frame_duration)
        
        config = VoiceConfig(
            recorder_config=RecorderConfig(
                channels=1,
                sample_rate=sample_rate,
                sample_width=2,
                chunk_size=chunk_size
            ),
            player_config=PlayerConfig(
                channels=1,
                sample_rate=sample_rate,
                sample_width=2,
                chunk_size=chunk_size
            ),
            vad_aggressiveness=3,
            silence_duration=1.0,
            min_audio_length=0.5,
            whisper_model="large",
            whisper_language="zh"
        )
        
        # 创建语音交互管理器
        self.voice_manager = VoiceInteractionManager(
            config=config,
            on_speech_start=self.on_speech_start,
            on_speech_end=self.on_speech_end,
            on_transcribe=self.on_transcribe
        )
        
    async def register_devices(self) -> List[DeviceInfo]:
        """注册设备
        
        Returns:
            List[DeviceInfo]: 设备列表
        """
        # 创建设备客户端
        devices = [
            SmartLightClient("light.001", "客厅灯", 8001),
            SmartLightClient("light.002", "卧室灯", 8002),
            SmartACClient("ac.001", "客厅空调", 8003),
            SmartCurtainClient("curtain.001", "卧室窗帘", 8004)
        ]
        
        # 获取设备状态
        device_infos = []
        for device in devices:
            try:
                status = await device.get_status()
                logger.info(f"设备 {device.name} 类型: {device.__class__.__name__}")
                logger.info(f"{device.name}状态: {status}")
                
                # 构造设备信息
                parameters = {}
                if isinstance(device, SmartLightClient):
                    parameters = {
                        "power": DeviceParameter(
                            type="boolean",
                            description="电源开关状态",
                            current_value=status["is_on"]
                        ),
                        "brightness": DeviceParameter(
                            type="integer",
                            description="亮度值",
                            current_value=status["brightness"],
                            min_value=0,
                            max_value=100,
                            unit="%"
                        )
                    }
                elif isinstance(device, SmartACClient):
                    parameters = {
                        "power": DeviceParameter(
                            type="boolean",
                            description="电源开关状态",
                            current_value=status["is_on"]
                        ),
                        "temperature": DeviceParameter(
                            type="integer",
                            description="温度值",
                            current_value=status["temperature"],
                            min_value=16,
                            max_value=30,
                            unit="°C"
                        ),
                        "mode": DeviceParameter(
                            type="string",
                            description="运行模式",
                            current_value=status["mode"],
                            enum_values=["auto", "cool", "heat", "dry", "fan"]
                        )
                    }
                elif isinstance(device, SmartCurtainClient):
                    parameters = {
                        "power": DeviceParameter(
                            type="boolean",
                            description="电源开关状态",
                            current_value=status["is_open"]
                        ),
                        "position": DeviceParameter(
                            type="integer",
                            description="位置值",
                            current_value=status["position"],
                            min_value=0,
                            max_value=100,
                            unit="%"
                        )
                    }
                    
                device_info = DeviceInfo(
                    id=device.device_id,
                    name=device.name,
                    type=device.__class__.__name__.replace("Client", ""),
                    location="",
                    capabilities=[],
                    parameters=parameters
                )
                device_infos.append(device_info)
                
            except Exception as e:
                logger.error(f"获取设备 {device.name} 状态失败: {str(e)}")
                
        return device_infos
        
    async def register_functions(self):
        """注册控制函数"""
        # 创建设备客户端
        ac = SmartACClient("ac.001", "客厅空调", 8003)
        light = SmartLightClient("light.001", "客厅灯", 8001)
        curtain = SmartCurtainClient("curtain.001", "卧室窗帘", 8004)
        
        # 注册空调控制函数
        self.llm_service.register_function(
            ac.set_power,
            description="控制空调电源",
            parameters={
                "power": {
                    "name": "power",
                    "type": "boolean",
                    "description": "电源状态",
                    "required": True
                }
            }
        )
        
        self.llm_service.register_function(
            ac.set_temperature,
            description="设置空调温度",
            parameters={
                "temperature": {
                    "name": "temperature",
                    "type": "number",
                    "description": "目标温度",
                    "required": True,
                    "min_value": 16,
                    "max_value": 30
                }
            }
        )
        
        self.llm_service.register_function(
            ac.set_mode,
            description="设置空调运行模式",
            parameters={
                "mode": {
                    "name": "mode",
                    "type": "string",
                    "description": "运行模式",
                    "required": True,
                    "enum_values": ["auto", "cool", "heat", "dry", "fan"]
                }
            }
        )
        
        # 注册灯光控制函数
        self.llm_service.register_function(
            light.set_power,
            description="控制灯光电源",
            parameters={
                "power": {
                    "name": "power",
                    "type": "boolean",
                    "description": "电源状态",
                    "required": True
                }
            }
        )
        
        self.llm_service.register_function(
            light.set_brightness,
            description="设置灯光亮度",
            parameters={
                "brightness": {
                    "name": "brightness",
                    "type": "number",
                    "description": "亮度百分比",
                    "required": True,
                    "min_value": 0,
                    "max_value": 100
                }
            }
        )
        
        # 注册窗帘控制函数
        self.llm_service.register_function(
            curtain.set_position,
            description="设置窗帘位置",
            parameters={
                "device_id": {
                    "name": "device_id",
                    "type": "string",
                    "description": "设备ID",
                    "required": True
                },
                "position": {
                    "name": "position",
                    "type": "integer",
                    "description": "位置值",
                    "required": True,
                    "min_value": 0,
                    "max_value": 100
                }
            }
        )
        
    async def print_device_status(self, devices: List[DeviceInfo]):
        """打印设备状态
        
        Args:
            devices: 设备列表
        """
        # 获取设备状态
        table_data = []
        headers = ["设备名称", "状态", "详细信息"]
        
        for device in devices:
            try:
                # 构造状态信息
                if device.type == "SmartLight":
                    name = "🔌 " + device.name
                    is_on = device.parameters["power"].current_value
                    brightness = device.parameters["brightness"].current_value
                    status = "🟢 开启" if is_on else "⚫️ 关闭"
                    details = f"💡 亮度: {brightness}%"
                elif device.type == "SmartAC":
                    name = "🎛️ " + device.name
                    is_on = device.parameters["power"].current_value
                    temperature = device.parameters["temperature"].current_value
                    mode = device.parameters["mode"].current_value
                    status = "🟢 开启" if is_on else "⚫️ 关闭"
                    mode_icons = {
                        "cool": "❄️",
                        "heat": "🔥",
                        "auto": "🔄"
                    }
                    mode_icon = mode_icons.get(mode, "")
                    details = f"🌡️ 温度: {temperature}°C, {mode_icon} 模式: {mode}"
                elif device.type == "SmartCurtain":
                    name = "🪟 " + device.name
                    is_open = device.parameters["power"].current_value
                    position = device.parameters["position"].current_value
                    status = "🟢 开启" if is_open else "⚫️ 关闭"
                    details = f"📏 位置: {position}%"
                else:
                    continue
                    
                table_data.append([name, status, details])
                
            except Exception as e:
                logger.error(f"获取设备 {device.name} 状态失败: {str(e)}")
                table_data.append([f"❌ {device.name}", "错误", str(e)])
                
        logger.debug(f"表格数据: {table_data}")
        
        # 打印状态表格
        print("\n当前设备状态:")
        print("=" * 80)
        
        if not table_data:
            print("暂无设备状态信息")
            logger.warning("没有设备状态数据被添加到表格中")
        else:
            try:
                # 使用简单的表格格式，避免特殊字符问题
                table = tabulate(
                    table_data,
                    headers=headers,
                    tablefmt="simple",
                    stralign="left"
                )
                print(table)
            except Exception as e:
                logger.error(f"格式化设备状态表格失败: {str(e)}")
                # 使用最简单的格式打印
                print(f"{headers[0]:<30} {headers[1]:<15} {headers[2]}")
                print("-" * 80)
                for row in table_data:
                    print(f"{row[0]:<30} {row[1]:<15} {row[2]}")
        
        print("=" * 80)
        
    async def on_transcribe(self, text: str):
        """语音识别回调"""
        logger.info(f"识别到语音: {text}")
        try:
            # 获取最新设备状态
            devices = await self.register_devices()
            
            # 处理语音命令
            result = await self.llm_service.execute_intent(text, devices)
            print(result)
            
            # 等待设备状态更新
            print("\n等待设备状态更新...")
            await asyncio.sleep(1)
            
            # 打印最新状态
            devices = await self.register_devices()
            await self.print_device_status(devices)
            
            # 语音反馈
            await self.voice_manager.speak(result)
            
        except Exception as e:
            logger.error(f"处理语音命令错误: {e}")
            await self.voice_manager.speak("抱歉，我没有理解您的意思")
    
    def on_speech_start(self):
        """说话开始回调"""
        logger.info("检测到说话开始")
    
    def on_speech_end(self):
        """说话结束回调"""
        logger.info("检测到说话结束")
        
    async def start(self):
        """启动所有服务"""
        try:
            logger.info("正在启动所有服务...")
            
            # 初始化LLM服务
            await self.llm_service.initialize()
            
            # 注册设备
            devices = await self.register_devices()
            logger.info(f"获取到的设备列表: {[f'{d.name} ({d.type})' for d in devices]}")
            
            # 注册函数
            await self.register_functions()
            logger.info("设备控制函数注册完成")
            
            # 初始化并启动语音服务
            await self.init_voice_service()
            
            # 打印当前设备状态
            await self.print_device_status(devices)
            
            # 播放欢迎语
            logger.info("启动语音助手...")
            await self.voice_manager.speak("所有服务已启动完成，请说话")
            
            # 启动语音交互
            self.voice_manager.start()
            self.is_running = True
            
            # 注册信号处理
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
                
            try:
                # 保持运行直到收到退出信号
                while self.is_running:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                logger.info("检测到退出信号")
            finally:
                await self.stop()
                
        except Exception as e:
            logger.error(f"启动服务时出错: {str(e)}")
            print(f"启动服务时出错: {str(e)}")
            
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号: {signum}")
        self.is_running = False
            
    async def stop(self):
        """停止所有服务"""
        logger.info("正在停止所有服务...")
        
        # 停止语音服务
        if self.voice_manager:
            self.voice_manager.stop()
            
        logger.info("所有服务已停止")

async def main():
    """主函数"""
    # 创建并启动服务管理器
    manager = ServiceManager()
    await manager.start()

if __name__ == "__main__":
    asyncio.run(main()) 