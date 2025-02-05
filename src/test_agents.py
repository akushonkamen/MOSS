"""测试 DecoderAgent 和 ExpertAgent 的集成"""
import asyncio
import logging
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.llm.decoderAgent import decoderAgent
from src.services.llm.expertAgent import ExpertAgent
from src.services.devices.base import DeviceInfo, DeviceParameter, DeviceStatus

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_agents():
    """测试 Agent 集成"""
    # 创建测试设备
    ac_params = {
        "power": DeviceParameter(
            name="power",
            type="boolean",
            description="电源状态",
            current_value=False
        ),
        "temperature": DeviceParameter(
            name="temperature",
            type="number",
            description="温度",
            current_value=26,
            min_value=16,
            max_value=30,
            unit="°C"
        ),
        "mode": DeviceParameter(
            name="mode",
            type="string",
            description="运行模式",
            current_value="auto",
            enum_values=["auto", "cool", "heat", "dry", "fan"]
        )
    }
    
    ac_device = DeviceInfo(
        id="ac.living_room",
        name="客厅空调",
        type="ac",
        location="客厅",
        status=DeviceStatus.ONLINE,
        parameters=ac_params,
        capabilities=["temperature_control", "mode_control"]
    )
    
    # 创建可用的控制函数
    available_functions = [
        {
            "name": "ac.set_power",
            "description": "控制空调电源",
            "parameters": {
                "device_id": {
                    "name": "device_id",
                    "type": "string",
                    "description": "设备ID",
                    "required": True
                },
                "power": {
                    "name": "power",
                    "type": "boolean",
                    "description": "电源状态",
                    "required": True
                }
            }
        },
        {
            "name": "ac.set_temperature",
            "description": "设置空调温度",
            "parameters": {
                "device_id": {
                    "name": "device_id",
                    "type": "string",
                    "description": "设备ID",
                    "required": True
                },
                "temperature": {
                    "name": "temperature",
                    "type": "number",
                    "description": "目标温度",
                    "required": True,
                    "min_value": 16,
                    "max_value": 30
                }
            }
        },
        {
            "name": "ac.set_mode",
            "description": "设置空调运行模式",
            "parameters": {
                "device_id": {
                    "name": "device_id",
                    "type": "string",
                    "description": "设备ID",
                    "required": True
                },
                "mode": {
                    "name": "mode",
                    "type": "string",
                    "description": "运行模式",
                    "required": True,
                    "enum_values": ["auto", "cool", "heat", "dry", "fan"]
                }
            }
        }
    ]
    
    # 创建 Agent 实例
    decoder = decoderAgent()
    expert = ExpertAgent()
    
    # 测试用例
    test_inputs = [
        "好热",
        "把温度调高一点",
        "空调开一下",
        "调到24度",
        "把空调关了"
    ]
    
    for user_input in test_inputs:
        print("\n" + "="*80)
        print(f"用户输入: {user_input}")
        print("="*80)
        
        # 1. DecoderAgent: 理解意图
        intent = await decoder.understand_intent(user_input, [ac_device])
        print("\nDecoderAgent 输出:")
        print("-"*40)
        print(f"意图类型: {intent.intent_type}")
        print(f"目标设备: {intent.device_name} ({intent.device_id})")
        print("参数:")
        print(f"  - 操作: {intent.parameters.operation}")
        print(f"  - 方向: {intent.parameters.direction}")
        print(f"  - 目标值: {intent.parameters.target_value}")
        print(f"  - 当前值: {intent.parameters.current_value}")
        print(f"  - 原因: {intent.parameters.reason}")
        
        if intent.intent_type != "unknown":
            # 2. ExpertAgent: 生成动作
            response = await expert.generate_actions(intent, ac_device, available_functions)
            print("\nExpertAgent 输出:")
            print("-"*40)
            print("函数调用:")
            for call in response.function_calls:
                print(f"  - {call.name}:")
                for param, value in call.parameters.items():
                    print(f"      {param}: {value}")
            print(f"\n说明: {response.explanation}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_agents()) 