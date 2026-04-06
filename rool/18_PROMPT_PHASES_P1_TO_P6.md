# 后续阶段提示词

## P1：实现 C++ 流媒体核心

```text
请阅读根目录 CLAUDE.md、.claude/rules/ 与已安装 skills。
现在执行 P1，只实现 services/stream-core 和其接口契约。

目标：
- 支持最多 20 路并发流管理
- 完成固定线程池、有界队列、背压、重连、指标
- 支持 RTSP / 文件输入
- 提供给上层调用的清晰接口

要求：
- 优先调用 /cpp-stream-runtime
- ingest 线程不阻塞
- 队列满时执行明确的丢帧或采样策略
- 每路流可单独 start/stop/restart
- 完成后更新 docs/architecture.md
- 输出测试情况与下一步建议
```

## P2：实现 AI Runtime 与事件协议

```text
请执行 P2，只实现 services/ai-runtime 和 shared event schema。

目标：
- 建立 detection / tracking / behavior / rule fusion 的可插拔 pipeline
- 定义统一事件输出协议
- 支持多人交互行为的参与者与角色区分
- 建立 ONNX 导出与加载路径

要求：
- 先把接口和 schema 做对
- 不把多人交互偷换成单标签分类
- 更新 packages/shared-types 与 docs/api-contract.md
- 输出当前 baseline provider 方案和可替换点
```

## P3：实现 FastAPI 控制面

```text
请执行 P3，只实现 apps/api 的真实业务层。

目标：
- 接入 stream-core 和 ai-runtime
- 提供 REST + WebSocket
- 提供 streams、events、reviews、clips、training、metrics 接口
- 建立 Redis + PostgreSQL 存储链路

要求：
- 优先调用 /fastapi-realtime
- 慢任务后台化
- 事件与历史记录必须持久化
- 所有接口返回统一错误格式
- 更新 docs/api-contract.md
```

## P4：实现 Next.js 企业级前端

```text
请执行 P4，只实现 apps/web 的真实前端。

目标：
- 做出企业级、克制、现代、微信气质但不是聊天产品的安防前端
- 与真实 API 联通
- 接收 WebSocket 告警
- 支持多路矩阵、事件详情、审核修改、导出入口

要求：
- 优先调用 /nextjs-wechat-admin
- 页面包括 overview / streams / alerts / history / review / settings / training
- 保证 loading / empty / error 状态齐全
- 不做长期假数据页面
```

## P5：实现压测与稳定性验证

```text
请执行 P5。

目标：
- 建立真实性能测试
- 覆盖单路延迟、多路并发、稳定性、导出能力
- 给出可复现 benchmark 流程

要求：
- 优先调用 /perf-benchmark
- 输出真实命令、真实日志、真实统计
- 输出 p50 / p95 / p99
- 标注硬件环境
```

## P6：完成比赛交付包装

```text
请执行 P6。

目标：
- 把项目整理成可演示、可答辩、可提交的作品
- 输出文档、演示脚本、部署说明、接口说明、测试说明

要求：
- 完成 README、competition-report、deployment、demo-script、model-retrain、benchmark 文档
- 明确区分已实现、待优化、风险项
- 不夸大效果
```
