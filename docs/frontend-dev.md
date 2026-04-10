# Campus Guard AI - 前端开发文档

## 1. 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 14.1.0 | React 全栈框架 |
| React | 18.2.x | UI 渲染 |
| TypeScript | 5.3.x | 类型安全 |
| Tailwind CSS | 3.4.x | 原子化样式 |
| Axios | - | HTTP 请求 |
| Lucide React | - | 图标库 |

## 2. 项目结构

```
apps/web/
├── app/
│   ├── (dashboard)/              # Dashboard 路由组
│   │   ├── layout.tsx            # 侧边栏 + 主内容区布局
│   │   ├── page.tsx              # 系统概览页（首页）
│   │   ├── globals.css           # Dashboard 全局样式
│   │   ├── streams/page.tsx      # 视频流管理页
│   │   ├── alerts/page.tsx       # 实时告警页
│   │   ├── history/page.tsx      # 历史记录页
│   │   ├── review/page.tsx       # 事件审核页
│   │   ├── training/page.tsx     # 模型训练页
│   │   └── settings/page.tsx     # 系统设置页
│   ├── layout.tsx                # 根布局
│   └── globals.css               # 全局样式
├── lib/
│   └── api.ts                    # API 客户端（Axios 封装）
├── types/
│   └── index.ts                  # TypeScript 类型定义
├── next.config.js                # Next.js 配置
├── tailwind.config.js            # Tailwind 配置
├── tsconfig.json                 # TypeScript 配置
└── package.json                  # 依赖管理
```

## 3. 路由与页面

### 3.1 路由表

| 路由 | 组件 | 功能 |
|------|------|------|
| `/` | `page.tsx` | 系统概览仪表盘，展示统计卡片、风险分布、最近事件 |
| `/streams` | `streams/page.tsx` | 视频流管理，网格展示所有流，支持启动/停止/重启 |
| `/alerts` | `alerts/page.tsx` | 实时告警列表，WebSocket 推送 |
| `/history` | `history/page.tsx` | 历史记录查询，支持多条件筛选与导出 |
| `/review` | `review/page.tsx` | 事件审核，支持确认/拒绝/修改/忽略 |
| `/training` | `training/page.tsx` | 模型训练任务管理 |
| `/settings` | `settings/page.tsx` | 系统配置 |

### 3.2 布局结构

```
┌──────────────────────────────────────────────┐
│ ┌──────────┐  ┌──────────────────────────┐   │
│ │          │  │                          │   │
│ │ Sidebar  │  │    Main Content          │   │
│ │          │  │                          │   │
│ │ - 概览   │  │    (各页面内容)           │   │
│ │ - 视频流  │  │                          │   │
│ │ - 告警   │  │                          │   │
│ │ - 历史   │  │                          │   │
│ │ - 审核   │  │                          │   │
│ │ - 训练   │  │                          │   │
│ │ - 设置   │  │                          │   │
│ │          │  │                          │   │
│ └──────────┘  └──────────────────────────┘   │
└──────────────────────────────────────────────┘
```

- 侧边栏可折叠（展开 256px / 折叠 64px）
- 主内容区自适应宽度，内边距 24px

## 4. 核心组件说明

### 4.1 DashboardLayout (`layout.tsx`)

Dashboard 布局组件，包含：
- **侧边栏导航**：7 个导航项，使用 Lucide 图标
- **当前路由高亮**：通过 `usePathname()` 判断
- **折叠控制**：`sidebarOpen` 状态切换

```tsx
const navItems = [
  { href: '/', label: '概览', icon: LayoutDashboard },
  { href: '/streams', label: '视频流', icon: Video },
  { href: '/alerts', label: '实时告警', icon: AlertTriangle },
  { href: '/history', label: '历史记录', icon: History },
  { href: '/review', label: '审核', icon: CheckCircle },
  { href: '/training', label: '模型训练', icon: Brain },
  { href: '/settings', label: '设置', icon: Settings },
];
```

### 4.2 OverviewPage (`page.tsx`)

首页仪表盘，功能包括：
- **统计卡片**：总视频流、检测事件、实时告警、系统状态
- **事件风险分布**：高/中/低风险分色展示
- **最近检测事件列表**：展示最新 5 条事件
- **演示模式提示**：蓝色提示条

数据源：
- 优先请求 `/demo/stats` 和 `/demo/events`
- 降级请求 `/metrics/dashboard`

### 4.3 StreamsPage (`streams/page.tsx`)

视频流管理页，功能包括：
- **视频流卡片网格**：1-3 列响应式布局
- **快照轮询播放器 (`SnapshotPlayer`)**：定时拉取 JPEG 快照模拟视频预览
  - 最高 10fps，最低间隔 100ms
  - 突破浏览器 6 并发连接限制
- **流状态标签**：运行中/已停止/错误等
- **行为检测标签**：右上角显示异常行为类型和严重级别
- **操作按钮**：启动、停止、重启、删除

### 4.4 SnapshotPlayer 组件

```tsx
function SnapshotPlayer({ streamId, fps }: { streamId: string; fps: number }) {
  // 定时请求单帧 JPEG 替代 MJPEG 长连接
  // 接口: GET /api/v1/streams/{streamId}/snapshot?_t={seq}
  // 间隔: max(1000/min(fps,10), 100) ms
}
```

