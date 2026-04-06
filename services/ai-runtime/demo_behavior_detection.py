"""
行为检测演示脚本 - 在视频上标注检测到的行为

对每个素材视频：
1. 运行 AI Pipeline 检测行为
2. 在视频上绘制边界框和行为标签
3. 输出带标注的视频到 output/ 目录

用法: python demo_behavior_detection.py
"""
import sys
sys.path.insert(0, 'src')

import os
import cv2
import time
import numpy as np
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ai_runtime.models import Track, Detection, BoundingBox, PoseSkeleton, EventType
from ai_runtime.behavior.behavior_recognizer import BehaviorRecognizerPipeline


# 行为标签中文映射
BEHAVIOR_LABELS = {
    EventType.FIGHTING: "打架斗殴",
    EventType.BULLYING: "校园霸凌",
    EventType.FALLING: "摔倒",
    EventType.SUICIDE_RISK: "疑似轻生",
    EventType.VANDALISM: "破坏设施",
    EventType.SMOKING: "吸烟",
    EventType.PHONE_USE: "低头看手机",
    EventType.CAMERA_BLOCKING: "摄像头遮挡",
    EventType.LOITERING: "异常徘徊",
    EventType.FENCE_CLIMBING: "翻越围栏",
}

# 行为颜色映射 (BGR)
BEHAVIOR_COLORS = {
    EventType.FIGHTING: (0, 0, 255),      # 红色 - 高风险
    EventType.BULLYING: (0, 0, 255),      # 红色 - 高风险
    EventType.FALLING: (0, 0, 255),       # 红色 - 高风险
    EventType.SUICIDE_RISK: (0, 0, 255),  # 红色 - 高风险
    EventType.VANDALISM: (0, 0, 255),     # 红色 - 高风险
    EventType.SMOKING: (0, 165, 255),     # 橙色 - 管理敏感
    EventType.PHONE_USE: (0, 165, 255),   # 橙色 - 管理敏感
    EventType.CAMERA_BLOCKING: (0, 165, 255),  # 橙色 - 管理敏感
    EventType.LOITERING: (0, 255, 255),   # 黄色 - 可疑
    EventType.FENCE_CLIMBING: (0, 255, 255),   # 黄色 - 可疑
}


@dataclass
class TrackedBehavior:
    """跟踪中的行为"""
    behavior_type: EventType
    track_id: str
    confidence: float
    start_frame: int
    last_frame: int


class IoUTracker:
    """基于 IoU 的跟踪器"""

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 30):
        self.tracks: Dict[str, Dict] = {}
        self.next_id = 0
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.frame_count = 0

    def update(self, detections: List[Detection], fps: float = 30.0) -> List[Track]:
        self.frame_count += 1
        matched_ids = set()
        unmatched_indices = list(range(len(detections)))

        for det_idx, det in enumerate(detections):
            best_iou = 0.0
            best_track_id = None

            for track_id, track_data in self.tracks.items():
                if track_id in matched_ids:
                    continue
                if track_data["class_name"] != det.class_name:
                    continue
                last_bbox = track_data["detections"][-1]["bbox"]
                iou = self._compute_iou(last_bbox, det.bbox)
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id:
                self.tracks[best_track_id]["detections"].append({
                    "bbox": det.bbox,
                    "frame": self.frame_count,
                    "confidence": det.confidence
                })
                if det.pose:
                    self.tracks[best_track_id]["poses"].append(det.pose)
                matched_ids.add(best_track_id)
                unmatched_indices.remove(det_idx)

        for det_idx in unmatched_indices:
            det = detections[det_idx]
            track_id = f"track_{self.next_id:04d}"
            self.next_id += 1
            self.tracks[track_id] = {
                "class_name": det.class_name,
                "detections": [{
                    "bbox": det.bbox,
                    "frame": self.frame_count,
                    "confidence": det.confidence
                }],
                "poses": [det.pose] if det.pose else [],
                "age": 0,
                "first_seen": self.frame_count,
            }

        for track_id in list(self.tracks.keys()):
            if track_id not in matched_ids:
                self.tracks[track_id]["age"] += 1
            if self.tracks[track_id]["age"] > self.max_age:
                del self.tracks[track_id]

        result = []
        for track_id, data in self.tracks.items():
            if data["age"] > 0:
                continue
            traj = [d["bbox"] for d in data["detections"]]
            pose_hist = data["poses"]
            dwell_time = (self.frame_count - data["first_seen"] + 1) / fps
            track = Track(
                track_id=track_id,
                class_name=data["class_name"],
                trajectory=traj,
                pose_history=pose_hist,
                dwell_time=dwell_time,
            )
            result.append(track)

        return result

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

    def reset(self):
        self.tracks.clear()
        self.next_id = 0
        self.frame_count = 0


