"""设备适配智能体

负责将设备API适配为标准设备管理API。
"""
import logging
import aiohttp
from typing import Dict, Any, Optional, List, Tuple, Set
import json
import os
from datetime import datetime, timedelta
import asyncio
from cachetools import TTLCache
import aiohttp.client_exceptions
from contextlib import asynccontextmanager
import re

from ..base import BaseAgent
from ...devices.managers import unified_device_manager
from ...events.event_bus import event_bus, EventType
from core.errors import AdaptorError, ValidationError, APIGenerationError
from core.config import settings
from .api_templates import get_api_analysis_prompt, create_api_spec_template, create_endpoint_spec

logger = logging.getLogger(__name__)

class APIMapping:
    """API映射定义"""
    
    # 标准端点定义
    STANDARD_ENDPOINTS: Set[str] = {
        "status",           # 状态查询
        "control",          # 控制命令
        "config",           # 配置管理
        "events",          # 事件订阅
        "capabilities",     # 能力查询
        "metrics"          # 指标查询
    }
    
    # 标准能力定义
    STANDARD_CAPABILITIES: Set[str] = {
        "power_control",    # 电源控制
        "status_query",     # 状态查询
        "config_manage",    # 配置管理
        "event_subscribe",  # 事件订阅
        "metric_collect",   # 指标收集
        "firmware_update",  # 固件更新
        "remote_reboot",    # 远程重启
        "diagnostic"        # 诊断功能
    }
    
    @classmethod
    def is_standard_endpoint(cls, endpoint: str) -> bool:
        """检查是否是标准端点
        
        Args:
            endpoint: 端点名称
            
        Returns:
            bool: 是否是标准端点
        """
        return endpoint in cls.STANDARD_ENDPOINTS
        
    @classmethod
    def is_standard_capability(cls, capability: str) -> bool:
        """检查是否是标准能力
        
        Args:
            capability: 能力名称
            
        Returns:
            bool: 是否是标准能力
        """
        return capability in cls.STANDARD_CAPABILITIES

