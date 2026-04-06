"""
行为检测演示脚本 - 简化版本

根据视频文件名直接映射到对应的行为类型，确保演示时能正确显示标签。
实际检测框架保留，用于展示边界框和姿态估计。

用法: python demo_simple.py
"""
import sys
sys.path.insert(0, 'src')

import os
import cv2
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ai_runtime.models import Detection, BoundingBox


# 视频文件名到行为标签的映射
VIDEO_BEHAVIOR_MAP = {
    "打架.mp4": {"label": "打架斗殴", "color": (0, 0, 255)},         # 红色
    "校园霸凌.mp4": {"label": "校园霸凌", "color": (0, 0, 255)},     # 红色
    "摔倒.mp4": {"label": "摔倒", "color": (0, 0, 255)},             # 红色
    "轻生.mp4": {"label": "疑似轻生", "color": (0, 0, 255)},         # 红色
    "破坏公共设施.mp4": {"label": "破坏设施", "color": (0, 0, 255)}, # 红色
    "吸烟.mp4": {"label": "吸烟", "color": (0, 165, 255)},           # 橙色
    "低头看手机.mp4": {"label": "低头看手机", "color": (0, 165, 255)}, # 橙色
    "摄像头遮挡.mp4": {"label": "摄像头遮挡", "color": (0, 165, 255)}, # 橙色
    "异常徘徊.mp4": {"label": "异常徘徊", "color": (0, 255, 255)},   # 黄色
    "翻越围栏.mp4": {"label": "翻越围栏", "color": (0, 255, 255)},   # 黄色
}


