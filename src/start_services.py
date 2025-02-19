"""智能工业AI服务启动脚本"""
import os
import sys
import asyncio
import signal
import logging
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime
import cmd
import threading
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.devices.managers.unified_device_manager import UnifiedDeviceManager
from services.devices.discovery.discovery_service import discovery_service
from services.devices.managers.state_manager import state_manager
from services.events.event_bus import event_bus, EventType, Event
from services.agents.dispatch.agent_dispatch_center import agent_dispatch_center
from core.config import settings
from services.devices.device_registry_server import registry_server

class ServiceShell(cmd.Cmd):
    """服务控制命令行"""
    
    intro = "欢迎使用Moss设备控制系统。输入 help 或 ? 查看命令列表。\n"
    prompt = "(Moss) "
    
    def __init__(self, service_manager):
        """初始化命令行
        
        Args:
            service_manager: 服务管理器实例
        """
        super().__init__()
        self.service_manager = service_manager
        self._setup_event_handlers()
        
    def _setup_event_handlers(self):
        """设置事件处理器"""
        # 订阅设备注册事件
        event_bus.subscribe(
            event_type=EventType.DEVICE,
            callback=self._on_device_registered,
            event_name="device_registered"
        )
        
        # 订阅设备注册失败事件
        event_bus.subscribe(
            event_type=EventType.DEVICE,
            callback=self._on_device_registration_failed,
            event_name="device_registration_failed"
        )
        
        # 订阅设备状态变更事件
        event_bus.subscribe(
            event_type=EventType.DEVICE,
            callback=self._on_device_state_changed,
            event_name="state_changed"
        )
        
    def do_list(self, arg):
        """列出所有已注册的设备"""
        try:
            devices = self.service_manager.device_manager.get_all_devices()
            if not devices:
                print("当前没有已注册的设备")
                return
            
            print("\n已注册设备列表:")
            for device in devices:
                print(f"设备ID: {device.device_id}")
                print(f"  名称: {device.name}")
                print(f"  类型: {device.device_type}")
                print(f"  状态: {device.status}")
                print(f"  最后在线时间: {device.last_seen}")
                if hasattr(device, 'capabilities'):
                    print(f"  设备能力: {', '.join(device.capabilities)}")
                if hasattr(device, 'metadata'):
                    print("  元数据:")
                    for key, value in device.metadata.items():
                        print(f"    {key}: {value}")
                if device.error_message:
                    print(f"  错误信息: {device.error_message}")
                print()
        except Exception as e:
            print(f"获取设备列表失败: {str(e)}")
            
    def do_status(self, device_id):
        """查看指定设备的状态
        
        Args:
            device_id: 设备ID
        """
        try:
            if not device_id:
                print("请提供设备ID")
                return
            
            device = self.service_manager.device_manager.get_device(device_id)
            if not device:
                print(f"未找到设备: {device_id}")
                return
            
            print(f"\n设备 {device.name} ({device_id}) 的详细状态:")
            print(f"基本信息:")
            print(f"  - 设备类型: {device.device_type}")
            print(f"  - 当前状态: {device.status}")
            print(f"  - 最后在线: {device.last_seen}")
            
            if hasattr(device, 'capabilities'):
                print("\n设备能力:")
                for cap in device.capabilities:
                    print(f"  - {cap}")
            
            if hasattr(device, 'metadata'):
                print("\n设备元数据:")
                for key, value in device.metadata.items():
                    print(f"  - {key}: {value}")
            
            if device.error_message:
                print(f"\n错误信息: {device.error_message}")
                
            # 获取设备状态
            state = self.service_manager.device_manager._state_manager.get_device_state(device_id)
            if state:
                print("\n实时状态:")
                for key, value in state.items():
                    print(f"  - {key}: {value}")
        except Exception as e:
            print(f"获取设备状态失败: {str(e)}")
            
    def do_scan(self, arg):
        """扫描网络中的设备"""
        print("正在扫描网络中的设备...")
        try:
            # 触发一次设备扫描
            local_ip = self.service_manager.discovery_service._get_local_ip()
            asyncio.run_coroutine_threadsafe(
                self.service_manager.discovery_service._scan_ports(local_ip),
                self.service_manager._loop
            )
            print("扫描已启动，请等待扫描结果...")
        except Exception as e:
            print(f"启动扫描失败: {str(e)}")
            
    def do_monitor(self, arg):
        """实时监控设备状态变化"""
        print("开始监控设备状态变化 (按 Ctrl+C 停止)...")
        try:
            while True:
                devices = self.service_manager.device_manager.get_all_devices()
                if devices:
                    os.system('clear' if os.name == 'posix' else 'cls')
                    print("\n实时设备状态:")
                    for device in devices:
                        status_color = self._get_status_color(device.status)
                        print(f"\n{status_color}设备: {device.name} ({device.device_id})")
                        print(f"状态: {device.status}")
                        print(f"最后更新: {device.last_seen}\033[0m")
                time.sleep(2)  # 每2秒更新一次
        except KeyboardInterrupt:
            print("\n停止监控")
            
    def _get_status_color(self, status):
        """获取状态对应的颜色代码"""
        colors = {
            "online": "\033[92m",  # 绿色
            "offline": "\033[91m",  # 红色
            "error": "\033[93m",    # 黄色
            "registering": "\033[94m"  # 蓝色
        }
        return colors.get(status.lower(), "\033[0m")  # 默认无色
        
    def do_help(self, arg):
        """显示帮助信息"""
        print("""
可用命令:
  list          - 列出所有已注册的设备
  status <id>   - 查看指定设备的详细状态
  scan          - 扫描网络中的设备
  monitor       - 实时监控所有设备状态
  exit          - 退出系统
  help          - 显示此帮助信息
        """)

    async def _on_device_registered(self, event: Event):
        """设备注册成功事件处理"""
        print(f"\n[设备注册] ✅ 新设备注册成功:")
        print(f"  - 名称: {event.data['name']}")
        print(f"  - 类型: {event.data['type']}")
        print(f"  - ID: {event.data['device_id']}")
        if event.data.get('capabilities'):
            print(f"  - 能力: {', '.join(event.data['capabilities'])}")
        print(f"\n{self.prompt}", end='', flush=True)
        
    async def _on_device_registration_failed(self, event: Event):
        """设备注册失败事件处理"""
        print(f"\n[设备注册] ❌ 设备注册失败:")
        print(f"  - ID: {event.data['device_id']}")
        print(f"  - 原因: {event.data['reason']}")
        print(f"\n{self.prompt}", end='', flush=True)
        
    async def _on_device_state_changed(self, event: Event):
        """设备状态变更事件处理"""
        device = self.service_manager.device_manager.get_device(event.data['device_id'])
        if device:
            status_color = self._get_status_color(device.status)
            print(f"\n[状态更新] {status_color}{device.name} ({device.device_id})")
            print(f"  - 状态: {device.status}")
            print(f"  - 时间: {event.data['timestamp']}\033[0m")
            print(f"\n{self.prompt}", end='', flush=True)

