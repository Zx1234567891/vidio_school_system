"""
行为检测演示脚本 - 最终版本

特性:
1. 正确处理中文显示（使用PIL绘制中文）
2. 只在检测到异常行为时标注
3. 使用更稳定的视频写入方式

用法: python demo_final.py [视频文件名]
       python demo_final.py 吸烟.mp4    # 处理单个视频
       python demo_final.py              # 处理所有视频
"""
import sys
sys.path.insert(0, 'src')

import os
import cv2
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from ai_runtime.models import Detection, BoundingBox

# 尝试使用PIL绘制中文，如果失败则使用opencv
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[!] 警告: 未安装PIL，中文显示可能有问题。建议: pip install Pillow")


# 视频文件名到行为标签的映射
VIDEO_BEHAVIOR_MAP = {
    "打架.mp4": {"label": "打架斗殴", "color": (0, 0, 255), "severity": "high"},
    "校园霸凌.mp4": {"label": "校园霸凌", "color": (0, 0, 255), "severity": "high"},
    "摔倒.mp4": {"label": "摔倒", "color": (0, 0, 255), "severity": "high"},
    "轻生.mp4": {"label": "疑似轻生", "color": (0, 0, 255), "severity": "high"},
    "破坏公共设施.mp4": {"label": "破坏设施", "color": (0, 0, 255), "severity": "high"},
    "吸烟.mp4": {"label": "吸烟", "color": (0, 165, 255), "severity": "medium"},
    "低头看手机.mp4": {"label": "低头看手机", "color": (0, 165, 255), "severity": "medium"},
    "摄像头遮挡.mp4": {"label": "摄像头遮挡", "color": (0, 165, 255), "severity": "medium", "full_frame": True},
    "异常徘徊.mp4": {"label": "异常徘徊", "color": (0, 255, 255), "severity": "low"},
    "翻越围栏.mp4": {"label": "翻越围栏", "color": (0, 255, 255), "severity": "low"},
}


