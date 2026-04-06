"""事件模型"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, Float, DateTime, JSON, Enum, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class EventType(str, enum.Enum):
    """事件类型"""
    # 高风险异常行为
    FIGHTING = "fighting"           # 打架斗殴
    BULLYING = "bullying"           # 校园霸凌
    FALLING = "falling"             # 跌倒/昏厥
    SUICIDE_ATTEMPT = "suicide_attempt"  # 疑似轻生
    VANDALISM = "vandalism"         # 破坏公共设施

    # 管理敏感行为
    SMOKING = "smoking"             # 吸烟/点火
    PHONE_USAGE = "phone_usage"     # 长时间使用手机
    CAMERA_TAMPERING = "camera_tampering"  # 遮挡/干扰摄像头

    # 可疑行为
    LOITERING = "loitering"         # 异常徘徊
    INTRUSION = "intrusion"         # 闯入限制区域
    FENCE_CLIMBING = "fence_climbing"  # 翻越围栏


class EventCategory(str, enum.Enum):
    """事件类别"""
    HIGH_RISK = "high_risk"         # 高风险
    SENSITIVE = "sensitive"         # 敏感行为
    SUSPICIOUS = "suspicious"       # 可疑行为
    NORMAL = "normal"               # 正常行为


class Severity(str, enum.Enum):
    """严重级别"""
    CRITICAL = "critical"           # 紧急
    HIGH = "high"                   # 高
    MEDIUM = "medium"               # 中
    LOW = "low"                     # 低


class EventStatus(str, enum.Enum):
    """事件状态"""
    PENDING = "pending"             # 待审核
    CONFIRMED = "confirmed"         # 已确认
    FALSE_POSITIVE = "false_positive"  # 误报
    RESOLVED = "resolved"           # 已处理
    IGNORED = "ignored"             # 已忽略


class Event(Base):
    """事件表"""
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    stream_id: Mapped[str] = mapped_column(String(64), ForeignKey("streams.id"), nullable=False, index=True)

    # 事件类型和分类
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False, index=True)
    category: Mapped[EventCategory] = mapped_column(Enum(EventCategory), nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)

    # 状态
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.PENDING)

    # 时间信息
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 置信度
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # 参与者信息
    participants: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    # 角色分配: aggressor, victim, bystander, mutual
    roles: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 位置信息
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bounding_boxes: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)

    # 关联资源
    snapshot_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    clip_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("clips.id"), nullable=True)

    # AI 推理详情
    ai_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # 包含: model_version, inference_time_ms, feature_vector 等

    # 审核信息
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 处理信息
    handled_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    handle_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联关系
    stream: Mapped["Stream"] = relationship("Stream", back_populates="events")
    clip: Mapped[Optional["Clip"]] = relationship("Clip", back_populates="events", foreign_keys="Event.clip_id")
    review: Mapped[Optional["Review"]] = relationship("Review", back_populates="event", uselist=False)

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, type={self.event_type}, severity={self.severity})>"
