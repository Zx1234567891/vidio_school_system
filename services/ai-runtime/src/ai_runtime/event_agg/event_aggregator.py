"""
事件聚合器 - 将识别结果聚合为完整事件

关键要求：
1. 必须输出 participants 和 roles
2. 必须输出 trackIds
3. 必须输出 clipRef（关联切片）
4. 具备时间窗口概念
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import uuid

from ai_runtime.models import (
    BehaviorEvent, BehaviorResult, RuleTrigger, Track,
    EventType, EventCategory, Severity, Participant, RoleAssignment,
    ParticipantRole, BoundingBox
)
from ai_runtime.config import settings


@dataclass
class PendingEvent:
    """待聚合事件"""
    event_id: str
    stream_id: str
    event_type: EventType
    category: EventCategory
    severity: Severity
    confidence: float

    start_time: datetime
    last_time: datetime
    duration: float = 0.0

    track_ids: List[str] = field(default_factory=list)
    participants: List[Participant] = field(default_factory=list)
    roles: List[RoleAssignment] = field(default_factory=list)

    behavior_result: Optional[BehaviorResult] = None
    rule_trigger: Optional[RuleTrigger] = None

    # 聚合统计
    frame_count: int = 0
    avg_confidence: float = 0.0


class EventAggregator:
    """
    事件聚合器

    功能：
    1. 合并短时间内的重复事件
    2. 关联参与者信息
    3. 分配角色（aggressor/victim/bystander）
    4. 生成完整的事件结构
    """

    def __init__(self):
        # 待处理事件映射
        self._pending_events: Dict[str, PendingEvent] = {}

        # 聚合窗口（秒）
        self.aggregation_window = settings.EVENT_AGGREGATION_WINDOW
        self.min_duration = settings.EVENT_MIN_DURATION

        # 已完成事件
        self._completed_events: List[BehaviorEvent] = []

    def add_result(
        self,
        stream_id: str,
        behavior_result: Optional[BehaviorResult] = None,
        rule_trigger: Optional[RuleTrigger] = None,
        tracks: Optional[List[Track]] = None,
        timestamp: Optional[datetime] = None
    ) -> List[BehaviorEvent]:
        """
        添加识别结果，生成或更新事件

        Returns:
            新完成的事件列表
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        completed = []

        # 提取事件类型
        if behavior_result:
            event_type = behavior_result.behavior_type
            category = behavior_result.category
            severity = self._category_to_severity(category)
            confidence = behavior_result.confidence
        elif rule_trigger:
            event_type = self._rule_to_event_type(rule_trigger.rule_type)
            category = EventCategory.SUSPICIOUS
            severity = Severity.MEDIUM
            confidence = 0.7
        else:
            return completed

        # 生成或查找待处理事件
        event_key = f"{stream_id}_{event_type.value}"

        # 检查是否有匹配的待处理事件
        matching_event = self._find_matching_event(
            event_key, stream_id, timestamp, tracks or []
        )

        if matching_event:
            # 更新已有事件
            self._update_event(matching_event, behavior_result, rule_trigger, tracks, timestamp)
        else:
            # 创建新事件
            event_id = f"evt_{uuid.uuid4().hex[:12]}"
            pending = PendingEvent(
                event_id=event_id,
                stream_id=stream_id,
                event_type=event_type,
                category=category,
                severity=severity,
                confidence=confidence,
                start_time=timestamp,
                last_time=timestamp,
            )

            if tracks:
                self._update_event_tracks(pending, tracks)

            self._pending_events[event_key] = pending

        # 检查是否有事件需要完成
        completed = self._check_completion(timestamp)

        return completed

    def _find_matching_event(
        self,
        event_key: str,
        stream_id: str,
        timestamp: datetime,
        tracks: List[Track]
    ) -> Optional[PendingEvent]:
        """查找匹配的事件"""
        # 如果有直接匹配的
        if event_key in self._pending_events:
            pending = self._pending_events[event_key]
            # 检查是否在时间窗口内
            if (timestamp - pending.last_time).total_seconds() < self.aggregation_window:
                return pending

        # 查找类似的参与者
        for key, pending in self._pending_events.items():
            if pending.stream_id != stream_id:
                continue

            if pending.event_type != self._pending_events.get(event_key, pending).event_type:
                continue

            # 检查时间窗口
            if (timestamp - pending.last_time).total_seconds() < self.aggregation_window:
                # 检查参与者重叠
                if tracks and pending.track_ids:
                    overlap = set(t.track_id for t in tracks) & set(pending.track_ids)
                    if overlap:
                        return pending

        return None

    def _update_event(
        self,
        pending: PendingEvent,
        behavior_result: Optional[BehaviorResult],
        rule_trigger: Optional[RuleTrigger],
        tracks: Optional[List[Track]],
        timestamp: datetime
    ):
        """更新事件"""
        pending.last_time = timestamp
        pending.frame_count += 1
        pending.duration = (timestamp - pending.start_time).total_seconds()

        # 更新置信度
        if behavior_result:
            pending.avg_confidence = (
                (pending.avg_confidence * (pending.frame_count - 1) + behavior_result.confidence)
                / pending.frame_count
            )
            pending.behavior_result = behavior_result

        if rule_trigger:
            pending.rule_trigger = rule_trigger

        if tracks:
            self._update_event_tracks(pending, tracks)

    def _update_event_tracks(self, pending: PendingEvent, tracks: List[Track]):
        """更新事件参与者"""
        current_ids = set(pending.track_ids)

        for track in tracks:
            if track.track_id not in current_ids:
                pending.track_ids.append(track.track_id)
                current_ids.add(track.track_id)

                # 创建参与者
                participant = Participant(
                    track_id=track.track_id,
                    bbox=track.trajectory[-1] if track.trajectory else None,
                    bbox_history=list(track.trajectory[-10:]) if track.trajectory else [],
                    features={
                        "dwell_time": track.dwell_time,
                        "velocity": track.velocity
                    }
                )
                pending.participants.append(participant)

    def _check_completion(self, timestamp: datetime) -> List[BehaviorEvent]:
        """检查事件是否完成"""
        completed = []

        to_remove = []

        for event_key, pending in self._pending_events.items():
            time_since_last = (timestamp - pending.last_time).total_seconds()

            # 超过聚合窗口且有足够持续时间
            if time_since_last >= self.aggregation_window and pending.duration >= self.min_duration:
                # 生成最终事件
                event = self._create_event(pending)
                completed.append(event)
                to_remove.append(event_key)

            # 超时未完成，丢弃
            elif time_since_last >= self.aggregation_window * 3:
                to_remove.append(event_key)

        for key in to_remove:
            del self._pending_events[key]

        return completed

    def _create_event(self, pending: PendingEvent) -> BehaviorEvent:
        """创建最终事件"""
        # 分配角色
        roles = self._assign_roles(pending)

        event = BehaviorEvent(
            event_id=pending.event_id,
            stream_id=pending.stream_id,
            event_type=pending.event_type,
            category=pending.category,
            severity=pending.severity,
            confidence=pending.avg_confidence,
            timestamp=pending.last_time.isoformat(),
            start_time=pending.start_time.isoformat(),
            end_time=pending.last_time.isoformat(),
            duration=pending.duration,
            track_ids=pending.track_ids,
            participants=pending.participants,
            roles=roles,
            behavior_result=pending.behavior_result,
            rule_trigger=pending.rule_trigger,
        )

        self._completed_events.append(event)
        return event

    def _assign_roles(self, pending: PendingEvent) -> List[RoleAssignment]:
        """分配参与者角色"""
        roles = []

        # 基于事件类型和特征分配角色
        event_type = pending.event_type
        tracks_dict = {p.track_id: p for p in pending.participants}

        if event_type == EventType.FIGHTING:
            # 互殴：所有参与者都是 mutual
            for track_id in pending.track_ids:
                roles.append(RoleAssignment(
                    track_id=track_id,
                    role=ParticipantRole.MUTUAL,
                    confidence=0.8,
                    reasoning="Mutual combat detected"
                ))

        elif event_type == EventType.BULLYING:
            # 霸凌：从行为结果中提取攻击者和受害者
            if pending.behavior_result and pending.behavior_result.evidence:
                evidence = pending.behavior_result.evidence
                aggressor_id = evidence.get("aggressor_id")
                victim_id = evidence.get("victim_id")

                if aggressor_id:
                    roles.append(RoleAssignment(
                        track_id=aggressor_id,
                        role=ParticipantRole.AGGRESSOR,
                        confidence=evidence.get("confidence", 0.7),
                        reasoning="Higher velocity detected as aggressor"
                    ))

                if victim_id:
                    roles.append(RoleAssignment(
                        track_id=victim_id,
                        role=ParticipantRole.VICTIM,
                        confidence=evidence.get("confidence", 0.7),
                        reasoning="Lower velocity detected as victim"
                    ))

            # 其他参与者为 bystander
            assigned_ids = {r.track_id for r in roles}
            for track_id in pending.track_ids:
                if track_id not in assigned_ids:
                    roles.append(RoleAssignment(
                        track_id=track_id,
                        role=ParticipantRole.BYSTANDER,
                        confidence=0.5,
                        reasoning="Present but not directly involved"
                    ))

        elif event_type == EventType.FALLING:
            # 跌倒：只有一个受害者
            for track_id in pending.track_ids:
                roles.append(RoleAssignment(
                    track_id=track_id,
                    role=ParticipantRole.VICTIM,
                    confidence=0.9,
                    reasoning="Falling person"
                ))

        elif event_type in [EventType.LOITERING, EventType.PROLOGED_STAY]:
            # 徘徊/滞留：所有参与者都是 aggressor（触发规则的人）
            for track_id in pending.track_ids:
                roles.append(RoleAssignment(
                    track_id=track_id,
                    role=ParticipantRole.AGGRESSOR,
                    confidence=0.8,
                    reasoning="Dwell time exceeded threshold"
                ))

        return roles

    def _category_to_severity(self, category: EventCategory) -> Severity:
        """类别转严重级别"""
        mapping = {
            EventCategory.HIGH_RISK: Severity.HIGH,
            EventCategory.MANAGEMENT_SENSITIVE: Severity.MEDIUM,
            EventCategory.SUSPICIOUS: Severity.MEDIUM,
            EventCategory.NORMAL: Severity.LOW,
        }
        return mapping.get(category, Severity.MEDIUM)

    def _rule_to_event_type(self, rule_type) -> EventType:
        """规则类型转事件类型"""
        mapping = {
            "roi": EventType.INTRUSION,
            "forbidden_area": EventType.INTRUSION,
            "dwell_time": EventType.LOITERING,
            "crossing_line": EventType.FENCE_CLIMBING,
        }
        return mapping.get(rule_type.value, EventType.LOITERING)

    def flush(self) -> List[BehaviorEvent]:
        """强制完成所有待处理事件"""
        now = datetime.utcnow()
        return self._check_completion(now)

    def get_pending_count(self) -> int:
        """获取待处理事件数"""
        return len(self._pending_events)
