# handoff 与 fork-topic 建节点改走路由引擎 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development 逐项实施；用 `- [ ]` 跟踪步骤。

**Goal:** 在 Agent Canvas 画布节点里，handoff 建接手节点改用 `create-routed-pty-node --category develop`，fork-topic 改为用 `create-routed-pty-node --category think` 建节点并发出 prompt；不在画布里时两者行为不变。

**Architecture:** 只改两个 skill 的正文：handoff 改 author 第 6 步，fork-topic 新增「在画布里」分支。字段标准、证据要求和 description 段落一律以 `describe-node-route-category` 的输出为准，skill 里不抄写。行为用两类测试锁定：`node:test` 静态测试锁文本契约（版本、hash、命令名、退回规则）；skill-harness eval 配一个可切换模式的画布命令桩，测 agent 的实际调用。

**Tech Stack:** Markdown skill、bash（画布命令桩）、node:test、bats（`npm test`）、`tools/skill-harness`（eval 运行与评分）。

**Requirements:** 已获批测试清单 `docs/superpowers/specs/2026-11-11-route-from-handoff-fork-topic-test-plan.md`（用例 H1–H5、F1–F4、验收标准 V1–V3），来源为 agent-canvas 画布节点 `ce78124f` 的澄清讨论。路由命令契约见 agent-canvas 仓库 `docs/superpowers/specs/2026-11-10-node-routing-category-params-design.md` §4.2–§4.4。

## Global Constraints

- 改动只在 harveyz-skill 仓库，本分支 `feature/route-from-handoff-fork-topic`。不改 `skills/agent-canvas/agent-canvas-control/`，不改 Agent Canvas App。
- 版本：handoff `1.18.1` → `1.19.0`；fork-topic `1.0.0` → `1.1.0`。`skills-index.json` 的 `contentVersion` 与 `contentHash` 同步更新，hash 算法与 `tests/handoff-worktree.test.mjs` 的 `hash()` 相同：把 `version:` 行替换为 `version: __HASH_PLACEHOLDER__` 后取 sha256 前 16 位。
- 命令名字面值：`list-node-route-categories`、`describe-node-route-category`、`create-routed-pty-node`。类别字面值：handoff 用 `develop`，fork-topic 用 `think`。
- 退回 `create-pty-node` 时的 `--task-type`：handoff 用 `execute`，fork-topic 用 `plan`。
- 退回条件：路由命令报未知子命令（旧版 App：退出码 1，stderr 以 `未知子命令:` 开头），或报 `PRECONDITION_FAILED`。`INVALID_ARGUMENT` 只能按报错修正后重试路由，不退回。用户点名节点类型或模型时直接用 `create-pty-node`，不走路由。
- skill 正文不出现任何路由字段名或 description 段名（`openDecisions`、`precedent`、`detailDifficulty`、`impact`、`scale`、`openness`、`informationGap`、`reasoningDepth`、`## 目标`、`## 问题`）：以 describe 为准，不在 skill 里形成第二真相源。
- handoff 第 9 步派发消息只含寻址信息，不变。路由的 `--description` 是节点说明，不是派发消息。
- fork-topic 在画布里不调用 `link-nodes`，不加 `--expect-reply`；prompt 临时文件写在仓库外（`mktemp`）。
- 不 `npm publish`，不合并到 `staging`（合并由交出方在用户明确要求后用 `scripts/merge-to-staging.sh` 完成）。

## Review Focus

- 当前已安装的 App 没有路由命令 → 新版 skill 部署后实际走的是退回路径：只建一个节点，并告诉用户已退回（H3、F3；Task 2、Task 3 的 eval 与静态测试）。
- 第一次路由被 `INVALID_ARGUMENT` 拒绝 → 修正后重试路由，不换 `create-pty-node`，最终只建一个节点（H4；Task 2）。
- 不在画布里 → 两个 skill 的行为与改动前一致（H5、F2；Task 2、Task 3 用现有 eval 回归）。
- 用户点名 codex 或某个模型 → 不调用任何路由命令（H2、F4；Task 2、Task 3）。
- fork-topic 在画布里 → 不建关系，临时文件不落在仓库里（F1；Task 3）。

---

### Task 1: 画布命令桩 fixture

