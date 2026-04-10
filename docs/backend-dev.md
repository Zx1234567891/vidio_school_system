# Campus Guard AI - 后端开发文档

## 1. 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行时 |
| FastAPI | 最新 | Web 框架 |
| SQLAlchemy | 2.x (async) | ORM |
| PostgreSQL | - | 主数据库 |
| SQLite | - | 备用数据库（开发环境） |
| Redis | - | 缓存、消息队列、Pub/Sub |
| Uvicorn | - | ASGI 服务器 |
| Pydantic v2 | - | 数据校验与序列化 |
| psutil | - | 系统资源监控 |

## 2. 项目结构

```
apps/api/
├── main.py                       # 应用入口，FastAPI 实例、路由注册、WebSocket
├── requirements.txt              # Python 依赖
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # 应用配置（Pydantic Settings）
│   │   ├── database.py           # 数据库引擎、会话工厂、初始化
│   │   └── redis.py              # Redis 连接池
│   ├── models/
│   │   ├── __init__.py           # 导出 Base 和所有模型
│   │   ├── stream.py             # 视频流表（Stream）
│   │   ├── event.py              # 事件表（Event）
│   │   ├── clip.py               # 切片表（Clip）
│   │   ├── review.py             # 审核记录表（Review）
│   │   └── training_job.py       # 训练任务表（TrainingJob）
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py             # ResponseModel 统一响应
│   │   ├── stream.py             # StreamCreate / StreamUpdate / StreamResponse
│   │   ├── event.py              # EventCreate / EventUpdate / EventResponse
│   │   ├── clip.py               # ClipCreate / ClipResponse / ClipExportRequest
│   │   ├── review.py             # ReviewCreate / ReviewResponse
│   │   ├── training.py           # TrainingJobCreate / TrainingJobResponse
│   │   └── metrics.py            # SystemMetrics / StreamMetrics
│   ├── routers/
│   │   ├── __init__.py           # 导出所有路由
│   │   ├── health.py             # GET /health
│   │   ├── streams.py            # /api/v1/streams CRUD + 启停控制
│   │   ├── events.py             # /api/v1/events CRUD + 统计
│   │   ├── reviews.py            # /api/v1/reviews 审核管理
│   │   ├── clips.py              # /api/v1/clips 切片管理与导出
│   │   ├── training.py           # /api/v1/training 训练任务管理
│   │   ├── metrics.py            # /api/v1/metrics 指标和仪表盘
│   │   └── system.py             # /api/v1/system 系统配置
│   └── services/
│       ├── __init__.py
│       ├── websocket_manager.py  # WebSocket 连接管理与广播
│       └── event_publisher.py    # 事件发布器（Redis Pub/Sub → WebSocket）
```

## 3. 应用配置

### 3.1 配置类 (`app/core/config.py`)

```python
class Settings(BaseSettings):
    APP_NAME: str = "Campus Guard AI API"
    VERSION: str = "0.1.0"
    ENV: str = "development"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    DATABASE_URL: str = "postgresql+asyncpg://campus_guard:campus_guard_secret@localhost:5432/campus_guard"
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_PATH: str = "./data/campus_guard.db"

    REDIS_URL: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "INFO"
```

- 支持 `.env` 文件加载
- PostgreSQL 为主数据库，SQLite 为备用
- CORS 默认允许前端 3000 端口

### 3.2 环境变量

```env
ENV=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
DATABASE_URL=postgresql+asyncpg://campus_guard:campus_guard_secret@localhost:5432/campus_guard
USE_SQLITE_FALLBACK=true
REDIS_URL=redis://localhost:6379/0
```

## 4. 数据库设计

### 4.1 数据库引擎

- 使用 SQLAlchemy 2.x **异步模式** (`AsyncSession`)
- 异步引擎 `create_async_engine`
- 异步会话工厂 `async_sessionmaker`
- ORM 使用 `Mapped` + `mapped_column` 声明式

### 4.2 数据库初始化