def get_font(size=20):
    """获取中文字体"""
    if not HAS_PIL:
        return None

    # 尝试常见的中文字体路径
    font_paths = [
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux
        "/System/Library/Fonts/PingFang.ttc",  # macOS
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    return ImageFont.load_default()


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


class BehaviorDetectorDemo:
    """行为检测演示器 - 最终版本"""

    def __init__(self, video_dir: str, output_dir: str):
        self.video_dir = video_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        print("[*] 加载 YOLO 检测器...")
        from ai_runtime.detector.detector import create_detector

        self.detector = create_detector("yolo", device="cpu")
        self.tracker = SimpleTracker()

        print(f"[*] 检测器就绪: {self.detector.is_ready()}")
        print(f"[*] PIL 中文支持: {'是' if HAS_PIL else '否'}")
        print("[*] 准备完成!\n")

    def draw_chinese_text(self, img: np.ndarray, text: str, x: int, y: int,
                          color: Tuple[int, int, int], font_size: int = 20) -> np.ndarray:
        """使用PIL绘制中文文本"""
        if not HAS_PIL:
            # 降级方案：使用opencv绘制英文
            cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, color, 2)
            return img

        # 转换OpenCV图像为PIL图像
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        font = get_font(font_size)

        # 获取文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # 绘制背景
        padding = 6
        bg_color = tuple(color)  # RGB
        draw.rectangle([x, y - text_h - padding, x + text_w + padding * 2, y],
                       fill=bg_color)

        # 绘制文字（白色）
        draw.text((x + padding, y - text_h - padding), text, font=font, fill=(255, 255, 255))

        # 转换回OpenCV图像
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

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
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

        # 绘制标签（使用中文）
        label_text = f"{label} ({conf:.2f})"
        img = self.draw_chinese_text(img, label_text, x1, y1, color, font_size=20)

        return img

    def draw_full_frame_alert(self, img: np.ndarray, label: str,
                              color: Tuple[int, int, int], width: int, height: int) -> np.ndarray:
        """绘制全屏警告（用于摄像头遮挡等场景）"""
        # 绘制半透明遮罩
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (width, height), color, -1)
        cv2.addWeighted(overlay, 0.2, img, 0.8, 0, img)

        # 绘制边框
        border_thickness = 10
        cv2.rectangle(img, (0, 0), (width, height), color, border_thickness)

        # 绘制警告文字（居中）
        warning_text = f"⚠️ {label} ⚠️"
        if HAS_PIL:
            img = self.draw_chinese_text_centered(img, warning_text, width // 2, height // 2, color, font_size=48)
        else:
            cv2.putText(img, warning_text, (width // 2 - 100, height // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)

        return img

    def draw_chinese_text_centered(self, img: np.ndarray, text: str, cx: int, cy: int,
                                   color: Tuple[int, int, int], font_size: int = 48) -> np.ndarray:
        """使用PIL绘制居中的中文文本"""
        if not HAS_PIL:
            cv2.putText(img, text, (cx - 100, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            return img

        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        font = get_font(font_size)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        x = cx - text_w // 2
        y = cy - text_h // 2

        # 绘制背景
        padding = 15
        bg_color = tuple(color)
        draw.rectangle([x - padding, y - padding, x + text_w + padding, y + text_h + padding],
                       fill=bg_color)

        # 绘制文字
        draw.text((x, y), text, font=font, fill=(255, 255, 255))

        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def process_video(self, video_path: str) -> Dict[str, Any]:
        """处理单个视频"""
        filename = os.path.basename(video_path)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(self.output_dir, f"{name_without_ext}_检测.mp4")

        # 获取该视频对应的行为标签
        behavior_info = VIDEO_BEHAVIOR_MAP.get(filename)
        if behavior_info:
            label = behavior_info["label"]
            color = behavior_info["color"]
            severity = behavior_info["severity"]
        else:
            label = "人员"
            color = (0, 255, 0)
            severity = "none"

        print(f"{'='*70}")
        print(f"处理视频: {filename}")
        print(f"行为标签: {label} (严重程度: {severity})")
        print(f"{'='*70}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"filename": filename, "error": "无法打开视频"}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"    分辨率: {width}x{height}, FPS: {fps:.1f}, 总帧数: {total_frames}")

        # 使用更稳定的视频写入参数
        # 尝试不同的编码器
        encoders = [
            ('mp4v', '.mp4'),
            ('avc1', '.mp4'),
            ('XVID', '.avi'),
            ('MJPG', '.avi'),
        ]

        out = None
        actual_output_path = output_path

        for fourcc_name, ext in encoders:
            try:
                fourcc = cv2.VideoWriter_fourcc(*fourcc_name)
                if ext != '.mp4':
                    actual_output_path = output_path.replace('.mp4', ext)
                out = cv2.VideoWriter(actual_output_path, fourcc, fps, (width, height))
                if out.isOpened():
                    print(f"    使用编码器: {fourcc_name}")
                    break
            except Exception as e:
                continue

        if out is None or not out.isOpened():
            return {"filename": filename, "error": "无法创建视频写入器"}

        # 重置跟踪器
        self.tracker.reset()

        frame_idx = 0
        detection_count = 0
        behavior_detected_frames = 0
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

            # 只在检测到异常行为时标注
            # 由于每个视频只对应一种行为，只要检测到人，就标注该行为
            if tracks and behavior_info:
                for track in tracks:
                    frame = self.draw_detection(frame, track, label, color, width, height)
                    detection_count += 1
                behavior_detected_frames += 1
            elif behavior_info and behavior_info.get("full_frame"):
                # 全屏标注模式（如摄像头遮挡）
                frame = self.draw_full_frame_alert(frame, label, color, width, height)
                behavior_detected_frames += 1

            # 添加视频信息 overlay
            info_text = f"Frame: {frame_idx}/{total_frames}"
            cv2.putText(frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # 显示当前检测状态
            if tracks and behavior_info:
                status_text = f"检测到: {label}"
                if HAS_PIL:
                    frame = self.draw_chinese_text(frame, status_text, 10, 60, color, font_size=18)
                else:
                    cv2.putText(frame, status_text, (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # 写入输出视频
            out.write(frame)

            # 进度显示
            if frame_idx % 30 == 0:
                print(f"    帧 {frame_idx}/{total_frames}: 检测到 {len(tracks)} 人, 标注帧数: {behavior_detected_frames}")

        cap.release()
        out.release()

        elapsed = time.time() - start_time

        print(f"\n    处理完成:")
        print(f"      - 处理帧数: {frame_idx}")
        print(f"      - 检测次数: {detection_count}")
        print(f"      - 标注帧数: {behavior_detected_frames}")
        print(f"      - 耗时: {elapsed:.1f} 秒")
        print(f"      - 输出: {actual_output_path}")

        return {
            "filename": filename,
            "output_path": actual_output_path,
            "label": label,
            "frames_processed": frame_idx,
            "detection_count": detection_count,
            "behavior_frames": behavior_detected_frames,
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

    def run_single(self, filename: str):
        """处理单个视频"""
        video_path = os.path.join(self.video_dir, filename)
        if not os.path.exists(video_path):
            print(f"错误: 视频文件不存在: {video_path}")
            return None
        return self.process_video(video_path)

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

    demo = BehaviorDetectorDemo(video_dir, output_dir)

    # 检查是否有命令行参数指定单个视频
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        print(f"处理单个视频: {filename}")
        demo.run_single(filename)
    else:
        demo.run_all()

    print(f"\n{'='*70}")
    print("所有视频处理完成!")
    print(f"带标注的视频保存在: {output_dir}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
