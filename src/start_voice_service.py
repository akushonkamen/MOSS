"""启动语音服务"""
import asyncio
import os
import sys
from loguru import logger
from typing import Optional, Dict, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.services.audio.voice_interaction import VoiceInteractionManager, VoiceConfig
from src.services.audio.recorder_service import AudioConfig as RecorderConfig
from src.services.audio.player_service import AudioConfig as PlayerConfig
from src.services.llm.llm_service import llm_service
from src.services.smart_home import SmartHomeController

class VoiceService:
    """语音服务管理器"""
    
    def __init__(self):
        """初始化语音服务"""
        self.voice_manager: Optional[VoiceInteractionManager] = None
        self.llm_service = llm_service()
        self.smart_home = SmartHomeController()
        self.is_running = False
        
    async def on_transcribe(self, text: str):
        """语音识别回调"""
        logger.info(f"识别到语音: {text}")
        try:
            # 处理语音命令
            response = await self.smart_home.process_command(text)
            if response:
                await self.voice_manager.speak(response)
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
        """启动语音服务"""
        # 创建配置
        frame_duration = 0.03  # 30ms
        sample_rate = 16000
        chunk_size = int(sample_rate * frame_duration)  # 480 samples for 30ms
        
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
        
        # 播放欢迎语
        logger.info("启动语音助手...")
        await self.voice_manager.speak("语音助手已启动，请说话")
        
        # 启动语音交互
        self.voice_manager.start()
        self.is_running = True
        
        try:
            # 保持运行直到按Ctrl+C
            while self.is_running:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("检测到退出信号")
        finally:
            await self.stop()
            
    async def stop(self):
        """停止语音服务"""
        if self.voice_manager:
            self.voice_manager.stop()
            self.is_running = False
            logger.info("语音助手已关闭")

async def main():
    """主函数"""
    # 配置日志
    logger.add(
        "logs/voice_service.log",
        rotation="1 MB",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )
    
    # 创建并启动语音服务
    service = VoiceService()
    await service.start()

if __name__ == "__main__":
    asyncio.run(main()) 