**Prerequisites:** 无

**Files:**
- Create: `skills/coding/handoff/evals/fixtures/canvas-stub/setup.sh`
- Create: `skills/coding/handoff/evals/fixtures/canvas-stub/describe-develop.json`
- Create: `skills/coding/handoff/evals/fixtures/canvas-stub/describe-think.json`
- Test: `tests/canvas-stub.test.mjs`

**Interfaces:**
- Produces: `bash setup.sh <routed|old-app|reject-once>`。未知模式退出码 2。在 `mktemp -d` 建的目录里（刻意建在 eval jail 之外，理由同 `accept-worktree/setup.sh`）生成以下内容，并在 stdout 逐行打印 `STUB_BIN=<绝对路径>`、`STUB_LOG=<绝对路径>`、`WORKTREE=<绝对路径>`：
  - `bin/agent-canvas-ctl`、`bin/agent-canvas-arrange`：每次调用向 `STUB_LOG` 追加一行 `<命令文件名> <参数逐个 printf %q>`。
  - 一个 git 仓库，加上它在 `feature/slugify-numbers` 分支上的链接 worktree（即 `WORKTREE`）。worktree 里已提交 `docs/superpowers/specs/2026-11-11-slugify-numbers-test-plan.md` 与 `src/slugify.js`，供 handoff eval 当作已建好的交接工作区。
- 桩的应答：

| 子命令 | routed | old-app | reject-once |
|---|---|---|---|
| `whoami` | `{"id":"node-src","title":"发起节点","kind":"pty"}` | 同左 | 同左 |
| `list-node-route-categories` | `{"configSource":"builtin","categories":[{"name":"develop","description":"产出是代码改动","taskType":"execute"},{"name":"think","description":"产出是结论、对比或 spec","taskType":"plan"}]}` | 退出码 1，stderr `未知子命令: list-node-route-categories` | 同 routed |
| `describe-node-route-category <c>` | 输出 `describe-<c>.json`；类别不存在时退出码 1，stderr 以 `INVALID_ARGUMENT` 开头 | 退出码 1，stderr `未知子命令: describe-node-route-category` | 同 routed |
| `create-routed-pty-node` | `{"nodeId":"node-new","startRequested":true,"routeId":"route-1","decision":{"category":"<--category 的值>","final":{"nodeType":"claude-code","tier":"standard","model":"sonnet","effort":"medium"}}}` | 退出码 1，stderr `未知子命令: create-routed-pty-node` | 第 1 次：退出码 1，stderr `INVALID_ARGUMENT: params 缺少字段 scale`；之后同 routed |
| `create-pty-node` | `{"nodeId":"node-new","startRequested":true}` | 同左 | 同左 |
| `link-nodes` / `send` / `search-nodes` | `{"relationId":"rel-1"}` / `{"messageId":"msg-1","status":"queued"}` / `{"results":[]}` | 同左 | 同左 |
| 其他子命令、`agent-canvas-arrange` 任意子命令 | `{}`，退出码 0 | 同左 | 同左 |

- `describe-<c>.json`：结构为 agent-canvas spec §4.4 的 `describe_node_route_category` 出参，内容取 §4.2（develop）、§4.3（think）的字段、级别判断标准、证据要求和 description 段落原文。

- [ ] **Step 1: 编写失败测试 `tests/canvas-stub.test.mjs`**

```js
test('routed mode answers the routing commands and logs every call', ...)
  // 断言：list 输出含 develop 与 think；describe develop 输出的 category.name === 'develop'；
  // create-routed-pty-node --category develop 输出的 decision.category === 'develop'；
  // STUB_LOG 恰有 3 行，且第 3 行以 'agent-canvas-ctl create-routed-pty-node' 开头
test('old-app mode rejects routing commands like an App without them', ...)
  // 断言：三个路由命令退出码都是 1，stderr 都以 '未知子命令: ' 开头；create-pty-node 退出码 0
test('reject-once mode rejects the first routed create with INVALID_ARGUMENT then accepts', ...)
  // 断言：第 1 次退出码 1 且 stderr 以 'INVALID_ARGUMENT' 开头；第 2 次退出码 0 且输出含 nodeId
test('setup prints a worktree on feature/slugify-numbers with the test plan committed', ...)
  // 断言：git -C WORKTREE branch --show-current === 'feature/slugify-numbers'；
  // git -C WORKTREE ls-files 含 docs/superpowers/specs/2026-11-11-slugify-numbers-test-plan.md
test('unknown mode exits 2', ...)
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/canvas-stub.test.mjs`
Expected: FAIL，提示 setup.sh 不存在

