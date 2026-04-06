# 使用说明

你现在拿到的是“单目录版 Claude Code 启动包”。

## 你的目标
你不需要手工把这些 markdown 放到不同目录。
你只需要把这些 `.md` 文件全部放到项目根目录，然后在 Claude Code 里执行提示词，让 Claude 自己完成：
- 读取根目录 `CLAUDE.md`
- 读取所有辅助 markdown
- 把规则移动到 `.claude/rules/`
- 把 skills 移动到 `.claude/skills/<skill-name>/SKILL.md`
- 更新根目录 `CLAUDE.md`
- 再开始 P0 架构搭建

## 使用顺序
1. 把本目录全部 `.md` 文件复制到你的项目根目录
2. 打开 Claude Code
3. 确认项目根目录有 `CLAUDE.md`
4. 将 `16_PROMPT_BOOTSTRAP_AND_INSTALL_SKILLS.md` 里的提示词整段发给 Claude
5. 等 Claude 归位完成后，再发 `17_PROMPT_START_P0.md` 里的提示词
6. 后续按 `18_PROMPT_PHASES_P1_TO_P6.md` 推进

## 注意
- 这些文件一开始都在根目录，是故意的
- 最终目录应由 Claude 自动整理
- 你只负责复制粘贴和批准修改
