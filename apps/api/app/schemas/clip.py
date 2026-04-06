"""Clip Schema"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.clip import ClipStatus


class ClipExportRequest(BaseModel):
    """导出切片请求"""
    event_id: str = Field(..., description="事件ID")
    seconds_before: int = Field(5, ge=0, le=60, description="事件前秒数")
    seconds_after: int = Field(5, ge=0, le=60, description="事件后秒数")
    format: str = Field("mp4", description="输出格式")


class ClipCreate(BaseModel):
    """创建切片记录请求"""
    id: Optional[str] = Field(None, description="切片ID")
    event_id: str = Field(..., description="事件ID")
    stream_id: str = Field(..., description="流ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    seconds_before: int = Field(5, ge=0, le=60)
    seconds_after: int = Field(5, ge=0, le=60)
    format: str = Field("mp4")


class ClipResponse(BaseModel):
    """切片响应"""
    id: str
    event_id: str
    stream_id: str
    file_path: Optional[str]
    file_size: Optional[int]
    duration: Optional[int]
    width: Optional[int]
    height: Optional[int]
    fps: Optional[int]
    codec: Optional[str]
    format: str
    start_time: datetime
    end_time: datetime
    seconds_before: int
    seconds_after: int
    status: ClipStatus
    error_message: Optional[str]
    download_count: int
    last_downloaded_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
