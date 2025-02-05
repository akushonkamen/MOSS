from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import Dict, Any
import io
import base64
from starlette.websockets import WebSocketDisconnect
import asyncio
import time

from .core.config import settings
from .services.llm.llm_service import llm_service
from .services.stt.whisper_service import WhisperService
from .services.tts.edge_tts_service import EdgeTTSService

app = FastAPI(title=settings.APP_NAME)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境下允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
llm_service = llm_service()
stt_service = WhisperService(model_name="large")
tts_service = EdgeTTSService()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 启动心跳任务
    heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
    
    # 生成会话ID
    session_id = str(id(websocket))
    
    # 添加处理状态标志
    is_processing = False
    
    try:
        while True:
            try:
                # 接收用户消息
                message = await websocket.receive_text()
                data: Dict[str, Any] = json.loads(message)
                
                # 如果正在处理消息，跳过新的请求
                if is_processing and data.get("type") != "ping":
                    await websocket.send_json({
                        "type": "status",
                        "content": "正在处理上一条消息，请稍候..."
                    })
                    continue
                
                # 处理用户输入
                if data.get("type") == "audio":
                    is_processing = True
                    try:
                        # 处理音频输入
                        audio_data = bytes.fromhex(data["data"])
                        audio_file = io.BytesIO(audio_data)
                        
                        await websocket.send_json({
                            "type": "status",
                            "content": "正在进行语音识别..."
                        })
                        
                        text = await stt_service.transcribe(audio_file)
                        print(f"语音识别结果: {text}")
                        
                        if not text or len(text.strip()) == 0:
                            await websocket.send_json({
                                "type": "error",
                                "content": "未能识别到有效的语音内容，请重试"
                            })
                            is_processing = False
                            continue
                        
                        await websocket.send_json({
                            "type": "status",
                            "content": f"识别结果: {text}"
                        })
                        
                        # 调用LLM处理语音识别结果
                        await process_llm_request(
                            websocket=websocket,
                            text=text,
                            session_id=session_id,
                            system_prompt=data.get("system_prompt"),
                            temperature=data.get("temperature", 0.7),
                            enable_tts=data.get("enable_tts", True)  # 默认启用TTS
                        )
                    except Exception as e:
                        print(f"处理音频时出错: {str(e)}")
                        await websocket.send_json({
                            "type": "error",
                            "content": f"处理音频时出错: {str(e)}"
                        })
                    finally:
                        is_processing = False
                        
                elif data.get("type") == "text":
                    is_processing = True
                    try:
                        await process_llm_request(
                            websocket=websocket,
                            text=data.get("text", ""),
                            session_id=session_id,
                            system_prompt=data.get("system_prompt"),
                            temperature=data.get("temperature", 0.7),
                            enable_tts=data.get("enable_tts", True)  # 默认启用TTS
                        )
                    except Exception as e:
                        print(f"处理文本时出错: {str(e)}")
                        await websocket.send_json({
                            "type": "error",
                            "content": f"处理文本时出错: {str(e)}"
                        })
                    finally:
                        is_processing = False
                        
                elif data.get("type") == "clear_history":
                    llm_service.clear_conversation(session_id)
                    await websocket.send_json({
                        "type": "status",
                        "content": "会话历史已清除"
                    })
                    
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                print("WebSocket连接已关闭")
                break
            except Exception as e:
                print(f"处理消息时出错: {str(e)}")
                is_processing = False
                try:
                    await websocket.send_json({
                        "type": "error",
                        "content": str(e)
                    })
                except:
                    break
    finally:
        # 清理资源
        heartbeat_task.cancel()
        llm_service.clear_conversation(session_id)
        try:
            await websocket.close()
        except:
            pass

async def process_llm_request(
    websocket: WebSocket,
    text: str,
    session_id: str,
    system_prompt: str = None,
    temperature: float = 0.7,
    enable_tts: bool = True
):
    """统一处理LLM请求"""
    await websocket.send_json({
        "type": "status",
        "content": "正在生成回复..."
    })
    
    # 用于累积文本以进行TTS
    text_buffer = ""
    last_tts_time = 0  # 上次TTS的时间
    min_tts_interval = 0.5  # 最小TTS间隔（秒）
    
    async for response_chunk in llm_service.chat_stream(
        prompt=text,
        session_id=session_id,
        system_prompt=system_prompt,
        temperature=temperature,
    ):
        # 发送文本响应
        await websocket.send_json({
            "type": "llm_response",
            "content": response_chunk
        })
        
        # 累积文本并在适当时机进行TTS
        if enable_tts:
            text_buffer += response_chunk
            current_time = time.time()
            
            # 当遇到句子结束标点符号或累积超过100个字符，且距离上次TTS超过最小间隔时进行TTS
            if ((any(p in text_buffer for p in "。！？!?") or len(text_buffer) >= 100) and 
                (current_time - last_tts_time >= min_tts_interval)):
                try:
                    audio_chunks = []
                    async for audio_chunk in tts_service.synthesize_stream(text_buffer):
                        audio_chunks.append(audio_chunk)
                    
                    # 合并音频数据后一次性发送
                    if audio_chunks:
                        combined_audio = b''.join(audio_chunks)
                        await websocket.send_json({
                            "type": "audio_response",
                            "data": base64.b64encode(combined_audio).decode('utf-8')
                        })
                        last_tts_time = current_time
                except Exception as e:
                    print(f"语音合成出错: {str(e)}")
                
                # 清空缓冲区
                text_buffer = ""
    
    # 处理剩余的文本
    if enable_tts and text_buffer:
        try:
            audio_chunks = []
            async for audio_chunk in tts_service.synthesize_stream(text_buffer):
                audio_chunks.append(audio_chunk)
            
            # 合并音频数据后一次性发送
            if audio_chunks:
                combined_audio = b''.join(audio_chunks)
                await websocket.send_json({
                    "type": "audio_response",
                    "data": base64.b64encode(combined_audio).decode('utf-8')
                })
        except Exception as e:
            print(f"语音合成出错: {str(e)}")
            
    # 发送完成标记
    await websocket.send_json({
        "type": "status",
        "content": "回复完成"
    })

async def send_heartbeat(websocket: WebSocket):
    """发送心跳以保持连接"""
    try:
        while True:
            await asyncio.sleep(20)  # 每20秒发送一次心跳
            try:
                await websocket.send_json({"type": "ping"})
            except:
                break
    except asyncio.CancelledError:
        pass

@app.get("/health")
async def health_check():
    return {"status": "ok"} 