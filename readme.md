# MOSS - 工业智能体系统

## 项目概述

MOSS (Manufacturing Operations Smart System) 是一个基于Python的工业智能体系统，专为制造业数字化转型设计。系统采用先进的多智能体架构，集成大语言模型与专家系统，实现工业设备的智能控制、预测性维护和生产优化。

## 核心特性

### 1. 多智能体协同系统
- 解码智能体：理解自然语言指令和工业现场需求
- 专家智能体：基于领域知识生成控制策略
- 记忆智能体：存储和检索历史运行数据
- 学习智能体：持续优化控制策略

### 2. 工业设备管理
- 支持多种工业协议（ModbusTCP、OPC UA、Profinet）
- 实时数据采集与监控
- 设备状态预测与健康管理
- 智能报警和故障诊断

### 3. 生产优化
- 生产计划智能排程
- 能源消耗优化
- 质量控制与追溯
- 设备利用率优化

### 4. 安全机制
- 多层级访问控制
- 操作审计日志
- 数据加密传输
- 应急处理机制

## 技术架构

### 1. 核心服务
- LLM服务：基于大语言模型的指令理解和决策生成
- 设备控制服务：工业设备实时控制和状态监控
- 数据分析服务：生产数据分析和预测建模
- 优化调度服务：生产计划智能排程

### 2. 通信机制
- 工业以太网
- OPC UA
- MQTT
- WebSocket

## 应用场景

### 1. 智能制造
- 柔性生产线控制
- 工艺参数优化
- 质量预测与控制
- 设备预测性维护

### 2. 过程工业
- 连续生产过程控制
- 工艺参数优化
- 能源管理
- 安全监控

### 3. 离散制造
- 生产计划排程
- 设备利用率优化
- 物料配送优化
- 质量追溯

## 部署要求

### 1. 硬件要求
- CPU: Intel Xeon E5 或更高
- 内存: 32GB+
- 存储: 1TB+ SSD
- 网络: 工业以太网

### 2. 软件要求
- OS: Ubuntu 20.04 LTS
- Python 3.10+
- Redis 6.0+
- PostgreSQL 13+

## 快速开始

1. 克隆仓库
```bash
git clone https://github.com/yourusername/moss.git
cd moss
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境
```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置您的环境参数
```

4. 启动服务
```bash
python src/start_services.py
```

## 开发指南

详细的开发文档请参考 `docs/` 目录：
- [架构设计](docs/development/architecture.md)
- [开发规范](docs/development/guidelines.md)
- [API文档](docs/api/README.md)
- [部署指南](docs/deployment/README.md)

## 许可证

本项目采用 Apache 2.0 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献指南

我们欢迎任何形式的贡献，包括但不限于：
- 提交问题和建议
- 改进文档
- 提交代码改进
- 分享使用经验

请参考 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细的贡献指南。