- [ ] **Step 3: 实现 `setup.sh`、`describe-develop.json`、`describe-think.json`**

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/canvas-stub.test.mjs`
Expected: PASS（5 个测试）

- [ ] **Step 5: 提交**

```bash
git add skills/coding/handoff/evals/fixtures/canvas-stub tests/canvas-stub.test.mjs
git commit -m "test(handoff): add canvas command stub for routing evals"
```

### Task 2: handoff 第 6 步改走路由

**Prerequisites:** Task 1（eval 依赖桩）

**Files:**
- Modify: `skills/coding/handoff/SKILL.md`（frontmatter `version`；Phase 1 第 6 步「建执行节点」）
- Modify: `skills-index.json`（`coding/handoff` 条目）
- Modify: `tests/handoff-worktree.test.mjs:16-17`（版本断言 `1.18.1` → `1.19.0`）
- Modify: `skills/coding/handoff/evals/evals.json`（新增 4 条 eval）
- Test: `tests/handoff-routing.test.mjs`

**Interfaces:**
- Consumes: Task 1 的 `setup.sh` 及其打印的 `STUB_BIN`、`STUB_LOG`、`WORKTREE`

- [ ] **Step 1: 编写失败测试 `tests/handoff-routing.test.mjs`**

```js
// step6 = SKILL.md 中 '6. **建执行节点**' 到 '7. **落库**' 之间的文本
test('author step 6 creates the receiver node through the routing engine', ...)
  // step6 依次包含 'list-node-route-categories'、'describe-node-route-category develop'、
  // 'create-routed-pty-node'、'--category develop'，且出现顺序与此相同
test('step 6 keeps create-pty-node only as the fallback', ...)
  // step6 中 'create-pty-node' 第一次出现的位置在 'create-routed-pty-node' 第一次出现之后；
  // step6 包含 '未知子命令'、'PRECONDITION_FAILED'、'INVALID_ARGUMENT'、'--task-type execute'
test('handoff body does not copy routing field standards', ...)
  // 全文不含 Global Constraints 列出的任何字段名或段名
test('dispatch message in step 9 stays addressing-only', ...)
  // '9. **派发**' 段仍含 '只放寻址信息，不放文档内容摘要'
