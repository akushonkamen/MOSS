from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用设置
    APP_NAME: str = "moss"
    DEBUG: bool = True
    
    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API设置
    API_V1_STR: str = "/api/v1"
    
    # CORS设置
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # LLM设置
    OLLAMA_API_URL: str = "http://localhost:11434/api"
    
    # 音频设置
    AUDIO_CACHE_DIR: str = "./media/audio"
    
    class Config:
        env_file = ".env"

settings = Settings() 