#!/bin/bash

# 启动客厅灯服务器
python -m src.services.devices.light_server --id light_001 --name "客厅灯" --port 8001 &

# 启动卧室灯服务器
python -m src.services.devices.light_server --id light_002 --name "卧室灯" --port 8002 &

# 启动客厅空调服务器
python -m src.services.devices.ac_server --id ac_001 --name "客厅空调" --port 8003 &

# 启动卧室窗帘服务器
python -m src.services.devices.curtain_server --id curtain_001 --name "卧室窗帘" --port 8004 &

# 等待所有服务器启动
sleep 2

echo "所有设备服务器已启动"
echo "- 客厅灯: http://localhost:8001"
echo "- 卧室灯: http://localhost:8002"
echo "- 客厅空调: http://localhost:8003"
echo "- 卧室窗帘: http://localhost:8004" 