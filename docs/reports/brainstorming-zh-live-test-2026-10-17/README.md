# brainstorming-zh 未合并源码实测记录

## 测试对象与执行方式

- 日期：2026-10-17。指定 worktree：`feature/superpowers-brainstorming-zh`。
- 技能入口：`skills/superpowers-rewrite/brainstorming-zh/SKILL.md`，版本 `0.1.27`，本次执行时 SHA-256：`ffbef3328f0f62a5d69293572dd5e32b86c5cfbcd9203cd8e8346f43a79d3f14`。
- 用 `run-turn.py` 调用真实 Claude Code CLI（Claude Sonnet 5.5）。每个场景独立会话，后续轮次用 `--resume` 延续。`--append-system-prompt-file` **直接读取上述 worktree 的 SKILL.md**；`--setting-sources ''` 禁用已安装技能配置。没有从安装目录复制技能。
- `--permission-mode bypassPermissions` 只用于隔离的虚构项目夹具；`--tools Read,Glob,Grep,Bash,Write,Edit` 允许保留实际工具调用记录。该工具白名单没有 `Task` 和 `Skill`，因此复杂任务的构建者独立检查及批准后调用 `superpowers:writing-plans` 均未在此宿主配置中实测。这是测试覆盖限制，不应解释成技能自身必然无法执行。
- 每条“用户”消息由测试执行者扮演虚构产品负责人输入；所有“批准”均为**模拟审批**。原始 JSONL 同时记录模型回复、工具调用和工具结果；`summary.json`、`transcript.md` 便于检索。`project/` 保存最后产物，`artifacts.json` 保存文件 SHA-256。

## 场景索引

| 场景 | 输入与检验重点 | 轮次 | 实际工具调用 | 结果 |
|---|---|---:|---:|---|
| [探索性新产品](scenarios/exploratory/transcript.md) | 邻里借物，先从经历发现需求；修订需求后重审；多方案；复杂 Spec | 10 | 20 | 形成记录与 Spec，模拟用户完整批准；没有产品代码 |
| [明确的现有代码需求](scenarios/defined/transcript.md) | 内存任务提醒加入稍后提醒；查现状；修订“完成取消”需求；方案与 Spec | 7 | 14 | 形成记录与 Spec，模拟用户完整批准；原产品代码未改 |
| [信息充分的小改动](scenarios/simple/transcript.md) | 精确指定标签标准化函数行为 | 1 | 4 | 直接改测试夹具的 `labels.py` 并运行示例验证 |

每个场景下的 `logs/turn-NN.user.txt`、`turn-NN.jsonl`、`turn-NN.summary.json`、`turn-NN.stderr` 保留逐轮输入、完整事件、提炼信息和错误输出。`transcript.md` 收录所有对话与工具调用索引；审批轮次见下表。

## 模拟审批轨迹

| 场景 | 轮次 | 送审或批准范围 |
|---|---:|---|
| 探索性 | 5 | R1–R18 需求清单首次送审 |
| 探索性 | 6 | 虚构用户修订 R8、R13、R17；其余逐项批准；模型重新送审受影响项及 D05–D06 |
| 探索性 | 7 | 虚构用户批准修订项；模型送审短信调度方案 P01 |
| 探索性 | 8 | 虚构用户选 P01 A，并补充 R19–R20；模型重审新需求及 P02–P03 |
| 探索性 | 9 | 虚构用户批准 R19–R20、P02/P03 和 D07–D11；模型写 Spec 并送审 |
| 探索性 | 10 | 虚构用户完整批准现有 Spec 与 D12–D25；模型仅记录审批 |
| 定义性 | 3 | 16 项需求清单首次送审 |
| 定义性 | 4 | 虚构用户批准其中 15 项，修订 #11；模型重新送审 #11 v2 |
| 定义性 | 5 | 虚构用户批准 #11 v2 与 I8/I9；模型送审 S1、S2 两组方案 |
| 定义性 | 6 | 虚构用户选择 S1=1B、S2=2A 并批准次要事项；模型写 Spec 并送审 |
| 定义性 | 7 | 虚构用户完整批准 Spec 与 I10–I13；模型仅记录审批 |
| 简单改动 | 1 | 用户给出完整、精确的直接修改请求；模型直接执行，未另设审批轮次 |

## 仓库验证

`npm test` 的[完整输出](npm-test.log)与[退出码](npm-test.exit)已保存：退出码 `1`。通用 `SKILL.md` 存在、frontmatter、版本和目录名检查通过。自定义 Python 套件中 11 个通过、3 个失败：`forge-doc` 缺少 `markdown` 模块；`browser-fetch` 和 `hub` 的测试环境缺失依赖或配置而失败。日志没有显示本次新增 `brainstorming-zh` 自带测试失败；该技能当前没有自带自动化测试。运行后清理了测试生成的两个未跟踪 `.venv` 目录。

## 审计

独立 Agent 的结论见 [independent-audit.md](independent-audit.md)。审计应以原始日志和 Spec/记录为准；摘要是检索辅助。

## 0.1.28 修复后复测

上述三个场景与独立审计针对 0.1.27。源码更新到 0.1.28 后，另做了 [7 轮聚焦复测](scenarios/regression_028/README.md)，保留逐轮对话、22 次工具调用、模拟审批与全部产物。独立 Agent 再次只读审计：原有两项问题在该场景已修复；新发现每日短信量推断错误和取消与实际发送之间的竞态口径未定。此次 `npm test` 的[输出](npm-test-028.log)与[退出码](npm-test-028.exit)也已保存，结果仍为失败，不能归因于 brainstorming-zh。

0.1.29 的一次[中断尝试](scenarios/regression_029/README.md)保留了已完成的首轮和部分夹具文件，不作为通过证据。以稳定的 0.1.30 源码完成的[三轮复测](scenarios/regression_030/README.md)确认了两项旧问题的修订和审批同步，但独立审计发现最终 Spec 的 AC-03 与并发流程相矛盾，故本轮不能判为完全通过。

0.1.31 的[三轮复测](scenarios/regression_031/README.md)期间活动源码升级为 0.1.32，不能作为稳定 0.1.31 的完整通过证据。产物仍出现 AC-03 与 AC-28 冲突，独立审计还发现 AC-26 的中断结果冲突。随后用冻结的 0.1.32 源码做了[单轮只读补查](scenarios/regression_031_frozen/README.md)：模型暂停制定计划并发现 AC-26 等问题，但仍漏掉 AC-03。

0.1.37 提交前的仓库验证：`node --test tests/skill-portability.test.mjs` 的 15 项全部通过；`npm test` 的[输出](npm-test-037.log)与[退出码](npm-test-037.exit)已保存，退出码仍为 `1`。失败发生在其他测试套件，包括缺少 Python `markdown`、浏览器权限和异步测试支持，不能直接归因于 brainstorming-zh；本次没有对 0.1.37 另做完整 CLI 场景复测。
