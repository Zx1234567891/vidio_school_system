---
paths:
  - "apps/api/**/*.py"
  - "packages/shared-types/**/*"
---

# 后端规则

## 目标
实现 FastAPI 控制面，作为系统的业务入口和控制中心。

## 必须实现的接口域
1. streams
2. events
3. reviews
4. clips
5. training jobs
6. model versions
7. system health / metrics
8. websocket broadcast

## 关键约束
- 所有接口必须有明确 request / response schema
- 所有错误返回必须统一格式
- 所有导出任务、切片任务、训练任务都必须后台化
- 历史事件必须持久化
- Redis 仅作实时广播或缓存，不可单独作为历史事实来源

## 数据要求
- 事件可查询、可审核、可导出
- 审核修改要记录审计信息
- 导出支持 csv / json
- clip 下载地址必须可追踪

## 工程要求
- 按 router / service / repository / schema 分层
- 保持 OpenAPI 清晰
- 改接口时同步更新 docs/api-contract.md
