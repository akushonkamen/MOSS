"""日志配置模块

提供统一的日志配置和处理器。
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import json
from typing import Dict, Any
from datetime import datetime

from .config import settings

class LearningLogFormatter(logging.Formatter):
    """学习日志格式化器"""
    
    def format(self, record):
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的日志字符串
        """
        # 创建基础日志信息
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        
        # 添加额外信息（如果有）
        if hasattr(record, "learning_data"):
            log_data["learning_data"] = record.learning_data
        if hasattr(record, "learning_result"):
            log_data["learning_result"] = record.learning_result
            
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging():
    """设置日志系统"""
    # 确保日志目录存在
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    
    # 创建学习日志处理器
    learning_log_file = os.path.join(settings.LOG_DIR, "learning.log")
    learning_handler = RotatingFileHandler(
        learning_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    learning_handler.setFormatter(LearningLogFormatter())
    learning_handler.setLevel(logging.DEBUG)
    
    # 获取学习日志记录器
    learning_logger = logging.getLogger("services.agents.scout.learning")
    learning_logger.setLevel(logging.DEBUG)
    learning_logger.addHandler(learning_handler)
    learning_logger.propagate = False  # 防止日志传播到根记录器
    
    # 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
    root_logger.addHandler(console_handler)
    
    # 创建文件处理器
    file_handler = RotatingFileHandler(
        os.path.join(settings.LOG_DIR, "moss.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
    root_logger.addHandler(file_handler) 