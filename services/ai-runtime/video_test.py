"""
视频素材测试脚本 - 逐帧跑 AI Pipeline

对 sucai 目录下的每个 MP4 视频，运行完整 AI 行为检测：
1. YOLO 检测
2. ByteTrack 跟踪（修正版，保留轨迹历史）
3. YOLO-Pose 姿态估计
4. 行为识别器（9个检测器）
5. 输出每类行为的检测次数和帧号

用法: python video_test.py
"""
import sys
sys.path.insert(0, 'src')

import os
import cv2
import time
from collections import defaultdict
from typing import List, Dict, Any, Optional

from ai_runtime.models import Track, Detection, BoundingBox, PoseSkeleton
from ai_runtime.behavior.behavior_recognizer import BehaviorRecognizerPipeline


# ============ 修正版跟踪器 ============

class IoUTracker:
    """基于 IoU 的跟踪器 - 保留完整轨迹历史"""

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 30):
        self.tracks: Dict[str, Dict] = {}  # track_id -> {detections, poses, class_name, age, first_seen}
        self.next_id = 0
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.frame_count = 0

    def update(self, detections: List[Detection], fps: float = 30.0) -> List[Track]:
        """更新跟踪器，返回当前活跃的 Track 列表"""
        self.frame_count += 1
        matched_ids = set()
        unmatched_indices = list(range(len(detections)))

        # 匹配已有轨迹
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

        # 创建新轨迹
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

        # 增加未匹配轨迹的年龄，移除过期轨迹
        for track_id in list(self.tracks.keys()):
            if track_id not in matched_ids:
                self.tracks[track_id]["age"] += 1
            if self.tracks[track_id]["age"] > self.max_age:
                del self.tracks[track_id]

        # 转换为 Track 对象
        result = []
        for track_id, data in self.tracks.items():
            if data["age"] > 0:  # 只返回匹配过的
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
        return inter / (area1 + area2 - inter + 1e-6)

    def reset(self):
        self.tracks.clear()
        self.next_id = 0
        self.frame_count = 0


# ============ 视频测试器 ============

