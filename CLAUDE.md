# Campus Guard AI - Root Claude Memory

@01_PROJECT_CONTEXT.md
@02_REPO_STRUCTURE.md
@03_GLOBAL_ENGINEERING_RULES.md
@10_PHASE_PLAN_P0_P6.md

> **项目规则已迁移到 `.claude/rules/`，项目技能已安装到 `.claude/skills/`**

## 根级核心要求
1. 这是一个参赛级项目，不是玩具 demo
2. 默认输出可运行代码，不要伪代码
3. 先给 plan，再实施
4. 所有改动要遵守模块边界
5. 所有接口改动同步更新文档
6. 不要把 20 路并发需求偷换成单路 demo
7. 不要编造 benchmark 结果
8. 对慢任务必须设计后台任务或异步流程
9. 历史记录和事件必须可追溯、可导出、可审核
10. ingest 线程不允许被慢推理阻塞

## 执行顺序
- 第一步：阅读根目录所有 `*.md`
- 第二步：执行 `16_PROMPT_BOOTSTRAP_AND_INSTALL_SKILLS.md` 中的提示词，将规则和 skills 安装到正确位置
- 第三步：执行 `17_PROMPT_START_P0.md`
- 第四步：按 `10_PHASE_PLAN_P0_P6.md` 逐阶段推进

## 已安装 Skills（可通过 /skill-name 调用）
- `/monorepo-architect` - 建立 monorepo 架构与基础目录
- `/cpp-stream-runtime` - 实现 C++20 流媒体核心
- `/fastapi-realtime` - 构建 FastAPI 控制面
- `/nextjs-wechat-admin` - 构建 Next.js 安防前端
- `/perf-benchmark` - 建立性能测试与压测
