# Campus Guard AI - 校园安防视频行为感知系统

自训练 **YOLO26** 校园行为识别模型（11 类）+ FastAPI 控制面 + Python 解码线程池 + Next.js 前端，支持 RTSP / RTMP / 本地文件 / 摄像头的多路并发接入，GPU 实时推理与叠加展示。

---

## 1. 总体架构（当前实现）

```
┌──────────────────┐         ┌────────────────────────────────────┐
│  Next.js 前端    │  HTTP   │  apps/api  (FastAPI :8000)         │
│  /streams 管理页 │ ──────▶ │  - 流 CRUD + 浏览本地文件 + 控制   │
│  /snapshot 轮询  │ ◀────── │  - 每路流一个解码线程(OpenCV)      │
└──────────────────┘  JPEG   │  - 推理**异步**派发（共享线程池）   │
                             │     解码循环不阻塞 → 画面流畅       │
                             │  - 最多 20 路并发                  │
                             └──────────────┬─────────────────────┘
                                            │ HTTP (base64 JPEG)
                                            ▼
                             ┌────────────────────────────────────┐
                             │ services/ai-runtime :9001          │
                             │ YOLO26 (11 类) @ CUDA              │
                             │ 返回 detections（本地画框）         │
                             └────────────────────────────────────┘
                                            │
                             PostgreSQL + Redis（Docker 一键起；无则自动回退 SQLite）
```

**设计要点：**

- **推理异步解耦**：解码线程每 N 帧把当前帧丢到共享线程池异步调 ai-runtime，**不等响应**；画框用最近一次返回的 detections。单 GPU 被 11 路流打满时，检测框更新会滞后 1-2 秒，**但每路画面仍是 30 fps 流畅**，不会整体卡住
- `services/stream-core`（C++ FFmpeg 线程池）**保留源码**但未接入当前数据链路，供未来切换
- `services/mock-streamer` 是旧演示入口，已由 apps/api 取代，保留作兼容

---

## 2. YOLO26 模型（自训练）

权重：`services/ai-runtime/models/yolo26_campus.pt`（~5.3 MB）

| 类别 | 含义 | 默认风险等级 |
|------|------|------|
| `Kick` | 踢打 | high |
| `Slap face` | 扇耳光 | high |
| `Hit wall` | 击墙 | high |
| `Slap table` | 拍桌 | medium |
| `Smoking` | 吸烟 | medium |
| `Phone` | 玩手机 | medium |
| `Pointing` | 指点 | low |
| `Touch` | 触碰 | low |
| `Laying` | 躺卧 | low |
| `Squating` | 蹲坐 | low |
| `Stand` | 站立 | info |

测试集（696 张）：**Precision 0.987 / Recall 0.989 / mAP50 0.992 / mAP50-95 0.987**，RTX 4060 Laptop (8GB) 上单帧 ~35-65 ms。

---

## 3. 环境要求

### 运行时（必需）

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | **3.11** | apps/api 与 services/ai-runtime 共用 |
| Node.js | 18+ | 前端构建与运行 |
| NVIDIA GPU + CUDA | 驱动 ≥ 535，CUDA ≥ 12.1 | 用 CUDA 12.1 版本的 torch；无 GPU 可设 `INFERENCE_DEVICE=cpu` |
| FFmpeg | 已随 OpenCV 自带 | 系统级 FFmpeg 非必需，但 RTSP 稳定性更好时建议装 |

### 运行时（可选）

- **Docker Desktop**：仅用来起 postgres / redis；未提供时 apps/api 自动回退 SQLite（`./data/campus_guard.db`）
- **PostgreSQL 16 / Redis 7**：生产部署用

### Python 依赖

两个服务共用同一套 Python（3.11），从 `services/ai-runtime/requirements.txt` 与 `apps/api/requirements.txt` 各自 `pip install -r ...` 即可。核心依赖清单：

```
# AI 推理栈
ultralytics>=8.4.0
torch>=2.1.0                 # CUDA 版本请按官方指引单独装，例：
                             # pip install torch --index-url https://download.pytorch.org/whl/cu121
opencv-python-headless>=4.8.0
numpy>=1.24.0

# Web 框架 / 数据
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
aiosqlite>=0.19.0            # SQLite 回退需要
asyncpg==0.29.0              # PostgreSQL（可选）
redis==5.0.1                 # Redis（可选）
httpx==0.26.0
pydantic==2.5.3
pydantic-settings==2.1.0
websockets==12.0
```