class VideoTester:
    VIDEO_EXPECTATIONS = {
        "摔倒.mp4": ["falling"],
        "打架.mp4": ["fighting", "bullying"],
        "校园霸凌.mp4": ["bullying"],
        "吸烟.mp4": ["smoking"],
        "低头看手机.mp4": ["phone_use"],
        "异常徘徊.mp4": ["loitering"],
        "翻越围栏.mp4": ["fence_climbing"],
        "破坏公共设施.mp4": ["vandalism"],
        "轻生.mp4": ["suicide_risk"],
        "摄像头遮挡.mp4": ["camera_blocking"],
    }

    def __init__(self, video_dir: str):
        self.video_dir = video_dir

        print("[*] Loading AI models...")
        from ai_runtime.detector.detector import create_detector
        from ai_runtime.pose.pose_estimator import create_pose_estimator
        from ai_runtime.behavior.behavior_recognizer import BehaviorRecognizerPipeline

        self.detector = create_detector("yolo", device="cpu")
        self.pose_estimator = create_pose_estimator("yolo", device="cpu")
        self.behavior_recognizer = BehaviorRecognizerPipeline()
        self.tracker = IoUTracker(iou_threshold=0.3, max_age=30)

        print(f"[*] Detector ready: {self.detector.is_ready()}")
        print(f"[*] Pose estimator ready: {self.pose_estimator.is_ready()}")
        print(f"[*] Behavior recognizers: {[type(r).__name__ for r in self.behavior_recognizer.recognizers]}")
        print("[*] Ready!\n")

    def process_video(self, video_path: str) -> Dict[str, Any]:
        filename = os.path.basename(video_path)
        expected = self.VIDEO_EXPECTATIONS.get(filename, [])

        print(f"{'='*70}")
        print(f"Video: {filename}")
        print(f"Expected: {expected}")
        print(f"{'='*70}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"filename": filename, "error": f"Cannot open video"}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"    {width}x{height} @ {fps:.1f}fps, {total_frames} frames")

        frame_idx = 0
        all_events: Dict[str, List] = defaultdict(list)
        start_time = time.time()

        # 处理每一帧（真实场景）
        skip = 1

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            if frame_idx % skip != 0:
                continue

            # BGR -> RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 1. YOLO 检测
            detections = self.detector.detect(frame_rgb)
            if not detections:
                continue

            # 2. YOLO-Pose 姿态估计
            poses = self.pose_estimator.estimate(frame_rgb, detections)
            for det, pose in zip(detections, poses):
                det.pose = pose

            # 3. 跟踪
            tracks = self.tracker.update(detections, fps=fps)

            # 4. 更新行为识别器（使用共享特征提取器）
            self.behavior_recognizer.feature_extractor.update(tracks)
            # 注意：recognizers 不需要单独 update，它们使用共享的 feature_extractor

            # 5. 行为识别
            results = self.behavior_recognizer.recognize(tracks)

            for result in results:
                et = result.behavior_type.value
                all_events[et].append({
                    "frame": frame_idx,
                    "confidence": round(result.confidence, 3),
                    "evidence": result.evidence,
                })

            # 进度
            if frame_idx % (skip * 10) == 0:
                detected = list(all_events.keys())
                print(f"    Frame {frame_idx}/{total_frames}: events={detected}")

        cap.release()
        elapsed = time.time() - start_time

        detected = list(all_events.keys())
        matched = [e for e in expected if e in detected]
        missed = [e for e in expected if e not in detected]
        false_pos = [d for d in detected if d not in expected]

        result = {
            "filename": filename,
            "expected": expected,
            "detected": detected,
            "matched": matched,
            "missed": missed,
            "false_positives": false_pos,
            "event_counts": {k: len(v) for k, v in all_events.items()},
            "all_events": dict(all_events),
            "frames_processed": frame_idx,
            "elapsed": round(elapsed, 1),
        }

        # 打印结果
        print(f"\n    Result:")
        for et, count in sorted(result["event_counts"].items()):
            avg_conf = sum(e["confidence"] for e in all_events[et]) / count
            print(f"      - {et}: {count} times, avg_conf={avg_conf:.3f}")

        if missed:
            print(f"    ❌ Missed: {missed}")
        if false_pos:
            print(f"    ⚠️  False positives: {false_pos}")
        if matched:
            print(f"    ✅ Matched: {matched}")

        print(f"    Processed {frame_idx} frames in {elapsed:.1f}s\n")
        return result

    def run_all(self) -> List[Dict[str, Any]]:
        results = []
        files = sorted([f for f in os.listdir(self.video_dir) if f.endswith('.mp4')])

        print(f"\nFound {len(files)} videos:")
        for f in files:
            print(f"  - {f}")
        print()

        for fn in files:
            vp = os.path.join(self.video_dir, fn)
            try:
                r = self.process_video(vp)
                results.append(r)
            except Exception as e:
                import traceback
                print(f"    ❌ Error: {e}")
                traceback.print_exc()
                results.append({"filename": fn, "error": str(e)})

        self._print_summary(results)
        return results

    def _print_summary(self, results: List[Dict[str, Any]]):
        print(f"\n{'='*70}")
        print("FINAL SUMMARY")
        print(f"{'='*70}")

        passed = sum(1 for r in results if not r.get("error") and not r.get("missed"))
        partial = sum(1 for r in results if not r.get("error") and r.get("missed"))
        errors = sum(1 for r in results if r.get("error"))

        print(f"\nTotal: {len(results)} | Passed: {passed} | Partial: {partial} | Errors: {errors}\n")

        for r in results:
            fn = r.get("filename", "?")
            if r.get("error"):
                print(f"  ❌ {fn}: ERROR - {r.get('error')}")
            elif r.get("missed"):
                print(f"  ⚠️  {fn}: Expected {r.get('expected')} → Detected {r.get('detected')} | Missed: {r.get('missed')}")
            else:
                print(f"  ✅ {fn}: {r.get('detected')}")


def main():
    video_dir = "D:/vidio_school_system/sucai"
    if not os.path.exists(video_dir):
        print(f"Video directory not found: {video_dir}")
        return
    tester = VideoTester(video_dir)
    tester.run_all()


if __name__ == "__main__":
    main()
