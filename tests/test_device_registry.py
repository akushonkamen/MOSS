import pytest
import asyncio
from datetime import datetime
from src.services.devices.models import (
    DeviceRegistrationValidation, DeviceMetadata, DeviceGroup,
    DeviceStatusReport, DeviceMetrics, DeviceCapability
)
from src.services.devices.registry import DeviceRegistry

@pytest.fixture
def registry():
    """创建设备注册管理器实例"""
    return DeviceRegistry()

@pytest.fixture
def sample_device_registration():
    """创建示例设备注册信息"""
    return DeviceRegistrationValidation(
        device_id="test_light_001",
        name="测试灯",
        type="light",
        port=8001,
        metadata=DeviceMetadata(
            manufacturer="测试制造商",
            model="TL-001",
            firmware="1.0.0",
            protocol="1.0",
            capabilities=[DeviceCapability.POWER, DeviceCapability.BRIGHTNESS]
        )
    )

@pytest.fixture
def sample_group():
    """创建示例设备分组"""
    return DeviceGroup(
        group_id="test_group",
        name="测试分组",
        location="测试位置",
        devices=[]
    )

@pytest.mark.asyncio
async def test_device_registration(registry, sample_device_registration):
    """测试设备注册功能"""
    # 注册设备
    device_info = await registry.register_device(sample_device_registration)
    assert device_info.id == sample_device_registration.device_id
    assert device_info.name == sample_device_registration.name
    assert device_info.type == sample_device_registration.type
    assert device_info.metadata == sample_device_registration.metadata
    
    # 测试重复注册
    with pytest.raises(ValueError):
        await registry.register_device(sample_device_registration)

@pytest.mark.asyncio
async def test_device_unregistration(registry, sample_device_registration):
    """测试设备注销功能"""
    # 注册设备
    await registry.register_device(sample_device_registration)
    
    # 注销设备
    await registry.unregister_device(sample_device_registration.device_id)
    assert registry.get_device(sample_device_registration.device_id) is None
    
    # 测试注销不存在的设备
    with pytest.raises(KeyError):
        await registry.unregister_device("non_existent_device")

@pytest.mark.asyncio
async def test_group_management(registry, sample_device_registration, sample_group):
    """测试分组管理功能"""
    # 注册设备
    await registry.register_device(sample_device_registration)
    
    # 创建分组
    await registry.create_group(sample_group)
    
    # 添加设备到分组
    await registry.add_device_to_group(
        sample_device_registration.device_id,
        sample_group.group_id
    )
    
    # 验证分组信息
    devices = registry.list_devices(sample_group.group_id)
    assert len(devices) == 1
    assert devices[0].id == sample_device_registration.device_id
    
    # 从分组移除设备
    await registry.remove_device_from_group(
        sample_device_registration.device_id,
        sample_group.group_id
    )
    assert len(registry.list_devices(sample_group.group_id)) == 0

@pytest.mark.asyncio
async def test_status_updates(registry, sample_device_registration):
    """测试状态更新功能"""
    # 注册设备
    await registry.register_device(sample_device_registration)
    
    # 创建状态更新
    status = DeviceStatusReport(
        online=True,
        parameters={
            "power": True,
            "brightness": 80
        },
        metrics=DeviceMetrics(
            cpu_usage=10.5,
            memory_usage=25.0,
            network_latency=50.0
        )
    )
    
    # 更新状态
    await registry.update_device_status(sample_device_registration.device_id, status)
    
    # 验证状态更新
    device = registry.get_device(sample_device_registration.device_id)
    assert device.status == status
    assert device.status.online is True
    assert device.status.parameters["brightness"] == 80

@pytest.mark.asyncio
async def test_status_subscription(registry, sample_device_registration):
    """测试状态订阅功能"""
    # 注册设备
    await registry.register_device(sample_device_registration)
    
    # 创建状态更新回调
    status_updates = []
    async def status_callback(device_id, status):
        status_updates.append((device_id, status))
    
    # 订阅状态更新
    registry.subscribe_status(status_callback, sample_device_registration.device_id)
    
    # 更新状态
    status = DeviceStatusReport(
        online=True,
        parameters={"power": True}
    )
    await registry.update_device_status(sample_device_registration.device_id, status)
    
    # 等待异步回调完成
    await asyncio.sleep(0.1)
    
    # 验证回调是否被调用
    assert len(status_updates) == 1
    assert status_updates[0][0] == sample_device_registration.device_id
    assert status_updates[0][1] == status
    
    # 取消订阅
    registry.unsubscribe_status(status_callback, sample_device_registration.device_id)

