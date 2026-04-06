# 全局工程规则

## 总体原则
1. 先保证最小闭环，再逐步增强
2. 先稳定模块边界，再写大量功能
3. 先定义契约，再跨模块联动
4. 所有队列必须有界
5. 慢任务必须异步化
6. 任何性能数字必须来自真实脚本和真实日志

## 开发风格
- 文档和注释使用中文
- 标识符、文件名、接口名使用英文
- 默认输出完整可运行代码
- 对关键组件同时写测试
- 不保留大量 TODO 占位
- 不无理由引入超重依赖

## 版本与交付
每个阶段结束时必须：
1. 更新 README
2. 更新 docs/architecture.md 或 docs/api-contract.md
3. 输出已完成项、未完成项、风险项
4. 给出下一阶段建议
5. 运行可运行的测试或构建命令

## 性能规则
- ingest 线程不得因慢推理阻塞
- 所有帧队列必须设置容量上限
- 队列满时必须明确采用丢旧帧、跳帧或采样策略
- 单路与多路策略必须分层考虑
- 浏览器端不要求 20 路同时满帧；应采用矩阵降级策略

## 数据与事件规则
事件必须至少包含：
- eventId
- streamId
- trackId
- timestamp
- eventType
- severity
- confidence
- participants
- roles
- sourceFrameRef
- clipRef
- reviewStatus

多人交互行为必须支持：
- aggressor
- victim
- bystander
- mutual participants

## 前后端约束
- 前端只消费 API，不拼接隐式字段
- 后端只按 schema 返回，不临时口头约定
- 修改接口时同步更新 shared-types 与 docs/api-contract.md

## 禁止事项
- 不要把多人交互问题简化成单标签分类
- 不要把历史记录只保存在 Redis Pub/Sub
- 不要把系统写成只能处理单文件离线视频的 demo
- 不要把根目录规则文件删除而不更新 CLAUDE.md