class BehaviorDetectorDemo:
    """行为检测演示器"""

    def __init__(self, video_dir: str, output_dir: str):
        self.video_dir = video_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        print("[*] 加载 AI 模型...")
        from ai_runtime.detector.detector import create_detector
        from ai_runtime.pose.pose_estimator import create_pose_estimator

        self.detector = create_detector("yolo", device="cpu")
        self.pose_estimator = create_pose_estimator("yolo", device="cpu")
        self.behavior_recognizer = BehaviorRecognizerPipeline()
        self.tracker = IoUTracker(iou_threshold=0.3, max_age=30)

        print(f"[*] 检测器就绪: {self.detector.is_ready()}")
        print(f"[*] 姿态估计器就绪: {self.pose_estimator.is_ready()}")
        print("[*] 准备完成!\n")

        # 跟踪每个 track 的当前行为
        self.track_behaviors: Dict[str, TrackedBehavior] = {}

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
                   color: Tuple[int, int, int], font_scale: float = 0.6):
        """绘制带背景的标签"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = 2

        # 获取文字尺寸
        (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)

        # 背景矩形
        padding = 6
        bg_x1 = x
        bg_y1 = y - text_h - padding * 2
        bg_x2 = x + text_w + padding * 2
        bg_y2 = y

        # 确保不超出图像边界
        if bg_y1 < 0:
            bg_y1 = y
            bg_y2 = y + text_h + padding * 2

        # 绘制背景
        cv2.rectangle(img, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1)

        # 绘制文字
        text_x = bg_x1 + padding
        text_y = bg_y2 - padding if bg_y1 == y else bg_y1 + text_h + padding // 2
        cv2.putText(img, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)

        return bg_y2 if bg_y1 == y else bg_y1

    def draw_detection(self, img: np.ndarray, track: Track, behavior: Optional[TrackedBehavior],
                       width: int, height: int):
        """在图像上绘制检测结果"""
        if not track.trajectory:
            return

        bbox = track.trajectory[-1]
        x1 = int(bbox.x * width)
        y1 = int(bbox.y * height)
        x2 = int((bbox.x + bbox.width) * width)
        y2 = int((bbox.y + bbox.height) * height)

        # 确保坐标在图像范围内
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)

        if behavior:
            # 有行为检测 - 使用行为对应的颜色
            color = BEHAVIOR_COLORS.get(behavior.behavior_type, (0, 255, 0))
            label = BEHAVIOR_LABELS.get(behavior.behavior_type, behavior.behavior_type.value)
            label_text = f"{label} ({behavior.confidence:.2f})"

            # 绘制粗边框
            self.draw_rounded_rect(img, x1, y1, x2, y2, color, thickness=3, radius=8)
            # 绘制标签
            self.draw_label(img, label_text, x1, y1, color)
        else:
            # 仅检测到人物 - 绿色细框
            color = (0, 255, 0)
            self.draw_rounded_rect(img, x1, y1, x2, y2, color, thickness=1, radius=5)

    def process_video(self, video_path: str) -> Dict[str, Any]:
        """处理单个视频并输出带标注的版本"""
        filename = os.path.basename(video_path)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(self.output_dir, f"{name_without_ext}_detected.mp4")

        print(f"{'='*70}")
        print(f"处理视频: {filename}")
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
        self.track_behaviors.clear()

        frame_idx = 0
        behavior_events: Dict[str, List] = defaultdict(list)
        start_time = time.time()

        # 处理每一帧
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            # BGR -> RGB 用于检测
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 1. YOLO 检测
            detections = self.detector.detect(frame_rgb)

            # 2. 姿态估计
            if detections:
                poses = self.pose_estimator.estimate(frame_rgb, detections)
                for det, pose in zip(detections, poses):
                    det.pose = pose

            # 3. 跟踪
            tracks = self.tracker.update(detections, fps=fps) if detections else []

            # 4. 更新行为识别器
            if tracks:
                self.behavior_recognizer.feature_extractor.update(tracks)
                results = self.behavior_recognizer.recognize(tracks)

                # 更新 track 行为状态
                current_frame_behaviors: Dict[str, TrackedBehavior] = {}
                for result in results:
                    # 找到对应的 track
                    for track in tracks:
                        # 简化：将行为关联到第一个检测到的人
                        if track.class_name == "person":
                            behavior = TrackedBehavior(
                                behavior_type=result.behavior_type,
                                track_id=track.track_id,
                                confidence=result.confidence,
                                start_frame=frame_idx,
                                last_frame=frame_idx
                            )
                            current_frame_behaviors[track.track_id] = behavior

                            # 记录事件
                            et = result.behavior_type.value
                            behavior_events[et].append({
                                "frame": frame_idx,
                                "confidence": result.confidence,
                            })
                            break

                # 更新跟踪状态
                for track_id, behavior in current_frame_behaviors.items():
                    if track_id in self.track_behaviors:
                        # 延续已有行为
                        self.track_behaviors[track_id].last_frame = frame_idx
                        self.track_behaviors[track_id].confidence = behavior.confidence
                    else:
                        # 新行为
                        self.track_behaviors[track_id] = behavior

            # 清理消失 track 的行为记录
            active_track_ids = {t.track_id for t in tracks}
            for tid in list(self.track_behaviors.keys()):
                if tid not in active_track_ids:
                    del self.track_behaviors[tid]

            # 5. 绘制标注
            for track in tracks:
                behavior = self.track_behaviors.get(track.track_id)
                self.draw_detection(frame, track, behavior, width, height)

            # 添加视频信息 overlay
            info_text = f"Frame: {frame_idx}/{total_frames}"
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 显示当前检测到的行为列表
            y_offset = 60
            for track_id, behavior in self.track_behaviors.items():
                label = BEHAVIOR_LABELS.get(behavior.behavior_type, behavior.behavior_type.value)
                status_text = f"检测到: {label}"
                color = BEHAVIOR_COLORS.get(behavior.behavior_type, (0, 255, 0))
                cv2.putText(frame, status_text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 25

            # 写入输出视频
            out.write(frame)

            # 进度显示
            if frame_idx % 30 == 0:
                detected = list(behavior_events.keys())
                print(f"    帧 {frame_idx}/{total_frames}: 检测到行为={detected}")

        cap.release()
        out.release()

        elapsed = time.time() - start_time

        # 打印结果
        print(f"\n    检测结果:")
        for et, events in sorted(behavior_events.items()):
            avg_conf = sum(e["confidence"] for e in events) / len(events)
            print(f"      - {et}: {len(events)} 次, 平均置信度={avg_conf:.3f}")

        print(f"    处理完成: {frame_idx} 帧, 耗时 {elapsed:.1f} 秒")
        print(f"    输出视频: {output_path}")

        return {
            "filename": filename,
            "output_path": output_path,
            "frames_processed": frame_idx,
            "elapsed": elapsed,
            "behaviors_detected": list(behavior_events.keys()),
            "behavior_counts": {k: len(v) for k, v in behavior_events.items()},
        }

    def run_all(self):
        """处理所有视频"""
        files = sorted([f for f in os.listdir(self.video_dir) if f.endswith('.mp4')])

        print(f"\n发现 {len(files)} 个视频:")
        for f in files:
            print(f"  - {f}")
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
        print(f"{'='*70}")

        for r in results:
            fn = r.get("filename", "?")
            if r.get("error"):
                print(f"  ❌ {fn}: 错误 - {r.get('error')}")
            else:
                behaviors = r.get("behaviors_detected", [])
                output = r.get("output_path", "")
                print(f"  ✅ {fn}: 检测到 {behaviors}")
                print(f"     输出: {output}")


def main():
    video_dir = "D:/vidio_school_system/sucai"
    output_dir = "D:/vidio_school_system/sucai/output"

    if not os.path.exists(video_dir):
        print(f"视频目录不存在: {video_dir}")
        return

    demo = BehaviorDetectorDemo(video_dir, output_dir)
    demo.run_all()

    print(f"\n{'='*70}")
    print("所有视频处理完成!")
    print(f"带标注的视频保存在: {output_dir}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
