---
paths:
  - "services/stream-core/**/*"
---

# 流媒体核心规则

## 目标
实现最多 20 路并发视频流接入和处理加速层。

## 技术栈
- C++20
- FFmpeg
- fixed-size thread pool
- bounded queue
- ring buffer
- metrics collector

## 核心组件
- StreamManager
- StreamSession
- ThreadPool
- BoundedQueue
- RingBuffer
- MetricsCollector
- ClipExporter
- ReconnectController

## 必须满足
1. ingest 线程不允许被慢推理阻塞
2. 所有队列必须有容量上限
3. 队列满时必须执行明确的丢帧或采样策略
4. 每路流必须有独立状态机：
   - INIT
   - CONNECTING
   - RUNNING
   - DEGRADED
   - RECONNECTING
   - STOPPED
   - ERROR
5. 必须支持 start / stop / restart / reconnect
6. 必须暴露每路流的指标：
   - fps
   - queue depth
   - dropped frames
   - decode latency
   - reconnect count
   - uptime

## 测试要求
至少覆盖：
- thread pool
- bounded queue
- stream lifecycle
- reconnect logic
- clip export basic path
