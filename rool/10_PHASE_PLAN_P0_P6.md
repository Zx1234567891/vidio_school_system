# 分阶段实施计划

## P0：仓库骨架与最小闭环
目标：
- 建立 monorepo 结构
- web/api/stream-core/ai-runtime 最小启动
- shared-types 与 ui 包就位
- Docker Compose 启动基础依赖
验收：
- 所有子项目能启动或构建
- README 有清晰命令
- docs/architecture.md 初版完成

## P1：流媒体核心 C++ 实现
目标：
- 完成 20 路流管理基础能力
- 完成线程池、有界队列、背压、重连、指标
- 支持 RTSP/文件输入
验收：
- stream-core 可编译
- 有基本单元测试
- 可返回 per-stream 状态和 metrics

## P2：AI Runtime 与事件协议
目标：
- 完成 detection/tracking/behavior/rule fusion 框架
- 统一事件 schema
- 支持角色区分
- 建立 ONNX 导出/加载路径
验收：
- 有真实可替换接口
- mock provider 可驱动全链路联调
- docs/api-contract.md 更新

## P3：FastAPI 控制面
目标：
- 实现 streams/events/reviews/clips/training/metrics API
- 接入 Redis 与 PostgreSQL
- 提供 WebSocket 实时告警
验收：
- OpenAPI 可用
- WebSocket 可推送
- 历史记录可查询与导出

## P4：Next.js 企业级前端
目标：
- 完成 overview/streams/alerts/history/review/settings/training 页面
- 联通真实 API
- 接收 WebSocket
验收：
- 页面路由完整
- 核心交互可用
- UI 风格统一

## P5：压测与稳定性
目标：
- 建立 benchmark 与 stress test
- 输出单路、多路、导出、重连等指标
验收：
- benchmark.md 完成
- 输出真实 p50 / p95 / p99
- 标注硬件环境

## P6：比赛交付包装
目标：
- 完成部署文档、演示脚本、比赛报告、模型训练说明
验收：
- 具备可演示与可答辩材料
- 文档完整、诚实、可复现
