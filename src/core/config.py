"""配置模块

提供全局配置管理。
"""
import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class VoiceConfig:
    """语音配置"""
    vad_aggressiveness: int = 3
    silence_duration: float = 0.5
    min_audio_length: float = 1.0
    whisper_model: str = "base"
    whisper_language: str = "zh"
    
    @dataclass
    class RecorderConfig:
        """录音配置"""
        sample_rate: int = 16000
        channels: int = 1
        
    @dataclass
    class PlayerConfig:
        """播放配置"""
        sample_rate: int = 16000
        channels: int = 1
        
    recorder_config: RecorderConfig = RecorderConfig()
    player_config: PlayerConfig = PlayerConfig()

class Settings:
    """全局设置"""
    
    def __init__(self):
        """初始化设置"""
        # LLM配置
        self.OLLAMA_GENERATE_URL = os.getenv(
            "OLLAMA_GENERATE_URL",
            "http://localhost:11434/api/generate"
        )
        self.DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.1:latest")
        
        # 设备发现配置
        self.ENABLE_PORT_SCAN = os.getenv("ENABLE_PORT_SCAN", "1") == "1"  # 默认启用
        self.PORT_SCAN_RANGE = (
            int(os.getenv("PORT_SCAN_START", "1024")),  # 起始端口
            int(os.getenv("PORT_SCAN_END", "65535"))    # 结束端口
        )
        self.PORT_SCAN_BATCH_SIZE = int(os.getenv("PORT_SCAN_BATCH_SIZE", "1000"))  # 每批扫描的端口数
        self.PORT_SCAN_INTERVAL = int(os.getenv("PORT_SCAN_INTERVAL", "3600"))  # 扫描间隔（秒）
        
        # 日志配置
        self.LOG_DIR = os.getenv(
            "LOG_DIR",
            os.path.join(os.path.dirname(__file__), "../../logs")
        )
        self.SCAN_LOG_FILE = os.path.join(self.LOG_DIR, "port_scan.log")
        self.DISCOVERY_LOG_FILE = os.path.join(self.LOG_DIR, "device_discovery.log")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        
        # 设备管理配置
        self.DEVICE_STATE_DIR = os.getenv(
            "DEVICE_STATE_DIR",
            os.path.join(os.path.dirname(__file__), "../../data/device_states")
        )
        self.DEVICE_HEARTBEAT_INTERVAL = 30  # 设备心跳间隔（秒）
        self.DEVICE_OFFLINE_TIMEOUT = 90  # 设备离线超时（秒）
        
        # 语音配置
        self.VOICE = VoiceConfig()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "OLLAMA_GENERATE_URL": self.OLLAMA_GENERATE_URL,
            "DEFAULT_MODEL": self.DEFAULT_MODEL,
            "ENABLE_PORT_SCAN": self.ENABLE_PORT_SCAN,
            "PORT_SCAN_RANGE": self.PORT_SCAN_RANGE,
            "PORT_SCAN_BATCH_SIZE": self.PORT_SCAN_BATCH_SIZE,
            "PORT_SCAN_INTERVAL": self.PORT_SCAN_INTERVAL,
            "DEVICE_STATE_DIR": self.DEVICE_STATE_DIR,
            "DEVICE_HEARTBEAT_INTERVAL": self.DEVICE_HEARTBEAT_INTERVAL,
            "DEVICE_OFFLINE_TIMEOUT": self.DEVICE_OFFLINE_TIMEOUT,
            "VOICE": {
                "vad_aggressiveness": self.VOICE.vad_aggressiveness,
                "silence_duration": self.VOICE.silence_duration,
                "min_audio_length": self.VOICE.min_audio_length,
                "whisper_model": self.VOICE.whisper_model,
                "whisper_language": self.VOICE.whisper_language,
                "recorder_config": {
                    "sample_rate": self.VOICE.recorder_config.sample_rate,
                    "channels": self.VOICE.recorder_config.channels
                },
                "player_config": {
                    "sample_rate": self.VOICE.player_config.sample_rate,
                    "channels": self.VOICE.player_config.channels
                }
            },
            "LOG_DIR": self.LOG_DIR,
            "SCAN_LOG_FILE": self.SCAN_LOG_FILE,
            "DISCOVERY_LOG_FILE": self.DISCOVERY_LOG_FILE,
            "LOG_LEVEL": self.LOG_LEVEL,
            "LOG_FORMAT": self.LOG_FORMAT
        }

# 创建全局设置实例
settings = Settings() 