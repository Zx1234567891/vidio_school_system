# Campus Guard AI 架构设计

## 系统概述

Campus Guard AI 是一个面向校园安防的视频行为感知与异常事件智能预警系统。

## 架构原则

1. **模块化设计**: 各模块职责清晰，通过明确接口通信
2. **异步优先**: 慢任务必须异步化，不阻塞主流程
3. **有界队列**: 所有队列必须有容量上限
4. **可观测性**: 全链路指标采集和日志记录

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层 (Next.js)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Overview │ │ Streams  │ │  Alerts  │ │ History  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ WebSocket / HTTP
┌─────────────────────────────────────────────────────────────────┐
│                      控制面 (FastAPI)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Streams  │ │  Events  │ │  Review  │ │ Training │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌──────────────────┐   ┌──────────────┐
│  Stream Core  │   │   AI Runtime     │   │  Data Layer  │
│  (C++20)      │   │   (Python)       │   │  PG + Redis  │
│  ┌──────────┐ │   │  ┌──────────┐    │   │              │
│  │ FFmpeg   │ │   │  │ Detection│    │   │              │
│  │ ThreadPool│ │   │  │ Tracking │    │   │              │
│  │ BoundedQ │ │   │  │ Behavior │    │   │              │
│  └──────────┘ │   │  └──────────┘    │   │              │
└───────────────┘   └──────────────────┘   └──────────────┘
```

## 模块职责

### apps/web - 前端
- 企业级安防控制台界面
- 多路视频矩阵展示
- 实时告警推送（WebSocket）
- 历史查询与导出

### apps/api - 控制面
- REST API 网关
- WebSocket 广播
- 业务逻辑编排
- 权限控制

### services/stream-core - 流媒体核心 (P1 已完成)

#### 核心组件

| 组件 | 职责 | 关键特性 |
|------|------|----------|
| `StreamManager` | 管理最多 20 路流 | 线程安全、全局指标聚合 |
| `StreamSession` | 单路流生命周期 | 状态机、双线程模型 |
| `FFmpegDecoder` | 视频解码 | 支持 RTSP/RTMP/文件 |
| `ThreadPool` | 固定线程池 | 8 线程、任务队列 |
| `BoundedQueue` | 有界队列 | 背压策略、满时丢帧 |
| `RingBuffer` | 环形缓冲区 | 30秒滑动窗口 |
| `ReconnectController` | 重连控制 | 指数退避、最大5次 |
| `ClipExporter` | 切片导出 | 异常事件视频导出 |
| `MetricsCollector` | 指标收集 | FPS/延迟/丢帧/码率 |

#### 线程模型

```
┌─────────────────────────────────────────┐
│           StreamSession                 │
│  ┌─────────────┐    ┌─────────────┐    │
│  │ Ingest Thread│    │ Process Thread│   │
│  │             │    │             │    │
│  │ FFmpegDecoder│ → │ BoundedQueue │   │
│  │  (解码)      │    │  (有界队列)   │   │
│  └─────────────┘    └──────┬──────┘    │
│                            │           │
│                            ▼           │
│                     ┌─────────────┐    │
│                     │ RingBuffer  │    │
│                     │ (环形缓冲)   │    │
│                     └─────────────┘    │
└─────────────────────────────────────────┘
```

#### 状态机

```
INIT → CONNECTING → RUNNING ←──────────┐
              ↓         │               │
              ↓    DEGRADED             │
              ↓         │               │
              └──→ ERROR ─→ RECONNECTING ┘
                          ↓
                    STOPPED
```

#### C API 接口

提供 C 语言接口供 Python 调用：

```c
// 创建管理器
CGStreamManagerHandle cg_stream_manager_create(max_streams, thread_pool_size);

// 流管理
cg_stream_create(handle, config, stream_id);
cg_stream_start(handle, stream_id);
cg_stream_stop(handle, stream_id);
cg_stream_restart(handle, stream_id);

// 回调设置
cg_set_frame_callback(handle, callback, user_data);
cg_set_status_callback(handle, callback, user_data);
cg_set_error_callback(handle, callback, user_data);

// 指标查询
cg_stream_get_metrics(handle, stream_id, &metrics);

// 切片导出
cg_export_clip(handle, stream_id, event_id, before_sec, after_sec, path, size);
```

#### 关键指标

| 指标 | 说明 | 采集方式 |
|------|------|----------|
| fps | 实际帧率 | 解码器统计 |
| queue_depth | 队列深度 | 实时查询 |
| dropped_frames | 丢帧数 | 背压触发时累加 |
| decode_latency_ms | 解码延迟 | 处理时间测量 |
| reconnect_count | 重连次数 | 重连控制器 |
| uptime | 运行时间 | 启动时间戳计算 |
| bitrate_kbps | 码率 | 字节数/时间 |

### services/ai-runtime - AI 运行时
- 人员检测
- 多目标跟踪
- 行为识别
- 规则融合
- 模型训练/导出

### packages/shared-types - 共享契约
- TypeScript 类型定义
- Python Pydantic 模型
- 统一事件 Schema

## 数据流

```
视频源 → Stream Core → AI Runtime → API → 前端
            ↓              ↓          ↓
        环形缓存      事件生成    持久化存储
            ↓              ↓          ↓
        切片导出      实时告警    历史查询
```

## 关键技术决策

### 1. 线程模型
- **Ingest 线程**: 独立解码，不阻塞
- **Process 线程**: 处理帧数据，入环形缓冲区
- **线程池**: 固定大小，处理 AI 推理
- **队列策略**: 满时丢旧帧（背压）

### 2. 背压策略

当 `BoundedQueue` 满时：
1. 丢弃新帧（默认策略）
2. 增加 `dropped_frames` 计数
3. 记录日志
4. 可选降级到更低帧率

### 3. 重连策略

网络断开时：
1. 进入 `RECONNECTING` 状态
2. 指数退避：1s → 2s → 4s → 8s（最大30s）
3. 最多重试 5 次
4. 用尽后进入 `ERROR` 状态

### 4. 通信协议
- **API**: REST + JSON
- **实时**: WebSocket
- **内部**: C API (ctypes)

### 5. 存储策略
- **PostgreSQL**: 事件、配置、审计日志
- **Redis**: 实时状态、缓存、Pub/Sub
- **本地磁盘**: 视频切片

## 接口契约

详见 [api-contract.md](./api-contract.md)

## 部署架构

```
Docker Compose
├── postgres    # 主数据库
├── redis       # 缓存和消息
├── api         # FastAPI 服务
├── web         # Next.js 前端
└── stream-core # C++ 流媒体（可选独立部署）
```

## 构建说明

### Stream Core 构建

```bash
cd services/stream-core
mkdir -p build && cd build
cmake ..
make -j$(nproc)

# 运行测试
ctest --output-on-failure

# 运行示例
./stream_core_app
```

### 依赖

- CMake >= 3.20
- C++20 编译器 (GCC 11+, Clang 14+, MSVC 2022+)
- FFmpeg 开发库 (libavcodec, libavformat, libavutil, libswscale)
- pkg-config

### Ubuntu/Debian 依赖安装

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

## 扩展性考虑

1. **水平扩展**: API 无状态，可多实例
2. **垂直扩展**: Stream Core 可利用多核
3. **AI 加速**: 支持 GPU 推理
4. **存储扩展**: 支持对象存储（S3/MinIO）

## 阶段完成情况

### P0 ✅ 已完成
- 仓库骨架与最小闭环
- 基础目录结构
- 可编译的 C++ 骨架

### P1 ✅ 已完成
- FFmpeg 解码器集成
- 固定线程池 + 有界队列
- 背压策略（丢帧）
- 重连控制器（指数退避）
- 环形缓冲区
- 指标收集器
- C API 接口
- 切片导出器（基础）

### P2 ⏳ 待开始
- AI Runtime 实现
- 检测/跟踪/行为识别 Pipeline
- ONNX 模型集成

### P3-P6 ⏳ 待开始
- FastAPI 控制面完善
- Next.js 前端实现
- 压测与优化
- 比赛交付包装
