# 让 Claude 自动归位并安装 skills 的总提示词

把下面整段直接发给 Claude Code：

```text
请先阅读项目根目录中的以下文件：
- CLAUDE.md
- 00_USE_ME_FIRST.md
- 01_PROJECT_CONTEXT.md
- 02_REPO_STRUCTURE.md
- 03_GLOBAL_ENGINEERING_RULES.md
- 04_RULE_FRONTEND.md
- 05_RULE_BACKEND.md
- 06_RULE_STREAM_CORE.md
- 07_RULE_AI_RUNTIME.md
- 08_RULE_API_EVENT_SCHEMA.md
- 09_RULE_UI_STYLE.md
- 10_PHASE_PLAN_P0_P6.md
- 11_SKILL_MONOREPO_ARCHITECT.md
- 12_SKILL_CPP_STREAM_RUNTIME.md
- 13_SKILL_FASTAPI_REALTIME.md
- 14_SKILL_NEXTJS_WECHAT_ADMIN.md
- 15_SKILL_PERF_BENCHMARK.md

完成阅读后，不要直接开始业务开发。你现在只做 Claude Code 初始化整理工作。

你的任务如下：

第一部分：输出理解
1. 先复述你理解到的：
   - 项目目标
   - 仓库结构
   - 技术栈
   - 不可违反的约束
   - P0~P6 阶段计划
2. 明确指出哪些文件应该继续保留在根目录，哪些应该迁移

第二部分：归位整理
请创建并整理以下目录与文件：

A. 创建目录：
- .claude/rules/
- .claude/skills/
- docs/

B. 迁移规则文件到 .claude/rules/：
- 04_RULE_FRONTEND.md            -> .claude/rules/frontend.md
- 05_RULE_BACKEND.md             -> .claude/rules/backend.md
- 06_RULE_STREAM_CORE.md         -> .claude/rules/stream-core.md
- 07_RULE_AI_RUNTIME.md          -> .claude/rules/ai-runtime.md
- 08_RULE_API_EVENT_SCHEMA.md    -> .claude/rules/api-event-schema.md
- 09_RULE_UI_STYLE.md            -> .claude/rules/ui-style.md

C. 安装 skills：
- 11_SKILL_MONOREPO_ARCHITECT.md     -> .claude/skills/monorepo-architect/SKILL.md
- 12_SKILL_CPP_STREAM_RUNTIME.md     -> .claude/skills/cpp-stream-runtime/SKILL.md
- 13_SKILL_FASTAPI_REALTIME.md       -> .claude/skills/fastapi-realtime/SKILL.md
- 14_SKILL_NEXTJS_WECHAT_ADMIN.md    -> .claude/skills/nextjs-wechat-admin/SKILL.md
- 15_SKILL_PERF_BENCHMARK.md         -> .claude/skills/perf-benchmark/SKILL.md

D. 根目录保留：
- CLAUDE.md
- 00_USE_ME_FIRST.md
- 01_PROJECT_CONTEXT.md
- 02_REPO_STRUCTURE.md
- 03_GLOBAL_ENGINEERING_RULES.md
- 10_PHASE_PLAN_P0_P6.md
- 16_PROMPT_BOOTSTRAP_AND_INSTALL_SKILLS.md
- 17_PROMPT_START_P0.md
- 18_PROMPT_PHASES_P1_TO_P6.md

E. 请更新根目录 CLAUDE.md：
- 保留对 01_PROJECT_CONTEXT.md、02_REPO_STRUCTURE.md、03_GLOBAL_ENGINEERING_RULES.md、10_PHASE_PLAN_P0_P6.md 的导入
- 删除对规则源文件和 skill 源文件的说明
- 增加一句：项目规则已迁移到 `.claude/rules/`，项目技能已安装到 `.claude/skills/`

第三部分：验证
1. 输出最终文件树
2. 列出已安装的 skills 名称
3. 说明后续可以直接调用的 slash 命令
4. 不要开始 P0 开发，只完成归位、安装和验证
5. 如果当前会话无法直接验证 slash 命令，也请清楚说明，并给出下一步建议
```
