# Moss - 智能语音助手

Moss是一个基于Python的智能语音助手系统，集成了语音识别、大语言模型和语音合成功能。

## 功能特点

1. 语音识别
   - 使用Whisper large模型
   - 支持实时语音输入
   - 高准确度的中文识别

2. 大语言模型
   - 使用llama3.1:latest模型
   - 支持上下文对话
   - 流式输出响应

3. 语音合成
   - 使用Edge TTS
   - 自然流畅的中文语音
   - 实时语音反馈

## 系统要求

- Python 3.10+
- 操作系统：macOS/Linux/Windows
- 麦克风设备
- 音频输出设备

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/Moss.git
cd Moss
```

2. 创建并激活虚拟环境：
```bash
conda create -n moss python=3.10
conda activate moss
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 启动所有服务：
```bash
python src/start_services.py
```

2. 或者分别启动各个服务：

启动设备服务：
```bash
python src/start_device_service.py
```

启动语音服务：
```bash
python src/start_voice_service.py
```

3. 使用方式：
   - 直接对着麦克风说话
   - 支持的语音命令示例：
     - "打开客厅的灯"
     - "把空调温度调到26度"
     - "关闭所有设备"
   - 按Ctrl+C退出程序

## 项目结构

```
Moss/
├── src/
│   ├── core/              # 核心配置
│   ├── services/          # 服务模块
│   │   ├── llm/          # 大语言模型服务
│   │   ├── audio/        # 音频服务
│   │   │   ├── recorder/ # 录音服务
│   │   │   └── player/   # 播放服务
│   │   ├── devices/      # 设备控制服务
│   │   └── tts/         # 语音合成服务
│   ├── start_services.py  # 主服务启动脚本
│   ├── start_voice_service.py  # 语音服务启动脚本
│   └── start_device_service.py # 设备服务启动脚本
├── README.md
└── requirements.txt
```

## 设备支持

当前支持的智能设备：

1. 智能灯光 (SmartLight)
   - 开关控制
   - 亮度调节 (0-100%)

2. 智能空调 (SmartAC)
   - 开关控制
   - 温度调节 (16-30°C)
   - 模式切换 (自动/制冷/制热/除湿/送风)

3. 智能窗帘 (SmartCurtain)
   - 开关控制
   - 位置调节 (0-100%)

## 开发计划

- [x] 支持语音控制
- [x] 集成大语言模型
- [x] 添加设备控制功能
- [ ] 支持更多设备类型
- [ ] 添加图形用户界面
- [ ] 优化对话上下文管理
- [ ] 添加更多语音定制选项

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License