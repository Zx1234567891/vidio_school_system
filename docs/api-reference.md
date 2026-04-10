# Campus Guard AI - API 接口参考文档

## 1. 基础信息

| 项目 | 值 |
|------|------|
| Base URL | `http://localhost:8000` |
| API 前缀 | `/api/v1` |
| WebSocket | `ws://localhost:8000/ws` |
| Content-Type | `application/json` |
| OpenAPI 文档 | `http://localhost:8000/docs` |

## 2. 统一响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误响应

```json
{
  "detail": "错误描述信息"
}
```

### HTTP 状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 202 | 异步任务已接受 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 分页响应格式

所有列表接口返回统一分页结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

## 3. 健康检查

### GET /health

检查服务健康状态。

**响应示例**：
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-04-10T00:00:00Z",
  "services": {
    "api": "up",
    "database": "up",
    "redis": "up",
    "stream_core": "up",
    "ai_runtime": "up"
  }
}
```

---

## 4. 视频流管理 `/api/v1/streams`

### GET /api/v1/streams

获取视频流列表。

**查询参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `status` | string | 否 | - | 按状态筛选：init/connecting/running/degraded/reconnecting/stopped/error |
| `input_type` | string | 否 | - | 按输入类型筛选：rtsp/rtmp/file |
| `page` | int | 否 | 1 | 页码，最小 1 |
| `page_size` | int | 否 | 20 | 每页数量，1-100 |

**响应**（200）：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "stream_abc123def456",
        "name": "教学楼A-1F-大厅",
        "url": "rtsp://192.168.1.100/stream1",
        "input_type": "rtsp",
        "status": "running",
        "status_message": null,
        "target_fps": 25,
        "max_queue_size": 100,
        "ring_buffer_seconds": 30,
        "width": 1920,
        "height": 1080,
        "fps": 25.0,
        "bitrate": 4000,
        "codec": "h264",
        "location": "教学楼A一楼大厅",
        "latitude": 30.5728,
        "longitude": 104.0668,
        "total_frames_decoded": 150000,
        "total_dropped_frames": 12,
        "reconnect_count": 0,
        "created_at": "2026-04-01T08:00:00",
        "updated_at": "2026-04-10T10:30:00",
        "started_at": "2026-04-10T08:00:00",
        "stopped_at": null
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

### POST /api/v1/streams

创建新视频流。

**请求体**：
```json
{
  "id": "stream_custom_id",          // 可选，不传则自动生成
  "name": "教学楼A-1F-大厅",          // 必填，1-255字符
  "url": "rtsp://192.168.1.100/stream1",  // 必填
  "input_type": "rtsp",              // 可选，默认 rtsp
  "target_fps": 25,                  // 可选，1-60，默认 25
  "max_queue_size": 100,             // 可选，10-1000，默认 100
  "ring_buffer_seconds": 30,         // 可选，5-300，默认 30
  "max_reconnect_attempts": 5,       // 可选，0-20，默认 5
  "reconnect_interval_ms": 1000,     // 可选，100-60000，默认 1000
  "location": "教学楼A一楼",          // 可选
  "latitude": 30.5728,               // 可选，-90~90
  "longitude": 104.0668,             // 可选，-180~180
  "region_config": {                  // 可选，ROI/禁区等配置
    "roi": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
  }
}
```

**响应**（201）：返回创建的流对象。

---

### GET /api/v1/streams/{stream_id}

获取单个流详情。

**路径参数**：`stream_id` - 流 ID

**响应**（200）：返回流对象。

**错误**（404）：`Stream {stream_id} not found`

---

### PUT /api/v1/streams/{stream_id}

更新流配置。

**请求体**（所有字段可选）：
```json
{
  "name": "新名称",
  "url": "rtsp://新地址",
  "target_fps": 30,
  "max_queue_size": 200,
  "location": "新位置"
}
```

**响应**（200）：返回更新后的流对象。

---

### DELETE /api/v1/streams/{stream_id}

删除流（软删除）。

**响应**（200）：
```json
{ "code": 0, "message": "Stream deleted successfully", "data": { "id": "stream_xxx" } }
```

---

### POST /api/v1/streams/{stream_id}/start

启动流。将状态设为 `running`。

**响应**（200）：返回更新后的流对象。

---

### POST /api/v1/streams/{stream_id}/stop

停止流。将状态设为 `stopped`。

**响应**（200）：返回更新后的流对象。

---

### POST /api/v1/streams/{stream_id}/restart

重启流。重置重连计数，将状态设为 `running`。

**响应**（200）：返回更新后的流对象。

---

## 5. 事件管理 `/api/v1/events`

### GET /api/v1/events

获取事件列表。

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `stream_id` | string | 否 | 按流ID筛选 |
| `event_type` | string | 否 | 按事件类型筛选 |
| `category` | string | 否 | 按类别筛选：high_risk/sensitive/suspicious/normal |
| `severity` | string | 否 | 按严重级别筛选：critical/high/medium/low |
| `status` | string | 否 | 按状态筛选：pending/confirmed/false_positive/resolved/ignored |
| `start_time` | datetime | 否 | 开始时间（ISO 8601） |
| `end_time` | datetime | 否 | 结束时间（ISO 8601） |
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页数量 |

**响应**（200）：
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "evt_abc123def456",
        "stream_id": "stream_0001",
        "event_type": "fighting",
        "category": "high_risk",
        "severity": "critical",
        "status": "pending",
        "start_time": "2026-04-10T12:00:00",
        "end_time": "2026-04-10T12:00:05",
        "duration_ms": 5000,
        "confidence": 0.95,
        "participants": [
          { "track_id": "track_001", "bbox": [0.1, 0.2, 0.05, 0.1], "confidence": 0.92 },
          { "track_id": "track_002", "bbox": [0.2, 0.2, 0.05, 0.1], "confidence": 0.88 }
        ],
        "roles": {
          "aggressor": ["track_001"],
          "victim": ["track_002"]
        },
        "location": "教学楼A一楼大厅",
        "snapshot_url": "/snapshots/evt_abc123.jpg",
        "clip_id": "clip_xyz789",
        "ai_details": {
          "model_version": "yolov8n",
          "inference_time_ms": 15.2
        },
        "reviewed_by": null,
        "reviewed_at": null,
        "created_at": "2026-04-10T12:00:00"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

### POST /api/v1/events

创建新事件（通常由 AI Runtime 调用）。

**请求体**：
```json
{
  "stream_id": "stream_0001",                    // 必填
  "event_type": "fighting",                      // 必填
  "category": "high_risk",                       // 必填
  "severity": "critical",                        // 必填
  "start_time": "2026-04-10T12:00:00Z",          // 必填
  "end_time": "2026-04-10T12:00:05Z",            // 可选
  "confidence": 0.95,                            // 必填，0-1
  "participants": [                              // 可选
    { "track_id": "track_001", "bbox": [0.1, 0.2, 0.05, 0.1], "confidence": 0.92 }
  ],
  "roles": { "aggressor": ["track_001"], "victim": ["track_002"] },  // 可选
  "location": "教学楼A",                          // 可选
  "bounding_boxes": [{ "x": 100, "y": 200, "w": 50, "h": 100 }],   // 可选
  "snapshot_url": "/snapshots/frame.jpg",         // 可选
  "ai_details": { "model": "yolov8n" }           // 可选
}
```

**响应**（201）：返回创建的事件对象。

---

### GET /api/v1/events/{event_id}

获取单个事件详情。

---

### PUT /api/v1/events/{event_id}

更新事件信息。

**请求体**（所有字段可选）：
```json
{
  "status": "confirmed",
  "end_time": "2026-04-10T12:00:10Z",
  "confidence": 0.98,
  "reviewed_by": "admin",
  "review_comment": "确认是打架事件",
  "handled_by": "security_001",
  "handle_result": "已通知保安处理"
}
```

---

### DELETE /api/v1/events/{event_id}

删除事件（软删除）。

---

### GET /api/v1/events/stats/overview

获取事件统计概览。

**查询参数**：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `days` | int | 7 | 统计天数，1-90 |

**响应**（200）：
```json
{
  "code": 0,
  "data": {
    "total": 150,
    "by_type": { "fighting": 20, "falling": 15, "smoking": 30 },
    "by_severity": { "critical": 10, "high": 35, "medium": 60, "low": 45 },
    "by_status": { "pending": 50, "confirmed": 80, "false_positive": 20 },
    "by_day": { "2026-04-10": 25, "2026-04-09": 30 }
  }
}
```

---

## 6. 审核管理 `/api/v1/reviews`

### GET /api/v1/reviews

获取审核记录列表。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `event_id` | string | 按事件ID筛选 |
| `reviewer_id` | string | 按审核人筛选 |
| `action` | string | 按动作筛选：confirm/reject/modify/resolve/ignore |
| `page/page_size` | int | 分页 |

---

### POST /api/v1/reviews

创建审核记录。同时更新关联事件的状态。

**请求体**：
```json
{
  "event_id": "evt_abc123",            // 必填
  "reviewer_id": "user_001",           // 必填
  "reviewer_name": "张三",              // 可选
  "action": "confirm",                 // 必填：confirm/reject/modify/resolve/ignore
  "original_data": null,               // 可选（修改时填写原始数据）
  "modified_data": null,               // 可选（修改时填写修改后数据）
  "comment": "确认是打架事件"            // 可选
}
```

**审核动作 → 事件状态映射**：

| 动作 | 事件状态更新为 |
|------|--------------|
| `confirm` | `confirmed` |
| `reject` | `false_positive` |
| `resolve` | `resolved` |
| `ignore` | `ignored` |
| `modify` | 不变 |

---

### GET /api/v1/reviews/{review_id}

获取单个审核记录。

### GET /api/v1/reviews/event/{event_id}

获取某事件的审核记录。

---

## 7. 视频切片管理 `/api/v1/clips`

### GET /api/v1/clips

获取切片列表。

**查询参数**：`event_id`、`stream_id`、`status`、`page`、`page_size`

---

### POST /api/v1/clips/export

导出事件切片（异步任务）。

**请求体**：
```json
{
  "event_id": "evt_abc123",       // 必填
  "seconds_before": 5,            // 可选，默认 5
  "seconds_after": 5,             // 可选，默认 5
  "format": "mp4"                 // 可选，默认 mp4
}
```

**响应**（202 Accepted）：
```json
{
  "code": 0,
  "data": {
    "clip_id": "clip_xyz789",
    "status": "pending",
    "message": "Export task is queued and will be processed asynchronously"
  }
}
```

---

### GET /api/v1/clips/{clip_id}

获取切片详情。

### GET /api/v1/clips/{clip_id}/download

下载切片文件。

- 仅 `status == completed` 时可下载
- 返回 `FileResponse`，Content-Type: video/mp4
- 自动累加下载次数

### DELETE /api/v1/clips/{clip_id}

删除切片（同时删除文件）。

---

## 8. 训练任务管理 `/api/v1/training`

### GET /api/v1/training

获取训练任务列表。

**查询参数**：`status`、`training_type`、`page`、`page_size`

---

### POST /api/v1/training

创建训练任务。

**请求体**：
```json
{
  "name": "行为识别模型 v2",
  "description": "基于 YOLOv8 的行为识别模型微调",
  "training_type": "behavior",          // detection/classification/behavior/end_to_end
  "dataset_config": {
    "source": "local",
    "data_path": "/data/behavior_dataset",
    "train_split": 0.8,
    "val_split": 0.2
  },
  "model_config": {
    "base_model": "yolov8n",
    "epochs": 100,
    "batch_size": 16,
    "learning_rate": 0.001,
    "image_size": 640
  },
  "hyperparameters": {
    "optimizer": "Adam",
    "scheduler": "cosine",
    "augmentation": true,
    "early_stopping": true
  },
  "created_by": "admin"
}
```

---

### GET /api/v1/training/{job_id}

获取训练任务详情。

### PUT /api/v1/training/{job_id}

更新训练任务配置。

### POST /api/v1/training/{job_id}/start

启动训练任务。仅 `pending` 或 `failed` 状态可启动。

### POST /api/v1/training/{job_id}/cancel

取消训练任务。

**查询参数**：`reason`（取消原因）、`cancelled_by`（取消人）

### DELETE /api/v1/training/{job_id}

删除训练任务（硬删除）。

---

## 9. 指标与监控 `/api/v1/metrics`

### GET /api/v1/metrics/system

获取系统级指标。

**响应**（200）：
```json
{
  "code": 0,
  "data": {
    "total_streams": 10,
    "active_streams": 5,
    "error_streams": 0,
    "thread_pool_size": 20,
    "pending_tasks": 0,
    "total_frames_decoded": 0,
    "total_dropped_frames": 0,
    "avg_system_fps": 0.0,
    "memory_usage_mb": 2048.5,
    "cpu_usage_percent": 15.5,
    "gpu_usage_percent": null,
    "disk_usage_percent": 35.0
  }
}
```

---

### GET /api/v1/metrics/streams

获取所有运行中流的指标。

**响应**（200）：
```json
{
  "code": 0,
  "data": [
    {
      "stream_id": "stream_0001",
      "status": "running",
      "fps": 25.0,
      "queue_depth": 5,
      "dropped_frames": 12,
      "decode_latency_ms": 15.5,
      "reconnect_count": 0,
      "uptime_seconds": 3600,
      "total_frames_decoded": 90000,
      "total_bytes_received": 450000000,
      "bitrate_kbps": 4000.0
    }
  ]
}
```

---

### GET /api/v1/metrics/streams/{stream_id}

获取单个流的指标。

---

### GET /api/v1/metrics/dashboard

获取仪表盘数据。

**查询参数**：`days`（统计天数，1-30，默认 7）

**响应**（200）：
```json
{
  "code": 0,
  "data": {
    "event_trend": {
      "2026-04-10": { "total": 25, "critical": 3, "high": 8 },
      "2026-04-09": { "total": 30, "critical": 5, "high": 10 }
    },
    "event_types": {
      "fighting": 20,
      "falling": 15,
      "smoking": 30
    },
    "stream_status": {
      "running": 5,
      "stopped": 3,
      "error": 0
    },
    "summary": {
      "total_streams": 8,
      "active_streams": 5,
      "total_events_7d": 150,
      "pending_reviews": 50
    }
  }
}
```

---

## 10. 系统管理 `/api/v1/system`

### GET /api/v1/system/metrics

获取系统资源指标（简化版）。

**响应**：
```json
{
  "cpu_percent": 15.5,
  "memory_percent": 42.0,
  "disk_usage_percent": 35.0,
  "active_streams": 0,
  "total_events_today": 0,
  "alerts_pending": 0,
  "timestamp": "2026-04-10T00:00:00Z"
}
```

### GET /api/v1/system/config

获取系统配置。

**响应**：
```json
{
  "max_streams": 20,
  "default_fps": 25,
  "alert_retention_days": 90,
  "clip_retention_days": 30
}
```

### POST /api/v1/system/config

更新系统配置。请求体与响应格式相同。

---

## 11. WebSocket 协议 `ws://localhost:8000/ws`

