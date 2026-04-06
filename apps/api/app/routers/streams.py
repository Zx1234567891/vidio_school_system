"""视频流管理路由 - 简化版"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.stream import Stream, StreamStatus, InputType
from app.schemas.stream import StreamCreate, StreamUpdate

router = APIRouter()


def generate_stream_id() -> str:
    """生成流ID"""
    return f"stream_{uuid.uuid4().hex[:12]}"


def stream_to_dict(stream: Stream) -> Dict[str, Any]:
    """将 Stream ORM 对象转换为字典"""
    return {
        "id": stream.id,
        "name": stream.name,
        "url": stream.url,
        "input_type": stream.input_type.value if stream.input_type else None,
        "status": stream.status.value if stream.status else None,
        "status_message": stream.status_message,
        "target_fps": stream.target_fps,
        "max_queue_size": stream.max_queue_size,
        "ring_buffer_seconds": stream.ring_buffer_seconds,
        "width": stream.width,
        "height": stream.height,
        "fps": stream.fps,
        "bitrate": stream.bitrate,
        "codec": stream.codec,
        "location": stream.location,
        "latitude": stream.latitude,
        "longitude": stream.longitude,
        "total_frames_decoded": stream.total_frames_decoded,
        "total_dropped_frames": stream.total_dropped_frames,
        "reconnect_count": stream.reconnect_count,
        "created_at": stream.created_at.isoformat() if stream.created_at else None,
        "updated_at": stream.updated_at.isoformat() if stream.updated_at else None,
        "started_at": stream.started_at.isoformat() if stream.started_at else None,
        "stopped_at": stream.stopped_at.isoformat() if stream.stopped_at else None
    }


@router.get("")
async def list_streams(
    status: Optional[StreamStatus] = Query(None, description="按状态筛选"),
    input_type: Optional[InputType] = Query(None, description="按输入类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取流列表"""
    query = select(Stream).where(Stream.is_deleted == False)

    if status:
        query = query.where(Stream.status == status)
    if input_type:
        query = query.where(Stream.input_type == input_type)

    count_query = select(Stream).where(Stream.is_deleted == False)
    if status:
        count_query = count_query.where(Stream.status == status)
    if input_type:
        count_query = count_query.where(Stream.input_type == input_type)

    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    query = query.order_by(desc(Stream.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    streams = result.scalars().all()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [stream_to_dict(s) for s in streams],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_stream(
    stream_data: StreamCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新流"""
    stream_id = stream_data.id or generate_stream_id()

    existing = await db.execute(select(Stream).where(Stream.id == stream_id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stream with id {stream_id} already exists"
        )

    stream = Stream(
        id=stream_id,
        name=stream_data.name,
        url=stream_data.url,
        input_type=stream_data.input_type,
        target_fps=stream_data.target_fps,
        max_queue_size=stream_data.max_queue_size,
        ring_buffer_seconds=stream_data.ring_buffer_seconds,
        max_reconnect_attempts=stream_data.max_reconnect_attempts,
        reconnect_interval_ms=stream_data.reconnect_interval_ms,
        location=stream_data.location,
        latitude=stream_data.latitude,
        longitude=stream_data.longitude,
        region_config=stream_data.region_config,
        status=StreamStatus.INIT
    )

    db.add(stream)
    await db.commit()
    await db.refresh(stream)

    return {
        "code": 0,
        "message": "Stream created successfully",
        "data": stream_to_dict(stream)
    }


@router.get("/{stream_id}")
async def get_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个流详情"""
    result = await db.execute(
        select(Stream).where(
            and_(Stream.id == stream_id, Stream.is_deleted == False)
        )
    )
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    return {
        "code": 0,
        "message": "success",
        "data": stream_to_dict(stream)
    }


@router.put("/{stream_id}")
async def update_stream(
    stream_id: str,
    stream_data: StreamUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新流配置"""
    result = await db.execute(
        select(Stream).where(
            and_(Stream.id == stream_id, Stream.is_deleted == False)
        )
    )
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    update_data = stream_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stream, field, value)

    stream.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(stream)

    return {
        "code": 0,
        "message": "Stream updated successfully",
        "data": stream_to_dict(stream)
    }


@router.delete("/{stream_id}")
async def delete_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除流（软删除）"""
    result = await db.execute(
        select(Stream).where(
            and_(Stream.id == stream_id, Stream.is_deleted == False)
        )
    )
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    stream.is_deleted = True
    stream.deleted_at = datetime.utcnow()
    stream.status = StreamStatus.STOPPED
    stream.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "code": 0,
        "message": "Stream deleted successfully",
        "data": {"id": stream_id}
    }


@router.post("/{stream_id}/start")
async def start_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db)
):
    """启动流"""
    result = await db.execute(
        select(Stream).where(
            and_(Stream.id == stream_id, Stream.is_deleted == False)
        )
    )
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    stream.status = StreamStatus.RUNNING
    stream.started_at = datetime.utcnow()
    stream.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(stream)

    return {
        "code": 0,
        "message": "Stream started successfully",
        "data": stream_to_dict(stream)
    }


@router.post("/{stream_id}/stop")
async def stop_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db)
):
    """停止流"""
    result = await db.execute(
        select(Stream).where(
            and_(Stream.id == stream_id, Stream.is_deleted == False)
        )
    )
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    stream.status = StreamStatus.STOPPED
    stream.stopped_at = datetime.utcnow()
    stream.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(stream)

    return {
        "code": 0,
        "message": "Stream stopped successfully",
        "data": stream_to_dict(stream)
    }


@router.post("/{stream_id}/restart")
async def restart_stream(
    stream_id: str,
    db: AsyncSession = Depends(get_db)
):
    """重启流"""
    result = await db.execute(
        select(Stream).where(
            and_(Stream.id == stream_id, Stream.is_deleted == False)
        )
    )
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )

    stream.status = StreamStatus.RUNNING
    stream.reconnect_count = 0
    stream.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(stream)

    return {
        "code": 0,
        "message": "Stream restarted successfully",
        "data": stream_to_dict(stream)
    }
