"""Stream Schema"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models.stream import StreamStatus, InputType


class StreamCreate(BaseModel):
    """创建流请求"""
    id: Optional[str] = Field(None, description="流ID，不传则自动生成")
    name: str = Field(..., min_length=1, max_length=255, description="流名称")
    url: str = Field(..., min_length=1, max_length=1024, description="流URL")
    input_type: InputType = Field(InputType.RTSP, description="输入类型")
    target_fps: int = Field(25, ge=1, le=60, description="目标帧率")
    max_queue_size: int = Field(100, ge=10, le=1000, description="最大队列大小")
    ring_buffer_seconds: int = Field(30, ge=5, le=300, description="环形缓冲区时长")
    max_reconnect_attempts: int = Field(5, ge=0, le=20, description="最大重连次数")
    reconnect_interval_ms: int = Field(1000, ge=100, le=60000, description="重连间隔")
    location: Optional[str] = Field(None, max_length=255, description="位置描述")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="纬度")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="经度")
    region_config: Optional[Dict[str, Any]] = Field(None, description="区域配置")


class StreamUpdate(BaseModel):
    """更新流请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = Field(None, min_length=1, max_length=1024)
    target_fps: Optional[int] = Field(None, ge=1, le=60)
    max_queue_size: Optional[int] = Field(None, ge=10, le=1000)
    ring_buffer_seconds: Optional[int] = Field(None, ge=5, le=300)
    max_reconnect_attempts: Optional[int] = Field(None, ge=0, le=20)
    reconnect_interval_ms: Optional[int] = Field(None, ge=100, le=60000)
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    region_config: Optional[Dict[str, Any]] = Field(None)


class StreamResponse(BaseModel):
    """流响应"""
    id: str
    name: str
    url: str
    input_type: InputType
    status: StreamStatus
    status_message: Optional[str]
    target_fps: int
    max_queue_size: int
    ring_buffer_seconds: int
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]
    bitrate: Optional[int]
    codec: Optional[str]
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    total_frames_decoded: int
    total_dropped_frames: int
    reconnect_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]

    class Config:
        from_attributes = True


class StreamListResponse(BaseModel):
    """流列表响应"""
    id: str
    name: str
    url: str
    status: StreamStatus
    input_type: InputType
    target_fps: int
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]
    total_frames_decoded: int
    total_dropped_frames: int
    created_at: datetime

    class Config:
        from_attributes = True
