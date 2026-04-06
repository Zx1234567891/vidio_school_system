"""事件管理路由"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.models.event import Event, EventType, EventCategory, Severity, EventStatus
from app.schemas.event import EventCreate, EventUpdate, EventResponse, EventListResponse
from app.schemas.common import ResponseModel

router = APIRouter()


def generate_event_id() -> str:
    """生成事件ID"""
    return f"evt_{uuid.uuid4().hex[:12]}"


@router.get("")
async def list_events(
    stream_id: Optional[str] = Query(None, description="按流ID筛选"),
    event_type: Optional[EventType] = Query(None, description="按事件类型筛选"),
    category: Optional[EventCategory] = Query(None, description="按类别筛选"),
    severity: Optional[Severity] = Query(None, description="按严重级别筛选"),
    status: Optional[EventStatus] = Query(None, description="按状态筛选"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取事件列表"""
    query = select(Event).where(Event.is_deleted == False)

    if stream_id:
        query = query.where(Event.stream_id == stream_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    if category:
        query = query.where(Event.category == category)
    if severity:
        query = query.where(Event.severity == severity)
    if status:
        query = query.where(Event.status == status)
    if start_time:
        query = query.where(Event.start_time >= start_time)
    if end_time:
        query = query.where(Event.start_time <= end_time)

    # 获取总数
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())

    # 分页
    query = query.order_by(desc(Event.start_time))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    events = result.scalars().all()

    return ResponseModel(
        code=0,
        message="success",
        data={
            "items": [EventListResponse.model_validate(e) for e in events],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建事件（通常由 AI Runtime 调用）"""
    event_id = event_data.id or generate_event_id()

    event = Event(
        id=event_id,
        stream_id=event_data.stream_id,
        event_type=event_data.event_type,
        category=event_data.category,
        severity=event_data.severity,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        confidence=event_data.confidence,
        participants=[p.model_dump() for p in event_data.participants] if event_data.participants else None,
        roles=event_data.roles,
        location=event_data.location,
        bounding_boxes=event_data.bounding_boxes,
        snapshot_url=event_data.snapshot_url,
        ai_details=event_data.ai_details,
        status=EventStatus.PENDING
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    return ResponseModel(
        code=0,
        message="Event created successfully",
        data=EventResponse.model_validate(event)
    )


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个事件详情"""
    result = await db.execute(
        select(Event).where(
            and_(Event.id == event_id, Event.is_deleted == False)
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )

    return ResponseModel(
        code=0,
        message="success",
        data=EventResponse.model_validate(event)
    )


@router.put("/{event_id}")
async def update_event(
    event_id: str,
    event_data: EventUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新事件"""
    result = await db.execute(
        select(Event).where(
            and_(Event.id == event_id, Event.is_deleted == False)
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )

    update_data = event_data.model_dump(exclude_unset=True)

    # 处理 participants 特殊字段
    if "participants" in update_data and update_data["participants"]:
        update_data["participants"] = [p.model_dump() for p in update_data["participants"]]

    for field, value in update_data.items():
        setattr(event, field, value)

    event.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(event)

    return ResponseModel(
        code=0,
        message="Event updated successfully",
        data=EventResponse.model_validate(event)
    )


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除事件（软删除）"""
    result = await db.execute(
        select(Event).where(
            and_(Event.id == event_id, Event.is_deleted == False)
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )

    event.is_deleted = True
    event.deleted_at = datetime.utcnow()
    event.updated_at = datetime.utcnow()

    await db.commit()

    return ResponseModel(
        code=0,
        message="Event deleted successfully",
        data={"id": event_id}
    )


@router.get("/stats/overview")
async def get_event_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db)
):
    """获取事件统计概览"""
    start_date = datetime.utcnow() - timedelta(days=days)

    query = select(Event).where(
        and_(
            Event.is_deleted == False,
            Event.start_time >= start_date
        )
    )

    result = await db.execute(query)
    events = result.scalars().all()

    # 统计
    stats = {
        "total": len(events),
        "by_type": {},
        "by_severity": {},
        "by_status": {},
        "by_day": {}
    }

    for event in events:
        # 按类型统计
        stats["by_type"][event.event_type.value] = stats["by_type"].get(event.event_type.value, 0) + 1
        # 按严重级别统计
        stats["by_severity"][event.severity.value] = stats["by_severity"].get(event.severity.value, 0) + 1
        # 按状态统计
        stats["by_status"][event.status.value] = stats["by_status"].get(event.status.value, 0) + 1
        # 按天统计
        day = event.start_time.strftime("%Y-%m-%d")
        stats["by_day"][day] = stats["by_day"].get(day, 0) + 1

    return ResponseModel(
        code=0,
        message="success",
        data=stats
    )
