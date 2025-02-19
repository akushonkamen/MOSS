"""语音交互管理器

提供语音交互的核心实现。
"""
import os
import logging
import asyncio
import sounddevice as sd
import numpy as np
import whisper
import edge_tts
from typing import Dict, Any, Optional, Callable, Awaitable
from .voice_config import VoiceConfig

class VoiceInteractionManager:
    """语音交互管理器"""
    
    def __init__(
        self,
        config: VoiceConfig,
        on_transcribe: Callable[[str], Awaitable[bool]],
        on_speech_start: Optional[Callable[[], None]] = None,
        on_speech_end: Optional[Callable[[], None]] = None
    ):
        """初始化语音交互管理器
        
        Args:
            config: 语音配置
            on_transcribe: 语音识别回调
            on_speech_start: 语音开始回调
            on_speech_end: 语音结束回调
        """
        self.logger = logging.getLogger("VoiceInteractionManager")
        self.config = config
        self.on_transcribe = on_transcribe
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        
        self.is_running = False
        self.is_recording = False
        self.audio_buffer = []
        
        # 初始化语音识别模型
        self.whisper_model = None
        
        # 初始化语音合成引擎
        self.tts_communicator = None
        
    async def initialize(self) -> None:
        """初始化管理器"""
        self.logger.info("正在初始化语音交互管理器...")
        
        # 加载语音识别模型
        self.whisper_model = whisper.load_model(self.config.whisper_model)
        
        # 创建语音合成引擎
        self.tts_communicator = edge_tts.Communicate(
            self.config.tts_voice,
            rate=self.config.tts_rate,
            volume=self.config.tts_volume
        )
        
        self.logger.info("语音交互管理器初始化完成")
        
    async def start(self) -> None:
        """启动管理器"""
        self.logger.info("正在启动语音交互管理器...")
        
        # 设置录音回调
        def audio_callback(indata, frames, time, status):
            if status:
                self.logger.warning(f"录音状态: {status}")
            if self.is_recording:
                self.audio_buffer.extend(indata.flatten())
                
        # 启动录音流
        self.stream = sd.InputStream(
            device=self.config.recorder_config.device_index,
            samplerate=self.config.recorder_config.sample_rate,
            channels=self.config.recorder_config.channels,
            callback=audio_callback,
            dtype=np.float32
        )
        
        self.stream.start()
        self.is_running = True
        
        # 启动语音检测循环
        asyncio.create_task(self._voice_detection_loop())
        
        self.logger.info("语音交互管理器启动完成")
        
    async def stop(self) -> None:
        """停止管理器"""
        self.logger.info("正在停止语音交互管理器...")
        
        self.is_running = False
        self.is_recording = False
        
        if hasattr(self, "stream"):
            self.stream.stop()
            self.stream.close()
            
        self.logger.info("语音交互管理器已停止")
        
    async def _voice_detection_loop(self) -> None:
        """语音检测循环"""
        silence_frames = 0
        speech_frames = 0
        
        while self.is_running:
            try:
                # 检查音频缓冲区
                if len(self.audio_buffer) < self.config.recorder_config.chunk_size:
                    await asyncio.sleep(0.01)
                    continue
                    
                # 获取音频片段
                chunk = self.audio_buffer[:self.config.recorder_config.chunk_size]
                self.audio_buffer = self.audio_buffer[self.config.recorder_config.chunk_size:]
                
                # 计算音量
                volume = np.abs(chunk).mean()
                
                # 检测语音
                if volume > 0.01:  # 可以根据需要调整阈值
                    if not self.is_recording:
                        self.is_recording = True
                        self.audio_buffer = []
                        if self.on_speech_start:
                            self.on_speech_start()
                    speech_frames += 1
                    silence_frames = 0
                else:
                    if self.is_recording:
                        silence_frames += 1
                        
                # 检查静音时长
                if silence_frames > int(self.config.silence_duration * self.config.recorder_config.sample_rate / self.config.recorder_config.chunk_size):
                    if speech_frames > int(self.config.min_audio_length * self.config.recorder_config.sample_rate / self.config.recorder_config.chunk_size):
                        # 停止录音
                        self.is_recording = False
                        if self.on_speech_end:
                            self.on_speech_end()
                            
                        # 处理录音
                        await self._process_recording()
                        
                    # 重置计数器
                    speech_frames = 0
                    silence_frames = 0
                    self.audio_buffer = []
                    
            except Exception as e:
                self.logger.error(f"语音检测失败: {e}")
                await asyncio.sleep(1)
                
    async def _process_recording(self) -> None:
        """处理录音"""
        try:
            if not self.audio_buffer:
                return
                
            # 转换音频格式
            audio_data = np.array(self.audio_buffer)
            
            # 保存音频文件
            import soundfile as sf
            temp_file = "temp.wav"
            sf.write(
                temp_file,
                audio_data,
                self.config.recorder_config.sample_rate
            )
            
            try:
                # 语音识别
                result = self.whisper_model.transcribe(
                    temp_file,
                    language=self.config.whisper_language
                )
                
                # 获取识别文本
                text = result["text"].strip()
                if text:
                    self.logger.info(f"识别结果: {text}")
                    
                    # 调用回调函数
                    if self.on_transcribe:
                        success = await self.on_transcribe(text)
                        if not success:
                            self.logger.warning("处理识别结果失败")
                            
            finally:
                # 删除临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            self.logger.error(f"处理录音失败: {e}")
            
    async def speak(self, text: str) -> None:
        """语音合成并播放
        
        Args:
            text: 要播放的文本
        """
        try:
            # 生成语音
            audio_data = await self.tts_communicator.synthesize(text)
            
            # 保存临时文件
            temp_file = "temp.mp3"
            with open(temp_file, "wb") as f:
                f.write(audio_data)
                
            try:
                # 播放音频
                import soundfile as sf
                data, samplerate = sf.read(temp_file)
                sd.play(data, samplerate)
                sd.wait()
                
            finally:
                # 删除临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            self.logger.error(f"语音合成失败: {e}") 