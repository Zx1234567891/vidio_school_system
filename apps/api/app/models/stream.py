"""视频流模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, JSON, Enum, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class StreamStatus(str, enum.Enum):
    """流状态"""
    INIT = "init"
    CONNECTING = "connecting"
    RUNNING = "running"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"
    ERROR = "error"


class InputType(str, enum.Enum):
    """输入类型"""
    RTSP = "rtsp"
    RTMP = "rtmp"
    FILE = "file"


class Stream(Base):
    """视频流表"""
    __tablename__ = "streams"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    input_type: Mapped[InputType] = mapped_column(Enum(InputType), default=InputType.RTSP)

    # 状态
    status: Mapped[StreamStatus] = mapped_column(Enum(StreamStatus), default=StreamStatus.INIT)
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 配置参数
    target_fps: Mapped[int] = mapped_column(Integer, default=25)
    max_queue_size: Mapped[int] = mapped_column(Integer, default=100)
    ring_buffer_seconds: Mapped[int] = mapped_column(Integer, default=30)
    max_reconnect_attempts: Mapped[int] = mapped_column(Integer, default=5)
    reconnect_interval_ms: Mapped[int] = mapped_column(Integer, default=1000)

    # 视频参数（运行时获取）
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    codec: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # 地理位置信息
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 区域配置（ROI、禁区等）
    region_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 统计信息
    total_frames_decoded: Mapped[int] = mapped_column(Integer, default=0)
    total_dropped_frames: Mapped[int] = mapped_column(Integer, default=0)
    reconnect_count: Mapped[int] = mapped_column(Integer, default=0)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联关系
    events: Mapped[list["Event"]] = relationship("Event", back_populates="stream")

    def __repr__(self) -> str:
        return f"<Stream(id={self.id}, name={self.name}, status={self.status})>"
