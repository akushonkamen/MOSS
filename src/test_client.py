import asyncio
import websockets
import json
import sys
import io
import sounddevice as sd
import soundfile as sf
import numpy as np
import base64
from websockets.exceptions import ConnectionClosed
from src.utils.audio import AudioRecorder
import os
import time
import tempfile

async def play_audio(audio_data: bytes):
    """播放音频数据"""
    try:
        # 使用内存流而不是临时文件
        with io.BytesIO(audio_data) as audio_stream:
            data, samplerate = sf.read(audio_stream)
            # 转换为float32类型，避免类型转换的开销
            if data.dtype != np.float32:
                data = data.astype(np.float32)
            # 使用异步方式播放音频
            sd.play(data, samplerate)
            # 等待播放完成，但不阻塞主线程
            while sd.get_stream().active:
                await asyncio.sleep(0.1)
    except Exception as e:
        print(f"播放音频时出错: {str(e)}")
        # 确保清理任何正在播放的流
        try:
            sd.stop()
        except:
            pass

async def connect_with_retry(uri: str, max_retries: int = 3) -> websockets.WebSocketClientProtocol:
    """带重试的WebSocket连接"""
    for i in range(max_retries):
        try:
            return await websockets.connect(
                uri,
                ping_interval=20,  # 20秒发送一次ping
                ping_timeout=60,   # 60秒超时
                close_timeout=60,  # 60秒关闭超时
                max_size=100 * 1024 * 1024,  # 100MB最大消息大小
                max_queue=32  # 增加消息队列大小
            )
        except Exception as e:
            if i == max_retries - 1:
                raise
            print(f"连接失败，{max_retries - i - 1}秒后重试...")
            await asyncio.sleep(1)

async def chat():
    uri = "ws://localhost:8000/ws/chat"
    recorder = None
    websocket = None
    retry_count = 0
    max_retries = 3
    
    while True:  # 外层循环，确保程序不会因为连接断开而退出
        try:
            websocket = await connect_with_retry(uri)
            print("已连接到服务器。")
            print("输入'voice'开始语音对话（自动检测语音），输入'quit'退出。")
            print("提示：说话时会自动开始录音，停顿超过1秒会自动结束录音。")
            
            if not recorder:
                recorder = AudioRecorder(
                    silence_threshold=0.03,    # 静音阈值
                    silence_duration=1.0,      # 静音持续1秒后停止
                    max_duration=10.0,         # 最长录音10秒
                    min_duration=1.0           # 最短录音1秒
                )
            
            # 启动心跳任务
            heartbeat_task = asyncio.create_task(handle_heartbeat(websocket))
            
            while True:
                try:
                    # 检查是否有文本输入
                    user_input = input("你: ")
                    if user_input.lower() == 'quit':
                        return  # 使用return而不是break，确保完全退出
                    
                    if user_input.lower() == 'voice':
                        audio_data = None
                        temp_file = None
                        
                        try:
                            recorder.start_recording()
                            
                            # 持续录音直到检测到应该停止
                            while recorder.record_chunk():
                                await asyncio.sleep(0.01)  # 避免CPU占用过高
                            
                            print("录音结束，正在处理...")
                            # 停止录音并获取音频数据
                            temp_file, audio_data = recorder.stop_recording()
                            
                            # 发送音频数据（带重试）
                            retry_count = 0
                            while retry_count < max_retries:
                                try:
                                    await websocket.send(json.dumps({
                                        "type": "audio",
                                        "data": audio_data.hex(),  # 将二进制数据转换为十六进制字符串
                                        "temperature": 0.7
                                    }))
                                    break  # 发送成功，跳出重试循环
                                except ConnectionClosed:
                                    print(f"\n连接已关闭，尝试重新连接... (尝试 {retry_count + 1}/{max_retries})")
                                    try:
                                        websocket = await connect_with_retry(uri)
                                        retry_count += 1
                                    except Exception as e:
                                        print(f"重连失败: {str(e)}")
                                        if retry_count == max_retries - 1:
                                            raise
                                except Exception as e:
                                    print(f"发送音频数据失败: {str(e)}")
                                    if retry_count == max_retries - 1:
                                        raise
                                    retry_count += 1
                                    await asyncio.sleep(1)
                        except Exception as e:
                            print(f"录音失败: {str(e)}")
                            continue
                        finally:
                            # 清理临时文件
                            if temp_file and os.path.exists(temp_file):
                                try:
                                    os.unlink(temp_file)
                                except Exception as e:
                                    print(f"清理临时文件失败: {str(e)}")
                    else:
                        # 发送文本消息
                        await websocket.send(json.dumps({
                            "type": "text",
                            "text": user_input,
                            "temperature": 0.7
                        }))
                    
                    # 接收响应
                    print("AI: ", end="", flush=True)
                    response_complete = False
                    response_started = False
                    while not response_complete:
                        try:
                            response = await websocket.recv()
                            data = json.loads(response)
                            
                            if data["type"] == "error":
                                print(f"\n错误: {data['content']}")
                                response_complete = True
                            elif data["type"] == "llm_response":
                                response_started = True
                                print(data["content"], end="", flush=True)
                            elif data["type"] == "audio_response":
                                # 解码并播放音频数据
                                audio_data = base64.b64decode(data["data"])
                                await play_audio(audio_data)
                            elif data["type"] == "status":
                                if not response_started:  # 只在响应开始前显示状态
                                    print(f"\n{data['content']}")
                                if "完成" in data["content"]:
                                    response_complete = True
                                    # 如果是语音模式，自动开始下一轮录音
                                    if user_input.lower() == 'voice':
                                        print("\n你: ", end="", flush=True)
                                        recorder.start_recording()
                                        while recorder.record_chunk():
                                            await asyncio.sleep(0.01)
                                        print("录音结束，正在处理...")
                                        temp_file, audio_data = recorder.stop_recording()
                                        await websocket.send(json.dumps({
                                            "type": "audio",
                                            "data": audio_data.hex(),
                                            "temperature": 0.7
                                        }))
                                        if temp_file and os.path.exists(temp_file):
                                            os.unlink(temp_file)
                            elif data["type"] == "ping":
                                await websocket.send(json.dumps({"type": "pong"}))
                            elif data["type"] == "pong":
                                continue
                        except ConnectionClosed:
                            if not response_started:
                                print("\n连接已关闭，尝试重新连接...")
                                websocket = await connect_with_retry(uri)
                                break
                            else:
                                response_complete = True  # 如果响应已经开始，则认为是完成了
                        except json.JSONDecodeError:
                            print("\n收到无效响应")
                            continue
                        except Exception as e:
                            print(f"\n接收响应时出错: {str(e)}")
                            if response_started:
                                response_complete = True
                            break
                    print()  # 换行
                except Exception as e:
                    print(f"处理消息时出错: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"连接服务器失败或发生错误: {str(e)}")
            await asyncio.sleep(1)  # 等待一秒后重试
            continue
        finally:
            # 取消心跳任务
            if 'heartbeat_task' in locals():
                heartbeat_task.cancel()
            # 确保清理资源
            if websocket:
                try:
                    await websocket.close()
                except:
                    pass
            
    if recorder:
        del recorder

async def handle_heartbeat(websocket):
    """处理心跳"""
    try:
        while True:
            await asyncio.sleep(30)  # 每30秒发送一次心跳
            try:
                await websocket.send(json.dumps({"type": "ping"}))
            except:
                break
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(chat())
    except KeyboardInterrupt:
        print("\n程序已退出")
        sys.exit(0) 