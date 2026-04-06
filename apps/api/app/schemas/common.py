"""通用 Schema"""

from typing import Optional, TypeVar, Generic, List, Any
from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    """统一响应模型"""
    code: int = Field(0, description="状态码，0表示成功")
    message: str = Field("success", description="状态信息")
    data: Optional[Any] = Field(None, description="响应数据")

    model_config = {
        "arbitrary_types_allowed": True
    }


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True
