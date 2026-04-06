"""应用配置"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置类"""

    # 应用信息
    APP_NAME: str = "Campus Guard AI API"
    VERSION: str = "0.1.0"
    ENV: str = "development"
    DEBUG: bool = True

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # 数据库配置（使用 asyncpg 异步驱动）
    DATABASE_URL: str = "postgresql+asyncpg://campus_guard:campus_guard_secret@localhost:5432/campus_guard"

    # SQLite 备用模式（当 PostgreSQL 不可用时使用）
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_PATH: str = "./data/campus_guard.db"

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
