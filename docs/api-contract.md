# Campus Guard AI API 契约

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API Prefix**: `/api/v1`
- **WebSocket**: `ws://localhost:8000/ws`
- **Content-Type**: `application/json`

## 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 错误码

| Code | 描述 |
|------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 接口列表

### 健康检查

#### GET /health

**响应**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-01T00:00:00Z",
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

### 视频流管理

#### GET /api/v1/streams

获取流列表

**查询参数**:
- `status`: 按状态筛选（可选）
- `skip`: 分页偏移（默认 0）
- `limit`: 每页数量（默认 20，最大 100）

**响应**:
```json
{
  "total": 5,
  "items": [
    {
      "id": "stream_0001",
      "name": "教学楼A-1F-大厅",
      "input": {
        "type": "rtsp",
        "url": "rtsp://192.168.1.100/stream1"
      },
      "status": "running",
      "enabled": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "metrics": {
        "fps": 25.0,
        "dropped_frames": 0,
        "decode_latency_ms": 15.5
      }
    }
  ]
}
```

#### POST /api/v1/streams

创建新流

**请求体**:
```json
{
  "name": "教学楼A-1F-大厅",
  "input": {
    "type": "rtsp",
    "url": "rtsp://192.168.1.100/stream1"
  },
  "enabled": true
}
```

**响应**: 201 Created，返回创建的流对象

#### GET /api/v1/streams/{stream_id}

获取单个流详情

#### POST /api/v1/streams/{stream_id}/start

启动流

#### POST /api/v1/streams/{stream_id}/stop

停止流

#### DELETE /api/v1/streams/{stream_id}

删除流

---

### 事件管理

#### GET /api/v1/events

获取事件列表

**查询参数**:
- `stream_id`: 按流ID筛选
- `severity`: 按严重级别筛选（low/medium/high/critical）
- `event_type`: 按事件类型筛选
- `review_status`: 按审核状态筛选
- `start_time`: 开始时间（ISO 8601）
- `end_time`: 结束时间（ISO 8601）
- `skip`: 分页偏移
- `limit`: 每页数量

**响应**:
```json
{
  "total": 100,
  "items": [
    {
      "event_id": "evt_abc123",
      "stream_id": "stream_0001",
      "event_type": "fighting",
      "severity": "critical",
      "confidence": 0.95,
      "timestamp": "2024-01-01T12:00:00Z",
      "start_time": "2024-01-01T12:00:00Z",
      "end_time": "2024-01-01T12:00:05Z",
      "track_ids": ["track_001", "track_002"],
      "participants": [
        {
          "track_id": "track_001",
          "person_id": "person_001",
          "bbox": [100, 200, 50, 100],
          "role": "aggressor"
        },
        {
          "track_id": "track_002",
          "bbox": [200, 200, 50, 100],
          "role": "victim"
        }
      ],
      "roles": [
        {
          "track_id": "track_001",
          "role": "aggressor",
          "confidence": 0.92
        },
        {
          "track_id": "track_002",
          "role": "victim",
          "confidence": 0.88
        }
      ],
      "source_frame_ref": "frame_abc123.jpg",
      "clip_ref": "clip_abc123.mp4",
      "review_status": "pending",
      "reviewer_note": null
    }
  ]
}
```

#### POST /api/v1/events/{event_id}/review

审核事件

**请求体**:
```json
{
  "review_status": "approved",
  "note": "确认是打架事件"
}
```

#### POST /api/v1/events/export

导出事件

**请求体**:
```json
{
  "format": "csv",
  "filter": {
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-02T00:00:00Z",
    "severity": "high"
  }
}
```

**响应**: 返回导出任务ID

---

### 系统管理

#### GET /api/v1/system/metrics

获取系统指标

**响应**:
```json
{
  "cpu_percent": 15.5,
  "memory_percent": 42.0,
  "disk_usage_percent": 35.0,
  "active_streams": 5,
  "total_events_today": 12,
  "alerts_pending": 3,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### GET /api/v1/system/config

获取系统配置

#### POST /api/v1/system/config

更新系统配置

---

## WebSocket 协议

### 连接

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### 消息格式

**客户端 → 服务器**:
```json
{
  "type": "subscribe",
  "channels": ["alerts", "stream_status"]
}
```

**服务器 → 客户端**:
```json
{
  "type": "alert",
  "payload": {
    "event_id": "evt_abc123",
    "severity": "critical",
    "message": "检测到打架事件"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 消息类型

- `alert`: 实时告警
- `stream_status`: 流状态变更
- `heartbeat`: 心跳
- `error`: 错误通知

---

## 错误码

| 错误码 | 描述 |
|--------|------|
| `INVALID_REQUEST` | 请求参数错误 |
| `STREAM_NOT_FOUND` | 流不存在 |
| `STREAM_LIMIT_EXCEEDED` | 超过最大流数限制 |
| `EVENT_NOT_FOUND` | 事件不存在 |
| `INTERNAL_ERROR` | 内部服务器错误 |
| `SERVICE_UNAVAILABLE` | 服务不可用 |

---

## 变更日志

### v0.2.0 (P2)
- 更新 Event Schema，支持多人交互行为
- 添加 RoleAssignment 结构（aggressor/victim/bystander/mutual）
- 添加 BehaviorResult 时序识别结果
- 添加 RuleTrigger 规则触发结构
- 明确区分 fighting（互殴）和 bullying（霸凌）
- 添加事件聚合时间窗口概念

### v0.1.0 (P0)
- 初始 API 契约定义
- 基础 CRUD 接口
- WebSocket 协议框架
