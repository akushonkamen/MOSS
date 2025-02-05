import webrtcvad
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class VADResult:
    is_speech: bool
    probability: float
    frame_duration: float

class VADService:
    def __init__(self, aggressiveness: int = 3, sample_rate: int = 16000):
        """
        初始化VAD服务
        
        Args:
            aggressiveness: VAD灵敏度 (0-3)
            sample_rate: 采样率
        """
        if sample_rate not in [8000, 16000, 32000]:
            raise ValueError("采样率必须是8000Hz、16000Hz或32000Hz")
            
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        
    def _validate_frame(self, frame: bytes, frame_duration: float) -> Tuple[bytes, float]:
        """
        验证并处理音频帧
        
        Args:
            frame: 音频数据
            frame_duration: 帧长度(秒)
            
        Returns:
            Tuple[bytes, float]: 处理后的音频帧和帧长度
        """
        # 计算帧大小（字节）
        # 采样率 * 帧长度 * 每样本字节数（16位=2字节）
        expected_frame_size = int(self.sample_rate * frame_duration * 2)
        
        if len(frame) != expected_frame_size:
            # 如果帧大小不匹配，调整frame_duration
            frame_duration = len(frame) / (self.sample_rate * 2)
            
        # 确保帧长度是10ms、20ms或30ms的倍数
        valid_durations = [0.01, 0.02, 0.03]
        if frame_duration not in valid_durations:
            # 选择最接近的有效帧长度
            frame_duration = min(valid_durations, key=lambda x: abs(x - frame_duration))
            expected_frame_size = int(self.sample_rate * frame_duration * 2)
            
            if len(frame) > expected_frame_size:
                # 如果帧太长，截断
                frame = frame[:expected_frame_size]
            elif len(frame) < expected_frame_size:
                # 如果帧太短，用静音填充
                frame = frame + b'\x00' * (expected_frame_size - len(frame))
                
        return frame, frame_duration
        
    def process_frame(self, frame: bytes, frame_duration: float = 0.03) -> VADResult:
        """
        处理一帧音频数据
        
        Args:
            frame: 音频数据
            frame_duration: 帧长度(秒)
            
        Returns:
            VADResult: VAD检测结果
        """
        try:
            # 验证并处理音频帧
            frame, frame_duration = self._validate_frame(frame, frame_duration)
            
            # 进行VAD检测
            is_speech = self.vad.is_speech(frame, self.sample_rate)
            
            # WebRTC VAD不提供概率，这里根据是否检测到语音给出一个简单的概率值
            probability = 0.9 if is_speech else 0.1
            
            return VADResult(is_speech, probability, frame_duration)
        except Exception as e:
            print(f"VAD处理错误: {e}")
            return VADResult(False, 0.0, frame_duration) 