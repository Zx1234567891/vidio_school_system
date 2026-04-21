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

    # AI Runtime 集成（阶段 2：解码在 apps/api，推理在 ai-runtime）
    AI_RUNTIME_URL: str = "http://127.0.0.1:9001"
    AI_RUNTIME_TIMEOUT: float = 30.0
    # 每 N 帧调用一次 ai-runtime 推理（节省 GPU，其它帧复用上一次检测结果画框）
    INFER_EVERY_N: int = 2
    # JPEG 编码质量 1-100（上行给 ai-runtime 以及对外 snapshot）
    JPEG_QUALITY: int = 75
    # 解码线程池最大并发流（与 stream-core 设计保持一致）
    MAX_CONCURRENT_STREAMS: int = 20

    # 「浏览本地文件」功能：列出容器/宿主机可见的视频文件供前端下拉选择
    FILE_BROWSE_ROOTS: str = "/project1,./project1,D:/vidio_school_system/project1"  # 逗号分隔的多个根
    FILE_BROWSE_EXTS: str = ".mp4,.avi,.mov,.mkv,.webm"
    FILE_BROWSE_MAX: int = 200

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
