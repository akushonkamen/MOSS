from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from typing import Dict, Any, Optional
import logging
from fastapi.middleware.cors import CORSMiddleware
from services.devices.managers import unified_device_manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="设备控制接口",
    description="提供设备的状态查询和控制功能",
    version="1.0.0"
)

# 添加CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """启动时初始化设备管理器"""
    try:
        await unified_device_manager.initialize()
        logger.info("Device manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize device manager: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理资源"""
    try:
        await unified_device_manager.stop()
        logger.info("Device manager shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

@app.get("/")
async def root():
    return {"message": "设备控制服务正在运行"}

@app.get("/devices")
async def list_devices() -> Dict[str, Any]:
    """获取所有已注册设备列表
    
    Returns:
        Dict[str, Any]: 包含设备列表的字典
    """
    try:
        devices = await unified_device_manager.list_devices()
        return {"devices": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/devices/{device_id}/status")
async def get_device_status(device_id: str) -> Dict[str, Any]:
    """获取指定设备的状态
    
    Args:
        device_id: 设备ID
        
    Returns:
        Dict[str, Any]: 包含设备当前状态的字典
    """
    try:
        status = await unified_device_manager.get_device_state(device_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        return status
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/devices/{device_id}/power/{action}")
async def control_device_power(device_id: str, action: str) -> Dict[str, str]:
    """控制设备电源
    
    Args:
        device_id: 设备ID
        action: 操作类型 (on/off)
        
    Returns:
        Dict[str, str]: 操作结果
    """
    if action not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'on' or 'off'")
    
    try:
        command = "power_on" if action == "on" else "power_off"
        result = await unified_device_manager.execute_device_command(device_id, command)
        return {"status": "success", "message": f"Device {device_id} powered {action}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/devices/{device_id}/command")
async def execute_device_command(device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """执行设备命令
    
    Args:
        device_id: 设备ID
        command: 命令参数字典
        
    Returns:
        Dict[str, Any]: 命令执行结果
    """
    try:
        result = await unified_device_manager.execute_device_command(
            device_id,
            command.get("command"),
            command.get("parameters")
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 