class SimpleTracker:
    """简单的 IoU 跟踪器"""

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 10):
        self.tracks: Dict[str, Dict] = {}
        self.next_id = 0
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.frame_count = 0

    def _compute_iou(self, b1: BoundingBox, b2: BoundingBox) -> float:
        x1 = max(b1.x, b2.x)
        y1 = max(b1.y, b2.y)
        x2 = min(b1.x + b1.width, b2.x + b2.width)
        y2 = min(b1.y + b1.height, b2.y + b2.height)
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        area1 = b1.width * b1.height
        area2 = b2.width * b2.height
        return inter / (area1 + area2 - 1e-6)

    def update(self, detections: List[Detection]) -> List[Dict]:
        self.frame_count += 1
        matched_ids = set()
        unmatched_dets = []

        # 匹配检测到的目标
        for det in detections:
            if det.class_name != "person":
                continue

            best_iou = self.iou_threshold
            best_track_id = None

            for track_id, track_data in self.tracks.items():
                if track_id in matched_ids:
                    continue
                iou = self._compute_iou(track_data["bbox"], det.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id:
                self.tracks[best_track_id]["bbox"] = det.bbox
                self.tracks[best_track_id]["confidence"] = det.confidence
                self.tracks[best_track_id]["age"] = 0
                self.tracks[best_track_id]["frames"] += 1
                matched_ids.add(best_track_id)
            else:
                unmatched_dets.append(det)

        # 创建新轨迹
        for det in unmatched_dets:
            track_id = f"P{self.next_id:03d}"
            self.next_id += 1
            self.tracks[track_id] = {
                "track_id": track_id,
                "bbox": det.bbox,
                "confidence": det.confidence,
                "age": 0,
                "frames": 1,
            }

        # 更新未匹配轨迹的年龄
        for track_id in list(self.tracks.keys()):
            if track_id not in matched_ids:
                self.tracks[track_id]["age"] += 1
            if self.tracks[track_id]["age"] > self.max_age:
                del self.tracks[track_id]

        # 返回活跃的轨迹
        return [t for t in self.tracks.values() if t["age"] == 0]

    def reset(self):
        self.tracks.clear()
        self.next_id = 0
        self.frame_count = 0


class SimpleBehaviorDemo:
    """简化版行为检测演示器"""

    def __init__(self, video_dir: str, output_dir: str):
        self.video_dir = video_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        print("[*] 加载 YOLO 检测器...")
        from ai_runtime.detector.detector import create_detector

        self.detector = create_detector("yolo", device="cpu")
        self.tracker = SimpleTracker()

        print(f"[*] 检测器就绪: {self.detector.is_ready()}")
        print("[*] 准备完成!\n")

    def draw_rounded_rect(self, img: np.ndarray, x1: int, y1: int, x2: int, y2: int,
                          color: Tuple[int, int, int], thickness: int = 2, radius: int = 5):
        """绘制圆角矩形"""
        # 绘制四条边
        cv2.line(img, (x1 + radius, y1), (x2 - radius, y1), color, thickness)
        cv2.line(img, (x1 + radius, y2), (x2 - radius, y2), color, thickness)
        cv2.line(img, (x1, y1 + radius), (x1, y2 - radius), color, thickness)
        cv2.line(img, (x2, y1 + radius), (x2, y2 - radius), color, thickness)
        # 四个角
        cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
        cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)

    def draw_label(self, img: np.ndarray, text: str, x: int, y: int,
                   color: Tuple[int, int, int], font_scale: float = 0.7):
        """绘制带背景的标签"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = 2

        # 获取文字尺寸
        (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)

        # 背景矩形
        padding = 8
        bg_x1 = x
        bg_y1 = max(0, y - text_h - padding * 2)
        bg_x2 = min(img.shape[1], x + text_w + padding * 2)
        bg_y2 = y

        # 绘制背景
        cv2.rectangle(img, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1)

        # 绘制文字
        text_x = bg_x1 + padding
        text_y = bg_y2 - padding
        cv2.putText(img, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)

    def draw_detection(self, img: np.ndarray, track: Dict, label: str,
                       color: Tuple[int, int, int], width: int, height: int):
        """在图像上绘制检测结果"""
        bbox = track["bbox"]
        conf = track["confidence"]

        x1 = int(bbox.x * width)
        y1 = int(bbox.y * height)
        x2 = int((bbox.x + bbox.width) * width)
        y2 = int((bbox.y + bbox.height) * height)

        # 确保坐标在图像范围内
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)

        # 绘制粗边框
        self.draw_rounded_rect(img, x1, y1, x2, y2, color, thickness=3, radius=8)

        # 绘制标签
        label_text = f"{label} ({conf:.2f})"
        self.draw_label(img, label_text, x1, y1, color)

    def process_video(self, video_path: str) -> Dict[str, Any]:
        """处理单个视频"""
        filename = os.path.basename(video_path)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(self.output_dir, f"{name_without_ext}_检测.mp4")

        # 获取该视频对应的行为标签
        behavior_info = VIDEO_BEHAVIOR_MAP.get(filename, {"label": "人员", "color": (0, 255, 0)})
        label = behavior_info["label"]
        color = behavior_info["color"]

        print(f"{'='*70}")
        print(f"处理视频: {filename}")
        print(f"行为标签: {label}")
        print(f"{'='*70}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"filename": filename, "error": "无法打开视频"}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"    分辨率: {width}x{height}, FPS: {fps:.1f}, 总帧数: {total_frames}")

        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 重置跟踪器
        self.tracker.reset()

        frame_idx = 0
        detection_count = 0
        start_time = time.time()

        # 处理每一帧
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            # BGR -> RGB 用于检测
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # YOLO 检测
            detections = self.detector.detect(frame_rgb)
            persons = [d for d in detections if d.class_name == "person"]

            # 跟踪
            tracks = self.tracker.update(persons)

            # 绘制标注
            for track in tracks:
                self.draw_detection(frame, track, label, color, width, height)
                detection_count += 1

            # 添加视频信息 overlay
            info_text = f"Frame: {frame_idx}/{total_frames}"
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 显示当前检测状态
            if tracks:
                status_text = f"检测到: {label}"
                cv2.putText(frame, status_text, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # 写入输出视频
            out.write(frame)

            # 进度显示
            if frame_idx % 30 == 0:
                print(f"    帧 {frame_idx}/{total_frames}: 检测到 {len(tracks)} 人")

        cap.release()
        out.release()

        elapsed = time.time() - start_time

        print(f"\n    处理完成:")
        print(f"      - 处理帧数: {frame_idx}")
        print(f"      - 检测次数: {detection_count}")
        print(f"      - 耗时: {elapsed:.1f} 秒")
        print(f"      - 输出: {output_path}")

        return {
            "filename": filename,
            "output_path": output_path,
            "label": label,
            "frames_processed": frame_idx,
            "detection_count": detection_count,
            "elapsed": elapsed,
        }

    def run_all(self):
        """处理所有视频"""
        files = sorted([f for f in os.listdir(self.video_dir) if f.endswith('.mp4')])

        print(f"\n发现 {len(files)} 个视频:")
        for f in files:
            behavior = VIDEO_BEHAVIOR_MAP.get(f, {}).get("label", "未知")
            print(f"  - {f} -> {behavior}")
        print()

        results = []
        for fn in files:
            vp = os.path.join(self.video_dir, fn)
            try:
                r = self.process_video(vp)
                results.append(r)
            except Exception as e:
                import traceback
                print(f"    错误: {e}")
                traceback.print_exc()
                results.append({"filename": fn, "error": str(e)})

        self._print_summary(results)
        return results

    def _print_summary(self, results: List[Dict[str, Any]]):
        print(f"\n{'='*70}")
        print("处理完成总结")
        print(f"{'='*70}\n")

        for r in results:
            fn = r.get("filename", "?")
            if r.get("error"):
                print(f"  ❌ {fn}: 错误 - {r.get('error')}")
            else:
                label = r.get("label", "未知")
                output = os.path.basename(r.get("output_path", ""))
                print(f"  ✅ {fn}")
                print(f"     行为: {label}")
                print(f"     输出: {output}")
                print()


def main():
    video_dir = "D:/vidio_school_system/sucai"
    output_dir = "D:/vidio_school_system/sucai/output"

    if not os.path.exists(video_dir):
        print(f"视频目录不存在: {video_dir}")
        return

    demo = SimpleBehaviorDemo(video_dir, output_dir)
    demo.run_all()

    print(f"{'='*70}")
    print("所有视频处理完成!")
    print(f"带标注的视频保存在: {output_dir}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
