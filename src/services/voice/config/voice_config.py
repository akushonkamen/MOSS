"""语音配置"""
from dataclasses import dataclass

@dataclass
class RecorderConfig:
    """录音配置"""
    channels: int
    sample_rate: int
    sample_width: int
    chunk_size: int

@dataclass
class PlayerConfig:
    """播放配置"""
    channels: int
    sample_rate: int
    sample_width: int
    chunk_size: int

@dataclass
class VoiceConfig:
    """语音配置"""
    recorder_config: RecorderConfig
    player_config: PlayerConfig
    vad_aggressiveness: int
    silence_duration: float
    min_audio_length: float
    whisper_model: str
    whisper_language: str 