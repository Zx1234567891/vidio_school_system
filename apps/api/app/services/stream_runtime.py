"""视频流运行时 - 阶段 2：纯 Python 解码线程池 + 远端 GPU 推理

每路流一个后台线程：

    OpenCV 解码 → 每 N 帧 **异步** POST /inference → 画框 → 编码 JPEG → 缓存

关键：推理调用**不阻塞**解码循环，而是丢到共享线程池里跑；结果回来前
复用上一次的检测框继续画，解码线程全速出帧。这样 N 路流争抢单 GPU 时，
前端看到的是「检测框略有滞后但画面流畅」，而非「整体卡顿」。
"""
from __future__ import annotations

import base64
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import cv2
import httpx
import numpy as np

from app.core.config import settings

logger = logging.getLogger("stream_runtime")


_SEVERITY_BGR = {
    "high": (60, 60, 220),
    "medium": (40, 140, 240),
    "low": (60, 200, 240),
    "info": (180, 180, 180),
}


@dataclass
class RuntimeState:
    stream_id: str
    url: str
    input_type: str
    running: bool = False
    width: int = 0
    height: int = 0
    fps: float = 0.0
    frames_decoded: int = 0
    frames_inferred: int = 0
    frames_dropped: int = 0
    reconnect_count: int = 0
    last_error: Optional[str] = None
    last_infer_ms: float = 0.0
    last_detections: List[Dict] = field(default_factory=list)
    last_device: str = ""


class _StreamWorker(threading.Thread):
    """单路流解码+推理线程。推理异步非阻塞。"""

    def __init__(self, state: RuntimeState, http: httpx.Client, infer_pool: ThreadPoolExecutor):
        super().__init__(name=f"stream-{state.stream_id}", daemon=True)
        self._state = state
        self._http = http
        self._infer_pool = infer_pool
        self._stop_evt = threading.Event()
        self._frame_lock = threading.Lock()
        self._jpeg: Optional[bytes] = None
        # 推理结果（由后台线程写，解码线程读）
        self._dets_lock = threading.Lock()
        self._last_dets: List[Dict] = []
        self._infer_busy = threading.Event()  # set 表示有推理在途

    # ---- 对外 ----
    def stop(self) -> None:
        self._stop_evt.set()

    def snapshot(self) -> Optional[bytes]:
        with self._frame_lock:
            return self._jpeg

    # ---- 内部 ----
    def _open(self) -> cv2.VideoCapture:
        st = self._state
        if st.input_type == "webcam":
            try:
                idx = int(st.url)
            except ValueError:
                idx = 0
            return cv2.VideoCapture(idx)
        if st.input_type in ("rtsp", "rtmp"):
            if st.input_type == "rtsp":
                os.environ.setdefault(
                    "OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp"
                )
            return cv2.VideoCapture(st.url, cv2.CAP_FFMPEG)
        return cv2.VideoCapture(st.url)

    def _draw(self, frame: np.ndarray, dets: List[Dict]) -> np.ndarray:
        """本地兜底画框（ai-runtime 已返回 annotated 时不走这里）。"""
        for d in dets:
            x1, y1, x2, y2 = d.get("bbox", [0, 0, 0, 0])
            color = _SEVERITY_BGR.get(d.get("severity", "info"), _SEVERITY_BGR["info"])
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            label = f"{d.get('class_name','?')} {float(d.get('confidence',0)):.2f}"
            (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            ytxt = max(int(y1) - 6, th + 4)
            cv2.rectangle(frame, (int(x1), ytxt - th - 4), (int(x1) + tw + 4, ytxt + base - 2), color, -1)
            cv2.putText(frame, label, (int(x1) + 2, ytxt - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        return frame

    def _dispatch_infer(self, frame: np.ndarray, frame_id: str) -> None:
        """异步派发一次推理。若池里没空位或已有在途任务则直接丢弃。"""
        if self._infer_busy.is_set():
            return
        # 编码在后台线程里做，避免占用解码时间
        self._infer_busy.set()
        frame_copy = frame  # 由 OpenCV 给出的是新 ndarray，直接提交
        try:
            self._infer_pool.submit(self._infer_job, frame_copy, frame_id)
        except RuntimeError:
            # 池已关闭
            self._infer_busy.clear()

    def _infer_job(self, frame: np.ndarray, frame_id: str) -> None:
        """在池里跑：编码 → POST ai-runtime → 存 detections。"""
        try:
            ok, buf = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(settings.JPEG_QUALITY)]
            )
            if not ok:
                return
            payload = {
                "frame_id": frame_id,
                "stream_id": self._state.stream_id,
                "timestamp": time.time(),
                "image_data": base64.b64encode(buf.tobytes()).decode("ascii"),
                # 不再回传 annotated JPEG；本地画框，省下行流量与服务端绘制
                "return_annotated": False,
                "jpeg_quality": int(settings.JPEG_QUALITY),
            }
            r = self._http.post(
                f"{settings.AI_RUNTIME_URL}/inference",
                json=payload,
                timeout=settings.AI_RUNTIME_TIMEOUT,
            )
            if r.status_code != 200:
                logger.warning("ai-runtime %s: %s", r.status_code, r.text[:200])
                return
            resp = r.json()
            dets = resp.get("detections") or []
            with self._dets_lock:
                self._last_dets = dets
            self._state.last_infer_ms = float(resp.get("processing_time_ms") or 0)
            self._state.last_device = resp.get("device") or ""
            self._state.last_detections = dets
            self._state.frames_inferred += 1
        except Exception as e:
            logger.warning("ai-runtime 调用失败: %s", e)
            self._state.last_error = str(e)
        finally:
            self._infer_busy.clear()

    def run(self) -> None:  # noqa: C901 - 线性流程，分段读易于跟踪
        st = self._state
        cap = self._open()
        if not cap.isOpened():
            st.last_error = f"无法打开视频源: {st.url}"
            st.running = False
            logger.error(st.last_error)
            return

        # 探测
        st.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or st.width
        st.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or st.height
        probed = cap.get(cv2.CAP_PROP_FPS) or 25.0
        st.fps = float(probed if probed > 0 else 25.0)
        frame_delay = 1.0 / max(st.fps, 1.0)

        infer_every = max(1, int(settings.INFER_EVERY_N))
        idx = 0
        t_prev = time.time()

        try:
            while not self._stop_evt.is_set():
                ok, frame = cap.read()
                if not ok:
                    # 文件类型循环；实时流尝试重连
                    if st.input_type == "file":
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    if st.input_type in ("rtsp", "rtmp"):
                        cap.release()
                        st.reconnect_count += 1
                        time.sleep(1.0)
                        cap = self._open()
                        if cap.isOpened():
                            continue
                    break

                idx += 1
                st.frames_decoded += 1

                # 异步派发推理，不阻塞解码循环
                if idx % infer_every == 0:
                    self._dispatch_infer(frame, f"f_{idx}")

                # 始终用最近一次检测结果画框（可能略滞后，但画面不卡）
                with self._dets_lock:
                    dets_snapshot = list(self._last_dets)
                if dets_snapshot:
                    frame = self._draw(frame, dets_snapshot)

                ok_enc, jpeg = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(settings.JPEG_QUALITY)]
                )
                if ok_enc:
                    with self._frame_lock:
                        self._jpeg = jpeg.tobytes()
                else:
                    st.frames_dropped += 1

                # 文件源按视频 fps 节流，避免飞速跑完
                if st.input_type == "file":
                    elapsed = time.time() - t_prev
                    if elapsed < frame_delay:
                        time.sleep(frame_delay - elapsed)
                    t_prev = time.time()
        except Exception as e:
            st.last_error = str(e)
            logger.exception("流 %s 推流异常", st.stream_id)
        finally:
            cap.release()
            st.running = False
            logger.info("流 %s 已退出", st.stream_id)


