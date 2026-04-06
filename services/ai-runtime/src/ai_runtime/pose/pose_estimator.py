"""
姿态估计模块 - 基于 YOLO-Pose

用于跌倒、打架、霸凌等姿态分析
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np

from ai_runtime.models import Detection, PoseSkeleton, KeyPoint
from ai_runtime.config import settings


class BasePoseEstimator(ABC):
    """姿态估计基类"""

    @abstractmethod
    def estimate(self, image: np.ndarray, detections: List[Detection]) -> List[PoseSkeleton]:
        """
        估计姿态

        Args:
            image: BGR 图像
            detections: 人员检测结果

        Returns:
            姿态列表（与 detections 一一对应）
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """是否就绪"""
        pass


class YOLOPoseEstimator(BasePoseEstimator):
    """YOLO-Pose 实现"""

    # COCO 关键点顺序
    KEYPOINT_NAMES = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.model_path = model_path or settings.MODEL_PATH
        self.device = device
        self.model = None
        self._ready = False

    def load_model(self) -> bool:
        """加载模型"""
        try:
            from ultralytics import YOLO

            model_file = f"{self.model_path}/{settings.POSE_MODEL}.pt"
            self.model = YOLO(model_file)
            self.model.to(self.device)
            self._ready = True
            print(f"[YOLOPose] Model loaded: {model_file}")
            return True
        except Exception as e:
            print(f"[YOLOPose] Failed to load model: {e}")
            return False

    def estimate(self, image: np.ndarray, detections: List[Detection]) -> List[PoseSkeleton]:
        """估计姿态"""
        if not self._ready or not detections:
            return [None] * len(detections)

        h, w = image.shape[:2]
        person_indices = [i for i, d in enumerate(detections) if d.class_name == "person"]

        if not person_indices:
            return [None] * len(detections)

        results = self.model(image, verbose=False)

        poses = [None] * len(detections)

        for result in results:
            if result.keypoints is None:
                continue

            keypoints = result.keypoints.xy.cpu().numpy()  # (N, 17, 2) in pixel coords
            confidences = result.keypoints.conf.cpu().numpy() if result.keypoints.conf is not None else None

            for i, (kpts, det_idx) in enumerate(zip(keypoints, person_indices)):
                if i >= len(person_indices):
                    break

                pose = self._keypoints_to_pose(kpts, confidences[i] if confidences is not None else None, h, w)
                poses[det_idx] = pose

        return poses

    def _keypoints_to_pose(self, keypoints: np.ndarray, confidences: Optional[np.ndarray], h: int, w: int) -> PoseSkeleton:
        """转换关键点为 PoseSkeleton（归一化到 0-1）"""
        pose_data = {}

        for i, name in enumerate(self.KEYPOINT_NAMES):
            if i < len(keypoints):
                x, y = keypoints[i]
                conf = confidences[i] if confidences is not None and i < len(confidences) else 0.5

                pose_data[name] = KeyPoint(
                    x=float(x) / w,  # 归一化到 0-1
                    y=float(y) / h,
                    confidence=float(conf),
                    visible=conf > 0.3
                )

        return PoseSkeleton(**pose_data)

    def is_ready(self) -> bool:
        return self._ready


class MockPoseEstimator(BasePoseEstimator):
    """Mock 姿态估计"""

    def __init__(self):
        self._ready = True

    def estimate(self, image: np.ndarray, detections: List[Detection]) -> List[PoseSkeleton]:
        """生成模拟姿态"""
        import random

        poses = []
        for det in detections:
            if det.class_name != "person":
                poses.append(None)
                continue

            # 模拟站立姿态
            bbox = det.bbox
            cx = bbox.x + bbox.width / 2
            cy = bbox.y + bbox.height / 2

            # 简化的关键点
            pose = PoseSkeleton(
                nose=KeyPoint(x=cx, y=bbox.y + bbox.height * 0.1, confidence=0.8),
                left_shoulder=KeyPoint(x=cx - 0.05, y=bbox.y + bbox.height * 0.2, confidence=0.8),
                right_shoulder=KeyPoint(x=cx + 0.05, y=bbox.y + bbox.height * 0.2, confidence=0.8),
                left_hip=KeyPoint(x=cx - 0.05, y=bbox.y + bbox.height * 0.5, confidence=0.7),
                right_hip=KeyPoint(x=cx + 0.05, y=bbox.y + bbox.height * 0.5, confidence=0.7),
                left_knee=KeyPoint(x=cx - 0.05, y=bbox.y + bbox.height * 0.7, confidence=0.7),
                right_knee=KeyPoint(x=cx + 0.05, y=bbox.y + bbox.height * 0.7, confidence=0.7),
                left_ankle=KeyPoint(x=cx - 0.05, y=bbox.y + bbox.height * 0.9, confidence=0.6),
                right_ankle=KeyPoint(x=cx + 0.05, y=bbox.y + bbox.height * 0.9, confidence=0.6),
            )
            poses.append(pose)

        return poses

    def is_ready(self) -> bool:
        return self._ready


def create_pose_estimator(estimator_type: str = "yolo", **kwargs) -> BasePoseEstimator:
    """工厂函数"""
    if estimator_type == "yolo":
        estimator = YOLOPoseEstimator(**kwargs)
        estimator.load_model()
        return estimator
    elif estimator_type == "mock":
        return MockPoseEstimator()
    else:
        raise ValueError(f"Unknown estimator type: {estimator_type}")
