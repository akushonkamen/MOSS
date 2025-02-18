"""LLM增强的设备侦察智能体

使用大语言模型增强的设备侦察智能体，提供智能的设备识别和分析能力。
"""
import logging
import json
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
import aiohttp
from datetime import datetime
import asyncio
import uuid

from ..base.base_agent import BaseAgent
from services.events.event_bus import event_bus, EventType

logger = logging.getLogger(__name__)

@dataclass
class ScoutAgentConfig:
    """侦察智能体配置"""
    api_url: str = "http://localhost:11434/api/generate"  # Ollama API地址
    model_name: str = "llama3.1:latest"  # 使用的模型名称
    temperature: float = 0.1    # 较低的temperature以获得更确定的输出
    max_tokens: int = 1000      # 输出长度限制
    timeout: int = 30           # API超时时间

class LLMScoutAgent(BaseAgent):
    """LLM增强的设备侦察智能体"""
    
    def __init__(self, agent_id: str, config: Optional[ScoutAgentConfig] = None):
        """初始化侦察智能体
        
        Args:
            agent_id: 智能体ID
            config: 智能体配置
        """
        super().__init__(agent_id)
        self._config = config or ScoutAgentConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._logger = logging.getLogger(__name__)
        self._is_running = False
        self._analysis_queue = asyncio.Queue()
        self._analysis_task = None
        self._analysis_results = {}
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """初始化智能体"""
        self._is_running = True
        self._analysis_task = asyncio.create_task(self._process_analysis_queue())
        self._logger.info(f"正在初始化LLM增强的侦察智能体 {self.agent_id}...")
        self._session = aiohttp.ClientSession()
        self._logger.info(f"LLM增强的侦察智能体 {self.agent_id} 初始化完成")
        
    async def stop(self) -> None:
        """停止智能体"""
        self._is_running = False
        if self._analysis_task:
            self._analysis_task.cancel()
            try:
                await self._analysis_task
            except asyncio.CancelledError:
                pass
        if self._session:
            await self._session.close()
            self._session = None
        self._logger.info(f"ScoutAgent已停止")
        
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求
        
        Args:
            context: 请求上下文
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            if "response_data" not in context:
                return {}
                
            return await self.analyze_port(context.get("port"), context["response_data"])
                
        except Exception as e:
            logger.error(f"处理请求失败: {str(e)}")
            return {}
            
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM服务
        
        Args:
            prompt: 提示词
            
        Returns:
            str: LLM响应
        """
        if not self._session:
            raise RuntimeError("智能体未初始化")
            
        request = {
            "model": self._config.model_name,
            "prompt": prompt,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "stream": False
        }
        
        try:
            async with self._session.post(
                self._config.api_url,
                json=request,
                timeout=self._config.timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"LLM API调用失败: {error_text}")
                    
                result = await response.json()
                return result.get("response", "")
                    
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            return ""
            
    async def analyze_port(self, port: Optional[int], response_data: dict) -> dict:
        """分析端口响应数据判断是否是设备
        
        Args:
            port: 端口号（可选）
            response_data: 响应数据
            
        Returns:
            dict: 分析结果
        """
        # 将分析任务加入队列
        task_id = str(uuid.uuid4())
        await self._analysis_queue.put((task_id, {"port": port, "response_data": response_data}))
        
        # 等待分析结果
        while task_id not in self._analysis_results:
            await asyncio.sleep(0.1)
            
        # 获取并清理结果
        async with self._lock:
            result = self._analysis_results.pop(task_id)
            
        return result

    async def _process_analysis_queue(self):
        """处理分析队列"""
        while self._is_running:
            try:
                # 获取分析任务
                task_id, port_data = await self._analysis_queue.get()
                
                # 执行分析
                try:
                    result = await self._analyze_single_port(port_data)
                    async with self._lock:
                        self._analysis_results[task_id] = result
                except Exception as e:
                    self._logger.error(f"端口分析失败: {str(e)}")
                    async with self._lock:
                        self._analysis_results[task_id] = {}
                        
                # 标记任务完成
                self._analysis_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"分析队列处理失败: {str(e)}")
                await asyncio.sleep(1)

    async def _analyze_single_port(self, port_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个端口
        
        Args:
            port_data: 端口数据
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            self._logger.info(f"开始分析端口数据: {port_data.get('port', 'unknown')}")
            
            # 准备原始响应数据
            response_data = port_data.get("response_data", {})
            
            # 构建分析提示
            prompt = f"""作为一个智能设备识别专家，请分析以下API响应数据，判断它是否代表一个设备控制接口。

