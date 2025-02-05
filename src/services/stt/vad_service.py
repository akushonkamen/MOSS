import webrtcvad
import numpy as np
from typing import List
from dataclasses import dataclass

@dataclass
class VADResult:
    """VAD检测结果"""
    is_speech: bool
    probability: float
    frame_duration_ms: int

class VADService:
    """语音活跃检测服务"""
    
    def __init__(self, aggressiveness: int = 3, frame_duration_ms: int = 30):
        """
        初始化VAD服务
        
        Args:
            aggressiveness: VAD的激进程度(0-3)，越高越容易检测到语音
            frame_duration_ms: 音频帧长度(10, 20, 30ms)
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.frame_duration_ms = frame_duration_ms
        
    def is_speech(self, audio_frame: bytes, sample_rate: int = 16000) -> VADResult:
        """
        检测音频帧是否包含语音
        
        Args:
            audio_frame: PCM音频数据
            sample_rate: 采样率
            
        Returns:
            VADResult: 检测结果
        """
        try:
            is_speech = self.vad.is_speech(audio_frame, sample_rate)
            return VADResult(
                is_speech=is_speech,
                probability=1.0 if is_speech else 0.0,
                frame_duration_ms=self.frame_duration_ms
            )
        except Exception as e:
            print(f"VAD检测出错: {str(e)}")
            return VADResult(
                is_speech=False,
                probability=0.0,
                frame_duration_ms=self.frame_duration_ms
            )
            
    def process_audio(self, audio_data: bytes, sample_rate: int = 16000) -> List[VADResult]:
        """
        处理一段音频数据
        
        Args:
            audio_data: PCM音频数据
            sample_rate: 采样率
            
        Returns:
            List[VADResult]: 所有帧的检测结果
        """
        # 计算每帧的样本数
        frame_length = int(sample_rate * (self.frame_duration_ms / 1000.0))
        frame_step = frame_length
        
        # 将音频数据转换为numpy数组
        audio = np.frombuffer(audio_data, dtype=np.int16)
        
        # 分帧处理
        results = []
        for start in range(0, len(audio) - frame_length + 1, frame_step):
            frame = audio[start:start + frame_length].tobytes()
            result = self.is_speech(frame, sample_rate)
            results.append(result)
            
        return results 