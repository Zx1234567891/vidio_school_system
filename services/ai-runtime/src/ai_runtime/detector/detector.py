"""
检测器模块 - 基于 YOLO 的目标检测

支持的类别：
- person: 人员
- phone: 手机
- smoke/cigarette: 烟雾/香烟
- fire: 火焰
- bag/backpack: 包/背包
- camera: 摄像头
- knife: 刀具
- mask: 口罩
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
    YOLO 检测器实现

    使用 ultralytics YOLOv8 作为基线
    """

    # 类别映射 - COCO 基础 + 自定义
    CLASS_NAMES = {
        0: "person",
        1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane", 5: "bus",
        6: "train", 7: "truck", 8: "boat", 9: "traffic light", 10: "fire hydrant",
        11: "stop sign", 12: "parking meter", 13: "bench", 14: "bird", 15: "cat",
        16: "dog", 17: "horse", 18: "sheep", 19: "cow", 20: "elephant",
        21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack", 25: "umbrella",
        26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee", 30: "skis",
        31: "snowboard", 32: "sports ball", 33: "kite", 34: "baseball bat",
        35: "baseball glove", 36: "skateboard", 37: "surfboard", 38: "tennis racket",
        39: "bottle", 40: "wine glass", 41: "cup", 42: "fork", 43: "knife",
        44: "spoon", 45: "bowl", 46: "banana", 47: "apple", 48: "sandwich",
        49: "orange", 50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza",
        54: "donut", 55: "cake", 56: "chair", 57: "couch", 58: "potted plant",
        59: "bed", 60: "dining table", 61: "toilet", 62: "tv", 63: "laptop",
        64: "mouse", 65: "remote", 66: "keyboard", 67: "cell phone",
        68: "microwave", 69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator",
        73: "book", 74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear",
        78: "hair drier", 79: "toothbrush"
    }

    # 关注的目标类别（校园安防场景）
    TARGET_CLASSES = {
        "person": 0,
        "backpack": 24,
        "handbag": 26,
        "suitcase": 28,
        "bottle": 39,
        "knife": 43,
        "cell phone": 67,
        "laptop": 63,
        "camera": 77,  # 破坏公共设施
    }

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.model_path = model_path or settings.MODEL_PATH
        self.device = device
        self.model = None
        self._ready = False

    def load_model(self) -> bool:
        """加载 YOLO 模型"""
        try:
            from ultralytics import YOLO

            model_file = f"{self.model_path}/{settings.DETECTOR_MODEL}.pt"
            self.model = YOLO(model_file)
            self.model.to(self.device)
            self._ready = True
            print(f"[YOLODetector] Model loaded: {model_file}")
            return True
        except Exception as e:
            print(f"[YOLODetector] Failed to load model: {e}")
            return False

    def detect(self, image: np.ndarray) -> List[Detection]:
        """执行检测"""
        if not self._ready:
            return []

        start_time = time.time()

        # YOLO 推理
        results = self.model(
            image,
            conf=settings.DETECTOR_CONFIDENCE,
            iou=settings.DETECTOR_IOU,
            verbose=False
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

        # 模拟检测到 1-3 个人
        num_persons = random.randint(1, 3)
        for i in range(num_persons):
            x = random.uniform(0.1, 0.7)
            y = random.uniform(0.1, 0.7)
            width = random.uniform(0.05, 0.15)
            height = random.uniform(0.1, 0.3)

            detection = Detection(
                class_name="person",
                class_id=0,
                confidence=random.uniform(0.7, 0.95),
                bbox=BoundingBox(x=x, y=y, width=width, height=height)
            )
            detections.append(detection)

        # 偶尔检测到手机
        if random.random() < 0.3:
            detection = Detection(
                class_name="cell phone",
                class_id=67,
                confidence=random.uniform(0.6, 0.85),
                bbox=BoundingBox(
                    x=random.uniform(0.2, 0.8),
                    y=random.uniform(0.2, 0.8),
                    width=0.02,
                    height=0.04
                )
            )
            detections.append(detection)

        return detections

    def is_ready(self) -> bool:
        return self._ready

    @property
    def supported_classes(self) -> List[str]:
        return ["person", "cell phone", "backpack"]


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
