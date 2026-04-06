"""
行为检测演示脚本 - 修复版

修复内容：
1. 使用 PIL 绘制中文标签
2. 只在检测到异常行为时标注，普通人员不标注
3. 保留真实的行为检测逻辑

用法: python demo_fixed.py
"""
import sys
sys.path.insert(0, 'src')

import os
import cv2
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from ai_runtime.models import Detection, BoundingBox, Track, EventType
from ai_runtime.behavior.behavior_recognizer import BehaviorRecognizerPipeline


# 视频文件名到期望行为的映射
VIDEO_EXPECTED_BEHAVIOR = {
    "打架.mp4": EventType.FIGHTING,
    "校园霸凌.mp4": EventType.BULLYING,
    "摔倒.mp4": EventType.FALLING,
    "轻生.mp4": EventType.SUICIDE_RISK,
    "破坏公共设施.mp4": EventType.VANDALISM,
    "吸烟.mp4": EventType.SMOKING,
    "低头看手机.mp4": EventType.PHONE_USE,
    "摄像头遮挡.mp4": EventType.CAMERA_BLOCKING,
    "异常徘徊.mp4": EventType.LOITERING,
    "翻越围栏.mp4": EventType.FENCE_CLIMBING,
}

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
    EventType.FIGHTING: (0, 0, 255),      # 红色
    EventType.BULLYING: (0, 0, 255),      # 红色
    EventType.FALLING: (0, 0, 255),       # 红色
    EventType.SUICIDE_RISK: (0, 0, 255),  # 红色
    EventType.VANDALISM: (0, 0, 255),     # 红色
    EventType.SMOKING: (0, 165, 255),     # 橙色
    EventType.PHONE_USE: (0, 165, 255),   # 橙色
    EventType.CAMERA_BLOCKING: (0, 165, 255),  # 橙色
    EventType.LOITERING: (0, 255, 255),   # 黄色
    EventType.FENCE_CLIMBING: (0, 255, 255),   # 黄色
}


class IoUTracker:
    """基于 IoU 的跟踪器"""

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 30):
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

    def reset(self):
        self.tracks.clear()
        self.next_id = 0
        self.frame_count = 0


