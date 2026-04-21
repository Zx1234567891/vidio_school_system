"""视频流管理路由 - 接入真实 YOLO26 解码+推理运行时"""

from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.stream import Stream, StreamStatus, InputType
from app.schemas.stream import StreamCreate, StreamUpdate
from app.services.stream_runtime import get_stream_runtime

router = APIRouter()


def generate_stream_id() -> str:
    """生成流ID"""
    return f"stream_{uuid.uuid4().hex[:12]}"


def stream_to_dict(stream: Stream) -> Dict[str, Any]:
    """将 Stream ORM 对象转换为字典，并合并运行时状态（检测结果/帧统计）。"""
    rt = get_stream_runtime().get_runtime(stream.id)
    running = bool(rt and rt.running)
    last_dets = rt.last_detections if rt else []
    top = last_dets[0] if last_dets else None
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
        "width": (rt.width if rt and rt.width else stream.width),
        "height": (rt.height if rt and rt.height else stream.height),
        "fps": (rt.fps if rt and rt.fps else stream.fps),
        "bitrate": stream.bitrate,
        "codec": stream.codec,
        "location": stream.location,
        "latitude": stream.latitude,
        "longitude": stream.longitude,
        "total_frames_decoded": (rt.frames_decoded if rt else stream.total_frames_decoded),
        "total_dropped_frames": (rt.frames_dropped if rt else stream.total_dropped_frames),
        "reconnect_count": (rt.reconnect_count if rt else stream.reconnect_count),
        "created_at": stream.created_at.isoformat() if stream.created_at else None,
        "updated_at": stream.updated_at.isoformat() if stream.updated_at else None,
        "started_at": stream.started_at.isoformat() if stream.started_at else None,
        "stopped_at": stream.stopped_at.isoformat() if stream.stopped_at else None,
        # 运行时新增
        "is_running": running,
        "infer_device": (rt.last_device if rt else None),
        "last_infer_ms": (rt.last_infer_ms if rt else None),
        "frames_inferred": (rt.frames_inferred if rt else 0),
        "last_detections": last_dets,
        "behavior_label": (top["class_name"] if top else None),
        "severity": (top["severity"] if top else None),
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

    # auto_start：立即启动解码+推理线程
    started = False
    if getattr(stream_data, "auto_start", True):
        try:
            get_stream_runtime().start(
                stream_id=stream.id,
                url=stream.url,
                input_type=stream.input_type.value,
            )
            stream.status = StreamStatus.RUNNING
            stream.started_at = datetime.utcnow()
            stream.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(stream)
            started = True
        except Exception as e:
            stream.status = StreamStatus.ERROR
            stream.status_message = str(e)
            await db.commit()

    return {
        "code": 0,
        "message": "Stream created" + (" and started" if started else ""),
        "data": stream_to_dict(stream),
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

    # 先停止运行时线程，再软删
    get_stream_runtime().stop(stream_id)

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

    try:
        get_stream_runtime().start(
            stream_id=stream.id,
            url=stream.url,
            input_type=stream.input_type.value,
        )
    except Exception as e:
        stream.status = StreamStatus.ERROR
        stream.status_message = str(e)
        stream.updated_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    stream.status = StreamStatus.RUNNING
    stream.started_at = datetime.utcnow()
    stream.status_message = None
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

    get_stream_runtime().stop(stream_id)

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

    runtime = get_stream_runtime()
    runtime.stop(stream_id)
    try:
        runtime.start(
            stream_id=stream.id,
            url=stream.url,
            input_type=stream.input_type.value,
        )
    except Exception as e:
        stream.status = StreamStatus.ERROR
        stream.status_message = str(e)
        stream.updated_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    stream.status = StreamStatus.RUNNING
    stream.reconnect_count = 0
    stream.status_message = None
    stream.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(stream)

    return {
        "code": 0,
        "message": "Stream restarted successfully",
        "data": stream_to_dict(stream)
    }


@router.get("/browse/local-files")
async def browse_local_files():
    """列出后端可见的视频文件，供前端「添加流」的文件下拉使用。

    扫描 `settings.FILE_BROWSE_ROOTS` 下所有指定扩展名的视频文件，返回
    （容器内的）绝对路径；前端直接把 path 放进 `url` 字段即可创建流。
    """
    from pathlib import Path
    from app.core.config import settings as cfg

    roots = [r.strip() for r in (cfg.FILE_BROWSE_ROOTS or "").split(",") if r.strip()]
    exts = {e.strip().lower() for e in (cfg.FILE_BROWSE_EXTS or "").split(",") if e.strip()}
    limit = int(cfg.FILE_BROWSE_MAX or 200)

    items: List[Dict[str, Any]] = []
    seen = set()
    for root in roots:
        p = Path(root)
        if not p.exists() or not p.is_dir():
            continue
        try:
            root_abs = p.resolve()
        except Exception:
            continue
        for f in root_abs.rglob("*"):
            if len(items) >= limit:
                break
            if not f.is_file():
                continue
            if f.suffix.lower() not in exts:
                continue
            try:
                full = str(f.resolve())
            except Exception:
                full = str(f)
            if full in seen:
                continue
            seen.add(full)
            try:
                rel = str(f.relative_to(root_abs)).replace("\\", "/")
            except Exception:
                rel = f.name
            try:
                size_mb = round(f.stat().st_size / 1024 / 1024, 1)
            except Exception:
                size_mb = 0
            # 显示名：目录名 + 文件名，便于在下拉里快速识别
            parent = f.parent.name or ""
            label = f"{parent}/{f.name}" if parent else f.name
            items.append({
                "path": full,      # 容器/后端可见路径（给 url 用）
                "relative": rel,
                "name": f.name,
                "label": label,
                "size_mb": size_mb,
                "root": str(root_abs),
            })
        if len(items) >= limit:
            break

    items.sort(key=lambda x: x["label"].lower())
    return {"code": 0, "data": {"items": items, "total": len(items), "roots": roots}}


@router.get("/{stream_id}/snapshot")
async def stream_snapshot(stream_id: str):
    """返回最新叠加了检测框的 JPEG 单帧（供前端轮询）"""
    runtime = get_stream_runtime()
    jpeg = runtime.get_snapshot(stream_id)
    if not jpeg:
        # 尚未就绪：轻度等待
        import asyncio as _asyncio
        for _ in range(30):
            jpeg = runtime.get_snapshot(stream_id)
            if jpeg:
                break
            await _asyncio.sleep(0.1)
    if not jpeg:
        raise HTTPException(status_code=503, detail="frame not ready")
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
