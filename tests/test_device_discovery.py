"""设备发现功能测试"""
import pytest
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from src.services.devices.device_discovery import DeviceDiscoveryService, DeviceInfo

@pytest.fixture
def discovery_service():
    """创建设备发现服务实例"""
    service = DeviceDiscoveryService()
    yield service
    service.stop_discovery()

def test_device_info():
    """测试设备信息数据类"""
    device_info = DeviceInfo(
        device_id="test-device-1",
        name="Test Device 1",
        type="light",
        host="127.0.0.1",
        port=8000,
        properties={"status": "on"},
        last_seen=datetime.now()
    )
    
    assert device_info.device_id == "test-device-1"
    assert device_info.name == "Test Device 1"
    assert device_info.type == "light"
    assert device_info.host == "127.0.0.1"
    assert device_info.port == 8000
    assert device_info.properties == {"status": "on"}
    assert isinstance(device_info.last_seen, datetime)

def test_device_discovery_service_init(discovery_service):
    """测试设备发现服务初始化"""
    assert discovery_service.devices == {}
    assert discovery_service.device_callbacks == set()

def test_device_registration(discovery_service):
    """测试设备注册"""
    discovery_service.register_device(
        device_id="test-device-1",
        name="Test Device 1",
        device_type="light",
        port=8000
    )
    
    # 等待设备注册完成
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
    
    # 验证设备是否已注册
    device = discovery_service.get_device("test-device-1")
    assert device is not None
    assert device.device_id == "test-device-1"
    assert device.name == "Test Device 1"
    assert device.type == "light"
    assert device.port == 8000

def test_device_discovery(discovery_service):
    """测试设备发现"""
    discovered_devices = []
    
    def on_device_found(event: str, device_info: DeviceInfo):
        if event == "added":
            discovered_devices.append(device_info)
            
    # 添加设备回调
    discovery_service.add_device_callback(on_device_found)
    
    # 注册测试设备
    discovery_service.register_device(
        device_id="test-device-1",
        name="Test Device 1",
        device_type="light",
        port=8000
    )
    
    # 等待设备发现
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
    
    # 验证设备是否被发现
    assert len(discovered_devices) == 1
    device = discovered_devices[0]
    assert device.device_id == "test-device-1"
    assert device.name == "Test Device 1"
    assert device.type == "light"
    assert device.port == 8000

def test_device_removal(discovery_service):
    """测试设备移除"""
    removed_devices = []
    
    def on_device_removed(event: str, device_info: DeviceInfo):
        if event == "removed":
            removed_devices.append(device_info)
            
    # 添加设备回调
    discovery_service.add_device_callback(on_device_removed)
    
    # 注册测试设备
    discovery_service.register_device(
        device_id="test-device-1",
        name="Test Device 1",
        device_type="light",
        port=8000
    )
    
    # 等待设备注册
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
    
    # 停止设备发现服务（模拟设备离线）
    discovery_service.stop_discovery()
    
    # 等待设备移除
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
    
    # 验证设备是否被移除
    assert len(removed_devices) == 1
    device = removed_devices[0]
    assert device.device_id == "test-device-1"
    assert device.name == "Test Device 1"
    assert device.type == "light"
    assert device.port == 8000

def test_device_filtering(discovery_service):
    """测试设备过滤"""
    # 注册不同类型的设备
    discovery_service.register_device(
        device_id="light-1",
        name="Light 1",
        device_type="light",
        port=8001
    )
    
    discovery_service.register_device(
        device_id="ac-1",
        name="AC 1",
        device_type="ac",
        port=8002
    )
    
    # 等待设备注册
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
    
    # 获取所有设备
    all_devices = discovery_service.get_devices()
    assert len(all_devices) == 2
    
    # 获取特定类型的设备
    light_devices = discovery_service.get_devices(device_type="light")
    assert len(light_devices) == 1
    assert list(light_devices.keys())[0] == "light-1"
    
    ac_devices = discovery_service.get_devices(device_type="ac")
    assert len(ac_devices) == 1
    assert list(ac_devices.keys())[0] == "ac-1"

def test_device_callback_management(discovery_service):
    """测试设备回调管理"""
    callback_count = 0
    
    def test_callback(event: str, device_info: DeviceInfo):
        nonlocal callback_count
        callback_count += 1
        
    # 添加回调
    discovery_service.add_device_callback(test_callback)
    
    # 注册设备
    discovery_service.register_device(
        device_id="test-device-1",
        name="Test Device 1",
        device_type="light",
        port=8000
    )
    
    # 等待回调执行
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
    
    # 验证回调是否被执行
    assert callback_count == 1
    
    # 移除回调
    discovery_service.remove_device_callback(test_callback)
    
    # 注册另一个设备
    discovery_service.register_device(
        device_id="test-device-2",
        name="Test Device 2",
        device_type="light",
        port=8001
    )
    
    # 等待
    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
    
    # 验证回调没有被执行
    assert callback_count == 1  # 计数器应该保持不变 