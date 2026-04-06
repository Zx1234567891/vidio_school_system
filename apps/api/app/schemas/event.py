"""Event Schema"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.event import EventType, EventCategory, Severity, EventStatus


class Participant(BaseModel):
    """参与者"""
    track_id: str
    bbox: List[float]  # [x, y, width, height]
    confidence: float


class RoleAssignment(BaseModel):
    """角色分配"""
    track_id: str
    role: str  # aggressor, victim, bystander, mutual
    confidence: float


class EventCreate(BaseModel):
    """创建事件请求"""
    id: Optional[str] = Field(None, description="事件ID，不传则自动生成")
    stream_id: str = Field(..., description="关联流ID")
    event_type: EventType = Field(..., description="事件类型")
    category: EventCategory = Field(..., description="事件类别")
    severity: Severity = Field(..., description="严重级别")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    participants: Optional[List[Participant]] = Field(None, description="参与者")
    roles: Optional[Dict[str, Any]] = Field(None, description="角色分配")
    location: Optional[str] = Field(None, max_length=255, description="位置")
    bounding_boxes: Optional[List[Dict[str, Any]]] = Field(None, description="边界框")
    snapshot_url: Optional[str] = Field(None, max_length=1024, description="快照URL")
    ai_details: Optional[Dict[str, Any]] = Field(None, description="AI推理详情")


class EventUpdate(BaseModel):
    """更新事件请求"""
    status: Optional[EventStatus] = Field(None)
    end_time: Optional[datetime] = Field(None)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    participants: Optional[List[Participant]] = Field(None)
    roles: Optional[Dict[str, Any]] = Field(None)
    reviewed_by: Optional[str] = Field(None)
    review_comment: Optional[str] = Field(None)
    handled_by: Optional[str] = Field(None)
    handle_result: Optional[str] = Field(None)


class EventResponse(BaseModel):
    """事件响应"""
    id: str
    stream_id: str
    event_type: EventType
    category: EventCategory
    severity: Severity
    status: EventStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[int]
    confidence: float
    participants: Optional[List[Dict[str, Any]]]
    roles: Optional[Dict[str, Any]]
    location: Optional[str]
    bounding_boxes: Optional[List[Dict[str, Any]]]
    snapshot_url: Optional[str]
    clip_id: Optional[str]
    ai_details: Optional[Dict[str, Any]]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_comment: Optional[str]
    handled_by: Optional[str]
    handled_at: Optional[datetime]
    handle_result: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """事件列表响应"""
    id: str
    stream_id: str
    event_type: EventType
    category: EventCategory
    severity: Severity
    status: EventStatus
    start_time: datetime
    confidence: float
    location: Optional[str]
    snapshot_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
