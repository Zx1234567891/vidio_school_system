"""
Campus Guard Stream Core - Python 绑定

使用 ctypes 调用 C API
"""

import ctypes
import os
import platform
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Callable, List


# 加载共享库
def _load_library():
    system = platform.system()
    if system == "Windows":
        lib_name = "campus_guard_stream.dll"
    elif system == "Darwin":
        lib_name = "libcampus_guard_stream.dylib"
    else:
        lib_name = "libcampus_guard_stream.so"

    # 尝试从多个路径加载
    search_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "build"),
        os.path.join(os.path.dirname(__file__), "..", ".."),
        "/usr/local/lib",
        "/usr/lib",
    ]

    for path in search_paths:
        lib_path = os.path.join(path, lib_name)
        if os.path.exists(lib_path):
            return ctypes.CDLL(lib_path)

    raise RuntimeError(f"Could not find {lib_name}")


# 尝试加载库
_lib = None
try:
    _lib = _load_library()
except RuntimeError as e:
    print(f"Warning: {e}")


class StreamStatus(IntEnum):
    INIT = 0
    CONNECTING = 1
    RUNNING = 2
    DEGRADED = 3
    RECONNECTING = 4
    STOPPED = 5
    ERROR = 6


class InputType(IntEnum):
    RTSP = 0
    RTMP = 1
    FILE = 2


class ErrorCode(IntEnum):
    OK = 0
    INVALID_HANDLE = -1
    INVALID_PARAM = -2
    OUT_OF_MEMORY = -3
    STREAM_NOT_FOUND = -4
    STREAM_LIMIT_EXCEEDED = -5
    FFMPEG_ERROR = -6
    UNKNOWN = -99


@dataclass
class StreamConfig:
    name: str
    input_type: InputType
    url: str
    enabled: bool = True
    max_queue_size: int = 100
    ring_buffer_seconds: int = 30
    max_reconnect_attempts: int = 5
    reconnect_interval_ms: int = 3000


@dataclass
class StreamMetrics:
    fps: float
    queue_depth: int
    dropped_frames: int
    decode_latency_ms: float
    reconnect_count: int
    uptime_seconds: int
    total_frames_decoded: int
    total_bytes_received: int
    bitrate_kbps: float


