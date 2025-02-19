"""语音配置

提供语音服务的配置定义。
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class RecorderConfig:
    """录音配置"""
    device_index: int = 0
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: str = "int16"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "device_index": self.device_index,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chunk_size": self.chunk_size,
            "format": self.format
        }

@dataclass
class PlayerConfig:
    """播放配置"""
    device_index: int = 0
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format: str = "int16"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "device_index": self.device_index,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chunk_size": self.chunk_size,
            "format": self.format
        }

@dataclass
class VoiceConfig:
    """语音配置"""
    
    # 录音配置
    recorder_config: RecorderConfig = RecorderConfig()
    
    # 播放配置
    player_config: PlayerConfig = PlayerConfig()
    
    # VAD配置
    vad_aggressiveness: int = 3
    silence_duration: float = 0.5
    min_audio_length: float = 1.0
    
    # 语音识别配置
    whisper_model: str = "base"
    whisper_language: str = "zh"
    
    # 语音合成配置
    tts_model: str = "edge-tts"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_rate: int = 0
    tts_volume: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "recorder_config": self.recorder_config.to_dict(),
            "player_config": self.player_config.to_dict(),
            "vad_aggressiveness": self.vad_aggressiveness,
            "silence_duration": self.silence_duration,
            "min_audio_length": self.min_audio_length,
            "whisper_model": self.whisper_model,
            "whisper_language": self.whisper_language,
            "tts_model": self.tts_model,
            "tts_voice": self.tts_voice,
            "tts_rate": self.tts_rate,
            "tts_volume": self.tts_volume
        } 