### 连接

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### 客户端 → 服务器消息

**心跳**：
```json
{ "type": "ping", "timestamp": 1712736000000 }
```

**订阅频道**：
```json
{ "type": "subscribe", "channels": ["alerts", "stream_status"] }
```

### 服务器 → 客户端消息

**心跳响应**：
```json
{ "type": "pong", "timestamp": 1712736000000 }
```

**订阅确认**：
```json
{ "type": "subscribed", "channels": ["alerts", "stream_status"] }
```

**实时告警**：
```json
{
  "type": "alert",
  "payload": {
    "event_id": "evt_abc123",
    "stream_id": "stream_0001",
    "event_type": "fighting",
    "severity": "critical",
    "confidence": 0.95,
    "message": "检测到打架事件",
    "participants": [...]
  },
  "timestamp": "2026-04-10T12:00:00Z"
}
```

**流状态变更**：
```json
{
  "type": "stream_status",
  "payload": {
    "stream_id": "stream_0001",
    "status": "running",
    "fps": 25.0
  }
}
```

### 消息类型汇总

| 类型 | 方向 | 说明 |
|------|------|------|
| `ping` | C→S | 心跳请求 |
| `pong` | S→C | 心跳响应 |
| `subscribe` | C→S | 订阅频道 |
| `subscribed` | S→C | 订阅确认 |
| `alert` | S→C | 实时告警推送 |
| `stream_status` | S→C | 流状态变更 |
| `heartbeat` | S→C | 服务器心跳 |
| `error` | S→C | 错误通知 |
| `echo` | S→C | 回显未知消息 |

