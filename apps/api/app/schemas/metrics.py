"""Metrics Schema"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class StreamMetrics(BaseModel):
    """单个流的指标"""
    stream_id: str
    status: str
    fps: float
    queue_depth: int
    dropped_frames: int
    decode_latency_ms: float
    reconnect_count: int
    uptime_seconds: int
    total_frames_decoded: int
    total_bytes_received: int
    bitrate_kbps: float


class SystemMetrics(BaseModel):
    """系统级指标"""
    total_streams: int
    active_streams: int
    error_streams: int
    thread_pool_size: int
    pending_tasks: int
    total_frames_decoded: int
    total_dropped_frames: int
    avg_system_fps: float
    memory_usage_mb: float
    cpu_usage_percent: float
    gpu_usage_percent: Optional[float]
    disk_usage_percent: float


class MetricsResponse(BaseModel):
    """指标响应"""
    timestamp: datetime
    system: SystemMetrics
    streams: list[StreamMetrics]
