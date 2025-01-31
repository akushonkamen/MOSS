import io
import tempfile
import whisper
from typing import BinaryIO
import soundfile as sf
import numpy as np
from .interface import STTService

class WhisperService(STTService):
    """Whisper语音识别服务"""
    
    def __init__(self, model_name: str = "base"):
        """
        初始化Whisper服务
        
        Args:
            model_name: 模型名称 ("tiny", "base", "small", "medium", "large")
        """
        self.model = whisper.load_model(model_name)
        
    async def transcribe(self, audio_data: BinaryIO) -> str:
        """
        将音频转换为文本
        
        Args:
            audio_data: 音频数据流
            
        Returns:
            str: 识别出的文本
        """
        # 将音频数据读入内存
        audio_data.seek(0)
        audio_bytes = audio_data.read()
        
        # 使用临时文件处理音频
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            temp_file.write(audio_bytes)
            temp_file.flush()
            
            # 使用soundfile读取音频
            audio, sample_rate = sf.read(temp_file.name)
            
            # 确保音频是float32类型
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            
            # 如果是立体声，转换为单声道
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
            
            # 使用Whisper进行识别
            result = self.model.transcribe(
                audio,
                language="zh",
                task="transcribe"
            )
            
            return result["text"].strip()
            
    async def transcribe_file(self, file_path: str) -> str:
        """
        从文件转录音频
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            str: 识别出的文本
        """
        # 使用Whisper直接处理文件
        result = self.model.transcribe(
            file_path,
            language="zh",
            task="transcribe"
        )
        
        return result["text"].strip() 