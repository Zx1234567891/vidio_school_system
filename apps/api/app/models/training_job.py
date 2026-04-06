"""训练任务模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, JSON, Enum, Text, Float
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class TrainingStatus(str, enum.Enum):
    """训练状态"""
    PENDING = "pending"             # 等待中
    PREPARING = "preparing"         # 准备数据
    RUNNING = "running"             # 训练中
    VALIDATING = "validating"       # 验证中
    COMPLETED = "completed"         # 完成
    FAILED = "failed"               # 失败
    CANCELLED = "cancelled"         # 已取消


class TrainingType(str, enum.Enum):
    """训练类型"""
    DETECTION = "detection"         # 检测模型
    CLASSIFICATION = "classification"  # 分类模型
    BEHAVIOR = "behavior"           # 行为识别模型
    END_TO_END = "end_to_end"       # 端到端模型


class TrainingJob(Base):
    """训练任务表"""
    __tablename__ = "training_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 训练类型
    training_type: Mapped[TrainingType] = mapped_column(Enum(TrainingType), nullable=False)

    # 状态
    status: Mapped[TrainingStatus] = mapped_column(Enum(TrainingStatus), default=TrainingStatus.PENDING)
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 数据集配置
    dataset_config: Mapped[dict] = mapped_column(JSON, default=dict)
    # 包含: source, data_path, annotation_path, train_split, val_split 等

    # 模型配置
    model_config: Mapped[dict] = mapped_column(JSON, default=dict)
    # 包含: base_model, epochs, batch_size, learning_rate, image_size 等

    # 训练参数
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict)
    # 包含: optimizer, scheduler, augmentation, early_stopping 等

    # 进度信息
    current_epoch: Mapped[int] = mapped_column(Integer, default=0)
    total_epochs: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)

    # 性能指标
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # 包含: loss, accuracy, precision, recall, f1, mAP 等

    # 最佳指标
    best_metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_metric_name: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # 输出模型
    output_model_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    output_model_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    onnx_export_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # 资源使用
    gpu_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    max_gpu_memory_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_training_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 创建者
    created_by: Mapped[str] = mapped_column(String(64), default="system")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 取消信息
    cancelled_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<TrainingJob(id={self.id}, name={self.name}, status={self.status})>"