class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        """初始化服务管理器"""
        self.logger = logging.getLogger("service_manager")
        self.is_running = False
        self._setup_logging()
        self._loop = None  # 添加事件循环引用
        
        # 核心服务组件
        self.device_manager = UnifiedDeviceManager()
        
    def _setup_logging(self):
        """配置日志系统"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
        
    async def start(self):
        """启动服务"""
        try:
            self.logger.info("正在启动服务...")
            self.is_running = True
            self._loop = asyncio.get_running_loop()  # 保存事件循环引用
            
            # 初始化服务
            await self._initialize_services()
            
            # 订阅事件
            self._subscribe_events()
            
            # 启动命令行界面
            shell = ServiceShell(self)
            shell_thread = threading.Thread(target=shell.cmdloop)
            shell_thread.daemon = True
            shell_thread.start()
            
            # 保持运行直到收到停止信号
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"服务启动失败: {str(e)}")
            raise
        finally:
            # 只有在服务不再运行时才停止
            if not self.is_running:
                await self.stop()
            
    async def stop(self):
        """停止服务"""
        if not self.is_running:
            return
            
        try:
            self.logger.info("正在停止服务...")
            self.is_running = False
            
            # 停止设备发现服务
            await discovery_service.stop()
            
            # 停止设备管理器
            await self.device_manager.shutdown()
            
            # 停止状态管理器
            await state_manager.shutdown()
            
            # 发布服务停止事件
            await event_bus.publish(
                EventType.SYSTEM,
                "service_stopped",
                {
                    "timestamp": datetime.now().isoformat(),
                    "components": ["discovery", "device", "state"]
                }
            )
            
        except Exception as e:
            self.logger.error(f"停止服务失败: {str(e)}")
            
    async def _initialize_services(self):
        """初始化所有服务"""
        try:
            # 初始化设备注册服务
            await registry_server.start(host='0.0.0.0', port=9001)
            self.logger.info("设备注册服务启动完成")
            
            # 初始化设备管理器
            await self.device_manager.initialize()
            
            # 初始化智能体调度中心
            await agent_dispatch_center.initialize()
            
            # 启动设备发现服务
            await discovery_service.start(enable_port_scan=settings.ENABLE_PORT_SCAN)
            
            # 发布服务启动事件
            await event_bus.publish(
                EventType.SYSTEM,
                "service_started",
                {
                    "timestamp": datetime.now().isoformat(),
                    "components": ["registry", "discovery", "device", "state", "agents"]
                }
            )
            
            self.logger.info("所有服务初始化完成")
            
        except Exception as e:
            self.logger.error(f"服务初始化失败: {str(e)}")
            raise
            
    def _subscribe_events(self):
        """订阅事件"""
        # 订阅设备发现事件
        event_bus.subscribe(
            event_type=EventType.DEVICE,
            callback=self._on_device_discovered,
            event_name="device_discovered"
        )
        
        # 订阅设备状态变更事件
        event_bus.subscribe(
            event_type=EventType.DEVICE,
            callback=self._on_device_state_changed,
            event_name="state_changed"
        )
        
        # 订阅错误事件
        event_bus.subscribe(
            event_type=EventType.ERROR,
            callback=self._on_error
        )
            
    async def _on_device_discovered(self, event: Event):
        """设备发现事件处理
        
        Args:
            event: 事件对象
        """
        device_id = event.data["device_id"]
        name = event.data["name"]
        self.logger.info(f"发现新设备: {name} ({device_id})")
        
    async def _on_device_state_changed(self, event: Event):
        """设备状态变更事件处理
        
        Args:
            event: 事件对象
        """
        device_id = event.data["device_id"]
        device = await self.device_manager.get_device(device_id)
        if device:
            self.logger.info(f"设备 {device.name} 状态已更新")
            
    async def _on_error(self, event: Event):
        """错误事件处理
        
        Args:
            event: 事件对象
        """
        self.logger.error(
            f"错误事件: {event.name} - {event.data.get('message', '未知错误')}"
        )

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Moss设备控制系统")
    parser.add_argument("--no-shell", action="store_true", help="不启动交互式命令行")
    args = parser.parse_args()
    
    # 创建服务管理器
    manager = ServiceManager()
    
    # 注册信号处理
    def signal_handler(signum, frame):
        print("\n正在停止服务...")
        manager.is_running = False
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 运行服务
    try:
        if not args.no_shell:
            # 启动带命令行的服务
            shell = ServiceShell(manager)
            shell_thread = threading.Thread(target=shell.cmdloop)
            shell_thread.daemon = True
            shell_thread.start()
            
        asyncio.run(manager.start())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"服务运行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 