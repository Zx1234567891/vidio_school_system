"""
模拟推流服务 - 使用检测好的视频文件模拟RTSP/RTMP推流
"""
import os
import sys
import cv2
import json
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import queue

# 视频到行为标签的映射
VIDEO_BEHAVIOR_MAP = {
    "低头看手机_检测.mp4": {"label": "低头看手机", "severity": "medium", "category": "敏感行为"},
    "吸烟_检测.mp4": {"label": "吸烟", "severity": "medium", "category": "敏感行为"},
    "异常徘徊_检测.mp4": {"label": "异常徘徊", "severity": "low", "category": "可疑行为"},
    "打架_检测.mp4": {"label": "打架斗殴", "severity": "high", "category": "高风险异常"},
    "摄像头遮挡_检测.mp4": {"label": "摄像头遮挡", "severity": "medium", "category": "敏感行为"},
    "摔倒_检测.mp4": {"label": "摔倒", "severity": "high", "category": "高风险异常"},
    "校园霸凌_检测.mp4": {"label": "校园霸凌", "severity": "high", "category": "高风险异常"},
    "破坏公共设施_检测.mp4": {"label": "破坏设施", "severity": "high", "category": "高风险异常"},
    "翻越围栏_检测.mp4": {"label": "翻越围栏", "severity": "low", "category": "可疑行为"},
    "轻生_检测.mp4": {"label": "疑似轻生", "severity": "high", "category": "高风险异常"},
}


@dataclass
class StreamInfo:
    """流信息"""
    id: str
    name: str
    video_path: str
    status: str  # running, stopped, error
    input_type: str = "file"
    width: int = 0
    height: int = 0
    fps: float = 0.0
    total_frames: int = 0
    current_frame: int = 0
    behavior_label: str = ""
    severity: str = ""
    category: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    loop: bool = True


