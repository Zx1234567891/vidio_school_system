# Campus Guard AI - 完整演示指南

## 概述

本演示使用 `D:\vidio_school_system\sucai\output` 中已检测好的视频数据，模拟完整的校园安防系统运行状态。

## 检测视频列表

| 视频文件 | 行为标签 | 严重程度 | 类别 |
|---------|---------|---------|------|
| 打架_检测.mp4 | 打架斗殴 | 高 | 高风险异常 |
| 校园霸凌_检测.mp4 | 校园霸凌 | 高 | 高风险异常 |
| 摔倒_检测.mp4 | 摔倒 | 高 | 高风险异常 |
| 轻生_检测.mp4 | 疑似轻生 | 高 | 高风险异常 |
| 破坏公共设施_检测.mp4 | 破坏设施 | 高 | 高风险异常 |
| 吸烟_检测.mp4 | 吸烟 | 中 | 敏感行为 |
| 低头看手机_检测.mp4 | 低头看手机 | 中 | 敏感行为 |
| 摄像头遮挡_检测.mp4 | 摄像头遮挡 | 中 | 敏感行为 |
| 异常徘徊_检测.mp4 | 异常徘徊 | 低 | 可疑行为 |
| 翻越围栏_检测.mp4 | 翻越围栏 | 低 | 可疑行为 |

## 快速启动

### 1. 启动演示服务器

**Windows:**
```bash
D:\vidio_school_system\start_demo.bat
```

**Linux/Mac:**
```bash
cd /path/to/vidio_school_system
bash start_demo.sh
```

或者手动启动:
```bash
cd services/mock-streamer
python demo_server.py
```

### 2. 启动前端 (可选)

```bash
cd apps/web
npm install  # 首次运行
npm run dev
```

访问 http://localhost:3000 查看前端界面

## 演示功能

### API端点

| 端点 | 方法 | 描述 |
|-----|------|------|
| `http://localhost:8080/` | GET | 演示状态页面 |
| `http://localhost:8080/health` | GET | 健康检查 |
| `/api/v1/demo/streams` | GET | 获取所有视频流 |
| `/api/v1/demo/streams/{id}/start` | POST | 启动推流 |
| `/api/v1/demo/streams/{id}/stop` | POST | 停止推流 |
| `/api/v1/demo/events` | GET | 获取事件列表 |
| `/api/v1/demo/alerts` | GET | 获取告警列表 |
| `/api/v1/demo/stats` | GET | 获取统计数据 |
| `ws://localhost:8080/ws` | WebSocket | 实时告警推送 |

### 演示数据

系统自动生成以下模拟数据:
- **视频流**: 10路 (对应10个检测视频)
- **检测事件**: 每个视频3-8个随机事件
- **实时告警**: 高严重度事件自动生成告警
- **统计数据**: 事件分布、审核状态等

## 演示场景

### 场景1: 查看系统概览
1. 访问 `http://localhost:8080/`
2. 查看系统状态和API端点
3. 查看已加载的检测视频列表

### 场景2: 管理视频流
```bash
# 获取所有流
curl http://localhost:8080/api/v1/demo/streams

# 启动特定流
curl -X POST http://localhost:8080/api/v1/demo/streams/stream_001/start

# 停止流
curl -X POST http://localhost:8080/api/v1/demo/streams/stream_001/stop
```

### 场景3: 查看事件和告警
```bash
# 获取事件列表
curl http://localhost:8080/api/v1/demo/events

# 获取告警列表
curl http://localhost:8080/api/v1/demo/alerts

# 获取统计数据
curl http://localhost:8080/api/v1/demo/stats
```

### 场景4: WebSocket实时告警
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
    console.log('已连接');
    ws.send(JSON.stringify({ type: 'subscribe', channels: ['alerts'] }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
};
```

## 项目结构

```
services/mock-streamer/
├── demo_server.py          # 演示服务器主文件
├── mock_streamer.py        # 模拟推流服务
├── demo_data_generator.py  # 演示数据生成器
└── demo_routes.py          # API路由
```

## 技术说明

### 模拟推流原理
- 读取检测好的视频文件
- 按原始帧率循环播放
- 模拟RTSP推流状态管理
- 支持启动/停止/状态查询

### 演示数据生成
- 基于视频行为标签生成对应事件
- 随机生成时间戳、置信度、边界框
- 自动生成参与者角色(aggressor/victim/bystander)
- 高严重度事件自动生成告警

### WebSocket推送
- 每5秒推送一次随机未确认告警
- 支持ping/pong心跳
- 支持频道订阅

## 扩展开发

### 添加新的检测视频
1. 将视频放入 `sucai/output/` 目录
2. 命名格式: `{行为标签}_检测.mp4`
3. 在 `mock_streamer.py` 的 `VIDEO_BEHAVIOR_MAP` 中添加映射
4. 重启演示服务器

### 修改演示数据
编辑 `demo_data_generator.py`:
- 修改 `BEHAVIORS` 定义新的行为类型
- 调整 `generate_events_from_video` 生成逻辑
- 修改事件数量、时间分布等参数

## 注意事项

1. 演示模式使用静态视频文件，非真实摄像头流
2. 事件数据为随机生成，仅用于演示UI功能
3. WebSocket告警为模拟推送，非真实检测结果
4. 视频文件较大，首次加载可能需要时间

## 下一步

- 集成真实AI Runtime进行检测
- 连接真实RTSP摄像头流
- 实现真实的事件检测和告警
- 添加用户认证和权限管理
