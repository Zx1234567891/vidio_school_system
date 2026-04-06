"""Review Schema"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.review import ReviewAction


class ReviewCreate(BaseModel):
    """创建审核请求"""
    event_id: str = Field(..., description="事件ID")
    reviewer_id: str = Field(..., description="审核人ID")
    reviewer_name: Optional[str] = Field(None, description="审核人姓名")
    action: ReviewAction = Field(..., description="审核动作")
    original_data: Optional[dict] = Field(None, description="原始数据")
    modified_data: Optional[dict] = Field(None, description="修改后数据")
    comment: Optional[str] = Field(None, description="审核意见")


class ReviewResponse(BaseModel):
    """审核响应"""
    id: str
    event_id: str
    reviewer_id: str
    reviewer_name: Optional[str]
    action: ReviewAction
    original_data: Optional[dict]
    modified_data: Optional[dict]
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
