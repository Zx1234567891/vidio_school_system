"""健康检查路由"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: str
    services: dict


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="健康检查",
    description="检查 API 服务及各依赖组件健康状态"
)
async def health_check():
    """
    健康检查端点

    返回:
    - status: 服务状态 (healthy/degraded/unhealthy)
    - version: API 版本
    - timestamp: 当前时间戳
    - services: 各依赖组件状态
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat(),
        services={
            "api": "up",
            "database": "unknown",  # P1 后实现真实检查
            "redis": "unknown",
            "stream_core": "unknown",
            "ai_runtime": "unknown"
        }
    )


@router.get("/")
async def root():
    """根路径 - API 信息"""
    return {
        "name": "Campus Guard AI API",
        "version": "0.1.0",
        "description": "校园安防视频行为感知系统控制面",
        "docs": "/docs"
    }
