"""语音服务API接口"""
from fastapi import APIRouter, WebSocket
from typing import Dict, Any
from loguru import logger
from .voice_interaction import VoiceInteractionManager, VoiceConfig
from .recorder_service import AudioConfig as RecorderConfig
from .player_service import AudioConfig as PlayerConfig
from ..smart_home import SmartHomeController

router = APIRouter()

# 全局语音管理器实例
voice_manager: VoiceInteractionManager = None
smart_home: SmartHomeController = None

@router.on_event("startup")
async def startup_event():
    """启动时初始化语音服务"""
    global voice_manager, smart_home
    
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
    
    # 创建智能家居控制器
    smart_home = SmartHomeController()
    
    async def on_transcribe(text: str):
        """语音识别回调"""
        logger.info(f"识别到语音: {text}")
        try:
            # 处理语音命令
            response = await smart_home.process_command(text)
            if response:
                await voice_manager.speak(response)
        except Exception as e:
            logger.error(f"处理语音命令错误: {e}")
            await voice_manager.speak("抱歉，我没有理解您的意思")
    
    def on_speech_start():
        """说话开始回调"""
        logger.info("检测到说话开始")
    
    def on_speech_end():
        """说话结束回调"""
        logger.info("检测到说话结束")
    
    # 创建语音交互管理器
    voice_manager = VoiceInteractionManager(
        config=config,
        on_speech_start=on_speech_start,
        on_speech_end=on_speech_end,
        on_transcribe=on_transcribe
    )
    
    # 启动语音交互
    voice_manager.start()
    logger.info("语音服务已启动")

@router.on_event("shutdown")
async def shutdown_event():
    """关闭时停止语音服务"""
    global voice_manager
    if voice_manager:
        voice_manager.stop()
        logger.info("语音服务已关闭")

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket语音接口"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            command_type = data.get("type")
            
            if command_type == "speak":
                # 语音合成请求
                text = data.get("text")
                if text:
                    await voice_manager.speak(text)
                    await websocket.send_json({"status": "success"})
            elif command_type == "start":
                # 启动语音识别
                voice_manager.start()
                await websocket.send_json({"status": "success"})
            elif command_type == "stop":
                # 停止语音识别
                voice_manager.stop()
                await websocket.send_json({"status": "success"})
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        await websocket.close()

@router.post("/speak")
async def speak(text: Dict[str, Any]):
    """语音合成接口"""
    try:
        await voice_manager.speak(text["text"])
        return {"status": "success"}
    except Exception as e:
        logger.error(f"语音合成错误: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/start")
async def start_voice():
    """启动语音识别"""
    try:
        voice_manager.start()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"启动语音服务错误: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/stop")
async def stop_voice():
    """停止语音识别"""
    try:
        voice_manager.stop()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"停止语音服务错误: {e}")
        return {"status": "error", "message": str(e)} 