> 使用 conda 管理环境示例：
> ```bash
> conda create -n campus_guard python=3.11 -y
> conda activate campus_guard
> pip install -r apps/api/requirements.txt
> pip install -r services/ai-runtime/requirements.txt
> # GPU 版 torch：
> pip install torch --index-url https://download.pytorch.org/whl/cu121
> ```

### Node 依赖

```bash
cd apps/web
npm install
```

---

## 4. 启动与验证

有两种模式：**A. 一键 Docker Compose**（推荐）与 **B. 本地裸跑**。

### A. Docker Compose 一键启动（推荐）

**最快路径**：项目根目录有一键脚本

```bash
# Windows（双击或 cmd 运行）
start.bat        # 启动全栈（检查 Docker → 构建 → 等就绪 → 开浏览器）
demo.bat         # 启动 + 自动推 11 路演示流（project1 下各类视频）
stop.bat         # 停止（保数据）
stop.bat -v      # 停止并清数据卷

# Linux / macOS / WSL
./start.sh
./demo.sh
./stop.sh
./stop.sh -v
```

- `start` 会自动：检查 Docker → 首次拉 pytorch 基础镜像 → `docker compose up -d --build` → 等健康检查 → 打开浏览器
- `demo` 在 `start` 之后自动 POST 11 路流，每路对应 `project1/` 下一段行为视频，**一键完成演示布置**

如果你想手动走，按下面步骤来：



**4.A.0 宿主机前置**：
- Docker Desktop（WSL2 backend）≥ 4.30，内置 nvidia runtime（查 `docker info` 应含 `Runtimes: ... nvidia runc`）
- Docker Engine 里配置镜像加速（Docker Hub 在国内不稳），Settings → Docker Engine：
  ```json
  {
    "registry-mirrors": [
      "https://docker.m.daocloud.io",
      "https://dockerproxy.com",
      "https://docker.mirrors.ustc.edu.cn",
      "https://hub-mirror.c.163.com"
    ]
  }
  ```
- （仅构建前）先拉一次 pytorch 基础镜像，避免一次性下载叠加 pip 安装耗尽 WSL2 虚拟磁盘触发 I/O error：
  ```bash
  docker pull pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime   # ~5GB
  ```

**4.A.1 构建 + 启动**：
```bash
cd D:/vidio_school_system
docker compose build       # 首次约 10-20 分钟
docker compose up -d       # 启 postgres / redis / ai-runtime(GPU) / api / web
docker compose ps          # 五个容器都应 healthy 或 running
```

访问：
- 前端 http://localhost:3000
- API http://localhost:8000/docs
- AI Runtime http://localhost:9001/models

**4.A.2 验证 GPU 推理**：
```bash
docker logs campus-guard-ai-runtime | grep "Model loaded"
# 应看到：[YOLODetector] Model loaded: ./models/yolo26_campus.pt (device=cuda:0)
```

**4.A.3 端到端测试**（用项目自带 `project1/` 测试视频；compose 已挂载到容器 `/project1`）：
```bash
curl -X POST http://localhost:8000/api/v1/streams \
  -H "Content-Type: application/json" \
  -d '{"name":"Test-Kick","url":"/project1/Kick/kick_backward_1-1.mp4","input_type":"file","auto_start":true}'
# 5 秒后
curl http://localhost:8000/api/v1/streams/{id}/snapshot -o frame.jpg
```

停止：`docker compose down`（保留数据库），加 `-v` 则同时清数据卷。

---

### B. 本地裸跑（不用 Docker）

#### 第 0 步（可选）：启动 postgres + redis

```bash
docker-compose up -d postgres redis
```

跳过这一步也能运行，apps/api 会自动在 `apps/api/data/campus_guard.db` 创建 SQLite。

#### 第 1 步：AI Runtime（端口 9001，需要 GPU）

```bash
cd services/ai-runtime
$env:PYTHONPATH="src"        # PowerShell；bash 用 export PYTHONPATH=src
python main.py
```

