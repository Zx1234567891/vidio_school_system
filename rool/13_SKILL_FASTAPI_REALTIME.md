---
name: fastapi-realtime
description: 构建 FastAPI 控制面，提供流管理、事件查询、WebSocket 实时告警、日志修改、导出、训练任务与系统测试接口
disable-model-invocation: true
---

实现 apps/api。

目标：
- 提供 REST API + WebSocket
- 管理 streams、events、clips、reviews、train-jobs、model-versions、system-health
- 对接 Redis 和 PostgreSQL
- 对接 C++ stream-core 与 Python ai-runtime
- 自动生成 OpenAPI 文档

必须实现的接口类型：
1. Stream 管理
   - CRUD
   - start / stop / restart
   - health / metrics
2. Event 中心
   - list / filter / detail
   - review / relabel / severity adjust
   - export csv / json
3. Clip 与回放
   - download
   - export
4. WebSocket
   - 实时告警广播
   - 实时流状态广播
5. Training
   - create job
   - query job
   - list model versions
6. Benchmark / test
   - replay test
   - stress test entry
   - metrics snapshot

约束：
- API schema 显式、稳定、可复用
- 事件必须包含 participants 和 roles 字段
- 历史记录必须可持久化
- 导出、切片、训练等慢任务要走后台任务
- 所有新增接口同步更新 api-contract.md
