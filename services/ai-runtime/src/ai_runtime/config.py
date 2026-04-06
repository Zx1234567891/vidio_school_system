"""
AI Runtime 配置
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """AI Runtime 配置"""

    APP_NAME: str = "Campus Guard AI Runtime"
    VERSION: str = "0.2.0"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 9001

    # 模型路径
    MODEL_PATH: str = "./models"

    # 推理配置
    INFERENCE_DEVICE: str = "cpu"  # cpu, cuda
    BATCH_SIZE: int = 1

    # 检测器配置 (YOLO)
    DETECTOR_MODEL: str = "yolov8n"
    DETECTOR_CONFIDENCE: float = 0.3  # 降低阈值以检测小目标
    DETECTOR_IOU: float = 0.45
    DETECTOR_CLASSES: List[str] = [
        "person", "phone", "smoke", "cigarette", "fire",
        "bag", "camera", "backpack", "knife", "mask"
    ]

    # 跟踪器配置 (ByteTrack)
    TRACKER_TYPE: str = "bytetrack"
    TRACKER_TRACK_THRESH: float = 0.5
    TRACKER_MATCH_THRESH: float = 0.8
    TRACKER_TRACK_BUFFER: int = 30

    # 姿态估计配置
    POSE_MODEL: str = "yolov8n-pose"
    POSE_CONFIDENCE: float = 0.5

    # 行为识别配置
    BEHAVIOR_WINDOW_SIZES: List[int] = [16, 32, 64]  # 时序窗口
    BEHAVIOR_CONFIDENCE: float = 0.6

    # 规则引擎配置
    RULE_CHECK_INTERVAL: float = 1.0  # 秒
    DWELL_TIME_THRESHOLD: float = 10.0  # 秒

    # 事件聚合配置
    EVENT_AGGREGATION_WINDOW: float = 5.0  # 秒
    EVENT_MIN_DURATION: float = 1.0  # 秒

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
