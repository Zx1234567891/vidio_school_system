"""
YOLO26 校园行为推理 - 在推流帧上叠加检测框与标签。

单例 `get_detector()`；无 ultralytics / 权重文件时静默降级（直接返回原帧）。
权重路径默认 `services/ai-runtime/models/yolo26_campus.pt`，可用环境变量
`YOLO26_WEIGHTS` 覆盖。设备可用 `YOLO26_DEVICE` 覆盖（cpu / cuda:0 ...）。
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np


CLASS_NAMES = [
    "Kick", "Laying", "Phone", "Pointing", "Slap face",
    "Slap table", "Smoking", "Squating", "Stand", "Touch", "Hit wall",
]

SEVERITY = {
    "Kick": "high", "Slap face": "high", "Hit wall": "high",
    "Slap table": "medium", "Smoking": "medium", "Phone": "medium",
    "Pointing": "low", "Touch": "low", "Laying": "low", "Squating": "low",
    "Stand": "info",
}

SEVERITY_BGR = {
    "high": (60, 60, 220),
    "medium": (40, 140, 240),
    "low": (60, 200, 240),
    "info": (180, 180, 180),
}


def _default_weights() -> str:
    here = Path(__file__).resolve().parent
    return str((here / ".." / "ai-runtime" / "models" / "yolo26_campus.pt").resolve())


class YOLO26Detector:
    def __init__(self, weights: str, device: str = "cpu", conf: float = 0.35, iou: float = 0.45):
        self.weights = weights
        self.device = device
        self.conf = conf
        self.iou = iou
        self._model = None
        self._ready = False
        self._err: Optional[str] = None

    def load(self) -> bool:
        try:
            from ultralytics import YOLO
        except Exception as e:
            self._err = f"ultralytics import failed: {e}"
            return False
        if not Path(self.weights).exists():
            self._err = f"weights not found: {self.weights}"
            return False
        try:
            self._model = YOLO(self.weights)
            # 预热一次（避免首帧卡顿）
            self._model.predict(np.zeros((320, 320, 3), dtype=np.uint8),
                                device=self.device, verbose=False)
            self._ready = True
            return True
        except Exception as e:
            self._err = f"YOLO load failed: {e}"
            return False

    def is_ready(self) -> bool:
        return self._ready

    def error(self) -> Optional[str]:
        return self._err

    def infer(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, int, float]]:
        """返回 [(x1,y1,x2,y2,cls_id,conf), ...]。未就绪返回空。"""
        if not self._ready:
            return []
        results = self._model.predict(
            frame, conf=self.conf, iou=self.iou, device=self.device, verbose=False
        )
        out: List[Tuple[int, int, int, int, int, float]] = []
        for r in results:
            if r.boxes is None:
                continue
            for b in r.boxes:
                xyxy = b.xyxy[0].cpu().numpy().astype(int)
                cls_id = int(b.cls[0])
                conf = float(b.conf[0])
                out.append((int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]), cls_id, conf))
        return out

    def draw(self, frame: np.ndarray,
             dets: List[Tuple[int, int, int, int, int, float]]) -> np.ndarray:
        """在帧上就地叠加检测框与标签。"""
        for x1, y1, x2, y2, cid, conf in dets:
            name = CLASS_NAMES[cid] if 0 <= cid < len(CLASS_NAMES) else str(cid)
            sev = SEVERITY.get(name, "info")
            color = SEVERITY_BGR[sev]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{name} {conf:.2f}"
            (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            ytxt = max(y1 - 6, th + 4)
            cv2.rectangle(frame, (x1, ytxt - th - 4), (x1 + tw + 4, ytxt + base - 2), color, -1)
            cv2.putText(frame, label, (x1 + 2, ytxt - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        return frame


_lock = threading.Lock()
_detector: Optional[YOLO26Detector] = None


def get_detector() -> Optional[YOLO26Detector]:
    """进程内单例。首次调用尝试加载；失败返回 None 并打印原因。"""
    global _detector
    if _detector is not None:
        return _detector if _detector.is_ready() else None

    with _lock:
        if _detector is not None:
            return _detector if _detector.is_ready() else None

        if os.environ.get("YOLO26_DISABLE") == "1":
            print("[YOLO26] 已通过 YOLO26_DISABLE=1 关闭推理")
            return None

        weights = os.environ.get("YOLO26_WEIGHTS") or _default_weights()
        device = os.environ.get("YOLO26_DEVICE", "cpu")
        conf = float(os.environ.get("YOLO26_CONF", "0.35"))

        d = YOLO26Detector(weights=weights, device=device, conf=conf)
        ok = d.load()
        _detector = d
        if ok:
            print(f"[YOLO26] 已加载: {weights} (device={device}, conf={conf})")
            return d
        print(f"[YOLO26] 加载失败，跳过推理叠加: {d.error()}")
        return None