```python
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

应用启动时自动创建所有表。

### 4.3 数据模型

#### streams 表（视频流）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(64) PK | 流 ID，格式 `stream_{uuid12}` |
| `name` | String(255) | 流名称 |
| `url` | String(1024) | 流地址 |
| `input_type` | Enum(rtsp/rtmp/file) | 输入类型 |
| `status` | Enum | 状态：init/connecting/running/degraded/reconnecting/stopped/error |
| `status_message` | Text | 状态附加信息 |
| `target_fps` | Integer | 目标帧率，默认 25 |
| `max_queue_size` | Integer | 最大队列大小，默认 100 |
| `ring_buffer_seconds` | Integer | 环形缓冲区时长，默认 30s |
| `max_reconnect_attempts` | Integer | 最大重连次数，默认 5 |
| `reconnect_interval_ms` | Integer | 重连间隔，默认 1000ms |
| `width/height/fps/bitrate/codec` | - | 视频参数（运行时获取） |
| `location/latitude/longitude` | - | 地理位置 |
| `region_config` | JSON | 区域配置（ROI、禁区） |
| `total_frames_decoded` | Integer | 已解码帧数 |
| `total_dropped_frames` | Integer | 丢帧数 |
| `reconnect_count` | Integer | 重连次数 |
| `is_deleted` | Boolean | 软删除标志 |
| `created_at/updated_at/started_at/stopped_at` | DateTime | 时间戳 |

#### events 表（事件）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(64) PK | 事件 ID，格式 `evt_{uuid12}` |
| `stream_id` | String(64) FK→streams | 关联流 |
| `event_type` | Enum | 事件类型（11种） |
| `category` | Enum | 类别：high_risk/sensitive/suspicious/normal |
| `severity` | Enum | 严重级别：critical/high/medium/low |
| `status` | Enum | 状态：pending/confirmed/false_positive/resolved/ignored |
| `start_time/end_time` | DateTime | 事件时间范围 |
| `duration_ms` | Integer | 持续时长 |
| `confidence` | Float | 置信度 0-1 |
| `participants` | JSON | 参与者列表 [{track_id, bbox, confidence}] |
| `roles` | JSON | 角色分配 {aggressor, victim, bystander, mutual} |
| `snapshot_url` | String | 快照图片 URL |
| `clip_id` | String FK→clips | 关联切片 |
| `ai_details` | JSON | AI 推理详情 |
| `reviewed_by/reviewed_at/review_comment` | - | 审核信息 |
| `handled_by/handled_at/handle_result` | - | 处理信息 |
| `is_deleted` | Boolean | 软删除 |

**事件类型枚举（EventType）**：

| 枚举值 | 中文 | 类别 |
|--------|------|------|
| `fighting` | 打架斗殴 | 高风险 |
| `bullying` | 校园霸凌 | 高风险 |
| `falling` | 跌倒/昏厥 | 高风险 |
| `suicide_attempt` | 疑似轻生 | 高风险 |
| `vandalism` | 破坏公共设施 | 高风险 |
| `smoking` | 吸烟/点火 | 管理敏感 |
| `phone_usage` | 长时间使用手机 | 管理敏感 |
| `camera_tampering` | 遮挡摄像头 | 管理敏感 |
| `loitering` | 异常徘徊 | 可疑行为 |
| `intrusion` | 闯入限制区域 | 可疑行为 |
| `fence_climbing` | 翻越围栏 | 可疑行为 |

#### clips 表（视频切片）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(64) PK | 切片 ID，格式 `clip_{uuid12}` |
| `stream_id` | String FK→streams | 关联流 |
| `event_id` | String FK→events | 关联事件 |
| `file_path` | String | 文件路径 |
| `file_size/duration/width/height/fps/codec/format` | - | 文件元数据 |
| `start_time/end_time` | DateTime | 时间范围 |
| `seconds_before/seconds_after` | Integer | 事件前后秒数 |
| `status` | Enum | pending/exporting/completed/failed/expired |
| `download_count` | Integer | 下载次数 |
| `expires_at` | DateTime | 过期时间 |

#### reviews 表（审核记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(64) PK | 审核 ID，格式 `rev_{uuid12}` |
| `event_id` | String FK→events (唯一) | 关联事件 |
| `reviewer_id/reviewer_name` | String | 审核人 |
| `action` | Enum | confirm/reject/modify/resolve/ignore |
| `original_data/modified_data` | JSON | 修改前后数据 |
| `comment` | Text | 审核意见 |

#### training_jobs 表（训练任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(64) PK | 任务 ID，格式 `train_{uuid12}` |
| `name/description` | String | 任务名称/描述 |
| `training_type` | Enum | detection/classification/behavior/end_to_end |
| `status` | Enum | pending/preparing/running/validating/completed/failed/cancelled |
| `dataset_config` | JSON | 数据集配置 |
| `model_config` | JSON | 模型配置（base_model, epochs, batch_size 等） |
| `hyperparameters` | JSON | 超参数 |
| `current_epoch/total_epochs/current_step/total_steps` | Integer | 进度 |
| `metrics` | JSON | 性能指标（loss, accuracy, mAP 等） |
| `output_model_path/onnx_export_path` | String | 输出模型路径 |
| `gpu_ids/max_gpu_memory_mb` | - | 资源使用 |

### 4.4 模型关联关系

```
Stream 1:N Event
Event 1:1 Review
Event N:1 Clip
Clip N:1 Stream
```

## 5. 路由详解

### 5.1 路由注册

```python
app.include_router(health_router, tags=["Health"])
app.include_router(streams_router, prefix="/api/v1/streams", tags=["Streams"])
app.include_router(events_router, prefix="/api/v1/events", tags=["Events"])
app.include_router(reviews_router, prefix="/api/v1/reviews", tags=["Reviews"])
app.include_router(clips_router, prefix="/api/v1/clips", tags=["Clips"])
app.include_router(training_router, prefix="/api/v1/training", tags=["Training"])
app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["Metrics"])
app.include_router(system_router, prefix="/api/v1/system", tags=["System"])
```

### 5.2 统一响应格式

```python
class ResponseModel(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None
```

所有 API 返回统一结构：`{ code: 0, message: "success", data: {...} }`

### 5.3 分页模式

所有列表接口支持分页参数：
- `page`: 页码（默认 1，最小 1）
- `page_size`: 每页数量（默认 20，最小 1，最大 100）

返回分页元数据：
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

### 5.4 软删除模式

Stream 和 Event 采用软删除：
- `is_deleted` 标志位
- `deleted_at` 时间戳
- 查询时默认过滤 `is_deleted == False`

Clip 和 TrainingJob 采用硬删除。

## 6. WebSocket 服务

### 6.1 WebSocket 管理器 (`services/websocket_manager.py`)

- 管理所有活跃的 WebSocket 连接
- 支持频道订阅（`alerts`、`stream_status`）
- 广播消息到所有订阅者

### 6.2 事件发布器 (`services/event_publisher.py`)

- 从 Redis Pub/Sub 接收事件
- 通过 WebSocket 转发到前端
- 应用启动时自动作为后台任务运行

### 6.3 WebSocket 端点

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # 支持消息类型：
    # - ping/pong 心跳
    # - subscribe 订阅
    # - echo 回显
```

## 7. 应用生命周期

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    await init_db()                              # 创建数据库表
    asyncio.create_task(event_publisher.start())  # 启动事件发布器
    yield
    # 关闭
    await event_publisher.stop()
```

## 8. 开发与部署

### 8.1 依赖安装

```bash
cd apps/api
pip install -r requirements.txt
```

### 8.2 启动开发服务器

```bash
cd apps/api
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 8.3 Docker Compose 部署

```yaml
# docker-compose.yml 包含：
# - postgres: PostgreSQL 数据库
# - redis: Redis 缓存
# - api: FastAPI 服务
# - web: Next.js 前端
```

### 8.4 OpenAPI 文档

启动后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 9. 关键设计决策

### 9.1 异步优先

所有数据库操作使用 `async/await`，不阻塞事件循环。

### 9.2 层次分明

```
Router (路由) → Schema (校验) → Model (ORM) → Database
```

### 9.3 后台任务

切片导出、模型训练等耗时操作使用 `BackgroundTasks` 或独立任务队列。

### 9.4 CORS 配置

允许前端跨域请求，支持 credentials。
