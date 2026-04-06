"""视频切片模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, JSON, Enum, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class ClipStatus(str, enum.Enum):
    """切片状态"""
    PENDING = "pending"             # 等待导出
    EXPORTING = "exporting"         # 导出中
    COMPLETED = "completed"         # 已完成
    FAILED = "failed"               # 导出失败
    EXPIRED = "expired"             # 已过期


class Clip(Base):
    """视频切片表"""
    __tablename__ = "clips"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    stream_id: Mapped[str] = mapped_column(String(64), ForeignKey("streams.id"), nullable=False, index=True)

    # 文件信息
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 字节
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # 秒
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    codec: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    format: Mapped[str] = mapped_column(String(16), default="mp4")

    # 时间范围
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    seconds_before: Mapped[int] = mapped_column(Integer, default=5)
    seconds_after: Mapped[int] = mapped_column(Integer, default=5)

    # 状态
    status: Mapped[ClipStatus] = mapped_column(Enum(ClipStatus), default=ClipStatus.PENDING)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 导出任务
    export_task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 访问控制
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    last_downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 过期时间
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联关系
    event_id: Mapped[str] = mapped_column(String(64), ForeignKey("events.id"), nullable=False, index=True)
    events: Mapped[list["Event"]] = relationship("Event", back_populates="clip", foreign_keys="Event.clip_id")

    def __repr__(self) -> str:
        return f"<Clip(id={self.id}, stream_id={self.stream_id}, status={self.status})>"
