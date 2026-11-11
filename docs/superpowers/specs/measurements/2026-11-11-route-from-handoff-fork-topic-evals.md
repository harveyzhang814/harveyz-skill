# handoff 与 fork-topic 路由 eval 实跑记录 · 2026-11-11

支撑 `docs/superpowers/plans/2026-11-11-route-from-handoff-fork-topic.md` 的 Task 4。只记事实与复现方法。

分支 `feature/route-from-handoff-fork-topic`，实跑代码 `e898710`。被测 `claude-sonnet-5-5`，量具（grader）`claude-opus-5-5`，平台 `claude`，`--repeat 1`。所有 `runId` 在 `~/.hskill/skill-harness/<runId>/`。

画布命令全部由 `canvas-stub` 桩提供。harness 的环境变量白名单不含 `AGENT_CANVAS_*`，在清洗过的环境里真实的 `agent-canvas-ctl whoami` 报「未检测到目标画布」、退出码 1，所以 eval 里的 agent 够不到真实画布。

## 最终结果（代码 `e898710`）

```bash
node tools/skill-harness/cli.js run --skill coding/handoff --platform claude --mode native --model claude-sonnet-5-5 --repeat 1
node tools/skill-harness/cli.js grade <runId> --grader-model claude-opus-5-5
node tools/skill-harness/cli.js run --skill coding/fork-topic --platform claude --mode inject --model claude-sonnet-5-5 --repeat 1
node tools/skill-harness/cli.js grade <runId> --grader-model claude-opus-5-5
```

### handoff：`20261111-014850-e2a9`（native）

| eval | 名称 | 结果 |
|---|---|---|
| 5 | `author-canvas-routes-develop` | 6/6 pass |
| 6 | `author-canvas-named-codex` | 2/2 pass |
| 7 | `author-canvas-old-app-fallback` | 3/3 pass |
| 8 | `author-canvas-invalid-retry` | 3/3 pass |
| 4 | `accept-goes-to-author-worktree`（既有） | 6/6 pass |
| 0 | `author-high-to-low-model`（既有） | 5/5 fail，见下「既有的红」 |
| 1 | `author-cross-device-continuation`（既有） | 1 fail + 3 unavailable，见下「既有的红」 |
| 2 | `accept-catches-failing-criterion`（既有） | 3 pass、`record-appended-to-anchor-section` fail，见下「不稳定项」 |

### fork-topic：`20261111-014850-0264`（inject）

| eval | 名称 | 结果 |
|---|---|---|
| 3 | `fork-canvas-routes-think` | 6/6 pass |
| 4 | `fork-canvas-old-app-fallback` | 4/4 pass |
| 5 | `fork-canvas-named-model` | 2/2 pass |
| 0 | `fork-side-discussion-awaited`（既有） | 8/8 pass |
| 1 | `fork-background-new-topic`（既有） | 7/7 pass |
| 2 | `fork-long-conversation-early-facts`（既有） | 11/11 pass |

## 既有的红（分叉点上同样红，放行）

分叉点 `5678799`（`git merge-base staging HEAD`），用 `git worktree add --detach` 临时检出，harness 命令同上，跑完删除。

| 现象 | 本分支 | 分叉点 |
|---|---|---|
| handoff eval 0 全部断言 fail | `20261111-014850-e2a9`（另有 `20261111-012503-f23e`、`20261111-014107-33de`） | `20261111-014107-83f1`：同样 5/5 fail |
| handoff eval 1 | `20261111-014850-e2a9`：1 fail + 3 unavailable | `20261111-014107-83f1`：4/4 fail |
| fork-topic eval 0 `no-extrapolation` fail | `20261111-012504-bd4a`：fail；最终跑 `20261111-014850-0264`：pass | `20261111-012817-822f`：fail |

原因是同一类：handoff eval 0、1 的 prompt 没给出可读的 spec 或进度，agent 反问而不写文档（耗时 17–22 秒，与分叉点一致）。fork-topic eval 0 的失败原文（分叉点）：「所以失效方案不能依赖新的外部组件（如消息队列、外部 pub/sub）。」任务原文只有「我说过不接受引入新的外部服务」；该断言在最终跑里 pass，属于模型输出的波动。

## 不稳定项

- handoff eval 2 `record-appended-to-anchor-section`：`20261111-012503-f23e` fail、`20261111-014107-33de` pass、`20261111-014850-e2a9` fail；分叉点 `20261111-014107-83f1` pass。该 eval 不在本次验收范围内，三次结果摇摆，没有做归因。
- 分叉点上 fork-topic eval 1、2 的断言全部为 `unavailable`（grader 输出不是合法 JSON），不影响本分支的结果。

## 过程中发现并修掉的问题

1. **eval 的桩路径在 native 模式找不到**（`20261111-012503-f23e`）：handoff eval 4、5、6 用 cwd 相对路径 `evals/fixtures/...`，native 模式下 skill 装在 `<jail>/.claude/skills/handoff/`，agent 找桩脚本耗到 300 秒被杀（退出码 143）；eval 7、8 勉强在 255 秒、282 秒内通过。修法：新增 eval 5–8 的 prompt 改用 `<skill 目录>/evals/fixtures/...` 并说明两种模式下 `<skill 目录>` 在哪（`4f426ba`）。修后各格耗时 41–50 秒。既有 eval 4 的 prompt 没改，修后同样能跑通（`20261111-014107-33de` 245 秒、`20261111-014850-e2a9` 44 秒），耗时波动大。
2. **桩返回的节点 id 不是合法 uuid**（`20261111-014107-33de` 的 eval 8）：桩的 `whoami` 返回 `node-src`，agent 把它写进交接文档的 `source_node`，被 `validate-handoff.sh` 的完整性门禁拒绝，agent 停在建节点之前，`retried-routed` 与 `single-node` 因此 fail。修法：桩的两个节点 id 改成 uuid 形式（`e898710`）。
3. **fork-topic 的 eval 只能在 inject 模式跑**：它通过 `<skill 目录>/../handoff/evals/fixtures/canvas-stub/setup.sh` 引用桩，native 模式的 jail 里只拷了 fork-topic 目录，`../handoff` 不存在。inject 模式下提示里带 `This skill directory is: <路径>` 这一行，路径可解析。代价：fork-topic 这三条新 eval 没有在 native 模式验证过。

## 未覆盖

测试清单「验收标准」V1–V3 需要带路由命令的 App 发版后才能验证，不在本次范围内。
