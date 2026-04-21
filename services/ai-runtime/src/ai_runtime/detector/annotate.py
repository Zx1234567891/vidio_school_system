"""帧叠加：把 YOLO26 检测框 + 类别 + 置信度画到 BGR 帧上。

颜色按 BEHAVIOR_SEVERITY 分档（high=红 / medium=橙 / low=黄 / info=灰），
与前端告警等级配色保持一致。
"""
from __future__ import annotations

from typing import List

import cv2
import numpy as np

from ai_runtime.detector.detector import YOLODetector
from ai_runtime.models import Detection

_SEVERITY_BGR = {
    "high": (60, 60, 220),
    "medium": (40, 140, 240),
    "low": (60, 200, 240),
    "info": (180, 180, 180),
}


def draw_detections(frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
    """在帧上就地叠加检测结果；返回同一个 ndarray。"""
    if frame is None or frame.size == 0:
        return frame
    h, w = frame.shape[:2]
    for det in detections:
        x1 = int(det.bbox.x * w)
        y1 = int(det.bbox.y * h)
        x2 = int((det.bbox.x + det.bbox.width) * w)
        y2 = int((det.bbox.y + det.bbox.height) * h)

        sev = YOLODetector.BEHAVIOR_SEVERITY.get(det.class_name, "info")
        color = _SEVERITY_BGR[sev]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        label = f"{det.class_name} {det.confidence:.2f}"
        (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        ytxt = max(y1 - 6, th + 4)
        cv2.rectangle(frame, (x1, ytxt - th - 4), (x1 + tw + 4, ytxt + base - 2), color, -1)
        cv2.putText(
            frame, label, (x1 + 2, ytxt - 2),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA,
        )
    return frame
