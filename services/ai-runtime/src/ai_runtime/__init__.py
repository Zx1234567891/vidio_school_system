"""
Campus Guard AI Runtime - P2

AI 推理运行时，提供：
- 目标检测（YOLO）
- 多目标跟踪（ByteTrack）
- 姿态估计（YOLO-Pose）
- 时序行为识别
- 规则引擎
- 事件聚合
"""

__version__ = "0.2.0"

from ai_runtime.models import (
    BehaviorEvent,
    BehaviorResult,
    Detection,
    Track,
    Participant,
    RoleAssignment,
    ParticipantRole,
    EventType,
    EventCategory,
    Severity,
    PipelineResult,
)

from ai_runtime.pipeline import AIPipeline, create_pipeline

__all__ = [
    "BehaviorEvent",
    "BehaviorResult",
    "Detection",
    "Track",
    "Participant",
    "RoleAssignment",
    "ParticipantRole",
    "EventType",
    "EventCategory",
    "Severity",
    "PipelineResult",
    "AIPipeline",
    "create_pipeline",
]
