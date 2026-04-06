---
name: monorepo-architect
description: 为校园安防视频系统建立 monorepo 架构、基础目录、共享契约、docker compose 与阶段化任务拆分
disable-model-invocation: true
---

你的任务是为当前仓库建立一个真正可落地的跨语言工程骨架。

目标：
- 创建 apps/web、apps/api、services/stream-core、services/ai-runtime、packages/shared-types、packages/ui、docs、infra
- 补齐 README、architecture.md、api-contract.md、docker-compose.yml、env example
- 所有目录必须能解释清楚职责
- 先保证最小可运行闭环，再扩展高级能力

硬性规则：
1. 不写伪代码骨架；所有初始化文件都要可运行
2. 所有服务必须有统一命名规则、日志规则、配置规则
3. 共享契约必须独立目录，不允许前后端各自定义重复 DTO
4. 需要输出 phase 拆分结果：P0~P6
5. 完成后输出：
   - 创建了哪些目录和文件
   - 当前能跑通的命令
   - 下一阶段最优先事项
