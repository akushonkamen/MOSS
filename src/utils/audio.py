import pyaudio
import wave
import numpy as np
from typing import Optional, Tuple
import tempfile
import os
import time

class AudioRecorder:
    """音频录制工具类"""
    
    def __init__(
        self,
        channels: int = 1,
        rate: int = 16000,  # 恢复到16kHz采样率
        chunk: int = 2048,  # 增大缓冲区以减少溢出
        format: int = pyaudio.paInt16,  # 使用16位整数格式
        silence_threshold: float = 0.03,  # 静音阈值
        silence_duration: float = 1.0,    # 静音持续时间（秒）
        max_duration: float = 10.0,       # 最大录音时间（秒）
        min_duration: float = 1.0         # 最小录音时间（秒）
    ):
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.format = format
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        self.min_duration = min_duration
        
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.frames = []
        self.is_recording = False
        self.recording_start_time = 0
        self.last_sound_time = 0
        
        # 列出所有可用的输入设备
        info = self.audio.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        self.input_device_index = None
        
        # 优先级列表 - 按照设备名称的优先级排序
        priority_devices = [
            "MacBook Pro Microphone",
            "ArasakaStudio-MobileCognitiveDevice Microphone",
            "Microphone",
            "mic",
            "input"
        ]
        
        # 存储所有输入设备
        available_devices = []
        
        # 找到所有输入设备
        for i in range(numdevices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                device_name = device_info.get('name')
                print(f"找到输入设备 {i}: {device_name}")
                available_devices.append((i, device_name))
        
        # 按优先级选择设备
        for priority_name in priority_devices:
            for index, name in available_devices:
                if priority_name.lower() in name.lower():
                    self.input_device_index = index
                    print(f"\n选择输入设备: {name}")
                    break
            if self.input_device_index is not None:
                break
        
        # 如果没有找到优先设备，使用第一个可用设备
        if self.input_device_index is None and available_devices:
            self.input_device_index = available_devices[0][0]
            print(f"\n未找到优先设备，使用第一个可用设备: {available_devices[0][1]}")
        
        if self.input_device_index is None:
            raise Exception("找不到可用的输入设备")
        
    def _is_silent(self, data) -> bool:
        """检测是否为静音"""
        audio_data = np.frombuffer(data, dtype=np.int16)
        rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float32))))
        normalized_rms = rms / 32768.0  # 归一化RMS值
        return normalized_rms < self.silence_threshold
            
    def start_recording(self):
        """开始录音"""
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
            
        self.frames = []
        self.is_recording = True
        self.recording_start_time = time.time()
        self.last_sound_time = self.recording_start_time
        
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.chunk,
                stream_callback=None
            )
            print(f"使用输入设备 {self.input_device_index}")
            print("开始录音...")
            # 等待流准备就绪
            time.sleep(0.1)
        except Exception as e:
            self.is_recording = False
            print(f"启动录音失败: {str(e)}")
            raise
        
    def should_stop_recording(self) -> bool:
        """检查是否应该停止录音"""
        current_time = time.time()
        recording_duration = current_time - self.recording_start_time
        silence_duration = current_time - self.last_sound_time
        
        # 如果超过最大录音时间，停止录音
        if recording_duration >= self.max_duration:
            print("\n达到最大录音时间，停止录音")
            return True
            
        # 如果录音时间超过最小时间且静音持续时间超过阈值，停止录音
        if recording_duration >= self.min_duration and silence_duration >= self.silence_duration:
            print("\n检测到静音，停止录音")
            return True
            
        return False
        
    def record_chunk(self) -> bool:
        """录制一个数据块，返回是否应该继续录音"""
        if not self.stream or not self.is_recording:
            return False
            
        try:
            data = self.stream.read(self.chunk, exception_on_overflow=False)
            if data:
                self.frames.append(data)
                # 更新最后一次检测到声音的时间
                if not self._is_silent(data):
                    self.last_sound_time = time.time()
                    
                # 检查是否应该停止录音
                return not self.should_stop_recording()
                
        except IOError as e:
            if e.errno == pyaudio.paInputOverflowed:
                print("警告: 输入溢出，跳过当前数据块")
                return True
            print(f"录制数据块失败: {str(e)}")
        except Exception as e:
            print(f"录制数据块失败: {str(e)}")
            
        return True
        
    def stop_recording(self) -> Tuple[str, bytes]:
        """
        停止录音并返回临时文件路径和音频数据
        
        Returns:
            Tuple[str, bytes]: (临时文件路径, 音频数据)
        """
        self.is_recording = False
        
        if not self.stream:
            raise Exception("录音流未打开")
            
        try:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
            if not self.frames:
                raise Exception("没有录制到音频数据")
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            )
            
            # 保存音频数据
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.frames))
            
            # 读取音频数据
            with open(temp_file.name, 'rb') as f:
                audio_data = f.read()
                
            return temp_file.name, audio_data
            
        except Exception as e:
            print(f"停止录音失败: {str(e)}")
            raise
        
    def __del__(self):
        """清理资源"""
        self.is_recording = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        try:
            self.audio.terminate()
        except:
            pass 