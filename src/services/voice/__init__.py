"""语音服务

提供语音交互的核心功能。
"""

from .voice_interaction_manager import VoiceInteractionManager
from .voice_config import VoiceConfig

__all__ = [
    'VoiceInteractionManager',
    'VoiceConfig'
]