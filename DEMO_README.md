# Campus Guard AI - 完整演示系统

基于检测好的视频数据，一键启动完整项目演示。

## 已加载的检测视频 (10路)

| 视频流 | 行为标签 | 严重程度 | 分辨率 | 帧率 |
|-------|---------|---------|--------|------|
| stream_001 | 低头看手机 | 中 | 1920x1080 | 30fps |
| stream_002 | 吸烟 | 中 | 1920x1080 | 30fps |
| stream_003 | 异常徘徊 | 低 | 1920x1080 | 30fps |
| stream_004 | 打架斗殴 | 高 | 1920x1080 | 30fps |
| stream_005 | 摄像头遮挡 | 中 | 1920x1080 | 30fps |
| stream_006 | 摔倒 | 高 | 1920x1080 | 30fps |
| stream_007 | 校园霸凌 | 高 | 1920x1080 | 30fps |
| stream_008 | 破坏设施 | 高 | 1920x1080 | 30fps |
| stream_009 | 翻越围栏 | 低 | 1920x1080 | 30fps |
| stream_010 | 疑似轻生 | 高 | 1920x1080 | 30fps |

## 快速启动

### 方式1: 一键启动 (推荐)

**Windows:**
```bash
start_demo.bat
```

**Linux/Mac:**
```bash
bash start_demo.sh
```

### 方式2: 手动启动

```bash
cd services/mock-streamer
python demo_server.py
```

### 方式3: 同时启动前端

```bash
# 终端1: 启动API服务器
cd services/mock-streamer
python demo_server.py

# 终端2: 启动前端
cd apps/web
npm run dev
```

## 访问地址

- **API服务器**: http://localhost:8080
- **前端界面**: http://localhost:3000
- **WebSocket**: ws://localhost:8080/ws

## 演示功能

### 1. 系统概览
- 实时统计面板
- 事件风险分布
- 最近检测事件

### 2. 视频流管理
- 10路检测视频流
- 启动/停止推流控制
- 视频预览卡片

### 3. 实时告警
- WebSocket实时推送
- 告警确认功能
- 风险等级标识

### 4. 历史记录
- 完整事件列表
- 多维度筛选
- 审核状态跟踪

## API端点

```
GET  /                  - 演示状态页面
GET  /health            - 健康检查
GET  /api/v1/demo/streams           - 视频流列表
POST /api/v1/demo/streams/{id}/start - 启动推流
POST /api/v1/demo/streams/{id}/stop  - 停止推流
GET  /api/v1/demo/events             - 事件列表
GET  /api/v1/demo/alerts             - 告警列表
GET  /api/v1/demo/stats              - 统计数据
WS   /ws                             - 实时告警
```

## 演示数据

系统自动生成:
- **58个检测事件** (每个视频3-8个)
- **22个实时告警** (高严重度事件)
- **完整参与者角色** (aggressor/victim/bystander)

## 项目结构

```
services/mock-streamer/
├── demo_server.py          # 演示服务器主文件
├── mock_streamer.py        # 模拟推流服务
├── demo_data_generator.py  # 演示数据生成器
└── demo_routes.py          # API路由
```

## 技术栈

- **后端**: FastAPI + WebSocket
- **前端**: Next.js + TypeScript + Tailwind CSS
- **数据**: 基于真实检测视频生成

## 下一步

1. 启动演示服务器
2. 访问 http://localhost:8000 查看状态
3. 访问 http://localhost:3000 查看前端 (如已启动)
4. 体验完整的视频流管理、实时告警、历史记录功能

---

**注意**: 此为演示模式，使用预检测视频模拟完整系统功能。