## 5. API 客户端

### 5.1 配置 (`lib/api.ts`)

```typescript
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8888/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});
```

- **BaseURL 环境变量**：`NEXT_PUBLIC_API_URL`
- **默认地址**：`http://localhost:8888/api/v1`
- **响应拦截器**：自动提取 `response.data`，错误时返回 `Error` 对象

### 5.2 API 调用模式

所有页面采用「优雅降级」模式：
1. 先请求演示模式 API（`/demo/*`）
2. 失败后降级到正式 API（`/streams`、`/events` 等）
3. 全部失败则显示"连接失败"提示

## 6. TypeScript 类型系统

### 6.1 核心类型 (`types/index.ts`)

```typescript
// 视频流
interface Stream {
  id: string;
  name: string;
  url: string;
  input_type: 'rtsp' | 'rtmp' | 'file';
  status: 'init' | 'connecting' | 'running' | 'degraded' | 'reconnecting' | 'stopped' | 'error';
  target_fps: number;
  width?: number;
  height?: number;
  fps?: number;
  total_frames_decoded: number;
  total_dropped_frames: number;
  reconnect_count: number;
}

// 事件
interface Event {
  id: string;
  stream_id: string;
  event_type: string;
  category: 'high_risk' | 'sensitive' | 'suspicious' | 'normal';
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'pending' | 'confirmed' | 'false_positive' | 'resolved' | 'ignored';
  confidence: number;
  participants?: Array<{ track_id: string; bbox: number[]; confidence: number }>;
  roles?: { aggressor?: string[]; victim?: string[]; bystander?: string[]; mutual?: string[] };
}

// 告警
interface Alert {
  id: string;
  event_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  stream_id: string;
  timestamp: string;
  is_read: boolean;
}

// 统一响应
interface ApiResponse<T> { code: number; message: string; data: T; }

// 分页数据
interface PaginatedData<T> { items: T[]; total: number; page: number; page_size: number; total_pages: number; }
```

## 7. UI 设计规范

### 7.1 设计原则

- **风格定位**：大气、现代、企业级
- **视觉参考**：微信的克制、秩序、留白与圆角感
- **配色方案**：以灰白为主，蓝色为强调色

### 7.2 色彩系统

| 用途 | 颜色 |
|------|------|
| 主色 | `blue-600` (#2563EB) |
| 背景 | `gray-50` (#F9FAFB) |
| 卡片背景 | `white` |
| 边框 | `gray-200` |
| 高风险 | `red-600` |
| 中风险 | `orange-600` |
| 低风险 | `yellow-600` |
| 成功/运行中 | `green-600` |

### 7.3 组件样式规范

| 组件 | 样式 |
|------|------|
| 卡片 | `bg-white rounded-xl border border-gray-200` |
| 按钮（主要） | `bg-blue-600 text-white rounded-lg hover:bg-blue-700` |
| 按钮（危险） | `bg-red-50 text-red-600 rounded-lg hover:bg-red-100` |
| 标签/Badge | `px-2 py-1 text-xs rounded-full` |
| 状态指示灯 | 红色脉冲圆点 `animate-pulse` + "LIVE" 文字 |

### 7.4 响应式断点

| 断点 | 宽度 | 视频流卡片列数 |
|------|------|---------------|
| 默认 | < 768px | 1 列 |
| `md` | ≥ 768px | 2 列 |
| `lg` | ≥ 1024px | 3 列 |

## 8. 开发与构建

### 8.1 环境变量

```env
NEXT_PUBLIC_API_URL=http://localhost:8888/api/v1
```

### 8.2 常用命令

```bash
cd apps/web

# 开发模式
pnpm dev           # 启动开发服务器 (端口 3000)

# 构建
pnpm build         # 生产环境构建
pnpm start         # 启动生产服务

# 代码检查
pnpm lint          # ESLint 检查
pnpm type-check    # TypeScript 类型检查
```

### 8.3 依赖安装

```bash
cd apps/web
pnpm install
```

## 9. WebSocket 实时告警

### 9.1 连接方式

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

### 9.2 消息协议

**客户端发送**：
```json
// 心跳
{ "type": "ping", "timestamp": 1704067200000 }

// 订阅频道
{ "type": "subscribe", "channels": ["alerts", "stream_status"] }
```

**服务器推送**：
```json
// 告警
{ "type": "alert", "payload": { "event_id": "evt_abc123", "severity": "critical", "message": "检测到打架事件" }, "timestamp": "..." }

// 流状态变更
{ "type": "stream_status", "payload": { "stream_id": "stream_0001", "status": "running" } }
```

## 10. 已知限制与后续计划

| 项目 | 当前状态 | 计划 |
|------|---------|------|
| 真实视频预览 | 快照轮询模式 | 接入 WebRTC 或 HLS |
| 添加流对话框 | 按钮占位 | 实现表单弹窗 |
| 告警声音提醒 | 未实现 | 加入浏览器通知 |
| 多语言支持 | 仅中文 | 加入 i18n |
| 暗色模式 | 未实现 | Tailwind dark mode |
| 流布局自定义 | 固定网格 | 拖拽式布局 |
