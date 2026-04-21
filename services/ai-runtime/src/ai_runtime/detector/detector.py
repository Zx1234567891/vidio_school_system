"""
检测器模块 - 基于 YOLO26 的校园行为检测

自训练模型 `yolo26_campus.pt`，11 类：
  0 Kick / 1 Laying / 2 Phone / 3 Pointing / 4 Slap face /
  5 Slap table / 6 Smoking / 7 Squating / 8 Stand / 9 Touch / 10 Hit wall
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np
import time

from ai_runtime.models import Detection, BoundingBox
from ai_runtime.config import settings


class BaseDetector(ABC):
    """检测器基类"""

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[Detection]:
        """
        检测图像中的目标

        Args:
            image: BGR 格式的 numpy 数组 (H, W, 3)

        Returns:
            检测结果列表
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """检测器是否就绪"""
        pass

    @property
    @abstractmethod
    def supported_classes(self) -> List[str]:
        """支持的类别列表"""
        pass


class YOLODetector(BaseDetector):
    """
    YOLO26 检测器实现 - 校园 11 类行为

    使用自训练模型 `yolo26_campus.pt` (best mAP50-95 ≈ 0.987 @ test set)
    """

    # YOLO26 自训练类别映射
    CLASS_NAMES = {
        0: "Kick",
        1: "Laying",
        2: "Phone",
        3: "Pointing",
        4: "Slap face",
        5: "Slap table",
        6: "Smoking",
        7: "Squating",
        8: "Stand",
        9: "Touch",
        10: "Hit wall",
    }

    # 全部 11 类都是关注目标（整个模型就是为校园场景训练的）
    TARGET_CLASSES = {name: cid for cid, name in CLASS_NAMES.items()}

    # 行为严重等级（供告警分级使用）
    BEHAVIOR_SEVERITY = {
        "Kick": "high",
        "Slap face": "high",
        "Hit wall": "high",
        "Slap table": "medium",
        "Smoking": "medium",
        "Phone": "medium",
        "Pointing": "low",
        "Touch": "low",
        "Laying": "low",
        "Squating": "low",
        "Stand": "info",
    }

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.model_path = model_path or settings.MODEL_PATH
        self.device = device
        self.model = None
        self._ready = False

    def load_model(self) -> bool:
        """加载 YOLO 模型；无 CUDA 时自动降级为 CPU。"""
        try:
            from ultralytics import YOLO
            try:
                import torch
                if self.device.startswith("cuda") and not torch.cuda.is_available():
                    print(f"[YOLODetector] CUDA 不可用，自动降级为 CPU")
                    self.device = "cpu"
            except Exception:
                pass

            model_file = f"{self.model_path}/{settings.DETECTOR_MODEL}.pt"
            self.model = YOLO(model_file)
            # 预热 + 绑定设备
            _ = self.model.predict(
                np.zeros((320, 320, 3), dtype=np.uint8),
                device=self.device, verbose=False,
            )
            self._ready = True
            print(f"[YOLODetector] Model loaded: {model_file} (device={self.device})")
            return True
        except Exception as e:
            print(f"[YOLODetector] Failed to load model: {e}")
            return False

    def detect(self, image: np.ndarray) -> List[Detection]:
        """执行检测"""
        if not self._ready:
            return []

        start_time = time.time()

        # YOLO 推理（在指定设备）
        results = self.model.predict(
            image,
            conf=settings.DETECTOR_CONFIDENCE,
            iou=settings.DETECTOR_IOU,
            device=self.device,
            verbose=False,
        )

        detections = []
        h, w = image.shape[:2]

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i, box in enumerate(boxes):
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])

                # 获取类别名
                class_name = self.CLASS_NAMES.get(cls_id, "unknown")

                # 转换为归一化坐标
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                bbox = BoundingBox(
                    x=float(x1) / w,
                    y=float(y1) / h,
                    width=float(x2 - x1) / w,
                    height=float(y2 - y1) / h
                )

                detection = Detection(
                    class_name=class_name,
                    class_id=cls_id,
                    confidence=conf,
                    bbox=bbox
                )
                detections.append(detection)

        return detections

    def is_ready(self) -> bool:
        return self._ready

    @property
    def supported_classes(self) -> List[str]:
        return list(self.TARGET_CLASSES.keys())


class MockDetector(BaseDetector):
    """Mock 检测器 - 用于测试和开发"""

    def __init__(self):
        self._ready = True
        self._frame_count = 0

    def detect(self, image: np.ndarray) -> List[Detection]:
        """生成模拟检测结果"""
        import random

        self._frame_count += 1
        detections = []
        h, w = image.shape[:2]

        # 模拟 YOLO26 的 11 类行为输出
        pool = list(YOLODetector.CLASS_NAMES.items())
        num = random.randint(1, 3)
        for _ in range(num):
            cid, cname = random.choice(pool)
            detection = Detection(
                class_name=cname,
                class_id=cid,
                confidence=random.uniform(0.6, 0.95),
                bbox=BoundingBox(
                    x=random.uniform(0.1, 0.7),
                    y=random.uniform(0.1, 0.7),
                    width=random.uniform(0.1, 0.3),
                    height=random.uniform(0.15, 0.4),
                ),
            )
            detections.append(detection)

        return detections

    def is_ready(self) -> bool:
        return self._ready

    @property
    def supported_classes(self) -> List[str]:
        return list(YOLODetector.CLASS_NAMES.values())


def create_detector(detector_type: str = "yolo", **kwargs) -> BaseDetector:
    """工厂函数创建检测器"""
    if detector_type == "yolo":
        detector = YOLODetector(**kwargs)
        detector.load_model()
        return detector
    elif detector_type == "mock":
        return MockDetector()
    else:
        raise ValueError(f"Unknown detector type: {detector_type}")