原始响应数据:
{json.dumps(response_data, indent=2, ensure_ascii=False)}

请基于以下几个方面进行分析：
1. 响应内容是否包含典型的设备控制特征
2. API结构是否符合设备控制接口的特点
3. 是否存在设备状态、控制、配置等相关端点
4. 响应中是否包含设备描述、能力或功能信息
5. 如果有API文档（如OpenAPI/Swagger），重点分析其中的端点定义和数据模型

请直接返回一个JSON对象（不要包含任何其他代码或说明），格式如下：

{{
    "is_device": true或false,
    "device_name": "从响应中提取或推断的设备名称",
    "device_type": "从API特征推断的设备类型",
    "brand": "如果能从响应中识别出品牌信息",
    "capabilities": [
        "从响应中识别出的设备功能列表"
    ],
    "api_endpoints": [
        "识别出的关键API端点及其用途"
    ],
    "api_type": "推断的API类型",
    "api_version": "如果能从响应中识别出版本信息",
    "supported_operations": [
        "从响应中识别出的具体操作"
    ],
    "data_models": [
        "识别出的关键数据结构及其用途"
    ],
    "reasoning": "详细解释分析推理过程",
    "confidence": 0.0-1.0之间的置信度
}}

注意：
1. 不要被预设的字段名限制，如果发现其他重要信息也请提取
2. 重点关注API响应的语义特征，而不是固定的字段名
3. 对于不确定的信息，可以基于上下文进行合理推断
4. 如果无法确定是设备控制接口，请给出详细的推理过程
"""
            response = await self._call_llm(prompt)
            
            if not response:
                self._logger.warning("LLM分析返回为空")
                return {}
                
            # 解析结果
            try:
                # 使用正则表达式查找JSON对象
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                    self._logger.debug(f"LLM原始响应: {response}")
                    self._logger.debug(f"提取的JSON字符串: {json_str}")
                    
                    result = json.loads(json_str)
                    self._logger.debug(f"解析后的结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    
                    if isinstance(result, dict) and result.get("is_device"):
                        # 从port_data中提取基本信息
                        metadata = response_data.get("metadata", {})
                        address = metadata.get("address", port_data.get("address", "unknown"))
                        port = metadata.get("port", port_data.get("port", 0))
                        
                        # 构建设备信息
                        device_info = {
                            "device_id": f"{result['device_type']}_{port}",
                            "device_type": result["device_type"],
                            "name": result.get("device_name", f"Device at port {port}"),
                            "brand": result.get("brand", "Unknown"),
                            "capabilities": result.get("capabilities", []),
                            "address": address,
                            "port": port,
                            "metadata": {
                                "address": address,
                                "port": port,
                                "api_type": result.get("api_type"),
                                "api_endpoints": result.get("api_endpoints", []),
                                "confidence": result.get("confidence", 0),
                                "discovery_time": datetime.now().isoformat(),
                                "reasoning": result.get("reasoning", ""),
                                "raw_analysis": result  # 保存完整的分析结果
                            }
                        }
                        
                        # 发布设备发现事件
                        await event_bus.publish(
                            EventType.DEVICE,
                            "device_discovered",
                            device_info
                        )
                        
                        self._logger.info(f"设备注册事件已发布: {device_info['name']} ({device_info['device_id']})")
                    else:
                        self._logger.info(f"\n[分析结果] 端口 {port_data.get('port', 'unknown')}:")
                        self._logger.info(f"结果: 不是设备控制接口")
                        self._logger.info(f"原因: {result.get('reasoning', 'No reasoning provided')}")
                        self._logger.info(f"置信度: {result.get('confidence', 0)}")

                    return result
            except json.JSONDecodeError:
                self._logger.warning(f"LLM返回的结果不是有效的JSON: {response}")
                
            return {}
            
        except Exception as e:
            self._logger.error(f"端口分析失败: {str(e)}")
            return {}