---

## 12. Stream Core C API 接口

Stream Core 提供 C 语言接口供 Python 通过 ctypes 调用：

```c
// 创建管理器
CGStreamManagerHandle cg_stream_manager_create(int max_streams, int thread_pool_size);

// 流管理
int cg_stream_create(CGStreamManagerHandle handle, CGStreamConfig* config, char* stream_id);
int cg_stream_start(CGStreamManagerHandle handle, const char* stream_id);
int cg_stream_stop(CGStreamManagerHandle handle, const char* stream_id);
int cg_stream_restart(CGStreamManagerHandle handle, const char* stream_id);

// 回调设置
void cg_set_frame_callback(CGStreamManagerHandle handle, FrameCallback callback, void* user_data);
void cg_set_status_callback(CGStreamManagerHandle handle, StatusCallback callback, void* user_data);
void cg_set_error_callback(CGStreamManagerHandle handle, ErrorCallback callback, void* user_data);

// 指标查询
int cg_stream_get_metrics(CGStreamManagerHandle handle, const char* stream_id, CGStreamMetrics* metrics);

// 切片导出
int cg_export_clip(CGStreamManagerHandle handle, const char* stream_id, const char* event_id,
                   float before_sec, float after_sec, char* path, int path_size);
```

---

## 13. 错误码

| 错误码 | HTTP 状态 | 描述 |
|--------|----------|------|
| `INVALID_REQUEST` | 400 | 请求参数错误 |
| `STREAM_NOT_FOUND` | 404 | 流不存在 |
| `STREAM_LIMIT_EXCEEDED` | 400 | 超过最大流数限制（20路） |
| `EVENT_NOT_FOUND` | 404 | 事件不存在 |
| `CLIP_NOT_FOUND` | 404 | 切片不存在 |
| `CLIP_NOT_READY` | 400 | 切片未就绪 |
| `TRAINING_JOB_NOT_FOUND` | 404 | 训练任务不存在 |
| `INVALID_JOB_STATUS` | 400 | 训练任务状态不允许操作 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |
