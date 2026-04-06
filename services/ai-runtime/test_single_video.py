"""
单视频测试脚本 - 用于逐个调优检测器

用法:
    python test_single_video.py <视频文件名> [选项]

示例:
    python test_single_video.py 吸烟.mp4
    python test_single_video.py 低头看手机.mp4 --show-poses
    python test_single_video.py 打架.mp4 --max-frames 300
"""
import sys
sys.path.insert(0, 'src')

import os
import cv2
import argparse
import numpy as np
from collections import defaultdict
from typing import List, Dict, Any

from ai_runtime.detector.detector import create_detector
from ai_runtime.pose.pose_estimator import create_pose_estimator
from ai_runtime.behavior.behavior_recognizer import BehaviorRecognizerPipeline
from ai_runtime.models import Track


class SimpleTracker:
    """简单的IoU跟踪器"""
    def __init__(self, iou_threshold=0.3):
        self.tracks = {}
        self.next_id = 0
        self.frame_count = 0
        self.iou_threshold = iou_threshold

    def _iou(self, b1, b2):
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

    def update(self, detections, fps=30.0):
        self.frame_count += 1
        matched = set()
        result = []

        for det in detections:
            if det.class_name != 'person':
                continue
            best_iou = self.iou_threshold
            best_id = None
            for tid, tdata in self.tracks.items():
                if tid in matched:
                    continue
                iou = self._iou(tdata['bbox'], det.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_id = tid

            if best_id:
                self.tracks[best_id]['bbox'] = det.bbox
                self.tracks[best_id]['detections'].append({'bbox': det.bbox, 'frame': self.frame_count})
                if det.pose:
                    self.tracks[best_id]['poses'].append(det.pose)
                matched.add(best_id)
                track = Track(
                    track_id=best_id,
                    class_name=det.class_name,
                    trajectory=[d['bbox'] for d in self.tracks[best_id]['detections']],
                    pose_history=self.tracks[best_id]['poses'],
                    dwell_time=self.frame_count / fps
                )
                result.append(track)
            else:
                tid = f'track_{self.next_id:04d}'
                self.next_id += 1
                self.tracks[tid] = {
                    'bbox': det.bbox,
                    'detections': [{'bbox': det.bbox, 'frame': self.frame_count}],
                    'poses': [det.pose] if det.pose else [],
                    'class_name': det.class_name
                }

        # 清理旧轨迹
        for tid in list(self.tracks.keys()):
            if tid not in matched and self.frame_count - self.tracks[tid]['detections'][-1]['frame'] > 30:
                del self.tracks[tid]

        return result


def analyze_poses(video_path: str, frame_nums: List[int]):
    """分析指定帧的姿态特征"""
    print(f"\n{'='*60}")
    print(f"姿态分析: {os.path.basename(video_path)}")
    print(f"{'='*60}")

    detector = create_detector('yolo', device='cpu')
    pose_estimator = create_pose_estimator('yolo', device='cpu')

    cap = cv2.VideoCapture(video_path)

    for frame_num in frame_nums:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detections = detector.detect(frame_rgb)
        persons = [d for d in detections if d.class_name == 'person']

        if not persons:
            print(f"\nFrame {frame_num}: No person detected")
            continue

        poses = pose_estimator.estimate(frame_rgb, persons)

        print(f"\nFrame {frame_num}: {len(persons)} person(s)")
        for i, (det, pose) in enumerate(zip(persons, poses)):
            print(f"  Person {i}: conf={det.confidence:.3f}, size={det.bbox.width:.3f}x{det.bbox.height:.3f}")
            if pose:
                if pose.nose and pose.left_wrist:
                    dist = np.sqrt((pose.left_wrist.x - pose.nose.x)**2 + (pose.left_wrist.y - (pose.nose.y + 0.03))**2)
                    print(f"    left_wrist_to_mouth: {dist:.3f}")
                if pose.nose and pose.right_wrist:
                    dist = np.sqrt((pose.right_wrist.x - pose.nose.x)**2 + (pose.right_wrist.y - (pose.nose.y + 0.03))**2)
                    print(f"    right_wrist_to_mouth: {dist:.3f}")
                if pose.nose and pose.left_hip and pose.right_hip:
                    tilt = pose.nose.y - (pose.left_hip.y + pose.right_hip.y) / 2
                    print(f"    head_tilt: {tilt:.3f}")

    cap.release()


def test_video(video_path: str, max_frames: int = None, show_progress: bool = True):
    """测试单个视频"""
    print(f"\n{'='*60}")
    print(f"测试视频: {os.path.basename(video_path)}")
    print(f"{'='*60}")

    # 加载模型
    detector = create_detector('yolo', device='cpu')
    pose_estimator = create_pose_estimator('yolo', device='cpu')
    behavior_recognizer = BehaviorRecognizerPipeline()
    tracker = SimpleTracker()

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"视频信息: {width}x{height} @ {fps:.1f}fps, {total} frames")

    all_events = defaultdict(list)
    frame_idx = 0
    max_frames = max_frames or total

    while frame_idx < min(max_frames, total):
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detections = detector.detect(frame_rgb)
        persons = [d for d in detections if d.class_name == 'person']

        if not persons:
            continue

        poses = pose_estimator.estimate(frame_rgb, persons)
        for det, pose in zip(persons, poses):
            det.pose = pose

        tracks = tracker.update(persons, fps=fps)
        if not tracks:
            continue

        behavior_recognizer.feature_extractor.update(tracks)
        results = behavior_recognizer.recognize(tracks)

        for r in results:
            et = r.behavior_type.value
            all_events[et].append({
                'frame': frame_idx,
                'conf': r.confidence,
                'evidence': r.evidence
            })

        if show_progress and frame_idx % 100 == 0:
            print(f"  Frame {frame_idx}/{max_frames}: {list(all_events.keys())}")

    cap.release()

    # 打印结果
    print(f"\n检测结果:")
    print(f"  检测到 {len(all_events)} 种行为:")
    for et, events in sorted(all_events.items()):
        avg_conf = sum(e['conf'] for e in events) / len(events)
        print(f"    - {et}: {len(events)} 次, 平均置信度={avg_conf:.3f}")

    return dict(all_events)


def main():
    parser = argparse.ArgumentParser(description='单视频行为检测测试')
    parser.add_argument('video', help='视频文件名 (如: 吸烟.mp4)')
    parser.add_argument('--video-dir', default='D:/vidio_school_system/sucai',
                       help='视频目录路径')
    parser.add_argument('--max-frames', type=int, default=None,
                       help='最大处理帧数')
    parser.add_argument('--analyze-poses', action='store_true',
                       help='分析姿态特征')
    parser.add_argument('--frames', type=int, nargs='+', default=[100, 200, 300],
                       help='要分析的帧号列表 (用于 --analyze-poses)')

    args = parser.parse_args()

    video_path = os.path.join(args.video_dir, args.video)
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在: {video_path}")
        return

    if args.analyze_poses:
        analyze_poses(video_path, args.frames)
    else:
        test_video(video_path, args.max_frames)


if __name__ == '__main__':
    main()
