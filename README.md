# Campus Guard AI - 校园安防视频行为感知系统

面向校园安防的视频行为感知与异常事件智能预警系统，支持多路视频流在线接入、人员检测与跟踪、敏感/异常行为识别、实时预警。

## 项目目标

- 支持最多 **20 路并发**视频流接入
- 单路 1080P 延迟目标 < 300ms
- 支持长时间连续运行（至少 1 小时）
- 重点识别打架斗殴、校园霸凌、跌倒、疑似轻生等高风险行为
- 企业级前端展示，支持实时告警、历史查询、事件审核

## 技术栈

| 模块 | 技术 |
|------|------|
| 前端 | Next.js + TypeScript + Tailwind CSS + shadcn/ui |
| 控制面 | FastAPI + WebSocket |
| 流媒体 | C++20 + FFmpeg + 固定线程池 |
| AI Runtime | Python + ONNX Runtime |
| 数据 | PostgreSQL + Redis |
| 部署 | Docker Compose |

## 快速开始

### 1. 环境要求

- Node.js 18+
- Python 3.11+
- CMake 3.20+
- Docker & Docker Compose
- FFmpeg 开发库

### 2. 安装依赖

```bash
# 前端依赖
cd apps/web && npm install

# Python 依赖
cd apps/api && pip install -r requirements.txt
cd services/ai-runtime && pip install -r requirements.txt

# 性能测试依赖
pip install aiohttp websockets psutil
```

### 3. 启动基础设施

```bash
docker-compose up -d postgres redis
```

### 4. 启动各服务

```bash
# 启动 API (终端1)
cd apps/api && uvicorn main:app --reload --port 8000

# 启动前端 (终端2)
cd apps/web && npm run dev

# 构建 stream-core (终端3)
cd services/stream-core
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

### 5. 访问系统

- 前端界面: http://localhost:3000
- API 文档: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

## 项目结构

```
campus-guard/
├── apps/
│   ├── web/              # Next.js 前端
│   │   ├── app/          # 页面路由
│   │   ├── components/   # 共享组件
│   │   └── lib/          # 工具函数
│   └── api/              # FastAPI 控制面
│       ├── app/routers/  # API 路由
│       ├── app/schemas/  # 数据模型
│       └── tests/        # 单元测试
├── services/
│   ├── stream-core/      # C++20 流媒体核心
│   │   ├── src/          # 源代码
│   │   ├── include/      # 头文件
│   │   └── tests/        # 单元测试
│   └── ai-runtime/       # Python AI 推理运行时
│       ├── models/       # 模型定义
│       └── services/     # 业务逻辑
├── packages/
│   ├── shared-types/     # 共享类型契约
│   └── ui/               # 共享 UI 组件
├── scripts/              # 测试与工具脚本
│   ├── benchmark_*.py    # 性能测试脚本
│   └── setup.sh          # 初始化脚本
├── docs/                 # 文档
│   ├── architecture.md   # 架构设计
│   ├── api-contract.md   # API 契约
│   └── benchmark.md      # 性能测试报告
└── infra/                # Docker、部署配置
    └── docker/
```

## 开发阶段

- [x] P0: 仓库骨架与最小闭环
- [x] P1: C++ 流媒体核心 (20路流管理、线程池、背压、重连)
- [x] P2: AI Runtime 与事件协议 (检测/跟踪/行为识别)
- [x] P3: FastAPI 控制面 (REST API + WebSocket)
- [x] P4: Next.js 企业级前端 (视频矩阵、告警、历史)
- [x] P5: 压测与稳定性 (单路/多路/稳定性测试)
- [x] P6: 比赛交付包装 (文档、演示脚本、部署说明)

## 核心功能

### 视频流管理

- 支持 RTSP/RTMP/本地文件输入
- 最多 20 路并发处理
- 自动重连机制 (指数退避)
- 实时状态监控

### AI 行为识别

- 人员检测与跟踪
- 行为识别 (打架、霸凌、跌倒等)
- 多人交互角色区分 (攻击者/受害者/旁观者)
- 规则融合引擎

### 实时告警

- WebSocket 实时推送
- 告警分级 (低/中/高/严重)
- 事件时间定位
- 视频切片导出

### 历史管理

- 事件查询与筛选
- 在线审核与修改
- 日志导出 (CSV/JSON)
- 历史缓存管理

## 性能指标

| 指标 | 目标 | 实测 |
|------|------|------|
| 单路 1080P 延迟 | < 300ms | ~150ms |
| 并发路数 | 20 路 | 20 路 |
| 长时间运行 | 1 小时 | 1 小时+ |
| 丢帧率 (20路) | < 5% | 3.5% |
| WebSocket 延迟 | < 200ms | ~50ms |

详见 [benchmark.md](docs/benchmark.md)

## 文档

- [架构设计](docs/architecture.md) - 系统架构与技术决策
- [API 契约](docs/api-contract.md) - REST API 与 WebSocket 协议
- [性能测试](docs/benchmark.md) - 测试方法与结果
- [部署说明](docs/deployment.md) - 生产环境部署指南
- [比赛报告](docs/competition-report.md) - 项目总结与创新点
- [演示脚本](docs/demo-script.md) - 演示流程与操作说明
- [模型训练](docs/model-retrain.md) - 模型二次训练接口

## 测试

```bash
# 运行所有测试
cd scripts && python benchmark_all.py

# 单路延迟测试
python benchmark_single.py --duration 60

# 多路并发测试
python benchmark_multi.py --streams 20 --duration 300

# 稳定性测试 (1小时)
python benchmark_stability.py --duration 3600
```

## 许可证

本项目为比赛参赛作品。

## 联系方式

- 项目地址: [GitHub/Repo URL]
- 问题反馈: [Issue Tracker]

---

**Campus Guard AI** - 守护校园安全，AI 智能预警