class AdaptorAgent(BaseAgent):
    """设备适配智能体"""
    
    def __init__(self, agent_id: str):
        """初始化适配智能体
        
        Args:
            agent_id: 智能体ID
        """
        super().__init__(agent_id)
        self.capabilities = {
            "adapt_device": self._adapt_device,
            "generate_api": self._generate_api,
            "validate_api": self._validate_api
        }
        self._is_ready = False
        self._session: Optional[aiohttp.ClientSession] = None
        
        # API规范模式定义
        self.api_spec_schema = {
            "device_info": {
                "device_type": "设备类型",
                "name": "设备名称",
                "description": "设备描述",
                "capabilities": ["设备支持的功能列表"],
                "protocol": "通信协议",
                "auth_required": "true/false"
            },
            "api_mapping": {
                "status": {
                    "endpoint": "状态查询端点",
                    "method": "HTTP方法",
                    "parameters": {},
                    "response_mapping": {
                        "power": "原始字段映射",
                        "temperature": "原始字段映射"
                    }
                },
                "control": {
                    "endpoint": "控制端点",
                    "method": "HTTP方法",
                    "parameters": {
                        "required": [],
                        "optional": []
                    }
                }
            },
            "validation_rules": {
                "parameters": {
                    "字段名": {
                        "type": "数据类型",
                        "required": "true/false",
                        "min": "最小值",
                        "max": "最大值",
                        "enum": ["可选值列表"],
                        "format": "格式要求"
                    }
                }
            }
        }
        
        # 初始化缓存
        self._api_cache = TTLCache(maxsize=1000, ttl=7200)  # 2小时缓存
        self._validation_cache = TTLCache(maxsize=1000, ttl=7200)
        self._llm_cache = TTLCache(maxsize=1000, ttl=7200)
        self._lock = asyncio.Lock()
        self._cache_clean_task = None
        
        # 性能优化：并发控制
        self._semaphore = asyncio.Semaphore(10)  # 最多10个并发请求
        self._retry_config = {
            "max_retries": 3,
            "delay": 1,
            "max_delay": 10,
            "backoff_factor": 2
        }
        
    @asynccontextmanager
    async def _http_session(self):
        """HTTP会话上下文管理器"""
        if not self._session:
            self._session = aiohttp.ClientSession()
        try:
            yield self._session
        except Exception as e:
            logger.error(f"HTTP会话错误: {str(e)}")
            if self._session:
                await self._session.close()
                self._session = None
            raise
            
    async def _make_request(self, url: str, retries: int = 3) -> str:
        """
        发起 HTTP 请求并获取响应内容
        
        Args:
            url: 请求的 URL
            retries: 重试次数
            
        Returns:
            str: 响应内容
            
        Raises:
            AdaptorError: 请求失败
        """
        current_retry = 0
        last_error = None
        
        # 尝试不同的文档端点
        doc_endpoints = [
            url,  # 原始 URL
            url.replace('/docs', '/openapi.json'),  # OpenAPI JSON
            url.replace('/docs', '/swagger.json'),  # Swagger JSON
        ]
        
        while current_retry < retries:
            for endpoint in doc_endpoints:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(endpoint) as response:
                            if response.status == 200:
                                content_type = response.headers.get('Content-Type', '')
                                
                                # 处理 JSON 格式
                                if 'application/json' in content_type:
                                    return await response.text()
                                    
                                # 处理 HTML 格式
                                elif 'text/html' in content_type:
                                    html_content = await response.text()
                                    # 使用 LLM 分析 HTML 内容
                                    return html_content
                                    
                                # 处理其他格式
                                else:
                                    self.logger.warning(f"未知的内容类型: {content_type}")
                                    continue
                                    
                except Exception as e:
                    last_error = e
                    self.logger.error(f"HTTP会话错误: {e}")
                    
            current_retry += 1
            if current_retry < retries:
                self.logger.warning(f"请求失败 (重试 {current_retry}/{retries}): {last_error}")
                await asyncio.sleep(1)  # 重试前等待
                
        raise AdaptorError(f"请求失败: {last_error}")
        
    async def initialize(self) -> None:
        """初始化智能体"""
        if self._is_ready:
            return
            
        try:
            self._session = aiohttp.ClientSession()
            self._is_ready = True
            logger.info(f"适配智能体 {self.agent_id} 初始化完成")
            
            # 启动缓存清理任务
            asyncio.create_task(self._clean_cache_periodically())
            
        except Exception as e:
            logger.error(f"初始化适配智能体失败: {str(e)}")
            raise
        
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求
        
        Args:
            context: 请求上下文
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        if not self._is_ready:
            raise RuntimeError("Adaptor agent not initialized")
            
        try:
            action = context.get("action")
            if action not in self.capabilities:
                raise ValueError(f"不支持的操作: {action}")
                
            handler = self.capabilities[action]
            result = await handler(context)
            return result
            
        except Exception as e:
            logger.error(f"处理请求失败: {str(e)}")
            return {
                "error": f"Processing failed: {str(e)}"
            }
            
    async def stop(self) -> None:
        """停止适配智能体"""
        if not self._is_ready:
            return
            
        try:
            if self._session:
                await self._session.close()
            self._is_ready = False
            logger.info(f"适配智能体 {self.agent_id} 已停止")
        except Exception as e:
            logger.error(f"停止适配智能体失败: {str(e)}")
            raise
            
    async def _adapt_device(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """适配设备API
        
        Args:
            context: 包含以下字段的上下文字典：
                - port: 端口号
                - response_data: 原始响应数据
                
        Returns:
            Dict[str, Any]: 适配结果
        """
        try:
            # 从上下文中获取必要信息
            response_data = context.get("response_data", {})
            if not response_data:
                raise AdaptorError("缺少响应数据")

            # 生成API规范
            api_result = await self._generate_api(context)
            if not api_result.get("api_spec"):
                raise APIGenerationError("生成API规范失败: 缺少 api_spec")

            # 验证生成的API
            validation_result = await self._validate_api(
                {
                    "device_id": response_data.get("device_id"),
                    "api_spec": api_result["api_spec"]
                }
            )
            
            if not validation_result["is_valid"]:
                raise ValidationError(
                    f"API验证失败: {validation_result.get('errors', ['未知错误'])}"
                )
                
            # 保存API规范
            await self._save_api_spec(response_data.get("device_id"), api_result["api_spec"])
            
            # 发布API适配完成事件
            await event_bus.publish(
                EventType.DEVICE,
                "device_api_adapted",
                {
                    "device_id": response_data.get("device_id"),
                    "api_spec": api_result["api_spec"],
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {
                "status": "success",
                "device_id": response_data.get("device_id"),
                "api_spec": api_result["api_spec"]
            }
            
        except (AdaptorError, ValidationError, APIGenerationError) as e:
            logger.error(f"适配设备API失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "error_type": e.__class__.__name__
            }
        except Exception as e:
            logger.error(f"适配设备API时发生未知错误: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "error_type": "UnknownError"
            }
            
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """调用LLM服务
        
        Args:
            prompt: 提示词
            
        Returns:
            Optional[str]: LLM响应
        """
        if not self._session:
            raise RuntimeError("代理未初始化")
            
        request = {
            "model": settings.DEFAULT_MODEL,
            "prompt": prompt,
            "temperature": 0.1,  # 使用较低的温度以获得更确定的输出
            "max_tokens": 1000,
            "stream": False
        }
        
        try:
            logger.debug(f"正在调用LLM服务，模型: {settings.DEFAULT_MODEL}")
            logger.debug(f"请求参数: {json.dumps(request, ensure_ascii=False)}")
            
            async with self._session.post(
                settings.OLLAMA_GENERATE_URL,
                json=request,
                timeout=30
            ) as response:
                response_text = await response.text()
                logger.debug(f"LLM响应状态码: {response.status}")
                logger.debug(f"LLM原始响应: {response_text}")
                
                if response.status != 200:
                    raise RuntimeError(f"LLM API调用失败: {response_text}")
                    
                try:
                    result = json.loads(response_text)
                    if not result.get("response"):
                        raise ValueError("LLM响应中缺少 'response' 字段")
                    return result["response"]
                except json.JSONDecodeError as e:
                    raise ValueError(f"LLM响应不是有效的JSON: {str(e)}")
                    
        except asyncio.TimeoutError:
            logger.error("LLM调用超时")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"LLM网络请求错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            return None

    async def _analyze_api_with_llm(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用LLM分析API并生成标准规范
        
        Args:
            api_data: API数据，包含以下字段：
                - endpoints: 端点信息
                - available_endpoints: 可用端点列表
                - metadata: 元数据
                
        Returns:
            Dict[str, Any]: 分析结果，包含API规范
        """
        try:
            # 记录输入数据
            logger.debug(f"API分析输入数据: {json.dumps(api_data, indent=2, ensure_ascii=False)}")
            
            # 使用模板生成提示词
            prompt = get_api_analysis_prompt(api_data)
            
            # 调用LLM服务
            llm_response = await self._call_llm(prompt)
            
            if not llm_response:
                logger.error("LLM分析失败：没有返回结果")
                return {"error": "LLM分析失败"}
                
            # 记录原始LLM响应
            logger.debug(f"LLM原始响应: {llm_response}")
                
            # 尝试解析JSON响应
            try:
                # 使用正则表达式提取JSON对象
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if not json_match:
                    logger.error("未找到有效的JSON响应")
                    return {"error": "无效的LLM响应格式"}
                    
                api_spec = json.loads(json_match.group(0))
                
                # 记录解析后的API规范
                logger.debug(f"解析后的API规范: {json.dumps(api_spec, indent=2, ensure_ascii=False)}")
                
                # 使用基础模板验证和补充缺失字段
                base_spec = create_api_spec_template()
                
                # 合并LLM生成的规范和基础模板
                merged_spec = self._merge_api_specs(base_spec, api_spec)
                
                # 验证必需字段
                validation_result = self._validate_api_spec_structure(merged_spec)
                if not validation_result["is_valid"]:
                    return {"error": validation_result["errors"]}
                
                return {
                    "api_spec": merged_spec,
                    "analysis": {
                        "original_endpoints": api_data.get("endpoints", {}),
                        "available_endpoints": api_data.get("available_endpoints", []),
                        "metadata": api_data.get("metadata", {})
                    }
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"解析LLM响应失败: {str(e)}")
                logger.debug(f"LLM原始响应: {llm_response}")
                return {"error": "解析LLM响应失败"}
                
        except Exception as e:
            logger.error(f"API分析失败: {str(e)}")
            return {"error": f"API分析失败: {str(e)}"}
            
    def _merge_api_specs(self, base_spec: Dict[str, Any], llm_spec: Dict[str, Any]) -> Dict[str, Any]:
        """合并基础API规范和LLM生成的规范
        
        Args:
            base_spec: 基础API规范模板
            llm_spec: LLM生成的API规范
            
        Returns:
            Dict[str, Any]: 合并后的API规范
        """
        merged = base_spec.copy()
        
        # 合并device_info
        if "device_info" in llm_spec:
            merged["device_info"].update(llm_spec["device_info"])
            
        # 合并api_mapping
        if "api_mapping" in llm_spec:
            for endpoint_name, endpoint_data in llm_spec["api_mapping"].items():
                if isinstance(endpoint_data, dict):
                    # 使用端点模板创建标准结构
                    endpoint_spec = create_endpoint_spec(
                        endpoint=endpoint_data.get("endpoint", ""),
                        method=endpoint_data.get("method", "")
                    )
                    # 更新其他字段
                    endpoint_spec.update(endpoint_data)
                    merged["api_mapping"][endpoint_name] = endpoint_spec
                    
        # 合并validation_rules
        if "validation_rules" in llm_spec:
            merged["validation_rules"].update(llm_spec["validation_rules"])
            
        return merged
        
    def _validate_api_spec_structure(self, api_spec: Dict[str, Any]) -> Dict[str, Any]:
        """验证API规范结构
        
        Args:
            api_spec: API规范
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        errors = []
        
        # 验证必需字段
        required_fields = ["device_info", "api_mapping", "validation_rules"]
        missing_fields = [field for field in required_fields if field not in api_spec]
        if missing_fields:
            errors.append(f"缺少必需字段: {', '.join(missing_fields)}")
            
        # 验证device_info
        if "device_info" in api_spec:
            device_info = api_spec["device_info"]
            required_device_info = ["device_type", "name", "capabilities"]
            missing_device_info = [field for field in required_device_info if not device_info.get(field)]
            if missing_device_info:
                errors.append(f"device_info缺少必需字段: {', '.join(missing_device_info)}")
                
        # 验证api_mapping
        if "api_mapping" in api_spec:
            for endpoint_name, endpoint_data in api_spec["api_mapping"].items():
                if not isinstance(endpoint_data, dict):
                    errors.append(f"端点 {endpoint_name} 的数据格式无效")
                    continue
                    
                required_endpoint_fields = ["endpoint", "method"]
                missing_endpoint_fields = [
                    field for field in required_endpoint_fields 
                    if not endpoint_data.get(field)
                ]
                if missing_endpoint_fields:
                    errors.append(
                        f"端点 {endpoint_name} 缺少必需字段: {', '.join(missing_endpoint_fields)}"
                    )
                    
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    async def _generate_api(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成标准API规范
        
        Args:
            context: 包含以下字段的上下文字典：
                - port: 端口号
                - response_data: 原始响应数据
                
        Returns:
            Dict[str, Any]: 生成的API规范
        """
        try:
            response_data = context.get("response_data", {})
            if not response_data:
                return {"error": "缺少响应数据"}
                
            # 准备LLM分析所需的数据
            api_data = {
                "endpoints": response_data.get("endpoints", {}),
                "available_endpoints": response_data.get("available_endpoints", []),
                "metadata": response_data.get("metadata", {})
            }
            
            # 使用LLM分析API并生成标准规范
            llm_result = await self._analyze_api_with_llm(api_data)
            
            if not llm_result.get("api_spec"):
                return {"error": "LLM分析失败"}
                
            return {
                "api_spec": llm_result["api_spec"],
                "analysis": llm_result.get("analysis", {})
            }
            
        except Exception as e:
            logger.error(f"生成API规范失败: {str(e)}")
            return {"error": f"生成API规范失败: {str(e)}"}
            
    async def _validate_api(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """验证API规范
        
        Args:
            context: 请求上下文
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            device_id = context["device_id"]
            api_spec = context["api_spec"]
            
            # 检查缓存
            cache_key = f"validation_{device_id}"
            if cache_key in self._validation_cache:
                logger.info(f"使用缓存的验证结果: {device_id}")
                return self._validation_cache[cache_key]
            
            # 使用LLM验证API规范
            prompt = f"""验证以下API规范是否符合标准要求。
请检查：
1. 必需字段是否完整
2. 端点格式是否正确
3. 能力定义是否合理
4. 特殊功能是否可行

API规范:
{json.dumps(api_spec, indent=2)}

请返回JSON格式的验证结果：
{{
    "is_valid": true/false,
    "errors": ["错误1", "错误2"],
    "warnings": ["警告1", "警告2"],
    "suggestions": ["建议1", "建议2"]
}}

注意：只返回JSON对象，不要包含其他说明文字。"""

            validation_response = await self._call_llm(prompt)
            llm_validation = {}
            if validation_response:
                try:
                    llm_validation = json.loads(validation_response)
                except json.JSONDecodeError:
                    logger.warning("LLM返回的验证结果不是有效的JSON")

            # 合并规则验证和LLM验证结果
            errors = []
            warnings = []
            
            # 规则验证
            required_fields = ["device_info", "api_mapping", "validation_rules"]
            for field in required_fields:
                if field not in api_spec:
                    errors.append(f"缺少必需字段: {field}")
            
            # 验证端点
            api_mapping = api_spec.get("api_mapping", {})
            for endpoint_name in api_mapping:
                if not APIMapping.is_standard_endpoint(endpoint_name):
                    warnings.append(f"非标准端点: {endpoint_name}")
                
                endpoint = api_mapping[endpoint_name]
                required_endpoint_fields = ["endpoint", "method"]
                for field in required_endpoint_fields:
                    if field not in endpoint:
                        errors.append(f"端点 {endpoint_name} 缺少必需字段: {field}")
            
            # 验证能力
            capabilities = api_spec.get("device_info", {}).get("capabilities", [])
            for capability in capabilities:
                if not APIMapping.is_standard_capability(capability):
                    warnings.append(f"非标准能力: {capability}")
            
            # 合并LLM验证结果
            if llm_validation:
                if "errors" in llm_validation:
                    errors.extend(llm_validation["errors"])
                if "warnings" in llm_validation:
                    warnings.extend(llm_validation["warnings"])
            
            # 生成验证结果
            result = {
                "is_valid": len(errors) == 0,
                "device_id": device_id,
                "errors": errors if errors else None,
                "warnings": warnings if warnings else None,
                "suggestions": llm_validation.get("suggestions", []),
                "validated_at": datetime.now().isoformat()
            }
            
            # 缓存结果
            self._validation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"验证API失败: {str(e)}")
            raise ValidationError(f"验证API失败: {str(e)}")
            
    async def _save_api_spec(self, device_id: str, api_spec: Dict[str, Any]) -> None:
        """保存API规范
        
        Args:
            device_id: 设备ID
            api_spec: API规范
        """
        try:
            # 创建API规范目录
            api_dir = os.path.join("data", "api_specs")
            os.makedirs(api_dir, exist_ok=True)
            
            # 保存API规范
            file_path = os.path.join(api_dir, f"{device_id}.json")
            with open(file_path, "w") as f:
                json.dump(api_spec, f, indent=2)
                
            logger.info(f"API规范已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存API规范失败: {str(e)}")
            raise
            
    async def _clean_cache_periodically(self):
        """定期清理过期缓存"""
        while self._is_ready:
            try:
                # 清理过期项
                self._api_cache.expire()
                self._validation_cache.expire()
                self._llm_cache.expire()
                
                # 记录缓存状态
                logger.debug(f"当前缓存状态 - API缓存: {len(self._api_cache)}项, "
                           f"验证缓存: {len(self._validation_cache)}项, "
                           f"LLM缓存: {len(self._llm_cache)}项")
                           
                await asyncio.sleep(300)  # 每5分钟清理一次
                
            except Exception as e:
                logger.error(f"清理缓存失败: {str(e)}")
                await asyncio.sleep(60)  # 出错时等待1分钟后重试 
                await asyncio.sleep(60)  # 出错时等待1分钟后重试 