class StreamManager:
    """流管理器 Python 封装"""

    def __init__(self, max_streams: int = 20, thread_pool_size: int = 8):
        if _lib is None:
            raise RuntimeError("Stream core library not loaded")

        self._lib = _lib
        self._handle = self._lib.cg_stream_manager_create(max_streams, thread_pool_size)
        if not self._handle:
            raise RuntimeError("Failed to create stream manager")

    def __del__(self):
        if hasattr(self, '_handle') and self._handle:
            self._lib.cg_stream_manager_destroy(self._handle)
            self._handle = None

    def create_stream(self, config: StreamConfig) -> str:
        """创建流，返回流ID"""
        class CGStreamConfig(ctypes.Structure):
            _fields_ = [
                ("name", ctypes.c_char_p),
                ("input_type", ctypes.c_int),
                ("url", ctypes.c_char_p),
                ("enabled", ctypes.c_int),
                ("max_queue_size", ctypes.c_uint32),
                ("ring_buffer_seconds", ctypes.c_uint32),
                ("max_reconnect_attempts", ctypes.c_uint32),
                ("reconnect_interval_ms", ctypes.c_uint32),
            ]

        cg_config = CGStreamConfig(
            name=config.name.encode('utf-8'),
            input_type=int(config.input_type),
            url=config.url.encode('utf-8'),
            enabled=1 if config.enabled else 0,
            max_queue_size=config.max_queue_size,
            ring_buffer_seconds=config.ring_buffer_seconds,
            max_reconnect_attempts=config.max_reconnect_attempts,
            reconnect_interval_ms=config.reconnect_interval_ms,
        )

        stream_id_buf = ctypes.create_string_buffer(32)
        result = self._lib.cg_stream_create(self._handle, ctypes.byref(cg_config), stream_id_buf)

        if result != ErrorCode.OK:
            raise RuntimeError(f"Failed to create stream: {result}")

        return stream_id_buf.value.decode('utf-8')

    def destroy_stream(self, stream_id: str) -> None:
        """删除流"""
        result = self._lib.cg_stream_destroy(self._handle, stream_id.encode('utf-8'))
        if result != ErrorCode.OK:
            raise RuntimeError(f"Failed to destroy stream: {result}")

    def start_stream(self, stream_id: str) -> None:
        """启动流"""
        result = self._lib.cg_stream_start(self._handle, stream_id.encode('utf-8'))
        if result != ErrorCode.OK:
            raise RuntimeError(f"Failed to start stream: {result}")

    def stop_stream(self, stream_id: str) -> None:
        """停止流"""
        result = self._lib.cg_stream_stop(self._handle, stream_id.encode('utf-8'))
        if result != ErrorCode.OK:
            raise RuntimeError(f"Failed to stop stream: {result}")

    def restart_stream(self, stream_id: str) -> None:
        """重启流"""
        result = self._lib.cg_stream_restart(self._handle, stream_id.encode('utf-8'))
        if result != ErrorCode.OK:
            raise RuntimeError(f"Failed to restart stream: {result}")

    def get_status(self, stream_id: str) -> StreamStatus:
        """获取流状态"""
        status = self._lib.cg_stream_get_status(self._handle, stream_id.encode('utf-8'))
        return StreamStatus(status)

    def get_metrics(self, stream_id: str) -> StreamMetrics:
        """获取流指标"""
        class CGStreamMetrics(ctypes.Structure):
            _fields_ = [
                ("fps", ctypes.c_double),
                ("queue_depth", ctypes.c_size_t),
                ("dropped_frames", ctypes.c_uint64),
                ("decode_latency_ms", ctypes.c_double),
                ("reconnect_count", ctypes.c_uint32),
                ("uptime_seconds", ctypes.c_uint64),
                ("total_frames_decoded", ctypes.c_uint64),
                ("total_bytes_received", ctypes.c_uint64),
                ("bitrate_kbps", ctypes.c_double),
            ]

        metrics = CGStreamMetrics()
        result = self._lib.cg_stream_get_metrics(self._handle, stream_id.encode('utf-8'), ctypes.byref(metrics))

        if result != ErrorCode.OK:
            raise RuntimeError(f"Failed to get metrics: {result}")

        return StreamMetrics(
            fps=metrics.fps,
            queue_depth=metrics.queue_depth,
            dropped_frames=metrics.dropped_frames,
            decode_latency_ms=metrics.decode_latency_ms,
            reconnect_count=metrics.reconnect_count,
            uptime_seconds=metrics.uptime_seconds,
            total_frames_decoded=metrics.total_frames_decoded,
            total_bytes_received=metrics.total_bytes_received,
            bitrate_kbps=metrics.bitrate_kbps,
        )

    def list_streams(self) -> List[str]:
        """列出所有流ID"""
        buffer_size = 4096
        buffer = ctypes.create_string_buffer(buffer_size)
        count = ctypes.c_uint32()

        result = self._lib.cg_stream_list(self._handle, buffer, buffer_size, ctypes.byref(count))
        if result != ErrorCode.OK:
            raise RuntimeError(f"Failed to list streams: {result}")

        # 解析以 '\0' 分隔的字符串
        ids = []
        i = 0
        while i < buffer_size:
            end = i
            while end < buffer_size and buffer.raw[end] != 0:
                end += 1
            if end == i:
                break
            ids.append(buffer.raw[i:end].decode('utf-8'))
            i = end + 1
            if i < buffer_size and buffer.raw[i] == 0:
                break

        return ids

    def export_clip(self, stream_id: str, event_id: str,
                    seconds_before: int = 5, seconds_after: int = 5) -> str:
        """导出切片"""
        buffer_size = 512
        buffer = ctypes.create_string_buffer(buffer_size)

        result = self._lib.cg_export_clip(
            self._handle,
            stream_id.encode('utf-8'),
            event_id.encode('utf-8'),
            seconds_before,
            seconds_after,
            buffer,
            buffer_size
        )

        if result != ErrorCode.OK:
            raise RuntimeError(f"Failed to export clip: {result}")

        return buffer.value.decode('utf-8')


# 使用示例
if __name__ == "__main__":
    print("Campus Guard Stream Core - Python Binding Example")
    print("=" * 50)

    try:
        # 创建管理器
        manager = StreamManager(max_streams=20, thread_pool_size=8)
        print("✓ Stream manager created")

        # 创建流
        config = StreamConfig(
            name="Test Stream",
            input_type=InputType.FILE,
            url="test_video.mp4",
            max_queue_size=50,
            ring_buffer_seconds=10,
        )

        stream_id = manager.create_stream(config)
        print(f"✓ Stream created: {stream_id}")

        # 查询状态
        status = manager.get_status(stream_id)
        print(f"✓ Stream status: {status.name}")

        # 列出流
        streams = manager.list_streams()
        print(f"✓ Active streams: {streams}")

        # 删除流
        manager.destroy_stream(stream_id)
        print(f"✓ Stream destroyed")

        print("\n✅ All operations successful!")

    except RuntimeError as e:
        print(f"\n❌ Error: {e}")
        print("Note: Make sure the shared library is built and accessible")
