# 交接：按已批准的实施计划实现 skill 跨平台 harness 第一期

**日期**：2026-08-14
**author 模型**：claude-opus-5
**状态**：待执行 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：spec 与实施计划已由用户批准并提交，接手方按计划逐 task 实现第一期代码，原 session 按最小验收锚点验收。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，按「工作流约定」开工，完成后等原 session 按「最小验收锚点」验收。

---

## 最小验收锚点

硬判据，逐条实跑，全绿才算达成：

1. `npm test` 全绿（`e2e.test.mjs` 的 7 条应显示 skipped，不是 failed）
2. `node tools/skill-harness/cli.js dry-run --model MiniMax-M2.7 --provider minimax-cn --skill mint/learn-skill` 输出 **6 段**（3 平台 × 2 模式），每段含 argv、打码 env、systemAppend、positional；native 段含 `jail writes:` 且**不含 skill 正文**
3. `node tools/skill-harness/cli.js coverage` 对当前 39 个 skill 输出完整三态矩阵，未跑过的格子显示 `never`，输出中**不出现 `✓`**
4. 把 `tools/skill-harness/matrix.json` 里那条 override 的 `reason` 改成空串，`npm test` 必须变红；改回后恢复绿
5. `SKILL_HARNESS_E2E=1 node --test tests/harness/e2e.test.mjs` 7 条全绿
6. `grep -rE 'sk-ant|oat01|MINIMAX_CN_API_KEY=' ~/.hskill/skill-harness/` 无命中（凭证未落盘）
7. 15 个 task 各自成 commit，`git log --oneline` 可见，全部通过仓库的 commit-msg hook

第 5 条需要真模型调用（约 6 次），有成本。若因凭证/网络跑不通，**如实报告哪几条没跑、卡在哪**，不要跳过后声称完成。

---

## 背景与现状

用户要为本仓库的 44 个 skill 建跨平台适配测试框架。经过 QM 深度调研 → spec → 三轮实测修正 → 实施计划，现在**规划阶段已全部完成并经用户批准**（原话："可以"）。接手方只做实现，不重新设计。

三轮实测推翻了 spec 的初始设计，结论已固化进 spec，**不要再质疑或重测**：

- 纯正文注入在 claude/pi/hermes 三平台**一律断开 skill 的路径锚点**（`references/` 读不到）。本仓 44 个 skill 中 31 个受影响。所以 native（走平台原生 skill 通道）为主模式，inject 为对照。
- 三平台**默认模型不同**（claude 是 `claude-sonnet-5`，pi 和 hermes 是 `MiniMax-M2.7`），不 pin 模型则"跨平台差异"实为平台⊗模型混合效应。已验证 claude 可经 `ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic` + `--model MiniMax-M2.7` 跑同一模型。
- claude 的 jail 挡不住 **16 个**内置 skill，pi 和 hermes 是 0。这个数来自 `stream-json` 首行 `system` 事件的 `skills` 数组，是程序可读的 ground truth。

**已经在仓库里、不要重新生成的东西**：

| 路径 | 是什么 |
|---|---|
| `tests/harness/fixtures/claude/probe-anchor-native.jsonl` | 真实抓取的 claude stream-json（9 行，8.5 KB） |
| `tests/harness/fixtures/pi/probe-anchor-native.jsonl` | 真实抓取的 pi `--mode json`（27 行，17 KB，已剔 143 条流式增量） |
| `docs/superpowers/specs/measurements/probe-anchor/` | 探针 skill 源，Task 8 Step 1 从这里复制到 `tools/skill-harness/probe/` |

计划里所有解析器断言的字段名都是从这两份 fixture 实测得来的，不是推断的。**fixture 不要重抓**——重抓会让计划里的断言值（`num_turns: 4`、`usage.input: 5` 等）全部对不上。

---

## 关键决定（别改动）

这些是实测得出或用户拍板的，接手方若擅自改动会推翻已定方案：

1. **native 为主、inject 为对照，两者是诊断对不是二选一。** 单跑任何一种都拿不到「触发问题 vs 正文问题」的判读表。
2. **inject 模式的路径补偿行不是可选的。** 缺了它三平台一律断锚，inject 组会因测试装置缺陷全线失败。
3. **`--model` 是必填参数，无默认值。** 缺失时必须报错退出，不许静默回退到平台默认模型。
4. **`builtinSkillFloor = [16, 0, 0]`** 钉在 L1 快照里。若 E2E 测出不是 16，说明上游改了内置 skill 集合——**回来更新 `profiles.js` 并在 `docs/superpowers/specs/measurements/` 追加记录，不要直接改断言了事**。
5. **报告三态：`not-run` 渲染成空格，绝不渲染成对勾**，也不得从矩阵里省略行列。这是防覆盖率静默腐烂的核心约束。
6. **`matrix.json` 的 `reason` 必填**，缺失即测试红。一条没写理由的排除，和忘了测无法区分。
7. **`parse` 必须是纯函数**——不碰进程、不碰文件系统、不读 `process.env`。这是 spec 唯一的硬约束。
8. **jail 目录名必须中性**，`mkdtemp` 前缀固定 `skill-harness-`，禁止出现 `jail`/`inject`/`probe` 等词。实测中 claude 曾因工作目录名叫 `jail-inject` 而把注入内容判为 prompt injection 拒绝执行。
9. **hermes 的 `--safe-mode` 保留。** help 里 `--ignore-rules` 写着 "skip ... and preloaded skills"，字面读像会关掉被测 skill，实测不会——那句只指 `-s` 的强制预载通道，不含目录发现。

