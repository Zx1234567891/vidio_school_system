"""
统一事件 Schema - 核心数据结构

所有模块必须围绕此 Schema 协作，不允许私自定义重复字段。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import uuid


# ============ 基础枚举 ============

class Severity(str, Enum):
    """事件严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(str, Enum):
    """审核状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ParticipantRole(str, Enum):
    """参与者角色 - 用于多人交互行为"""
    AGGRESSOR = "aggressor"    # 攻击方
    VICTIM = "victim"          # 受害方
    BYSTANDER = "bystander"    # 旁观者
    MUTUAL = "mutual"          # 互为攻击方


class EventCategory(str, Enum):
    """事件大类"""
    HIGH_RISK = "high_risk"        # 高风险异常
    MANAGEMENT_SENSITIVE = "management_sensitive"  # 管理敏感
    SUSPICIOUS = "suspicious"      # 可疑行为
    NORMAL = "normal"             # 正常行为


class EventType(str, Enum):
    """具体事件类型"""
    # 高风险
    FIGHTING = "fighting"                  # 打架斗殴 (互殴)
    BULLYING = "bullying"                 # 校园霸凌 (单向攻击)
    FALLING = "falling"                   # 跌倒/昏厥
    SUICIDE_RISK = "suicide_risk"         # 疑似轻生
    VANDALISM = "vandalism"               # 破坏公共设施

    # 管理敏感
    SMOKING = "smoking"                   # 吸烟
    PHONE_USE = "phone_use"               # 长时间使用手机
    CAMERA_BLOCKING = "camera_blocking"    # 遮挡摄像头

    # 可疑行为
    LOITERING = "loitering"               # 异常徘徊
    PROLONGED_STAY = "prolonged_stay"      # 长时间滞留
    FENCE_CLIMBING = "fence_climbing"     # 翻越围栏
    INTRUSION = "intrusion"               # 闯入限制区域

    # 正常行为
    PERSON_DETECTED = "person_detected"    # 人员检测
    NORMAL_WALKING = "normal_walking"     # 正常行走
    CROWD_GATHERING = "crowd_gathering"   # 人群聚集


# ============ 边界框 ============

class BoundingBox(BaseModel):
    """边界框 [x, y, width, height] 归一化到 0-1"""
    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)
    width: float = Field(..., ge=0, le=1)
    height: float = Field(..., ge=0, le=1)

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.width, self.height]


class KeyPoint(BaseModel):
    """人体关键点"""
    x: float
    y: float
    confidence: float = Field(..., ge=0, le=1)
    visible: bool = True


class PoseSkeleton(BaseModel):
    """人体姿态骨架"""
    nose: Optional[KeyPoint] = None
    left_eye: Optional[KeyPoint] = None
    right_eye: Optional[KeyPoint] = None
    left_ear: Optional[KeyPoint] = None
    right_ear: Optional[KeyPoint] = None
    left_shoulder: Optional[KeyPoint] = None
    right_shoulder: Optional[KeyPoint] = None
    left_elbow: Optional[KeyPoint] = None
    right_elbow: Optional[KeyPoint] = None
    left_wrist: Optional[KeyPoint] = None
    right_wrist: Optional[KeyPoint] = None
    left_hip: Optional[KeyPoint] = None
    right_hip: Optional[KeyPoint] = None
    left_knee: Optional[KeyPoint] = None
    right_knee: Optional[KeyPoint] = None
    left_ankle: Optional[KeyPoint] = None
    right_ankle: Optional[KeyPoint] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            k: {"x": v.x, "y": v.y, "confidence": v.confidence, "visible": v.visible}
            if v else None
            for k, v in self.model_dump().items()
        }


# ============ 检测结果 ============

class Detection(BaseModel):
    """单次检测结果"""
    class_name: str                    # 检测类别
    class_id: int                      # 类别 ID
    confidence: float = Field(..., ge=0, le=1)
    bbox: BoundingBox
    track_id: Optional[str] = None     # 跟踪 ID（跟踪后填充）
    pose: Optional[PoseSkeleton] = None # 姿态骨架（如果检测到人）


class Track(BaseModel):
    """跟踪轨迹"""
    track_id: str
    class_name: str
    history: List[Dict[str, Any]] = Field(default_factory=list)
    # 轨迹特征
    velocity: Optional[Dict[str, float]] = None  # {vx, vy}
    trajectory: List[BoundingBox] = Field(default_factory=list)
    # 姿态历史（用于时序分析）
    pose_history: List[Optional[PoseSkeleton]] = Field(default_factory=list)
    # 时间统计
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    dwell_time: float = 0.0  # 停留时间（秒）
    # 区域统计
    dwell_zones: Dict[str, float] = Field(default_factory=dict)  # 各区域停留时间


# ============ 角色分配 ============

class RoleAssignment(BaseModel):
    """参与者角色分配"""
    track_id: str
    role: ParticipantRole
    confidence: float = Field(..., ge=0, le=1)
    reasoning: Optional[str] = None  # 角色判断依据


# ============ 参与者 ============

class Participant(BaseModel):
    """事件参与者"""
    track_id: str
    person_id: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    bbox_history: List[BoundingBox] = Field(default_factory=list)
    pose: Optional[PoseSkeleton] = None
    role: Optional[ParticipantRole] = None
    features: Dict[str, Any] = Field(default_factory=dict)  # 交互特征


# ============ 规则触发 ============

class RuleType(str, Enum):
    """规则类型"""
    ROI = "roi"                      # 区域入侵
    FORBIDDEN_AREA = "forbidden_area"  # 禁区
    DWELL_TIME = "dwell_time"        # 停留超时
    TRAJECTORY = "trajectory"        # 轨迹异常
    CROSSING_LINE = "crossing_line" # 越线
    SPEED = "speed"                  # 速度异常
    CROWD = "crowd"                 # 人群聚集


class RuleTrigger(BaseModel):
    """规则触发信息"""
    rule_type: RuleType
    rule_id: str
    rule_name: str
    triggered_by: List[str]  # 触发的 track_id 列表
    details: Dict[str, Any] = Field(default_factory=dict)


# ============ 行为识别结果 ============

class BehaviorResult(BaseModel):
    """行为识别结果"""
    behavior_type: EventType
    category: EventCategory
    confidence: float = Field(..., ge=0, le=1)
    # 时序特征
    window_size: int = 0                    # 使用的时序窗口大小
    temporal_scores: Dict[int, float] = Field(default_factory=dict)  # 各窗口得分
    # 交互特征（多人时）
    interaction_features: Dict[str, Any] = Field(default_factory=dict)
    # 姿态特征
    pose_features: Dict[str, Any] = Field(default_factory=dict)
    # 基础证据
    evidence: Dict[str, Any] = Field(default_factory=dict)


# ============ 聚合事件 ============

class BehaviorEvent(BaseModel):
    """
    行为事件 - 核心输出结构

    特点：
    1. 支持单人行为和多人交互行为
    2. 必须包含 participants 和 roles
    3. 具备时间窗口概念（startTime/endTime）
    4. 可驱动历史查询、审核和导出
    """

    # 基础信息
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    stream_id: str
    event_type: EventType
    category: EventCategory
    severity: Severity

    # 置信度
    confidence: float = Field(..., ge=0, le=1)

    # 时间信息
    timestamp: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: float = 0.0  # 事件持续时间（秒）

    # 参与者
    track_ids: List[str] = Field(default_factory=list)
    participants: List[Participant] = Field(default_factory=list)
    roles: List[RoleAssignment] = Field(default_factory=list)

    # 行为识别结果
    behavior_result: Optional[BehaviorResult] = None

    # 规则触发（如果有）
    rule_trigger: Optional[RuleTrigger] = None

    # 参考
    source_frame_ref: Optional[str] = None  # 参考帧
    clip_ref: Optional[str] = None          # 关联切片
    key_frame_refs: List[str] = Field(default_factory=list)  # 关键帧

    # 审核信息
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewer_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_multi_person(self) -> bool:
        """是否多人交互事件"""
        return len(self.participants) > 1

    def get_participant_role(self, track_id: str) -> Optional[ParticipantRole]:
        """获取特定参与者的角色"""
        for role in self.roles:
            if role.track_id == track_id:
                return role.role
        return None

    def get_aggressor_ids(self) -> List[str]:
        """获取攻击方 ID 列表"""
        return [r.track_id for r in self.roles if r.role == ParticipantRole.AGGRESSOR]

    def get_victim_ids(self) -> List[str]:
        """获取受害方 ID 列表"""
        return [r.track_id for r in self.roles if r.role == ParticipantRole.VICTIM]


# ============ 检测帧结果 ============

class DetectionFrameResult(BaseModel):
    """一帧的检测结果"""
    frame_id: str
    stream_id: str
    timestamp_ms: int
    width: int
    height: int
    detections: List[Detection] = Field(default_factory=list)
    processing_time_ms: float = 0.0


# ============ Pipeline 输出 ============

class PipelineResult(BaseModel):
    """Pipeline 完整输出"""
    frame_result: DetectionFrameResult
    tracks: List[Track] = Field(default_factory=list)
    events: List[BehaviorEvent] = Field(default_factory=list)
    rule_triggers: List[RuleTrigger] = Field(default_factory=list)
    total_processing_time_ms: float = 0.0


# ============ 工厂函数 ============

def create_event(
    stream_id: str,
    event_type: EventType,
    category: EventCategory,
    severity: Severity,
    confidence: float,
    participants: List[Participant],
    roles: List[RoleAssignment],
    timestamp: Optional[str] = None,
    **kwargs
) -> BehaviorEvent:
    """创建事件的工厂函数"""
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()

    return BehaviorEvent(
        stream_id=stream_id,
        event_type=event_type,
        category=category,
        severity=severity,
        confidence=confidence,
        timestamp=timestamp,
        track_ids=[p.track_id for p in participants],
        participants=participants,
        roles=roles,
        **kwargs
    )