```

同时把 `tests/handoff-worktree.test.mjs` 的版本断言改为 `/^version: ["']?1\.19\.0["']?$/m` 与 `'1.19.0'`。

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/handoff-routing.test.mjs tests/handoff-worktree.test.mjs`
Expected: FAIL（第 6 步尚无路由命令；版本仍为 1.18.1）

- [ ] **Step 3: 改写 handoff 第 6 步，升版本到 1.19.0，更新 `skills-index.json` 的 hash**

Approach：第 6 步的「建接手节点」改为：先调用 list 与 describe，按 describe 的指南给字段定级，证据指向第 5 步写出的交接文档以及 plan 或测试清单，description 按 describe 的段落写。之后调用 `create-routed-pty-node --category develop --title ... --cwd <工作区>`，不带 `--message`。点名 agent 或模型的情况、两种退回条件、`INVALID_ARGUMENT` 重试，各写一句。第 6 步其余内容（`put`、`link-nodes`、失败处置）不变。

- [ ] **Step 4: 新增 eval（`evals.json`，id 接现有最大值顺延）**

每条 prompt 都要求先跑 `evals/fixtures/canvas-stub/setup.sh <模式>`，在本次运行内执行的每条画布命令前加上 `PATH=<STUB_BIN>:$PATH`，并说明交接工作区已建好（`WORKTREE`，复用、不新建）。断言 `source` 一律为 `transcript`。

| name | 模式 / 用户输入要点 | assertions（id：文本） |
|---|---|---|
| `author-canvas-routes-develop` | routed；低档任务交接，未点名 agent | `describe-before-create`：创建节点前调用过 describe-node-route-category develop｜`routed-create`：调用了 create-routed-pty-node 且带 --category develop｜`params-complete`：--params 恰好包含 describe 列出的全部字段｜`evidence-real`：--evidence 的路径都是 WORKTREE 里真实存在的文件｜`no-direct-create`：没有调用 create-pty-node｜`dispatch-addressing-only`：send 发出的派发消息只含工作区路径、分支、文档路径，没有内容摘要 |
| `author-canvas-named-codex` | routed；用户说「交给 codex 做」 | `direct-codex`：调用了 create-pty-node --node-type codex｜`no-routing`：没有调用任何路由命令 |
| `author-canvas-old-app-fallback` | old-app；未点名 agent | `fallback-create`：路由命令报未知子命令后调用了 create-pty-node --node-type claude-code --task-type execute｜`single-node`：create-pty-node 与 create-routed-pty-node 成功创建的节点合计恰好 1 个｜`told-user`：回复告诉用户路由不可用、已退回 |
| `author-canvas-invalid-retry` | reject-once；未点名 agent | `retried-routed`：被 INVALID_ARGUMENT 拒绝后再次调用 create-routed-pty-node｜`no-fallback`：没有调用 create-pty-node｜`single-node`：成功创建的节点恰好 1 个 |

- [ ] **Step 5: 运行本任务的全部测试，验证通过**

Run: `node --test tests/handoff-routing.test.mjs tests/handoff-worktree.test.mjs tests/harness/declarations.test.mjs`
Expected: PASS（含「仓库里每一份 evals.json 都必须合法」）

- [ ] **Step 6: 提交**

```bash
git add skills/coding/handoff/SKILL.md skills/coding/handoff/evals/evals.json skills-index.json tests/handoff-routing.test.mjs tests/handoff-worktree.test.mjs
git commit -m "feat(handoff): create the receiver node through the routing engine"
```

### Task 3: fork-topic 在画布里建 think 节点并派发

**Prerequisites:** Task 1（eval 依赖桩）

**Files:**
- Modify: `skills/coding/fork-topic/SKILL.md`（frontmatter `description`、`version`；正文）
- Modify: `docs/superpowers/specs/2026-10-11-fork-topic-design.md`（「边界」一节）
- Modify: `skills-index.json`（`coding/fork-topic` 条目）
- Modify: `skills/coding/fork-topic/evals/evals.json`（新增 3 条 eval）
- Test: `tests/fork-topic-routing.test.mjs`

**Interfaces:**
- Consumes: Task 1 的 `setup.sh`，fork-topic 的 eval 通过 `<skill 目录>/../handoff/evals/fixtures/canvas-stub/setup.sh` 引用

- [ ] **Step 1: 编写失败测试 `tests/fork-topic-routing.test.mjs`**

```js
test('fork-topic version and index hash are 1.1.0', ...)
  // version 1.1.0；index contentVersion '1.1.0'；contentHash === hash(body)
test('fork-topic routes a think node when inside a canvas node', ...)
  // 正文依次包含 'agent-canvas-ctl whoami'、'describe-node-route-category think'、
  // 'create-routed-pty-node'、'--category think'，且含 'send'、'--file'
test('fork-topic keeps the fallback and named-model rules', ...)
  // 正文含 '未知子命令'、'PRECONDITION_FAILED'、'INVALID_ARGUMENT'、'--task-type plan'；
  // 'create-pty-node' 第一次出现在 'create-routed-pty-node' 之后
test('fork-topic never links nodes or copies routing field standards', ...)
  // 正文不含 'link-nodes'、'--expect-reply' 与 Global Constraints 列出的任何字段名或段名
test('fork-topic description no longer claims text-only everywhere', ...)
  // frontmatter description 不含 'Text only: no files, branches, or acceptance.'，
  // 且含 'outside a canvas node'
test('fork-topic design doc limits no-dispatch to outside the canvas', ...)
  // 设计文档「边界」一节不再含 '不替用户派给其他 agent——只输出文本，用户自己贴'，且含 '画布'
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/fork-topic-routing.test.mjs`
Expected: FAIL（版本仍为 1.0.0，正文无路由命令）

- [ ] **Step 3: 改写 fork-topic，升版本到 1.1.0，更新设计文档与 `skills-index.json` 的 hash**

Approach：保留现有起草规则，在「输出」处分两条路：
- `agent-canvas-ctl whoami` 取不到节点 id：照旧只输出代码块里的 prompt。
- 取得到：先 list、再 `describe-node-route-category think`，按指南定级并写 description，然后 `create-routed-pty-node --category think`。接着 `agent-canvas-arrange put`，把 prompt 写进 `mktemp` 临时文件，再 `send <nodeId> --file`，回复里说明派给了哪个节点、`messageId` 是什么。点名模型的情况与退回规则同 Task 2。

frontmatter description 改为：在画布节点里建节点并发出 prompt，outside a canvas node 只出文本。

- [ ] **Step 4: 新增 eval（id 接现有最大值顺延）**

prompt 要求与 Task 2 Step 4 相同（setup 路径按上面的 Interfaces 给出）；断言 `source` 一律为 `transcript`。

| name | 模式 / 用户输入要点 | assertions（id：文本） |
|---|---|---|
| `fork-canvas-routes-think` | routed；主讨论在等支线结论 | `routed-create`：调用了 create-routed-pty-node 且带 --category think｜`params-complete`：--params 恰好包含 describe-node-route-category think 列出的全部字段｜`sent-prompt`：调用 send --file 把 prompt 发给新节点，临时文件不在当前仓库目录内｜`no-link`：没有调用 link-nodes｜`return-requested`：发出的 prompt 要求接手方交回可贴回主讨论的结论｜`reports-node`：回复说明派给了哪个节点与 messageId |
| `fork-canvas-old-app-fallback` | old-app | `fallback-create`：路由命令报未知子命令后调用了 create-pty-node --task-type plan｜`single-node`：成功创建的节点恰好 1 个｜`still-sent`：仍然 send 了 prompt｜`told-user`：回复说明已退回 |
| `fork-canvas-named-model` | routed；用户说「用 opus 开个支线」 | `direct-model`：调用了 create-pty-node 且带 --model opus｜`no-routing`：没有调用任何路由命令 |

- [ ] **Step 5: 运行本任务的全部测试，验证通过**

Run: `node --test tests/fork-topic-routing.test.mjs tests/harness/declarations.test.mjs`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add skills/coding/fork-topic docs/superpowers/specs/2026-10-11-fork-topic-design.md skills-index.json tests/fork-topic-routing.test.mjs
git commit -m "feat(fork-topic): dispatch a think node through the routing engine on the canvas"
```

### Task 4: 全量回归与 eval 实跑

**Prerequisites:** Task 2、Task 3

**Files:**
- Create: `docs/superpowers/specs/measurements/2026-11-11-route-from-handoff-fork-topic-evals.md`

- [ ] **Step 1: 跑全量测试**

Run: `npm test`
Expected: PASS（bats、skill 自带测试、node:test 全绿）

- [ ] **Step 2: 实跑 handoff 的 eval（新增 4 条 + 回归 author eval 0、1）**

Run: `node tools/skill-harness/cli.js run --skill coding/handoff --platform claude --mode native --model claude-sonnet-5-5 --repeat 1`，随后 `node tools/skill-harness/cli.js grade <runId>`
Expected: 新增 4 条 eval 的全部断言为 pass；eval 0、1 的断言结果不比改动前差

- [ ] **Step 3: 实跑 fork-topic 的 eval（新增 3 条 + 回归 eval 0–2）**

Run: 同上，`--skill coding/fork-topic`
Expected: 新增 3 条 eval 的全部断言为 pass；eval 0–2 全部 pass

- [ ] **Step 4: 把 runId、各断言结果、失败断言的原文写进 measurements 文档**

- [ ] **Step 5: 提交**

```bash
git add docs/superpowers/specs/measurements/2026-11-11-route-from-handoff-fork-topic-evals.md
git commit -m "docs(measurements): routing evals for handoff and fork-topic"
```

测试清单「验证方式」第 3 条的真实试跑（需要带路由命令的 App，以及用户同意画布写操作）不在本计划内，由交出方在 App 升级后另行安排。
