# handoff 与 fork-topic 路由 eval 实跑记录 · 2026-11-11

支撑 `docs/superpowers/plans/2026-11-11-route-from-handoff-fork-topic.md` 的 Task 4。只记事实与复现方法。

分支 `feature/route-from-handoff-fork-topic`，最终代码 `5fc2b9e`。被测 `claude-sonnet-5-5`，量具（grader）`claude-opus-5-5`，平台 `claude`。所有 `runId` 在 `~/.hskill/skill-harness/<runId>/`。

画布命令全部由 `canvas-stub` 桩提供。harness 的环境变量白名单不含 `AGENT_CANVAS_*`，在清洗过的环境里真实的 `agent-canvas-ctl whoami` 报「未检测到目标画布」、退出码 1，所以 eval 里的 agent 够不到真实画布。

## 最终结果（代码 `5fc2b9e`）

```bash
node tools/skill-harness/cli.js run --skill coding/handoff --platform claude --mode native --model claude-sonnet-5-5 --repeat 1
node tools/skill-harness/cli.js run --skill coding/fork-topic --platform claude --mode inject --model claude-sonnet-5-5 --repeat 1
node tools/skill-harness/cli.js grade <runId> --grader-model claude-opus-5-5
```

### handoff：`20261111-021009-244e`（native）

| eval | 名称 | 结果 |
|---|---|---|
| 5 | `author-canvas-routes-develop` | 6/6 pass |
| 6 | `author-canvas-named-codex` | 2/2 pass |
| 7 | `author-canvas-old-app-fallback` | 3/3 pass |
| 8 | `author-canvas-invalid-retry` | 3/3 pass |
| 4 | `accept-goes-to-author-worktree`（既有） | 6/6 pass |
| 2 | `accept-catches-failing-criterion`（既有） | 4/4 pass |
| 0 | `author-high-to-low-model`（既有） | 5/5 fail，分叉点同样 fail，见「既有的红」 |
| 1 | `author-cross-device-continuation`（既有） | 4/4 fail，分叉点同样 fail，见「既有的红」 |

### fork-topic：`20261111-020755-23b5`（inject）

| eval | 名称 | 结果 |
|---|---|---|
| 3 | `fork-canvas-routes-think` | 6/6 pass |
| 4 | `fork-canvas-old-app-fallback` | 4/4 pass |
| 5 | `fork-canvas-named-model` | 2/2 pass |
| 2 | `fork-long-conversation-early-facts`（既有） | 11/11 pass |
| 0 | `fork-side-discussion-awaited`（既有） | 7 pass + `no-extrapolation` fail |
| 1 | `fork-background-new-topic`（既有） | 6 pass + `no-extrapolation` fail |

eval 0、1 的 fail 见下「波动项」，**未在 eval 1 上证明与分叉点等价**。

## 既有的红（分叉点上同样红，放行）

分叉点 `5678799`（`git merge-base staging HEAD`），用 `git worktree add --detach` 临时检出（harness 依赖通过指向主仓库 `node_modules` 的软链提供），harness 命令同上，跑完删除。

| 现象 | 本分支（`5fc2b9e` 上的跑） | 分叉点 |
|---|---|---|
| handoff eval 0 全部断言 fail | `20261111-021009-244e`：5/5 fail | `20261111-014107-83f1`：5/5 fail |
| handoff eval 1 全部断言 fail | `20261111-021009-244e`：4/4 fail | `20261111-014107-83f1`：4/4 fail |
| fork-topic eval 0 `no-extrapolation` fail | `20261111-020755-23b5`：fail | `20261111-012817-822f`：fail；`20261111-021422-8a0d`（repeat 3）：fail、fail、unavailable |

handoff eval 0、1 的原因：prompt 没给出可读的 spec 或进度，agent 反问而不写文档（耗时 17–26 秒，与分叉点一致）。fork-topic eval 0 的失败原文（分叉点）：「所以失效方案不能依赖新的外部组件（如消息队列、外部 pub/sub）。」任务原文只有「我说过不接受引入新的外部服务」。

## 波动项（没有做归因）

