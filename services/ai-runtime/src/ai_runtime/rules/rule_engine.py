"""
规则引擎 - ROI、禁区、停留时间、越线检测

支持规则类型：
- ROI: 区域入侵
- FORBIDDEN_AREA: 禁区检测
- DWELL_TIME: 停留超时
- TRAJECTORY: 轨迹异常
- CROSSING_LINE: 越线检测
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
import numpy as np

from ai_runtime.models import (
    Track, RuleType, RuleTrigger, EventType, EventCategory,
    Severity, BehaviorEvent, Participant, RoleAssignment
)
from ai_runtime.config import settings


class RuleConfig(BaseModel):
    """规则配置"""
    rule_id: str
    rule_name: str
    rule_type: RuleType
    enabled: bool = True
    # 区域定义
    polygon: Optional[List[Tuple[float, float]]] = None  # 归一化坐标
    line: Optional[List[Tuple[float, float]]] = None     # 越线检测用
    # 阈值
    threshold: float = 10.0  # 秒（停留时间）或其他阈值
    # 严重级别
    severity: Severity = Severity.MEDIUM
    # 关联流
    stream_id: Optional[str] = None


class BaseRuleChecker(ABC):
    """规则检查基类"""

    @abstractmethod
    def check(self, tracks: List[Track], config: RuleConfig) -> Optional[RuleTrigger]:
        """检查规则"""
        pass


class ROIChecker(BaseRuleChecker):
    """区域入侵检测"""

    def check(self, tracks: List[Track], config: RuleConfig) -> Optional[RuleTrigger]:
        if not config.polygon:
            return None

        roi = Polygon(config.polygon)
        triggered_tracks = []

        for track in tracks:
            if not track.trajectory:
                continue

            # 检查当前位置是否在 ROI 内
            bbox = track.trajectory[-1] if track.trajectory else None
            if bbox:
                center = Point(bbox.x + bbox.width / 2, bbox.y + bbox.height / 2)
                if roi.contains(center):
                    triggered_tracks.append(track.track_id)

        if triggered_tracks:
            return RuleTrigger(
                rule_type=config.rule_type,
                rule_id=config.rule_id,
                rule_name=config.rule_name,
                triggered_by=triggered_tracks,
                details={"polygon": config.polygon}
            )

        return None


class ForbiddenAreaChecker(BaseRuleChecker):
    """禁区检测"""

    def check(self, tracks: List[Track], config: RuleConfig) -> Optional[RuleTrigger]:
        if not config.polygon:
            return None

        forbidden = Polygon(config.polygon)
        triggered_tracks = []

        for track in tracks:
            bbox = track.trajectory[-1] if track.trajectory else None
            if bbox:
                center = Point(bbox.x + bbox.width / 2, bbox.y + bbox.height / 2)
                if forbidden.contains(center):
                    triggered_tracks.append(track.track_id)

        if triggered_tracks:
            return RuleTrigger(
                rule_type=RuleType.FORBIDDEN_AREA,
                rule_id=config.rule_id,
                rule_name=config.rule_name,
                triggered_by=triggered_tracks,
                details={"area": config.polygon}
            )

        return None


class DwellTimeChecker(BaseRuleChecker):
    """停留超时检测"""

    def __init__(self):
        self.dwell_times: Dict[str, float] = {}

    def check(self, tracks: List[Track], config: RuleConfig) -> Optional[RuleTrigger]:
        threshold = config.threshold
        triggered_tracks = []

        for track in tracks:
            if track.dwell_time > threshold:
                triggered_tracks.append(track.track_id)

        if triggered_tracks:
            return RuleTrigger(
                rule_type=RuleType.DWELL_TIME,
                rule_id=config.rule_id,
                rule_name=config.rule_name,
                triggered_by=triggered_tracks,
                details={
                    "threshold": threshold,
                    "dwell_times": {t: next((tr.dwell_time for tr in tracks if tr.track_id == t), 0)
                                   for t in triggered_tracks}
                }
            )

        return None


class CrossingLineChecker(BaseRuleChecker):
    """越线检测"""

    def __init__(self):
        self.crossed: Dict[str, bool] = {}

    def check(self, tracks: List[Track], config: RuleConfig) -> Optional[RuleTrigger]:
        if not config.line or len(config.line) < 2:
            return None

        line = LineString(config.line)
        triggered_tracks = []

        for track in tracks:
            if len(track.trajectory) < 2:
                continue

            # 检查轨迹是否穿越线
            prev_bbox = track.trajectory[-2]
            curr_bbox = track.trajectory[-1]

            prev_center = Point(prev_bbox.x + prev_bbox.width / 2, prev_bbox.y + prev_bbox.height / 2)
            curr_center = Point(curr_bbox.x + curr_bbox.width / 2, curr_bbox.y + curr_bbox.height / 2)

            trajectory_line = LineString([prev_center, curr_center])

            if trajectory_line.crosses(line):
                triggered_tracks.append(track.track_id)

        if triggered_tracks:
            return RuleTrigger(
                rule_type=RuleType.CROSSING_LINE,
                rule_id=config.rule_id,
                rule_name=config.rule_name,
                triggered_by=triggered_tracks,
                details={"line": config.line}
            )

        return None


class RuleEngine:
    """规则引擎"""

    def __init__(self):
        self.rules: Dict[str, RuleConfig] = {}
        self.checkers: Dict[RuleType, BaseRuleChecker] = {
            RuleType.ROI: ROIChecker(),
            RuleType.FORBIDDEN_AREA: ForbiddenAreaChecker(),
            RuleType.DWELL_TIME: DwellTimeChecker(),
            RuleType.CROSSING_LINE: CrossingLineChecker(),
        }

    def add_rule(self, config: RuleConfig):
        """添加规则"""
        self.rules[config.rule_id] = config

    def remove_rule(self, rule_id: str):
        """移除规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]

    def check_all(self, tracks: List[Track]) -> List[RuleTrigger]:
        """检查所有规则"""
        triggers = []

        for rule_id, config in self.rules.items():
            if not config.enabled:
                continue

            checker = self.checkers.get(config.rule_type)
            if checker:
                trigger = checker.check(tracks, config)
                if trigger:
                    triggers.append(trigger)

        return triggers

    def get_rules_for_stream(self, stream_id: str) -> List[RuleConfig]:
        """获取特定流的规则"""
        return [r for r in self.rules.values() if r.stream_id == stream_id]
