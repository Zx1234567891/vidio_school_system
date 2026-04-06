"""
主 Pipeline - 整合所有模块

detection → tracking → pose estimation → behavior recognition → rule checking → event aggregation
"""

import time
from typing import List, Optional, Callable
import numpy as np
from datetime import datetime

from ai_runtime.models import PipelineResult, DetectionFrameResult, BehaviorEvent, Track
from ai_runtime.config import settings

# 导入各模块
from ai_runtime.detector.detector import create_detector, BaseDetector
from ai_runtime.tracker.tracker import create_tracker, BaseTracker
from ai_runtime.pose.pose_estimator import create_pose_estimator, BasePoseEstimator
from ai_runtime.behavior.behavior_recognizer import BehaviorRecognizerPipeline
from ai_runtime.rules.rule_engine import RuleEngine, RuleConfig
from ai_runtime.event_agg.event_aggregator import EventAggregator


class AIPipeline:
    """
    AI 推理 Pipeline

    整合检测、跟踪、姿态估计、行为识别、规则引擎和事件聚合
    """

    def __init__(
        self,
        detector_type: str = "mock",
        tracker_type: str = "mock",
        pose_type: str = "mock",
        device: str = "cpu"
    ):
        self.device = device

        # 初始化各模块
        print("[AIPipeline] Initializing...")

        self.detector: BaseDetector = create_detector(detector_type, device=device)
        print(f"  ✓ Detector: {detector_type}")

        self.tracker: BaseTracker = create_tracker(tracker_type)
        print(f"  ✓ Tracker: {tracker_type}")

        self.pose_estimator: BasePoseEstimator = create_pose_estimator(pose_type, device=device)
        print(f"  ✓ Pose Estimator: {pose_type}")

        self.behavior_recognizer = BehaviorRecognizerPipeline()
        print("  ✓ Behavior Recognizer")

        self.rule_engine = RuleEngine()
        print("  ✓ Rule Engine")

        self.event_aggregator = EventAggregator()
        print("  ✓ Event Aggregator")

        # 回调
        self.event_callback: Optional[Callable[[BehaviorEvent], None]] = None

        print("[AIPipeline] Ready!")

    def add_rule(self, config: RuleConfig):
        """添加规则"""
        self.rule_engine.add_rule(config)

    def set_event_callback(self, callback: Callable[[BehaviorEvent], None]):
        """设置事件回调"""
        self.event_callback = callback

    def process_frame(
        self,
        image: np.ndarray,
        stream_id: str,
        frame_id: Optional[str] = None
    ) -> PipelineResult:
        """
        处理单帧

        Args:
            image: BGR 图像
            stream_id: 流 ID
            frame_id: 帧 ID

        Returns:
            Pipeline 结果
        """
        start_time = time.time()

        # 1. 检测
        detect_start = time.time()
        detections = self.detector.detect(image)
        detect_time = (time.time() - detect_start) * 1000

        # 2. 跟踪
        track_start = time.time()
        tracks = self.tracker.update(detections)
        track_time = (time.time() - track_start) * 1000

        # 3. 姿态估计
        pose_start = time.time()
        poses = self.pose_estimator.estimate(image, detections)
        pose_time = (time.time() - pose_start) * 1000

        # 关联姿态到检测
        for det, pose in zip(detections, poses):
            det.pose = pose

        # 关联姿态到跟踪
        for track in tracks:
            for det in detections:
                if det.track_id == track.track_id and det.pose:
                    track.pose_history.append(det.pose)
                    break

        # 4. 行为识别
        behavior_start = time.time()
        self.behavior_recognizer.update(tracks)
        behavior_results = self.behavior_recognizer.recognize(tracks)
        behavior_time = (time.time() - behavior_start) * 1000

        # 5. 规则检查
        rule_start = time.time()
        rule_triggers = self.rule_engine.check_all(tracks)
        rule_time = (time.time() - rule_start) * 1000

        # 6. 事件聚合
        agg_start = time.time()
        events = []

        for result in behavior_results:
            completed = self.event_aggregator.add_result(
                stream_id=stream_id,
                behavior_result=result,
                tracks=tracks
            )
            events.extend(completed)

        for trigger in rule_triggers:
            completed = self.event_aggregator.add_result(
                stream_id=stream_id,
                rule_trigger=trigger,
                tracks=tracks
            )
            events.extend(completed)

        agg_time = (time.time() - agg_start) * 1000

        # 触发事件回调
        if self.event_callback:
            for event in events:
                self.event_callback(event)

        # 构建帧结果
        h, w = image.shape[:2]
        frame_result = DetectionFrameResult(
            frame_id=frame_id or f"frame_{int(time.time() * 1000)}",
            stream_id=stream_id,
            timestamp_ms=int(time.time() * 1000),
            width=w,
            height=h,
            detections=detections,
            processing_time_ms=detect_time
        )

        total_time = (time.time() - start_time) * 1000

        return PipelineResult(
            frame_result=frame_result,
            tracks=tracks,
            events=events,
            rule_triggers=rule_triggers,
            total_processing_time_ms=total_time
        )

    def flush_events(self) -> List[BehaviorEvent]:
        """强制完成所有待处理事件"""
        return self.event_aggregator.flush()

    def is_ready(self) -> bool:
        """Pipeline 是否就绪"""
        return all([
            self.detector.is_ready(),
            self.pose_estimator.is_ready()
        ])


# 便捷函数
def create_pipeline(
    use_real_models: bool = False,
    device: str = "cpu"
) -> AIPipeline:
    """
    创建 Pipeline

    Args:
        use_real_models: 是否使用真实模型（YOLO等），否则使用 Mock
        device: 推理设备

    Returns:
        AIPipeline 实例
    """
    if use_real_models:
        return AIPipeline(
            detector_type="yolo",
            tracker_type="bytetrack",
            pose_type="yolo",
            device=device
        )
    else:
        return AIPipeline(
            detector_type="mock",
            tracker_type="mock",
            pose_type="mock",
            device=device
        )
