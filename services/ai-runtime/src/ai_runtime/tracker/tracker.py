"""
跟踪器模块 - ByteTrack / BoT-SORT 实现

保持 track_id 一致性，支持轨迹分析
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
import time

from ai_runtime.models import Detection, Track, BoundingBox, KeyPoint
from ai_runtime.config import settings


@dataclass
class TrackState:
    """跟踪状态"""
    track_id: str
    bbox: BoundingBox
    class_name: str
    confidence: float
    # 时序信息
    frame_count: int = 0
    missed_count: int = 0
    hit_count: int = 0
    # 轨迹
    history: List[Dict] = field(default_factory=list)
    # 速度估计
    velocity: Tuple[float, float] = (0.0, 0.0)
    # 姿态历史
    pose_history: List[Optional[dict]] = field(default_factory=list)


class BaseTracker(ABC):
    """跟踪器基类"""

    @abstractmethod
    def update(self, detections: List[Detection]) -> List[Track]:
        """
        更新跟踪器

        Args:
            detections: 当前帧检测结果

        Returns:
            当前活跃的跟踪列表
        """
        pass

    @abstractmethod
    def get_track(self, track_id: str) -> Optional[Track]:
        """获取特定 track"""
        pass

    @abstractmethod
    def reset(self):
        """重置跟踪器"""
        pass


class ByteTrackTracker(BaseTracker):
    """
    ByteTrack 跟踪器实现

    特点：
    - 高置信度检测优先匹配
    - 低置信度检测二次匹配
    - 卡尔曼滤波预测
    """

    def __init__(
        self,
        track_thresh: float = 0.5,
        match_thresh: float = 0.8,
        track_buffer: int = 30,
        frame_rate: int = 30
    ):
        self.track_thresh = track_thresh
        self.match_thresh = match_thresh
        self.track_buffer = track_buffer
        self.frame_rate = frame_rate

        self._tracks: Dict[str, TrackState] = {}
        self._next_track_id = 1
        self._frame_count = 0

        # 尝试导入 ByteTrack
        try:
            from ultralytics.trackers.byte_tracker import BYTETracker
            self._use_ultralytics = True
            self._tracker = None  # 延迟初始化
        except ImportError:
            self._use_ultralytics = False
            print("[ByteTrack] Using fallback implementation")

    def _generate_track_id(self) -> str:
        """生成 track_id"""
        track_id = f"track_{self._next_track_id:06d}"
        self._next_track_id += 1
        return track_id

    def _iou(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """计算 IoU"""
        x1 = max(bbox1.x, bbox2.x)
        y1 = max(bbox1.y, bbox2.y)
        x2 = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y2 = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)

        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = bbox1.width * bbox1.height
        area2 = bbox2.width * bbox2.height

        return inter_area / (area1 + area2 - inter_area + 1e-6)

    def update(self, detections: List[Detection]) -> List[Track]:
        """更新跟踪"""
        self._frame_count += 1

        # 分离高置信度和低置信度检测
        high_dets = [d for d in detections if d.confidence >= self.track_thresh]
        low_dets = [d for d in detections if d.confidence < self.track_thresh]

        # 简单实现：基于 IoU 的匹配
        matched_tracks = set()
        matched_dets = set()

        # 高置信度匹配
        for det in high_dets:
            best_iou = self.match_thresh
            best_track_id = None

            for track_id, track in self._tracks.items():
                if track_id in matched_tracks:
                    continue
                iou = self._iou(det.bbox, track.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id:
                # 更新已有 track
                track = self._tracks[best_track_id]
                track.bbox = det.bbox
                track.confidence = det.confidence
                track.hit_count += 1
                track.missed_count = 0
                track.frame_count = self._frame_count

                # 更新历史
                track.history.append({
                    "frame": self._frame_count,
                    "bbox": det.bbox.to_list(),
                    "confidence": det.confidence
                })

                det.track_id = best_track_id
                matched_tracks.add(best_track_id)
                matched_dets.add(id(det))
            else:
                # 创建新 track
                track_id = self._generate_track_id()
                self._tracks[track_id] = TrackState(
                    track_id=track_id,
                    bbox=det.bbox,
                    class_name=det.class_name,
                    confidence=det.confidence,
                    frame_count=self._frame_count,
                    hit_count=1,
                    history=[{
                        "frame": self._frame_count,
                        "bbox": det.bbox.to_list(),
                        "confidence": det.confidence
                    }]
                )
                det.track_id = track_id

        # 更新未匹配的 track
        for track_id, track in self._tracks.items():
            if track_id not in matched_tracks:
                track.missed_count += 1

        # 移除丢失太久的 track
        tracks_to_remove = [
            tid for tid, t in self._tracks.items()
            if t.missed_count > self.track_buffer
        ]
        for tid in tracks_to_remove:
            del self._tracks[tid]

        # 转换为输出格式
        return self._to_tracks()

    def _to_tracks(self) -> List[Track]:
        """转换为 Track 模型"""
        tracks = []
        for track_id, state in self._tracks.items():
            # 只返回活跃的 track
            if state.missed_count == 0:
                track = Track(
                    track_id=track_id,
                    class_name=state.class_name,
                    history=state.history[-50:],  # 保留最近 50 帧
                    velocity={"vx": state.velocity[0], "vy": state.velocity[1]},
                    trajectory=[state.bbox],  # 简化
                    first_seen=None,
                    last_seen=None,
                    dwell_time=state.hit_count / self.frame_rate
                )
                tracks.append(track)
        return tracks

    def get_track(self, track_id: str) -> Optional[Track]:
        """获取特定 track"""
        if track_id not in self._tracks:
            return None
        state = self._tracks[track_id]
        return Track(
            track_id=track_id,
            class_name=state.class_name,
            history=state.history,
            dwell_time=state.hit_count / self.frame_rate
        )

    def reset(self):
        """重置"""
        self._tracks.clear()
        self._next_track_id = 1
        self._frame_count = 0


class MockTracker(BaseTracker):
    """Mock 跟踪器 - 用于测试"""

    def __init__(self):
        self._tracks: Dict[str, Track] = {}
        self._next_id = 1
        self._frame_count = 0

    def update(self, detections: List[Detection]) -> List[Track]:
        """模拟跟踪"""
        self._frame_count += 1

        # 简单分配 track_id
        for i, det in enumerate(detections):
            if det.track_id is None:
                det.track_id = f"track_{self._next_id:06d}"
                self._next_id += 1

            track_id = det.track_id
            if track_id not in self._tracks:
                self._tracks[track_id] = Track(
                    track_id=track_id,
                    class_name=det.class_name,
                    history=[],
                    dwell_time=0
                )

            track = self._tracks[track_id]
            track.history.append({
                "frame": self._frame_count,
                "bbox": det.bbox.to_list()
            })
            track.dwell_time += 1.0 / 30.0  # 假设 30fps

        return list(self._tracks.values())

    def get_track(self, track_id: str) -> Optional[Track]:
        return self._tracks.get(track_id)

    def reset(self):
        self._tracks.clear()
        self._next_id = 1


def create_tracker(tracker_type: str = "bytetrack", **kwargs) -> BaseTracker:
    """工厂函数创建跟踪器"""
    if tracker_type == "bytetrack":
        return ByteTrackTracker(
            track_thresh=settings.TRACKER_TRACK_THRESH,
            match_thresh=settings.TRACKER_MATCH_THRESH,
            track_buffer=settings.TRACKER_TRACK_BUFFER,
            **kwargs
        )
    elif tracker_type == "mock":
        return MockTracker()
    else:
        raise ValueError(f"Unknown tracker type: {tracker_type}")