class StreamRuntime:
    """流运行时单例。线程安全。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: Dict[str, _StreamWorker] = {}
        self._states: Dict[str, RuntimeState] = {}
        # httpx 默认每 host 最多 10 并发连接，放宽以支持多流同时调用
        self._http = httpx.Client(
            timeout=settings.AI_RUNTIME_TIMEOUT,
            limits=httpx.Limits(
                max_connections=int(settings.MAX_CONCURRENT_STREAMS) * 2,
                max_keepalive_connections=int(settings.MAX_CONCURRENT_STREAMS),
            ),
        )
        # 共享推理线程池：大小 = 最大并发流数，每路最多占 1 个线程
        self._infer_pool = ThreadPoolExecutor(
            max_workers=int(settings.MAX_CONCURRENT_STREAMS),
            thread_name_prefix="infer",
        )

    def start(self, stream_id: str, url: str, input_type: str) -> RuntimeState:
        with self._lock:
            w = self._workers.get(stream_id)
            if w and w.is_alive():
                return self._states[stream_id]
            # 清理旧线程
            if w:
                w.stop()
                self._workers.pop(stream_id, None)

            if len(self._workers) >= int(settings.MAX_CONCURRENT_STREAMS):
                raise RuntimeError(f"已达最大并发流数 {settings.MAX_CONCURRENT_STREAMS}")

            state = RuntimeState(stream_id=stream_id, url=url, input_type=input_type, running=True)
            self._states[stream_id] = state
            worker = _StreamWorker(state, self._http, self._infer_pool)
            self._workers[stream_id] = worker
            worker.start()
            logger.info("启动流 %s [%s] %s", stream_id, input_type, url)
            return state

    def stop(self, stream_id: str) -> bool:
        with self._lock:
            w = self._workers.get(stream_id)
            if not w:
                return False
            w.stop()
        w.join(timeout=3.0)
        with self._lock:
            self._workers.pop(stream_id, None)
            st = self._states.get(stream_id)
            if st:
                st.running = False
        return True

    def stop_all(self) -> None:
        with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()
        for w in workers:
            w.stop()
        for w in workers:
            w.join(timeout=2.0)
        try:
            self._infer_pool.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        try:
            self._http.close()
        except Exception:
            pass

    def get_snapshot(self, stream_id: str) -> Optional[bytes]:
        with self._lock:
            w = self._workers.get(stream_id)
        return w.snapshot() if w else None

    def get_runtime(self, stream_id: str) -> Optional[RuntimeState]:
        with self._lock:
            return self._states.get(stream_id)

    def is_running(self, stream_id: str) -> bool:
        with self._lock:
            w = self._workers.get(stream_id)
            return bool(w and w.is_alive())


# 模块级单例
_runtime: Optional[StreamRuntime] = None


def get_stream_runtime() -> StreamRuntime:
    global _runtime
    if _runtime is None:
        _runtime = StreamRuntime()
    return _runtime
