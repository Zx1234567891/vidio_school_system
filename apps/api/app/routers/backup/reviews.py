"""审核管理路由"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.review import Review, ReviewAction
from app.models.event import Event, EventStatus
from app.schemas.review import ReviewCreate, ReviewResponse
from app.schemas.common import ResponseModel

router = APIRouter()


def generate_review_id() -> str:
    """生成审核ID"""
    return f"rev_{uuid.uuid4().hex[:12]}"


@router.get("", response_model=ResponseModel)
async def list_reviews(
    event_id: Optional[str] = Query(None, description="按事件ID筛选"),
    reviewer_id: Optional[str] = Query(None, description="按审核人筛选"),
    action: Optional[ReviewAction] = Query(None, description="按动作筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取审核记录列表"""
    query = select(Review)

    if event_id:
        query = query.where(Review.event_id == event_id)
    if reviewer_id:
        query = query.where(Review.reviewer_id == reviewer_id)
    if action:
        query = query.where(Review.action == action)

    # 获取总数
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())

    # 分页
    query = query.order_by(desc(Review.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    reviews = result.scalars().all()

    return ResponseModel(
        code=0,
        message="success",
        data={
            "items": [ReviewResponse.model_validate(r) for r in reviews],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建审核记录"""
    # 检查事件是否存在
    event_result = await db.execute(
        select(Event).where(
            and_(Event.id == review_data.event_id, Event.is_deleted == False)
        )
    )
    event = event_result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {review_data.event_id} not found"
        )

    # 创建审核记录
    review = Review(
        id=generate_review_id(),
        event_id=review_data.event_id,
        reviewer_id=review_data.reviewer_id,
        reviewer_name=review_data.reviewer_name,
        action=review_data.action,
        original_data=review_data.original_data,
        modified_data=review_data.modified_data,
        comment=review_data.comment
    )

    # 更新事件状态
    if review_data.action == ReviewAction.CONFIRM:
        event.status = EventStatus.CONFIRMED
    elif review_data.action == ReviewAction.REJECT:
        event.status = EventStatus.FALSE_POSITIVE
    elif review_data.action == ReviewAction.RESOLVE:
        event.status = EventStatus.RESOLVED
    elif review_data.action == ReviewAction.IGNORE:
        event.status = EventStatus.IGNORED

    event.reviewed_by = review_data.reviewer_id
    event.reviewed_at = datetime.utcnow()
    event.review_comment = review_data.comment
    event.updated_at = datetime.utcnow()

    db.add(review)
    await db.commit()
    await db.refresh(review)

    return ResponseModel(
        code=0,
        message="Review created successfully",
        data=ReviewResponse.model_validate(review)
    )


@router.get("/{review_id}", response_model=ResponseModel)
async def get_review(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个审核记录"""
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found"
        )

    return ResponseModel(
        code=0,
        message="success",
        data=ReviewResponse.model_validate(review)
    )


@router.get("/event/{event_id}", response_model=ResponseModel)
async def get_event_review(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取事件的审核记录"""
    result = await db.execute(
        select(Review).where(Review.event_id == event_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review for event {event_id} not found"
        )

    return ResponseModel(
        code=0,
        message="success",
        data=ReviewResponse.model_validate(review)
    )