---

## 范围铁律

**In：** `docs/superpowers/plans/2026-08-14-skill-harness-phase1.md` 里的 Task 1–15，一个不多一个不少。

**Out：**

- **任何评估逻辑**（过程评估、质量评估、grader、负向断言判定）——那是第二、三期
- **claude / pi / hermes 之外的平台**（codex / opencode / cursor-agent / openclaw）
- **往用户真实 skill 目录写任何东西**（`~/.claude/skills/`、`~/.hermes/skills/`、`~/.pi/agent/skills/`）——jail 内的 skill 目录已经能走原生通道
- **修改 `skills/` 下的任何 skill**——本期只建框架，不改被测对象
- **修改 spec 里的实测数值**——除非你自己重新实测并在 measurements 目录留下记录
- **引入新的 npm 依赖**——`fs-extra`/`chalk` 已有，`node:test` 内置，够用

---

## 相关文档索引

| 路径 | 用途 |
|---|---|
| `docs/superpowers/plans/2026-08-14-skill-harness-phase1.md` | **主依据**，15 个 task 的完整代码与测试，逐步执行 |
| `docs/superpowers/specs/2026-08-14-skill-harness-adapter-design.md` | 设计依据，遇到计划没覆盖的判断回这里查 |
| `docs/superpowers/specs/measurements/2026-08-14-native-vs-inject.md` | 全部实测记录与复现命令，含各平台轨迹字段表 |
| `docs/reference/testing-guide.md` | 仓库测试约定，Task 15 Step 4 要往这里追加一节 |
| `CLAUDE.md` | 仓库总约定 |
| `docs/reference/git-workflow.md` | 分支命名与合并流程 |

---

## 受影响文件/落点

**新建**（全部在 `tools/skill-harness/` 与 `tests/harness/` 下，完整清单见计划的 File Structure 一节）：
`select.js` `matrix.json` `jail.js` `profiles.js` `record.js` `prompt.js` `parse/claude-code-jsonl.js` `parse/pi-jsonl.js` `adapters/{claude,pi,hermes}.js` `runner.js` `coverage.js` `report.js` `cli.js` `probe/probe-anchor/`，以及对应的 10 个 `.test.mjs`。

**修改**（只有两处，都很小）：

- `package.json:10` 的 `scripts.test` —— Task 1 Step 5，把 harness 测试接进 `npm test`
- `docs/reference/testing-guide.md` 末尾 —— Task 15 Step 4，追加 harness 一节

**运行时产物**：`$HOME/.hskill/skill-harness/<run-id>/`，不写进项目目录。

---

## 工作流约定

本仓库有会实打实拦住你的约束，开工前务必知道：

1. **你在一个 git worktree 里**：`/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/qm-research`，分支 `doc/qm-research`。所有命令从这里运行，**不要 `cd` 到主仓** `/Users/harveyzhang96/Projects/harveyz-skill`（那里是 `staging` 分支）。

2. **不要新建分支。** 仓库约定是「一个功能或迭代用一个分支，积累所有相关改动」。继续在 `doc/qm-research` 上提交。

3. **不要 merge 到 staging。** 只有用户明确说"合并"或"完成"时才合。合并时必须 `--no-ff`。

4. **commit message 受 hook 强制**：
   - Conventional Commits，类型限 `feat|fix|chore|docs|refactor|test|style|perf`
   - **首行 ≤ 80 字符**（我在这次会话里被这条拦过一次）
   - 计划里每个 task 的 Step「提交」已给出合规的 message，直接用

5. **git stash 栈与主仓和其他 worktree 共享。** 不要用裸 `git stash` / `git stash pop`，会弹到别人的改动。要暂存就用临时 WIP commit。

6. **代码风格**：ESM，**不写分号**，单引号，2 空格缩进。参照 `lib/installer.js`、`lib/targets.js`。计划里的代码块已按此风格写好。

---

## 验证步骤

计划里每个 task 都自带 `Run:` / `Expected:`，按步执行即可。以下三条是计划里不够显眼、容易漏的：

**E2E 需要凭证**，`e2e.test.mjs` 默认全部 skip：

```bash
SKILL_HARNESS_E2E=1 node --test tests/harness/e2e.test.mjs
```

它从 keychain 取 claude 的 OAuth token（`security find-generic-password -s "Claude Code-credentials"`），从 `~/.hermes/.env` 取 `MINIMAX_CN_API_KEY`。两者在本机都可用，已验证。

**Task 1 Step 5 改了 `npm test`**，之后每个 task 结束都跑一次 `npm test` 而不只是单文件，确保没破坏既有的 bats 测试。

**Task 14 Step 5 的 dry-run 是人工核对项**，不是自动断言——真的读一遍输出，确认 native 段里没有 skill 正文、inject 段里有路径补偿行。

---

## author 冷读核对结论

- 交接目的、最小验收锚点：均在，锚点 7 条全部可证伪
- 相关文档索引 6 条路径：已逐条 `ls` 核实存在
- 受影响文件与文档索引自洽：计划的 File Structure 与本文「受影响文件/落点」一致
- 关键决定 9 条：覆盖了三轮实测推翻的全部结论，接手方无需回问
- 范围铁律：in/out 均点名，无模糊地带
- 反向检查：补写了「fixture 不要重抓」——这条若漏，接手方很可能出于谨慎重新抓取，导致计划里所有断言值失配，是最可能踩的坑
