"""系统管理路由"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()


class SystemMetrics(BaseModel):
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_streams: int
    total_events_today: int
    alerts_pending: int


class SystemConfig(BaseModel):
    """系统配置"""
    max_streams: int = 20
    default_fps: int = 25
    alert_retention_days: int = 90
    clip_retention_days: int = 30


@router.get("/metrics")
async def get_metrics():
    """获取系统指标"""
    # P0 阶段返回模拟数据
    return {
        "cpu_percent": 15.5,
        "memory_percent": 42.0,
        "disk_usage_percent": 35.0,
        "active_streams": 0,
        "total_events_today": 0,
        "alerts_pending": 0,
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.get("/config")
async def get_config():
    """获取系统配置"""
    return SystemConfig()


@router.post("/config")
async def update_config(config: SystemConfig):
    """更新系统配置"""
    return config
