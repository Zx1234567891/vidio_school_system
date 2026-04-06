# 推荐仓库结构与模块边界

```text
campus-guard/
├─ apps/
│  ├─ web/                    # Next.js 前端
│  └─ api/                    # FastAPI 控制面
├─ services/
│  ├─ stream-core/            # C++20 + FFmpeg 流媒体接入、线程池、切片、背压
│  └─ ai-runtime/             # Python 训练/推理编排、ONNX 导出/加载、规则融合
├─ packages/
│  ├─ shared-types/           # DTO、事件契约、公共 schema
│  └─ ui/                     # 共享 UI 组件、设计 token
├─ docs/
│  ├─ architecture.md
│  ├─ api-contract.md
│  ├─ benchmark.md
│  ├─ deployment.md
│  └─ competition-report.md
├─ infra/
│  ├─ docker/
│  └─ scripts/
├─ models/
├─ datasets/
├─ .claude/
│  ├─ rules/
│  └─ skills/
├─ docker-compose.yml
└─ README.md
```

## 模块边界

### apps/web
职责：
- 多路视频矩阵展示
- 实时预警展示
- 历史查询与筛选
- 事件审核与日志在线修改
- 设置与训练任务入口
不负责：
- 直接做视频解码
- 直接保存业务核心状态
- 直接承载模型推理

### apps/api
职责：
- REST API
- WebSocket
- 训练任务与导出任务编排
- 事件查询、审核、导出
- 统一错误处理、鉴权与日志
不负责：
- 高吞吐实时解码
- 重型图像处理

### services/stream-core
职责：
- RTSP / RTMP / 文件输入
- 解码
- 固定线程池
- 有界队列
- 背压
- 环形缓存
- clip 导出
- per-stream 状态与指标
不负责：
- 前端页面
- 复杂业务权限

### services/ai-runtime
职责：
- 检测
- 跟踪
- 行为识别
- 规则融合
- 角色区分
- 模型导出/加载
- 训练任务
不负责：
- 浏览器端展示

### packages/shared-types
职责：
- 统一 DTO
- 统一事件 schema
- 统一 review schema
- 统一 metrics schema

## 技术栈锁定
- Frontend: Next.js + TypeScript + Tailwind CSS + shadcn/ui
- Backend: FastAPI + WebSocket + PostgreSQL + Redis
- Streaming: C++20 + FFmpeg + fixed-size thread pool
- AI runtime: Python + ONNX Runtime
- Deploy: Docker Compose
