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

1. 启动服务器：
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

2. 运行客户端：
```bash
python -m src.test_client
```

3. 使用方式：
   - 输入 "voice" 开始5秒语音录制
   - 直接输入文本进行对话
   - 输入 "quit" 退出程序

## 项目结构

```
Moss/
├── src/
│   ├── core/           # 核心配置
│   ├── services/       # 服务模块
│   │   ├── llm/       # 大语言模型服务
│   │   ├── stt/       # 语音识别服务
│   │   └── tts/       # 语音合成服务
│   ├── utils/         # 工具函数
│   ├── main.py        # 主服务器
│   └── test_client.py # 测试客户端
├── README.md
└── requirements.txt
```

## 开发计划

- [ ] 支持更多语音模型
- [ ] 添加图形用户界面
- [ ] 优化对话上下文管理
- [ ] 添加更多语音定制选项

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License