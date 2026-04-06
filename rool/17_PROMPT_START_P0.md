# P0 启动提示词

把下面整段发给 Claude Code：

```text
请阅读根目录 CLAUDE.md、.claude/rules/ 下的规则，以及已安装的 skills。

现在开始执行 P0，但不要进入 P1 以后。

P0 目标：
- 建立完整 monorepo 基础目录结构
- 创建 apps/web、apps/api、services/stream-core、services/ai-runtime、packages/shared-types、packages/ui、docs、infra
- 为 web、api、stream-core、ai-runtime 创建最小可运行骨架
- 创建 README、docs/architecture.md、docs/api-contract.md、docker-compose.yml、env example
- 所有初始化脚本与配置必须可运行，不能是伪代码
- 输出可执行命令与当前阶段完成情况

工作规则：
1. 先给 plan，再改代码
2. 优先调用 /monorepo-architect skill
3. 不要扩展到真实流媒体解码、真实推理或真实压测
4. 需要跨模块改动时先更新 docs/architecture.md
5. 完成后输出：
   - 新建文件清单
   - 目录职责说明
   - 运行命令
   - 风险项
   - 下一阶段建议
```
