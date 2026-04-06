"""视频切片管理路由"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional
from datetime import datetime
import uuid
import os

from app.core.database import get_db
from app.core.config import settings
from app.models.clip import Clip, ClipStatus
from app.models.event import Event
from app.schemas.clip import ClipCreate, ClipResponse, ClipExportRequest
from app.schemas.common import ResponseModel

router = APIRouter()


def generate_clip_id() -> str:
    """生成切片ID"""
    return f"clip_{uuid.uuid4().hex[:12]}"


async def export_clip_task(clip_id: str, stream_id: str, start_time: datetime, end_time: datetime):
    """后台导出切片任务"""
    # TODO: 调用 Stream Core 导出切片
    pass


@router.get("", response_model=ResponseModel)
async def list_clips(
    event_id: Optional[str] = Query(None, description="按事件ID筛选"),
    stream_id: Optional[str] = Query(None, description="按流ID筛选"),
    status: Optional[ClipStatus] = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取切片列表"""
    query = select(Clip)

    if event_id:
        query = query.where(Clip.event_id == event_id)
    if stream_id:
        query = query.where(Clip.stream_id == stream_id)
    if status:
        query = query.where(Clip.status == status)

    # 获取总数
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())

    # 分页
    query = query.order_by(desc(Clip.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    clips = result.scalars().all()

    return ResponseModel(
        code=0,
        message="success",
        data={
            "items": [ClipResponse.model_validate(c) for c in clips],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    )


@router.post("/export", response_model=ResponseModel, status_code=status.HTTP_202_ACCEPTED)
async def export_clip(
    request: ClipExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """导出事件切片（异步任务）"""
    # 检查事件是否存在
    event_result = await db.execute(
        select(Event).where(
            and_(Event.id == request.event_id, Event.is_deleted == False)
        )
    )
    event = event_result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {request.event_id} not found"
        )

    # 创建切片记录
    clip_id = generate_clip_id()
    clip = Clip(
        id=clip_id,
        event_id=request.event_id,
        stream_id=event.stream_id,
        start_time=event.start_time,
        end_time=event.end_time or event.start_time,
        seconds_before=request.seconds_before,
        seconds_after=request.seconds_after,
        format=request.format,
        status=ClipStatus.PENDING
    )

    db.add(clip)
    await db.commit()
    await db.refresh(clip)

    # 启动后台导出任务
    # TODO: 使用 Celery 或 RQ 处理后台任务
    # background_tasks.add_task(export_clip_task, clip_id, event.stream_id, ...)

    return ResponseModel(
        code=0,
        message="Clip export task created",
        data={
            "clip_id": clip_id,
            "status": "pending",
            "message": "Export task is queued and will be processed asynchronously"
        }
    )


@router.get("/{clip_id}", response_model=ResponseModel)
async def get_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取切片详情"""
    result = await db.execute(
        select(Clip).where(Clip.id == clip_id)
    )
    clip = result.scalar_one_or_none()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clip {clip_id} not found"
        )

    return ResponseModel(
        code=0,
        message="success",
        data=ClipResponse.model_validate(clip)
    )


@router.get("/{clip_id}/download")
async def download_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db)
):
    """下载切片文件"""
    result = await db.execute(
        select(Clip).where(Clip.id == clip_id)
    )
    clip = result.scalar_one_or_none()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clip {clip_id} not found"
        )

    if clip.status != ClipStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clip is not ready for download, current status: {clip.status.value}"
        )

    if not clip.file_path or not os.path.exists(clip.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip file not found"
        )

    # 更新下载统计
    clip.download_count += 1
    clip.last_downloaded_at = datetime.utcnow()
    await db.commit()

    from fastapi.responses import FileResponse
    return FileResponse(
        clip.file_path,
        filename=f"{clip.id}.{clip.format}",
        media_type="video/mp4"
    )


@router.delete("/{clip_id}", response_model=ResponseModel)
async def delete_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除切片"""
    result = await db.execute(
        select(Clip).where(Clip.id == clip_id)
    )
    clip = result.scalar_one_or_none()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clip {clip_id} not found"
        )

    # 删除文件
    if clip.file_path and os.path.exists(clip.file_path):
        os.remove(clip.file_path)

    await db.delete(clip)
    await db.commit()

    return ResponseModel(
        code=0,
        message="Clip deleted successfully",
        data={"id": clip_id}
    )
