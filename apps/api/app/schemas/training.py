"""Training Schema"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class TrainingJobCreate(BaseModel):
    """创建训练任务请求"""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    training_type: str = Field(..., description="训练类型: detection/classification/behavior/end_to_end")
    dataset_config: Dict[str, Any] = Field(default_factory=dict)
    model_cfg: Dict[str, Any] = Field(default_factory=dict, alias="model_config")
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    created_by: str = "system"

    class Config:
        populate_by_name = True


class TrainingJobUpdate(BaseModel):
    """更新训练任务请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    model_cfg: Optional[Dict[str, Any]] = Field(None, alias="model_config")
    hyperparameters: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class TrainingJobResponse(BaseModel):
    """训练任务响应"""
    id: str
    name: str
    description: Optional[str]
    training_type: str
    status: str
    status_message: Optional[str]
    dataset_config: Dict[str, Any]
    model_cfg: Dict[str, Any] = Field(alias="model_config")
    hyperparameters: Dict[str, Any]
    current_epoch: int
    total_epochs: int
    current_step: int
    total_steps: int
    metrics: Optional[Dict[str, Any]]
    best_metric_value: Optional[float]
    best_metric_name: Optional[str]
    output_model_path: Optional[str]
    output_model_size: Optional[int]
    onnx_export_path: Optional[str]
    gpu_ids: Optional[List[int]]
    max_gpu_memory_mb: Optional[int]
    total_training_time_seconds: Optional[int]
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_by: Optional[str]
    cancelled_at: Optional[datetime]
    cancel_reason: Optional[str]

    model_config = {"from_attributes": True, "populate_by_name": True}
