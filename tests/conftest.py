"""
Pytest configuration file.
"""
import os
import sys
import pytest
import asyncio
import logging
from pathlib import Path

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 设置测试环境变量
os.environ.setdefault('TESTING', 'True')

def pytest_configure(config):
    """Pytest配置"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers",
        "slow: 标记耗时较长的测试"
    )
    config.addinivalue_line(
        "markers",
        "integration: 标记集成测试"
    )
    config.addinivalue_line(
        "markers",
        "e2e: 标记端到端测试"
    )
    config.addinivalue_line(
        "markers",
        "performance: 标记性能测试"
    )

# 配置异步测试
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "test_timeout": int(os.getenv("TEST_TIMEOUT", "30")),
        "test_ports": {
            "light": 8001,
            "ac": 8002,
            "curtain": 8003
        },
        "test_devices": {
            "light": {
                "id": "light_001",
                "name": "客厅灯",
                "type": "light"
            },
            "ac": {
                "id": "ac_001",
                "name": "客厅空调",
                "type": "ac"
            },
            "curtain": {
                "id": "curtain_001",
                "name": "卧室窗帘",
                "type": "curtain"
            }
        }
    }

def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="跳过耗时较长的测试"
    )

@pytest.fixture
def mock_device_discovery(monkeypatch):
    """Mock设备发现服务"""
    class MockDeviceDiscovery:
        def __init__(self):
            self.devices = {}
        
        async def register_device(self, device):
            self.devices[device.device_id] = device
        
        async def get_device_status(self, device_id):
            return {"power": "on"}
        
        async def execute_device_command(self, device_id, command, **params):
            return {"success": True}
    
    return MockDeviceDiscovery()

@pytest.fixture
def mock_smart_home_controller(mock_device_discovery):
    """Mock智能工业AI控制器"""
    from src.services.smart_home.smart_home_controller import Industrial AIController
    
    controller = Industrial AIController()
    controller.device_discovery = mock_device_discovery
    return controller

@pytest.fixture(autouse=True)
def setup_test_env():
    """设置测试环境"""
    # 在每个测试前执行的操作
    yield
    # 在每个测试后执行的操作

@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """设置日志捕获"""
    caplog.set_level('DEBUG') 