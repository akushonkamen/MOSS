"""智能家居服务启动脚本"""
import os
import sys
import asyncio
import signal
from typing import Dict, Any, List, Optional
from loguru import logger
from tabulate import tabulate
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
from src.services.devices.device_manager import DeviceManager
from src.services.llm.decoderAgent import DecoderAgent
from src.services.llm.expertAgent import ExpertAgent
from src.services.devices.device_discovery import DeviceDiscoveryService
from src.services.devices.smart_light import SmartLightClient
from src.services.devices.smart_ac import SmartACClient
from src.services.devices.smart_curtain import SmartCurtainClient

class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        """初始化服务管理器"""
        self.device_manager = DeviceManager()
        self.decoder = None
        self.expert = None
        self.voice_manager = None
        self.logger = logging.getLogger(__name__)
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
        """注册所有设备
        
        Returns:
            List[DeviceInfo]: 设备信息列表
        """
        device_infos = []
        
        try:
            # 获取所有设备
            devices = await self.device_manager.get_all_devices()
            
            for device in devices:
                try:
                    # 获取设备类型
                    device_type = device.__class__.__name__.replace("Client", "")
                    self.logger.info(f"设备 {device.name} 类型: {device_type}")
                    
                    # 获取设备状态
                    device_state = await device.get_state()
                    self.logger.info(f"{device.name}状态: {device_state}")
                    
                    # 构建设备参数
                    parameters = {}
                    
                    # 根据设备类型构建参数
                    if isinstance(device, SmartLightClient):
                        parameters = {
                            "power": DeviceParameter(
                                type="boolean",
                                description="电源状态",
                                current_value=device_state.get("is_on", False)
                            ),
                            "brightness": DeviceParameter(
                                type="integer",
                                description="亮度",
                                current_value=device_state.get("brightness", 0),
                                min_value=0,
                                max_value=100,
                                unit="%"
                            )
                        }
                    elif isinstance(device, SmartACClient):
                        parameters = {
                            "power": DeviceParameter(
                                type="boolean",
                                description="电源状态",
                                current_value=device_state.get("is_on", False)
                            ),
                            "temperature": DeviceParameter(
                                type="integer",
                                description="温度",
                                current_value=device_state.get("temperature", 25),
                                min_value=16,
                                max_value=30,
                                unit="°C"
                            ),
                            "mode": DeviceParameter(
                                type="string",
                                description="运行模式",
                                current_value=device_state.get("mode", "auto"),
                                enum_values=["auto", "cool", "heat", "dry", "fan"]
                            )
                        }
                    elif isinstance(device, SmartCurtainClient):
                        parameters = {
                            "power": DeviceParameter(
                                type="boolean",
                                description="电源状态",
                                current_value=device_state.get("is_open", False)
                            ),
                            "position": DeviceParameter(
                                type="integer",
                                description="位置",
                                current_value=device_state.get("position", 0),
                                min_value=0,
                                max_value=100,
                                unit="%"
                            )
                        }
                    
                    # 创建设备信息对象
                    device_info = DeviceInfo(
                        id=device.device_id,
                        name=device.name,
                        type=device_type,  # 使用处理后的设备类型
                        location="",
                        capabilities=[],
                        parameters=parameters
                    )
                    device_infos.append(device_info)
                    
                except Exception as e:
                    self.logger.error(f"获取设备 {device.name} 状态失败: {str(e)}")
                    
            return device_infos
            
        except Exception as e:
            self.logger.error(f"注册设备失败: {str(e)}")
            return []
        
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
        # 准备表格数据
        table_data = []
        for device in devices:
            # 获取设备图标
            icon = self.get_device_icon(device.type)
            
            # 获取设备名称
            name = f"{icon} {device.name}"
            
            # 获取设备状态
            power = device.parameters.get("power")
            if power:
                status = "🟢 开启" if power.current_value else "⚫️ 关闭"
            else:
                status = "❓ 未知"
            
            # 获取详细信息
            details = []
            if "brightness" in device.parameters:
                brightness = device.parameters["brightness"]
                details.append(f"💡 亮度: {brightness.current_value}%")
            if "temperature" in device.parameters:
                temperature = device.parameters["temperature"]
                mode = device.parameters["mode"]
                details.append(f"🌡️ 温度: {temperature.current_value}°C")
                details.append(f"❄️ 模式: {mode.current_value}")
            if "position" in device.parameters:
                position = device.parameters["position"]
                details.append(f"📏 位置: {position.current_value}%")
            
            # 添加到表格数据
            table_data.append([name, status, ", ".join(details)])
        
        logger.debug(f"表格数据: {table_data}")
        
        # 打印表格
        print("\n当前设备状态:")
        print("="*80)
        headers = ["设备名称", "状态", "详细信息"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        print("="*80)

    def get_device_icon(self, device_type: str) -> str:
        """获取设备图标
        
        Args:
            device_type: 设备类型
            
        Returns:
            str: 设备图标
        """
        icons = {
            "SmartLight": "🔌",
            "SmartAC": "🎛️",
            "SmartCurtain": "🪟"
        }
        return icons.get(device_type, "❓")
        
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
            self.logger.info("正在启动所有服务...")
            
            # 初始化LLM服务
            self.decoder = DecoderAgent(
                api_url="http://localhost:11434/api/chat",
                model_name="llama3.1:latest"
            )
            await self.decoder.initialize()
            
            self.expert = ExpertAgent(
                agent_id="expert_001",
                api_url="http://localhost:11434/api/chat",
                model_name="llama3.1:latest"
            )
            await self.expert.initialize()
            
            # 初始化设备管理器
            await self.device_manager.initialize()
            
            # 注册设备
            devices = await self.register_devices()
            self.logger.info(f"获取到的设备列表: {[f'{d.name} ({d.type})' for d in devices]}")
            
            # 注册设备控制函数
            await self.register_functions()
            self.logger.info("设备控制函数注册完成")
            
            # 初始化语音配置
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
            
            # 初始化语音交互管理器
            self.voice_manager = VoiceInteractionManager(
                config=config,
                on_transcribe=self.on_transcribe,
                on_speech_start=self.on_speech_start,
                on_speech_end=self.on_speech_end
            )
            await self.voice_manager.initialize()
            
            # 打印设备状态
            await self.print_device_status(devices)
            
            # 启动语音助手
            self.logger.info("启动语音助手...")
            await self.voice_manager.start()
            
            # 保持主循环运行
            self.is_running = True
            try:
                while self.is_running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("收到退出信号")
                self.is_running = False
                await self.stop()
            
        except Exception as e:
            self.logger.error(f"启动服务时出错: {str(e)}")
            print(f"启动服务时出错: {str(e)}")
            raise
            
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