def get_font(size=20):
    """获取中文字体"""
    font_paths = [
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
        "C:/Windows/Fonts/msyhbd.ttc",  # 微软雅黑粗体
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


class BehaviorDemo:
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

        self.font = get_font(24)
        self.font_small = get_font(16)

        print(f"[*] 检测器就绪: {self.detector.is_ready()}")
        print(f"[*] 姿态估计器就绪: {self.pose_estimator.is_ready()}")
        print("[*] 准备完成!\n")

    def draw_chinese_text(self, img: np.ndarray, text: str, x: int, y: int,
                          color: Tuple[int, int, int], font=None):
        """使用 PIL 绘制中文文字"""
        if font is None:
            font = self.font

        # 转换颜色从 BGR 到 RGB
        color_rgb = (color[2], color[1], color[0])

        # 转换为 PIL Image
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        # 获取文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # 绘制背景
        padding = 6
        bg_x1 = x
        bg_y1 = y
        bg_x2 = x + text_w + padding * 2
        bg_y2 = y + text_h + padding * 2

        # 确保不超出边界
        h, w = img.shape[:2]
        if bg_x2 > w:
            bg_x1 = w - text_w - padding * 2
            bg_x2 = w
        if bg_y2 > h:
            bg_y1 = h - text_h - padding * 2
            bg_y2 = h

        draw.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=color_rgb)

        # 绘制文字
        draw.text((bg_x1 + padding, bg_y1 + padding), text, font=font, fill=(255, 255, 255))

        # 转换回 OpenCV 格式
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def draw_detection(self, img: np.ndarray, track: Track, behavior_type: Optional[EventType],
                       confidence: float, width: int, height: int):
        """在图像上绘制检测结果"""
        if not track.trajectory:
            return img

        bbox = track.trajectory[-1]
        x1 = int(bbox.x * width)
        y1 = int(bbox.y * height)
        x2 = int((bbox.x + bbox.width) * width)
        y2 = int((bbox.y + bbox.height) * height)

        # 确保坐标在图像范围内
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)

        if behavior_type:
            # 有异常行为 - 使用对应颜色
            color = BEHAVIOR_COLORS.get(behavior_type, (0, 0, 255))
            label = BEHAVIOR_LABELS.get(behavior_type, behavior_type.value)
            label_text = f"{label} {confidence:.0%}"

            # 绘制粗边框
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

            # 绘制中文标签
            img = self.draw_chinese_text(img, label_text, x1, y1 - 40, color)
        #  else: 普通人员不绘制任何标注

        return img

    def process_video(self, video_path: str) -> Dict[str, Any]:
        """处理单个视频"""
        filename = os.path.basename(video_path)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(self.output_dir, f"{name_without_ext}_检测.mp4")

        # 获取该视频期望检测的行为
        expected_behavior = VIDEO_EXPECTED_BEHAVIOR.get(filename)

        print(f"{'='*70}")
        print(f"处理视频: {filename}")
        if expected_behavior:
            print(f"期望检测: {BEHAVIOR_LABELS.get(expected_behavior, expected_behavior.value)}")
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
        self.behavior_recognizer = BehaviorRecognizerPipeline()  # 重新创建以清空状态

        frame_idx = 0
        behavior_events: Dict[str, List] = defaultdict(list)
        start_time = time.time()

        # 当前活跃的行为 {track_id: (behavior_type, confidence)}
        active_behaviors: Dict[str, Tuple[EventType, float]] = {}

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
            if not detections:
                out.write(frame)
                continue

            # 2. 姿态估计
            poses = self.pose_estimator.estimate(frame_rgb, detections)
            for det, pose in zip(detections, poses):
                det.pose = pose

            # 3. 跟踪
            tracks = self.tracker.update(detections, fps=fps)

            # 4. 行为识别
            if tracks:
                self.behavior_recognizer.feature_extractor.update(tracks)
                results = self.behavior_recognizer.recognize(tracks)

                # 更新活跃行为
                current_behaviors = {}
                for result in results:
                    # 简化：将行为关联到第一个检测到的人
                    for track in tracks:
                        if track.class_name == "person":
                            current_behaviors[track.track_id] = (result.behavior_type, result.confidence)

                            # 记录事件
                            et = result.behavior_type.value
                            behavior_events[et].append({
                                "frame": frame_idx,
                                "confidence": result.confidence,
                            })
                            break

                # 更新活跃行为状态（使用平滑）
                for track_id, (btype, conf) in current_behaviors.items():
                    if track_id in active_behaviors:
                        # 平滑置信度
                        old_conf = active_behaviors[track_id][1]
                        conf = old_conf * 0.7 + conf * 0.3
                    active_behaviors[track_id] = (btype, conf)

            # 清理消失的 track
            active_track_ids = {t.track_id for t in tracks}
            for tid in list(active_behaviors.keys()):
                if tid not in active_track_ids:
                    del active_behaviors[tid]

            # 5. 绘制标注（只标注有异常行为的人）
            for track in tracks:
                behavior_info = active_behaviors.get(track.track_id)
                if behavior_info:
                    btype, conf = behavior_info
                    frame = self.draw_detection(frame, track, btype, conf, width, height)

            # 添加视频信息 overlay
            info_text = f"Frame: {frame_idx}/{total_frames}"
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 显示当前检测到的行为列表
            y_offset = 60
            for track_id, (btype, conf) in active_behaviors.items():
                label = BEHAVIOR_LABELS.get(btype, btype.value)
                status_text = f"检测到: {label} ({conf:.0%})"
                color = BEHAVIOR_COLORS.get(btype, (0, 255, 0))
                # 使用英文显示状态（避免 OpenCV 中文问题）
                cv2.putText(frame, f"Detected: {btype.value} ({conf:.0%})", (10, y_offset),
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
            expected = VIDEO_EXPECTED_BEHAVIOR.get(f)
            label = BEHAVIOR_LABELS.get(expected, "未知") if expected else "未知"
            print(f"  - {f} -> {label}")
        print()

        results = []
        # 只处理一个短视频用于测试
        test_file = "吸烟.mp4"  # 选择较小的视频测试
        if test_file in files:
            fn = test_file
        else:
            fn = files[0]
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
                behaviors = r.get("behaviors_detected", [])
                output = os.path.basename(r.get("output_path", ""))
                print(f"  ✅ {fn}")
                print(f"     检测到: {behaviors}")
                print(f"     输出: {output}")
                print()


def main():
    video_dir = "D:/vidio_school_system/sucai"
    output_dir = "D:/vidio_school_system/sucai/output_fixed"

    if not os.path.exists(video_dir):
        print(f"视频目录不存在: {video_dir}")
        return

    demo = BehaviorDemo(video_dir, output_dir)
    demo.run_all()

    print(f"{'='*70}")
    print("所有视频处理完成!")
    print(f"带标注的视频保存在: {output_dir}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
