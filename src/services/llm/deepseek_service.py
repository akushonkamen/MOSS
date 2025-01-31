import json
from typing import AsyncGenerator, Optional, List, Dict
import aiohttp
import re
from .interface import LLMService
from ...core.config import settings

class DeepSeekService(LLMService):
    """DeepSeek语言模型服务"""
    
    def __init__(self):
        """初始化DeepSeek服务"""
        self.api_url = "http://localhost:11434/api"  # Ollama API地址
        self.conversations: Dict[str, List[Dict[str, str]]] = {}  # 会话历史
        
    def _get_or_create_conversation(self, session_id: str) -> List[Dict[str, str]]:
        """获取或创建会话历史"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]
        
    def _remove_think_tags(self, text: str) -> str:
        """移除<think>标签及其内容"""
        # 使用非贪婪模式匹配<think>标签及其内容
        pattern = r'<think>.*?</think>'
        return re.sub(pattern, '', text, flags=re.DOTALL)
        
    async def chat_stream(
        self,
        prompt: str,
        session_id: str,
        system_prompt: str = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        流式对话
        
        Args:
            prompt: 用户输入
            session_id: 会话ID
            system_prompt: 系统提示词
            temperature: 温度参数
            
        Yields:
            str: 模型响应片段
        """
        # 获取会话历史
        conversation = self._get_or_create_conversation(session_id)
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": system_prompt or "你是一个有帮助的AI助手。请直接回答问题，不要重复自我介绍。不要输出思考过程。"}
        ]
        
        # 添加历史消息
        messages.extend(conversation)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": "llama3.1:latest",  # 使用llama3.1最新模型
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/chat", json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"API调用失败 (HTTP {response.status}): {error_text}"
                        return
                    
                    buffer = ""
                    response_done = False
                    
                    async for line in response.content:
                        if not line or response_done:
                            continue
                            
                        try:
                            json_line = json.loads(line)
                            
                            # 检查是否是最后一条消息
                            if json_line.get("done", False):
                                response_done = True
                                # 保存对话历史（移除think标签后再保存）
                                if buffer:
                                    clean_buffer = self._remove_think_tags(buffer)
                                    conversation.append({"role": "assistant", "content": clean_buffer})
                                    # 限制历史长度
                                    if len(conversation) > 10:  # 保留最近5轮对话
                                        conversation.pop(0)
                                        conversation.pop(0)
                                continue
                                
                            if "message" in json_line and "content" in json_line["message"]:
                                new_chunk = json_line["message"]["content"]
                                if new_chunk == buffer:  # 跳过重复内容
                                    continue
                                    
                                if new_chunk.startswith(buffer):  # 处理增量内容
                                    increment = new_chunk[len(buffer):]
                                    if increment:  # 只在有新内容时yield
                                        # 处理增量内容中的think标签
                                        clean_increment = self._remove_think_tags(increment)
                                        if clean_increment:  # 确保处理后的内容不为空
                                            yield clean_increment
                                else:  # 处理不连续的内容
                                    if new_chunk:  # 确保不是空内容
                                        # 处理新内容中的think标签
                                        clean_chunk = self._remove_think_tags(new_chunk)
                                        if clean_chunk:  # 确保处理后的内容不为空
                                            yield clean_chunk
                                buffer = new_chunk
                                
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"处理响应时出错: {str(e)}")
                            continue
                            
        except Exception as e:
            yield f"API调用出错: {str(e)}"
            
    def clear_conversation(self, session_id: str):
        """清除指定会话的历史记录"""
        if session_id in self.conversations:
            del self.conversations[session_id]

    async def chat_stream_old(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        使用Ollama API进行流式对话
        """
        data = {
            "model": "deepseek-r1:1.5b",
            "messages": [
                {"role": "system", "content": system_prompt or "你是一个有帮助的AI助手。"},
                {"role": "user", "content": prompt}
            ],
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/chat", json=data) as response:
                async for line in response.content:
                    if line:
                        try:
                            json_line = json.loads(line)
                            if "message" in json_line and "content" in json_line["message"]:
                                yield json_line["message"]["content"]
                        except json.JSONDecodeError:
                            continue 