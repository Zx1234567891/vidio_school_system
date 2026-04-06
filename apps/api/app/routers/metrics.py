"""指标和监控路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.stream import Stream, StreamStatus
from app.models.event import Event, EventStatus, Severity
from app.schemas.metrics import MetricsResponse, StreamMetrics, SystemMetrics
from app.schemas.common import ResponseModel

router = APIRouter()


@router.get("/system")
async def get_system_metrics(
    db: AsyncSession = Depends(get_db)
):
    """获取系统级指标"""
    # 统计流状态
    total_streams_result = await db.execute(
        select(func.count()).select_from(Stream).where(Stream.is_deleted == False)
    )
    total_streams = total_streams_result.scalar()

    active_streams_result = await db.execute(
        select(func.count()).select_from(Stream).where(
            and_(Stream.status == StreamStatus.RUNNING, Stream.is_deleted == False)
        )
    )
    active_streams = active_streams_result.scalar()

    error_streams_result = await db.execute(
        select(func.count()).select_from(Stream).where(
            and_(Stream.status == StreamStatus.ERROR, Stream.is_deleted == False)
        )
    )
    error_streams = error_streams_result.scalar()

    # 统计事件
    total_events_result = await db.execute(
        select(func.count()).select_from(Event).where(Event.is_deleted == False)
    )
    total_events = total_events_result.scalar()

    pending_events_result = await db.execute(
        select(func.count()).select_from(Event).where(
            and_(Event.status == EventStatus.PENDING, Event.is_deleted == False)
        )
    )
    pending_events = pending_events_result.scalar()

    # 今日事件统计
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_events_result = await db.execute(
        select(func.count()).select_from(Event).where(
            and_(Event.start_time >= today, Event.is_deleted == False)
        )
    )
    today_events = today_events_result.scalar()

    # 严重事件统计
    critical_events_result = await db.execute(
        select(func.count()).select_from(Event).where(
            and_(
                Event.severity == Severity.CRITICAL,
                Event.status == EventStatus.PENDING,
                Event.is_deleted == False
            )
        )
    )
    critical_events = critical_events_result.scalar()

    # TODO: 获取真实的系统资源使用情况
    import psutil

    metrics = SystemMetrics(
        total_streams=total_streams,
        active_streams=active_streams,
        error_streams=error_streams,
        thread_pool_size=20,  # TODO: 从 Stream Core 获取
        pending_tasks=0,  # TODO: 从任务队列获取
        total_frames_decoded=0,  # TODO: 从 Stream Core 获取
        total_dropped_frames=0,  # TODO: 从 Stream Core 获取
        avg_system_fps=0.0,  # TODO: 计算平均值
        memory_usage_mb=psutil.virtual_memory().used / 1024 / 1024,
        cpu_usage_percent=psutil.cpu_percent(),
        gpu_usage_percent=None,  # TODO: 获取 GPU 使用率
        disk_usage_percent=psutil.disk_usage('/').percent
    )

    return ResponseModel(
        code=0,
        message="success",
        data=metrics
    )


@router.get("/streams")
async def get_streams_metrics(
    db: AsyncSession = Depends(get_db)
):
    """获取所有流的指标"""
    result = await db.execute(
        select(Stream).where(
            and_(Stream.is_deleted == False, Stream.status == StreamStatus.RUNNING)
        )
    )
    streams = result.scalars().all()

    # TODO: 从 Stream Core 获取真实的运行时指标
    metrics_list = []
    for stream in streams:
        metrics = StreamMetrics(
            stream_id=stream.id,
            status=stream.status.value,
            fps=stream.fps or 0.0,
            queue_depth=0,  # TODO: 从 Stream Core 获取
            dropped_frames=stream.total_dropped_frames,
            decode_latency_ms=0.0,  # TODO: 从 Stream Core 获取
            reconnect_count=stream.reconnect_count,
            uptime_seconds=0,  # TODO: 计算运行时间
            total_frames_decoded=stream.total_frames_decoded,
            total_bytes_received=0,  # TODO: 从 Stream Core 获取
            bitrate_kbps=0.0  # TODO: 计算码率
        )
        metrics_list.append(metrics)

    return ResponseModel(
        code=0,
        message="success",
        data=metrics_list
    )


@router.get("/streams/{stream_id}")
async def get_stream_metrics(
    stream_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个流的指标"""
    result = await db.execute(
        select(Stream).where(
            and_(Stream.id == stream_id, Stream.is_deleted == False)
        )
    )
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")

    # TODO: 从 Stream Core 获取真实的运行时指标
    metrics = StreamMetrics(
        stream_id=stream.id,
        status=stream.status.value,
        fps=stream.fps or 0.0,
        queue_depth=0,
        dropped_frames=stream.total_dropped_frames,
        decode_latency_ms=0.0,
        reconnect_count=stream.reconnect_count,
        uptime_seconds=0,
        total_frames_decoded=stream.total_frames_decoded,
        total_bytes_received=0,
        bitrate_kbps=0.0
    )

    return ResponseModel(
        code=0,
        message="success",
        data=metrics
    )


@router.get("/dashboard")
async def get_dashboard_metrics(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    db: AsyncSession = Depends(get_db)
):
    """获取仪表盘数据"""
    start_date = datetime.utcnow() - timedelta(days=days)

    # 事件趋势（按天统计）
    daily_stats = {}
    for i in range(days):
        day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_stats[day] = {"total": 0, "critical": 0, "high": 0}

    events_result = await db.execute(
        select(Event).where(
            and_(Event.start_time >= start_date, Event.is_deleted == False)
        )
    )
    events = events_result.scalars().all()

    for event in events:
        day = event.start_time.strftime("%Y-%m-%d")
        if day in daily_stats:
            daily_stats[day]["total"] += 1
            if event.severity == Severity.CRITICAL:
                daily_stats[day]["critical"] += 1
            elif event.severity == Severity.HIGH:
                daily_stats[day]["high"] += 1

    # 事件类型分布
    event_types = {}
    for event in events:
        event_type = event.event_type.value
        event_types[event_type] = event_types.get(event_type, 0) + 1

    # 流状态分布
    streams_result = await db.execute(
        select(Stream).where(Stream.is_deleted == False)
    )
    streams = streams_result.scalars().all()

    stream_status = {}
    for stream in streams:
        status = stream.status.value
        stream_status[status] = stream_status.get(status, 0) + 1

    return ResponseModel(
        code=0,
        message="success",
        data={
            "event_trend": daily_stats,
            "event_types": event_types,
            "stream_status": stream_status,
            "summary": {
                "total_streams": len(streams),
                "active_streams": sum(1 for s in streams if s.status == StreamStatus.RUNNING),
                "total_events_7d": len(events),
                "pending_reviews": sum(1 for e in events if e.status == EventStatus.PENDING)
            }
        }
    )