class MockStreamer:
    """模拟推流器 - 从检测视频模拟实时推流"""

    def __init__(self, video_dir: str, output_rtsp_url: str = "rtsp://localhost:8554"):
        self.video_dir = video_dir
        self.output_rtsp_url = output_rtsp_url
        self.streams: Dict[str, StreamInfo] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        self.frame_queues: Dict[str, queue.Queue] = {}
        # 最新帧缓冲区：每个 stream_id -> 最新的 JPEG bytes
        self.latest_frames: Dict[str, bytes] = {}
        self._frame_locks: Dict[str, threading.Lock] = {}

        # 加载所有视频
        self._scan_videos()

    def _scan_videos(self):
        """扫描视频目录"""
        video_files = sorted([f for f in os.listdir(self.video_dir) if f.endswith('_检测.mp4')])

        for idx, filename in enumerate(video_files, 1):
            video_path = os.path.join(self.video_dir, filename)
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                print(f"[!] 无法打开视频: {filename}")
                continue

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            # 获取行为标签
            behavior_info = VIDEO_BEHAVIOR_MAP.get(filename, {
                "label": "未知行为",
                "severity": "unknown",
                "category": "未知"
            })

            stream_id = f"stream_{idx:03d}"
            stream = StreamInfo(
                id=stream_id,
                name=f"{behavior_info['label']}检测",
                video_path=video_path,
                status="stopped",
                input_type="file",
                width=width,
                height=height,
                fps=fps,
                total_frames=total_frames,
                current_frame=0,
                behavior_label=behavior_info["label"],
                severity=behavior_info["severity"],
                category=behavior_info["category"],
                loop=True
            )

            self.streams[stream_id] = stream
            self._frame_locks[stream_id] = threading.Lock()
            print(f"[*] 加载视频: {filename} -> {stream_id}")

    def get_all_streams(self) -> List[Dict]:
        """获取所有流信息"""
        return [asdict(s) for s in self.streams.values()]

    def get_stream(self, stream_id: str) -> Optional[Dict]:
        """获取单个流信息"""
        if stream_id in self.streams:
            return asdict(self.streams[stream_id])
        return None

    def start_stream(self, stream_id: str) -> bool:
        """启动推流"""
        if stream_id not in self.streams:
            return False

        if stream_id in self.threads and self.threads[stream_id].is_alive():
            print(f"[!] 流 {stream_id} 已在运行")
            return True

        stream = self.streams[stream_id]
        stream.status = "running"
        stream.start_time = datetime.now().isoformat()
        stream.current_frame = 0

        stop_event = threading.Event()
        self.stop_events[stream_id] = stop_event

        thread = threading.Thread(
            target=self._stream_worker,
            args=(stream_id, stop_event)
        )
        thread.daemon = True
        thread.start()
        self.threads[stream_id] = thread

        print(f"[*] 启动推流: {stream_id} - {stream.name}")
        return True

    def stop_stream(self, stream_id: str) -> bool:
        """停止推流"""
        if stream_id not in self.streams:
            return False

        if stream_id in self.stop_events:
            self.stop_events[stream_id].set()

        stream = self.streams[stream_id]
        stream.status = "stopped"
        stream.end_time = datetime.now().isoformat()

        print(f"[*] 停止推流: {stream_id}")
        return True

    def _stream_worker(self, stream_id: str, stop_event: threading.Event):
        """推流工作线程"""
        stream = self.streams[stream_id]
        video_path = stream.video_path

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            stream.status = "error"
            print(f"[!] 无法打开视频: {video_path}")
            return

        frame_delay = 1.0 / stream.fps
        last_frame_time = time.time()

        try:
            while not stop_event.is_set():
                ret, frame = cap.read()

                if not ret:
                    if stream.loop:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        stream.current_frame = 0
                        continue
                    else:
                        break

                stream.current_frame += 1

                # 将帧编码为 JPEG 并存入最新帧缓冲区
                ret_enc, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret_enc:
                    with self._frame_locks[stream_id]:
                        self.latest_frames[stream_id] = jpeg.tobytes()

                # 控制帧率
                current_time = time.time()
                elapsed = current_time - last_frame_time
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)
                last_frame_time = time.time()

        except Exception as e:
            stream.status = "error"
            print(f"[!] 推流错误 {stream_id}: {e}")
        finally:
            cap.release()
            if stream.status != "error":
                stream.status = "stopped"
            print(f"[*] 推流结束: {stream_id}")

    def start_all(self):
        """启动所有流"""
        for stream_id in self.streams:
            self.start_stream(stream_id)

    def stop_all(self):
        """停止所有流"""
        for stream_id in list(self.streams.keys()):
            self.stop_stream(stream_id)

    def get_latest_frame(self, stream_id: str) -> Optional[bytes]:
        """获取指定流的最新 JPEG 帧"""
        if stream_id not in self._frame_locks:
            return None
        with self._frame_locks[stream_id]:
            return self.latest_frames.get(stream_id)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        running = sum(1 for s in self.streams.values() if s.status == "running")
        return {
            "total_streams": len(self.streams),
            "running_streams": running,
            "stopped_streams": len(self.streams) - running,
        }


# 全局模拟推流器实例
streamer: Optional[MockStreamer] = None


def init_streamer(video_dir: str) -> MockStreamer:
    """初始化推流器"""
    global streamer
    streamer = MockStreamer(video_dir)
    return streamer


def get_streamer() -> Optional[MockStreamer]:
    """获取推流器实例"""
    return streamer


if __name__ == "__main__":
    # 测试模式
    video_dir = "D:/vidio_school_system/sucai/output"

    if not os.path.exists(video_dir):
        print(f"[!] 视频目录不存在: {video_dir}")
        sys.exit(1)

    streamer = init_streamer(video_dir)

    print(f"\n{'='*60}")
    print("模拟推流服务")
    print(f"{'='*60}")
    print(f"加载了 {len(streamer.streams)} 个视频流")

    # 显示所有流
    for sid, s in streamer.streams.items():
        print(f"  {sid}: {s.name} ({s.behavior_label}) - {s.width}x{s.height}@{s.fps:.1f}fps")

    # 启动所有流
    print("\n[*] 启动所有推流...")
    streamer.start_all()

    try:
        while True:
            time.sleep(1)
            stats = streamer.get_stats()
            print(f"\r[*] 运行中: {stats['running_streams']}/{stats['total_streams']}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\n[*] 停止所有推流...")
        streamer.stop_all()
        print("[*] 完成")
