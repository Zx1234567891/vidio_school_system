# Campus Guard Stream Core

高性能 C++20 视频流接入层，支持最多 20 路并发视频流处理。

## 特性

- ✅ **多协议支持**: RTSP, RTMP, 本地视频文件
- ✅ **并发能力**: 最多 20 路视频流同时处理
- ✅ **固定线程池**: 8 线程，避免线程爆炸
- ✅ **有界队列**: 背压策略，队列满时丢帧
- ✅ **自动重连**: 指数退避策略，最多 5 次重试
- ✅ **环形缓冲**: 30 秒滑动窗口，支持异常切片导出
- ✅ **完整指标**: FPS、延迟、丢帧、码率、重连次数
- ✅ **C API**: 提供 Python 绑定接口

## 架构

```
┌─────────────────────────────────────────┐
│           StreamManager                 │
│  (管理最多 20 路流，线程安全)              │
└─────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Stream 1 │   │Stream 2 │   │Stream N │
└────┬────┘   └────┬────┘   └────┬────┘
     │             │             │
┌────┴─────────────┴─────────────┴────┐
│         StreamSession                 │
│  ┌─────────┐      ┌─────────────┐    │
│  │ Ingest  │      │   Process   │    │
│  │ Thread  │─────▶│   Thread    │    │
│  └────┬────┘      └──────┬──────┘    │
│       │                  │           │
│  ┌────┴────┐        ┌────┴────┐      │
│  │ FFmpeg  │        │ Bounded │      │
│  │ Decoder │        │  Queue  │      │
│  └─────────┘        └────┬────┘      │
│                          │           │
│                     ┌────┴────┐      │
│                     │  Ring   │      │
│                     │ Buffer  │      │
│                     └─────────┘      │
└──────────────────────────────────────┘
```

## 构建

### 依赖

- CMake >= 3.20
- C++20 编译器 (GCC 11+, Clang 14+, MSVC 2022+)
- FFmpeg 开发库
- pkg-config

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev
```

### macOS

```bash
brew install cmake pkg-config ffmpeg
```

### 编译

```bash
cd services/stream-core
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

### 运行测试

```bash
ctest --output-on-failure
# 或
./stream_core_tests
```

### 运行示例

```bash
./stream_core_app
```

## C API 使用

```c
#include "stream_core/c_api.h"

// 创建管理器
CGStreamManagerHandle mgr = cg_stream_manager_create(20, 8);

// 配置流
CGStreamConfig config = {
    .name = "Camera 1",
    .input_type = CG_INPUT_RTSP,
    .url = "rtsp://192.168.1.100/stream1",
    .enabled = 1,
    .max_queue_size = 100,
    .ring_buffer_seconds = 30,
    .max_reconnect_attempts = 5,
    .reconnect_interval_ms = 3000
};

// 创建并启动流
char stream_id[32];
cg_stream_create(mgr, &config, stream_id);
cg_stream_start(mgr, stream_id);

// 查询指标
CGStreamMetrics metrics;
cg_stream_get_metrics(mgr, stream_id, &metrics);
printf("FPS: %.2f, Queue: %zu\n", metrics.fps, metrics.queue_depth);

// 停止并清理
cg_stream_stop(mgr, stream_id);
cg_stream_destroy(mgr, stream_id);
cg_stream_manager_destroy(mgr);
```

## Python 绑定

```python
from stream_core import StreamManager, StreamConfig, InputType

# 创建管理器
manager = StreamManager(max_streams=20, thread_pool_size=8)

# 创建流
config = StreamConfig(
    name="Camera 1",
    input_type=InputType.RTSP,
    url="rtsp://192.168.1.100/stream1"
)
stream_id = manager.create_stream(config)

# 启动
manager.start_stream(stream_id)

# 查询指标
metrics = manager.get_metrics(stream_id)
print(f"FPS: {metrics.fps}, Queue: {metrics.queue_depth}")

# 停止
manager.stop_stream(stream_id)
```

## 流状态机

```
INIT → CONNECTING → RUNNING ←──────────┐
              ↓         │               │
              ↓    DEGRADED             │
              ↓         │               │
              └──→ ERROR ─→ RECONNECTING ┘
                          ↓
                    STOPPED
```

## 背压策略

当处理队列满时：

1. **DROP_OLDEST** (默认): 丢弃最旧的帧
2. **DROP_LATEST**: 丢弃最新的帧
3. **SKIP_FRAME**: 跳帧处理

## 指标说明

| 指标 | 说明 |
|------|------|
| fps | 实际解码帧率 |
| queue_depth | 处理队列当前深度 |
| dropped_frames | 因背压丢弃的帧数 |
| decode_latency_ms | 帧处理延迟（毫秒）|
| reconnect_count | 重连次数 |
| uptime_seconds | 运行时间（秒）|
| total_frames_decoded | 总解码帧数 |
| bitrate_kbps | 码率（kbps）|

## 性能目标

- 单路 1080P 延迟: < 300ms
- 支持 20 路 1080P 并发
- 长时间稳定运行（> 1 小时）

## 许可证

本项目为比赛参赛作品。