- **fork-topic eval 1 `no-extrapolation`**：本分支 4 次里 fail 2 次（`20261111-020424-1df8`、`20261111-020755-23b5`），pass 2 次（`20261111-012504-bd4a`、`20261111-014850-0264`）。分叉点 `20261111-021422-8a0d`（repeat 3）只有 1 次可判，pass；另外 2 次 grader 输出不是合法 JSON（`unavailable`），所以无法证明分叉点同样会 fail。fork-topic 在 inject 模式下 frontmatter 会被剥掉，本分支对非画布路径的正文改动只是把「输出」一节拆成两条路；没有证据表明这是回归，也没有证据排除。**这是一个未闭环的项**，由验收方判断。
- **fork-topic eval 2**：分叉点 `20261111-021422-8a0d` 的 repeat 1 有 `return-requested` fail；本分支 `20261111-020755-23b5` 全过，`20261111-020424-1df8` 有 `prompt-in-code-block`、`pointers-not-content` 两条 fail（grader 判代码块外有两句说明、判某句在描述文件内容）。
- **handoff eval 2 `record-appended-to-anchor-section`**：`20261111-012503-f23e` fail、`20261111-014107-33de` pass、`20261111-014850-e2a9` fail、`20261111-021009-244e` pass；分叉点 `20261111-014107-83f1` pass。该 eval 不在本次验收范围内。
- grader 对 fork-topic 的 eval 1、2 在分叉点多次返回非法 JSON（`unavailable`），不影响本分支的结果。

## 无效的跑

- `20261111-020424-e133`（handoff）：eval 2、4、5、6、7、8 全部 `Failed to authenticate: OAuth token revoked`，退出码 1，不作数；`20261111-020424-1df8`（fork-topic）的 eval 3 同样在最后一轮回复时报这个错（它在报错前已完成 routed 建节点、`put`、`send`）。认证随后恢复，上面的最终结果是认证恢复后重跑的。

## 过程中发现并修掉的问题

1. **eval 的桩路径在 native 模式找不到**（`20261111-012503-f23e`）：handoff eval 4、5、6 用 cwd 相对路径 `evals/fixtures/...`，native 模式下 skill 装在 `<jail>/.claude/skills/handoff/`，三格都跑到 300 秒被杀（退出码 143），eval 7、8 在 255、282 秒勉强通过。agent 的转录显示它在找 `setup.sh`（eval 5 用 `find ~ -maxdepth 6`，目录深度不够没找到）。修法：新增 eval 5–8 的 prompt 改用 `<skill 目录>/evals/fixtures/...` 并说明两种模式下 `<skill 目录>` 在哪（`4f426ba`），修后各格耗时 41–64 秒。既有 eval 4 的 prompt 没改，它在修复后的几次跑里耗时 35–245 秒、都通过；它超时的根因没有单独证实（同一 prompt 在 `20261111-014107-33de` 跑了 245 秒就通过）。
2. **桩返回的节点 id 不是合法 uuid**（`20261111-014107-33de` 的 eval 8）：桩的 `whoami` 返回 `node-src`，agent 把它写进交接文档的 `source_node`，被 `validate-handoff.sh` 的完整性门禁拒绝；这次 agent 在写完文档、跑门禁被拦后就停下，没有去建节点，`retried-routed` 与 `single-node` 因此 fail。修法：桩的两个节点 id 改成 uuid 形式（`e898710`）。
3. **fork-topic 的 eval 只能在 inject 模式跑**：它通过 `<skill 目录>/../handoff/evals/fixtures/canvas-stub/setup.sh` 引用桩，native 模式的 jail 里只拷了 fork-topic 目录，`../handoff` 不存在。inject 模式下提示里带 `This skill directory is: <路径>` 这一行，路径可解析。代价：fork-topic 这三条新 eval 没有在 native 模式验证过。

## 未覆盖

- 测试清单「验收标准」V1–V3 需要带路由命令的 App 发版后才能验证，不在本次范围内。
- 桩的 `get-node` 走兜底返回 `{}`，没有模拟「对方在线」的 `actions[]`；handoff 的 `send` 前检查对方是否在线这一步在桩环境里没有被真正验证。
- 两个 skill 都没有写「列表里没有 develop / think 类别」时怎么办，此时只会间接落到 `INVALID_ARGUMENT` 那条路。
