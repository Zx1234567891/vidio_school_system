"""阶段 1 验证：启动 ai-runtime 后运行本脚本。

用法：
  # 终端1：启动服务（cwd 必须在 services/ai-runtime 下，以便 ./models 路径生效）
  cd D:/vidio_school_system/services/ai-runtime
  python main.py

  # 终端2：
  python test_phase1.py
  python test_phase1.py "D:/vidio_school_system/project1/Kick/kick_backward_1-1.mp4"

输出：在当前目录写入 phase1_result.jpg（叠加后的帧）并打印检测列表。
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import cv2
import httpx

API = "http://127.0.0.1:9001"
DEFAULT_VIDEO = r"D:/vidio_school_system/project1/Smoking/smoking_backward_1-1.mp4"


def main() -> int:
    video = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VIDEO
    frame_index = int(sys.argv[2]) if len(sys.argv) > 2 else 30  # 跳到第 30 帧

    if not Path(video).exists():
        print(f"[!] 视频不存在: {video}")
        return 2

    # 1. health
    with httpx.Client(timeout=30.0) as cli:
        r = cli.get(f"{API}/health")
        r.raise_for_status()
        print("[health]", r.json())

        m = cli.get(f"{API}/models").json()
        print(f"[models.detector] status={m['detector']['status']} "
              f"device={m['detector']['device']} weights={m['detector']['weights']}")

        # 2. 读一帧
        cap = cv2.VideoCapture(video)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            print(f"[!] 无法读取第 {frame_index} 帧")
            return 3
        print(f"[frame] shape={frame.shape}")

        # 3. 编码 → base64
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            return 4
        b64 = base64.b64encode(buf.tobytes()).decode("ascii")

        # 4. 调 /inference
        payload = {
            "frame_id": f"test_{frame_index}",
            "stream_id": "phase1_test",
            "timestamp": time.time(),
            "image_data": b64,
            "return_annotated": True,
            "jpeg_quality": 85,
        }
        t0 = time.time()
        r = cli.post(f"{API}/inference", json=payload, timeout=60.0)
        dt = (time.time() - t0) * 1000
        if r.status_code != 200:
            print(f"[!] {r.status_code}: {r.text[:400]}")
            return 5
        data = r.json()

    print(f"[inference] roundtrip={dt:.1f}ms server={data['processing_time_ms']:.1f}ms "
          f"device={data['device']} dets={data['detections_count']}")
    for d in data["detections"]:
        print(f"  - {d['class_name']:10s} conf={d['confidence']:.3f} "
              f"severity={d['severity']:6s} bbox={d['bbox']}")

    # 5. 保存叠加后的 JPEG
    if data.get("annotated_jpeg_b64"):
        out = Path("phase1_result.jpg")
        out.write_bytes(base64.b64decode(data["annotated_jpeg_b64"]))
        print(f"[ok] annotated saved → {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
