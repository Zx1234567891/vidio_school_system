---
name: cpp-stream-runtime
description: 实现高性能 C++20 视频流接入层，支持最多 20 路并发、固定线程池、FFmpeg 解码、背压、重连、切片导出与指标采集
disable-model-invocation: true
---

实现 services/stream-core。

目标：
- 支持 RTSP / RTMP / 本地视频文件输入
- 支持最多 20 路并发流管理
- 使用 C++20
- 使用 FFmpeg 作为主视频 I/O 与解码能力
- 实现固定大小线程池 + 有界任务队列 + 背压策略
- 实现 per-stream 状态机：INIT / CONNECTING / RUNNING / DEGRADED / RECONNECTING / STOPPED / ERROR
- 实现帧时间戳、采样、环形缓冲区、异常切片导出
- 实现指标：fps、decode latency、queue depth、dropped frames、reconnect count、uptime

必须满足：
1. ingest 线程不得因慢推理阻塞
2. 所有队列都必须有最大长度
3. 队列满时明确执行丢帧/跳帧策略
4. 提供 stream manager、thread pool、ring buffer、metrics collector、clip exporter
5. 给出基础单元测试，至少覆盖：
   - thread pool
   - bounded queue
   - stream lifecycle
   - reconnect logic
6. 输出清晰的 C API 或 Python binding 接口，供 api/ai-runtime 调用