启动日志关键行：
```
[YOLODetector] Model loaded: ./models/yolo26_campus.pt (device=cuda:0)
AI Runtime Ready! (detector_ready=True)
```

独立测试（无需 apps/api）：
```bash
python test_phase1.py "D:/vidio_school_system/project1/Kick/kick_backward_1-1.mp4"
# → phase1_result.jpg 可以打开看叠加后的检测框
```

#### 第 2 步：apps/api（端口 8000）

```bash
cd apps/api
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

启动日志关键行：
```
✅ 数据库就绪：sqlite+aiosqlite   （或 postgresql+asyncpg）
🚀 Campus Guard API 启动
```

#### 第 3 步：前端（端口 3000）

```bash
cd apps/web
npm run dev
```

- 前端：http://localhost:3000
- API 文档：http://localhost:8000/docs

---

## 5. 添加流（两种方式）

项目提供 11 段测试视频在 `project1/<类别>/*.mp4`，可直接用来验收。

### 5.1 Web UI

访问 `/streams` → 右上角 **添加流** → 选择类型：

- **RTSP 摄像头**：`rtsp://user:pass@192.168.1.64:554/Streaming/Channels/101`
- **RTMP 推流**：`rtmp://host/app/stream`
- **本地视频文件**：
  - 对话框会自动从 `FILE_BROWSE_ROOTS`（默认 `/project1`、`./project1`、`D:/vidio_school_system/project1`）里扫出所有视频文件，出现在下拉列表里，**直接点选即可**
  - 或手动输入后端可见的绝对路径
- **本地摄像头**：索引（`0`、`1`……）

勾选「创建后立即启动」即开始 YOLO26 推理，画面实时叠加红/橙/黄/灰的检测框（按风险等级配色）。

### 5.2 REST API

```bash
# 创建 + 立即启动
curl -X POST http://localhost:8000/api/v1/streams \
  -H "Content-Type: application/json" \
  -d '{
        "name":"教学楼-1F",
        "url":"D:/vidio_school_system/project1/Smoking/smoking_backward_1-1.mp4",
        "input_type":"file",
        "auto_start":true
      }'

# 获取实时状态（包含 is_running / 最近检测 / 推理设备 / 每帧耗时）
curl http://localhost:8000/api/v1/streams/{id}

# 取叠加后的最新一帧 JPEG（前端 SnapshotPlayer 就是轮询这个接口）
curl http://localhost:8000/api/v1/streams/{id}/snapshot -o frame.jpg

# 启停 / 重启 / 删除
curl -X POST   http://localhost:8000/api/v1/streams/{id}/stop
curl -X POST   http://localhost:8000/api/v1/streams/{id}/start
curl -X POST   http://localhost:8000/api/v1/streams/{id}/restart
curl -X DELETE http://localhost:8000/api/v1/streams/{id}
```

---

## 6. 环境变量参考

### apps/api（写入 `apps/api/.env` 或系统环境变量）

| 变量 | 默认 | 说明 |
|------|------|------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL；连接失败自动回退 SQLite |
| `USE_SQLITE_FALLBACK` | `True` | 允许回退到 SQLite |
| `SQLITE_PATH` | `./data/campus_guard.db` | SQLite 文件位置 |
| `AI_RUNTIME_URL` | `http://127.0.0.1:9001` | ai-runtime 地址 |
| `AI_RUNTIME_TIMEOUT` | `30.0` | HTTP 超时（秒） |
| `INFER_EVERY_N` | `2` | 每 N 帧推理一次（节省 GPU） |
| `JPEG_QUALITY` | `75` | 上行/下发 JPEG 质量 1-100 |
| `MAX_CONCURRENT_STREAMS` | `20` | 最大并发流数 |
| `FILE_BROWSE_ROOTS` | `/project1,./project1,D:/vidio_school_system/project1` | 前端「本地文件」下拉扫描的根目录（逗号分隔） |
| `FILE_BROWSE_EXTS` | `.mp4,.avi,.mov,.mkv,.webm` | 可识别的视频扩展名 |
| `FILE_BROWSE_MAX` | `200` | 单次扫描返回的最大条数 |

### services/ai-runtime

| 变量 | 默认 | 说明 |
|------|------|------|
| `INFERENCE_DEVICE` | `cuda:0` | 无 GPU 时设 `cpu` |
| `DETECTOR_MODEL` | `yolo26_campus` | 权重文件名（不含 `.pt`），置于 `services/ai-runtime/models/` |
| `DETECTOR_CONFIDENCE` | `0.35` | 置信度阈值 |
| `USE_REAL_MODELS` | `True` | `False` 用随机检测 mock（无 GPU 调试用） |
| `PORT` | `9001` | |

### apps/web

| 变量 | 默认 | 说明 |
|------|------|------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | apps/api 地址（含 `/api/v1` 前缀） |

---

## 7. 项目结构

```
vidio_school_system/
├── apps/
│   ├── web/              # Next.js 前端（/streams 等页面）
│   └── api/              # FastAPI 控制面 + 解码线程池
│       ├── app/
│       │   ├── routers/streams.py         # 流 CRUD + start/stop + /snapshot
│       │   ├── services/stream_runtime.py # 解码 + HTTP 调 ai-runtime
│       │   ├── core/database.py           # postgres → sqlite 自动回退
│       │   └── ...
│       └── main.py
├── services/
│   ├── ai-runtime/       # YOLO26 GPU 推理服务
│   │   ├── models/
│   │   │   └── yolo26_campus.pt          # 11 类校园行为自训练权重
│   │   ├── src/ai_runtime/
│   │   │   ├── detector/detector.py      # YOLODetector + 类别映射
│   │   │   └── detector/annotate.py      # 画框
│   │   ├── main.py                        # /inference 端点
│   │   └── test_phase1.py                 # 阶段 1 独立自测
│   ├── stream-core/      # C++ FFmpeg 线程池（保留源码，未接入当前链路）
│   └── mock-streamer/    # 旧演示路径（兼容保留）
├── project1/             # 11 类测试视频（Kick / Smoking / Phone / ...）
├── packages/             # 共享类型 / UI
└── docker-compose.yml    # postgres + redis
```

---

## 8. 性能实测（RTX 4060 Laptop 8GB, Windows 11 + Docker Desktop WSL2）

| 指标 | 实测 |
|------|------|
| 模型加载 | ~3s（含首次 CUDA 预热） |
| 单帧推理 | 35-65 ms (1280×720) |
| 端到端 RTT（apps/api → ai-runtime → 回帧） | 60-100 ms |
| 并发 4 路（`INFER_EVERY_N=2`） | ~90% GPU 利用率 |
| 并发 11 路 | 单路解码 ~30 fps 稳定；检测框更新频率 ~3 Hz/路（GPU 排队） |

**关键数字：** 由于推理已异步解耦，**解码帧率不随并发路数下降**。仅检测框的"更新频率"会随路数线性摊薄。8GB 显存支撑 10-15 路并发无压力；20 路以上建议提升 `INFER_EVERY_N` 到 5 或部署多 GPU。

---

## 9. 常见问题

### Q1. `Failed to load model: xxx/yolo26_campus.pt`
确认权重文件存在；ai-runtime 必须在 `services/ai-runtime/` 目录下启动（配置 `MODEL_PATH=./models`）。

### Q2. `CUDA 不可用，自动降级为 CPU`
torch 没装 CUDA 版。用 `python -c "import torch; print(torch.cuda.is_available())"` 验证；安装：
```
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### Q3. 前端显示「无法连接 apps/api」
确认 `apps/api` 跑在 8000 端口；前端环境变量 `NEXT_PUBLIC_API_URL` 对齐。

### Q4. RTSP 流反复重连
已默认走 TCP (`rtsp_transport=tcp`)。若仍不稳，`apps/api/.env` 里加长 `AI_RUNTIME_TIMEOUT`；或把 `INFER_EVERY_N` 调大降压。

### Q5. Postgres 连不上
apps/api 会自动回退到 SQLite，日志会打 `↪ 回退到 SQLite`。想用 PostgreSQL 就 `docker-compose up -d postgres redis`。

---

## 10. 文档

- [架构设计](docs/architecture.md)
- [API 契约](docs/api-contract.md)
- [性能测试](docs/benchmark.md)
- [部署说明](docs/deployment.md)
- [模型训练](docs/model-retrain.md)
