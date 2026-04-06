"""审核记录模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, Enum, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class ReviewAction(str, enum.Enum):
    """审核动作"""
    CONFIRM = "confirm"             # 确认事件
    REJECT = "reject"               # 拒绝/误报
    MODIFY = "modify"               # 修改信息
    RESOLVE = "resolve"             # 标记已处理
    IGNORE = "ignore"               # 忽略


class Review(Base):
    """审核记录表"""
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    event_id: Mapped[str] = mapped_column(String(64), ForeignKey("events.id"), nullable=False, unique=True, index=True)

    # 审核人信息
    reviewer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # 审核动作
    action: Mapped[ReviewAction] = mapped_column(Enum(ReviewAction), nullable=False)

    # 修改内容（如果是修改操作）
    original_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    modified_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 审核意见
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联关系
    event: Mapped["Event"] = relationship("Event", back_populates="review")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, event_id={self.event_id}, action={self.action})>"
