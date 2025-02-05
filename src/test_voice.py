import asyncio
from loguru import logger
from services.audio.voice_interaction import VoiceInteractionManager, VoiceConfig
from services.audio.recorder_service import AudioConfig as RecorderConfig
from services.audio.player_service import AudioConfig as PlayerConfig

async def on_transcribe(text: str):
    """语音识别回调"""
    logger.info(f"识别到语音: {text}")
    # 简单的回复
    if "你好" in text:
        await manager.speak("你好，我是智能助手")
    elif "再见" in text:
        logger.info("检测到再见指令，准备退出...")
        manager.stop()
        
def on_speech_start():
    """说话开始回调"""
    logger.info("检测到说话开始")
    
def on_speech_end():
    """说话结束回调"""
    logger.info("检测到说话结束")

async def main():
    global manager
    
    # 配置日志
    logger.add("voice_test.log", rotation="1 MB")
    
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
        whisper_model="large",  # 使用large模型以获得最佳准确率
        whisper_language="zh"  # 设置为中文
    )
    
    # 创建语音交互管理器
    manager = VoiceInteractionManager(
        config=config,
        on_speech_start=on_speech_start,
        on_speech_end=on_speech_end,
        on_transcribe=on_transcribe
    )
    
    # 播放欢迎语
    logger.info("启动语音助手...")
    await manager.speak("语音助手已启动，请说话")
    
    # 启动语音交互
    manager.start()
    
    try:
        # 保持运行直到按Ctrl+C
        while True:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("检测到退出信号")
    finally:
        # 停止服务
        manager.stop()
        logger.info("语音助手已关闭")

if __name__ == "__main__":
    manager = None
    asyncio.run(main()) 