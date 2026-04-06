"""训练任务管理路由"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.training_job import TrainingJob
from app.schemas.training import TrainingJobCreate, TrainingJobUpdate, TrainingJobResponse
from app.schemas.common import ResponseModel

router = APIRouter()


def generate_job_id() -> str:
    """生成任务ID"""
    return f"train_{uuid.uuid4().hex[:12]}"


@router.get("", response_model=ResponseModel)
async def list_training_jobs(
    status: Optional[str] = Query(None, description="按状态筛选"),
    training_type: Optional[str] = Query(None, description="按类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取训练任务列表"""
    query = select(TrainingJob)

    if status:
        query = query.where(TrainingJob.status == status)
    if training_type:
        query = query.where(TrainingJob.training_type == training_type)

    # 获取总数
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())

    # 分页
    query = query.order_by(desc(TrainingJob.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return ResponseModel(
        code=0,
        message="success",
        data={
            "items": [TrainingJobResponse.model_validate(j) for j in jobs],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    )


@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_training_job(
    job_data: TrainingJobCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建训练任务"""
    job_id = job_data.id or generate_job_id()

    # 检查ID是否已存在
    existing = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Training job with id {job_id} already exists"
        )

    job = TrainingJob(
        id=job_id,
        name=job_data.name,
        description=job_data.description,
        training_type=job_data.training_type,
        dataset_config=job_data.dataset_config,
        model_config=job_data.model_config,
        hyperparameters=job_data.hyperparameters,
        created_by=job_data.created_by,
        status="pending"
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    return ResponseModel(
        code=0,
        message="Training job created successfully",
        data=TrainingJobResponse.model_validate(job)
    )


@router.get("/{job_id}", response_model=ResponseModel)
async def get_training_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取训练任务详情"""
    result = await db.execute(
        select(TrainingJob).where(TrainingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found"
        )

    return ResponseModel(
        code=0,
        message="success",
        data=TrainingJobResponse.model_validate(job)
    )


@router.put("/{job_id}", response_model=ResponseModel)
async def update_training_job(
    job_id: str,
    job_data: TrainingJobUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新训练任务"""
    result = await db.execute(
        select(TrainingJob).where(TrainingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found"
        )

    update_data = job_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    job.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    return ResponseModel(
        code=0,
        message="Training job updated successfully",
        data=TrainingJobResponse.model_validate(job)
    )


@router.post("/{job_id}/start", response_model=ResponseModel)
async def start_training_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """启动训练任务"""
    result = await db.execute(
        select(TrainingJob).where(TrainingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found"
        )

    if job.status not in ["pending", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start job with status {job.status}"
        )

    # TODO: 启动后台训练任务
    job.status = "running"
    job.started_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    return ResponseModel(
        code=0,
        message="Training job started",
        data=TrainingJobResponse.model_validate(job)
    )


@router.post("/{job_id}/cancel", response_model=ResponseModel)
async def cancel_training_job(
    job_id: str,
    reason: Optional[str] = None,
    cancelled_by: str = "system",
    db: AsyncSession = Depends(get_db)
):
    """取消训练任务"""
    result = await db.execute(
        select(TrainingJob).where(TrainingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found"
        )

    if job.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status {job.status}"
        )

    job.status = "cancelled"
    job.cancelled_by = cancelled_by
    job.cancelled_at = datetime.utcnow()
    job.cancel_reason = reason
    job.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    return ResponseModel(
        code=0,
        message="Training job cancelled",
        data=TrainingJobResponse.model_validate(job)
    )


@router.delete("/{job_id}", response_model=ResponseModel)
async def delete_training_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除训练任务"""
    result = await db.execute(
        select(TrainingJob).where(TrainingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found"
        )

    await db.delete(job)
    await db.commit()

    return ResponseModel(
        code=0,
        message="Training job deleted successfully",
        data={"id": job_id}
    )
