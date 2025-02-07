"""语音配置"""
from dataclasses import dataclass

@dataclass
class VoiceConfig:
    """语音配置"""
    
    # 录音参数
    sample_rate: int = 16000  # 采样率
    channels: int = 1  # 声道数
    chunk_size: int = 1024  # 块大小
    silence_threshold: float = 0.03  # 静音阈值
    silence_duration: float = 1.0  # 静音持续时间
    
    # 语音识别参数
    model_name: str = "large"  # 模型名称
    language: str = "zh"  # 语言
    
    # 语音合成参数
    voice_name: str = "zh-CN-XiaoxiaoNeural"  # 语音名称
    voice_rate: float = 1.0  # 语速
    voice_pitch: float = 1.0  # 音调 