@pytest.mark.asyncio
async def test_group_subscription(registry, sample_group):
    """测试分组订阅功能"""
    # 创建分组更新回调
    group_updates = []
    async def group_callback(group_id, group):
        group_updates.append((group_id, group))
    
    # 订阅分组更新
    registry.subscribe_group(group_callback)
    
    # 创建分组
    await registry.create_group(sample_group)
    
    # 等待异步回调完成
    await asyncio.sleep(0.1)
    
    # 验证回调是否被调用
    assert len(group_updates) == 1
    assert group_updates[0][0] == sample_group.group_id
    assert group_updates[0][1] == sample_group
    
    # 取消订阅
    registry.unsubscribe_group(group_callback)

@pytest.mark.asyncio
async def test_validation(registry):
    """测试参数验证功能"""
    # 测试无效的设备ID
    with pytest.raises(ValueError):
        await registry.register_device(DeviceRegistrationValidation(
            device_id="invalid id",  # 包含空格
            name="测试设备",
            type="light",
            port=8001,
            metadata=DeviceMetadata(
                manufacturer="测试制造商",
                model="TL-001",
                firmware="1.0.0",
                protocol="1.0"
            )
        ))
    
    # 测试无效的端口号
    with pytest.raises(ValueError):
        await registry.register_device(DeviceRegistrationValidation(
            device_id="test_device",
            name="测试设备",
            type="light",
            port=80,  # 小于1024
            metadata=DeviceMetadata(
                manufacturer="测试制造商",
                model="TL-001",
                firmware="1.0.0",
                protocol="1.0"
            )
        ))
    
    # 测试过长的设备名称
    with pytest.raises(ValueError):
        await registry.register_device(DeviceRegistrationValidation(
            device_id="test_device",
            name="x" * 33,  # 33个字符
            type="light",
            port=8001,
            metadata=DeviceMetadata(
                manufacturer="测试制造商",
                model="TL-001",
                firmware="1.0.0",
                protocol="1.0"
            )
        ))

@pytest.mark.asyncio
async def test_group_error_handling(registry, sample_group):
    """测试分组错误处理"""
    # 测试创建重复分组
    await registry.create_group(sample_group)
    with pytest.raises(ValueError):
        await registry.create_group(sample_group)
    
    # 测试删除不存在的分组
    with pytest.raises(KeyError):
        await registry.delete_group("non_existent_group")
    
    # 测试添加设备到不存在的分组
    with pytest.raises(KeyError):
        await registry.add_device_to_group("device_001", "non_existent_group")
    
    # 测试从不存在的分组移除设备
    with pytest.raises(KeyError):
        await registry.remove_device_from_group("device_001", "non_existent_group")

@pytest.mark.asyncio
async def test_subscription_error_handling(registry, sample_device_registration):
    """测试订阅错误处理"""
    await registry.register_device(sample_device_registration)
    
    # 测试回调函数抛出异常
    async def error_callback(device_id, status):
        raise Exception("Callback error")
    
    registry.subscribe_status(error_callback, sample_device_registration.device_id)
    
    # 更新状态，确保异常被正确处理
    status = DeviceStatusReport(online=True, parameters={})
    await registry.update_device_status(sample_device_registration.device_id, status)
    
    # 测试取消不存在的订阅
    async def dummy_callback(device_id, status):
        pass
    
    registry.unsubscribe_status(dummy_callback, sample_device_registration.device_id)

@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_operations(registry, sample_device_registration):
    """测试并发操作"""
    # 创建多个设备注册任务
    devices = []
    for i in range(10):
        device = DeviceRegistrationValidation(
            device_id=f"test_device_{i}",
            name=f"测试设备{i}",
            type="light",
            port=8001 + i,
            metadata=DeviceMetadata(
                manufacturer="测试制造商",
                model="TL-001",
                firmware="1.0.0",
                protocol="1.0"
            )
        )
        devices.append(device)
    
    # 并发注册设备
    await asyncio.gather(*(
        registry.register_device(device)
        for device in devices
    ))
    
    # 验证所有设备都已注册
    assert len(registry.list_devices()) == 10
    
    # 并发更新状态
    status = DeviceStatusReport(online=True, parameters={})
    await asyncio.gather(*(
        registry.update_device_status(f"test_device_{i}", status)
        for i in range(10)
    ))
    
    # 验证所有设备状态都已更新
    for i in range(10):
        device = registry.get_device(f"test_device_{i}")
        assert device.status is not None
        assert device.status.online is True 