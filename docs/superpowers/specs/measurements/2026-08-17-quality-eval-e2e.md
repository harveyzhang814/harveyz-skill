# 质量评估端到端实测记录 · 2026-08-17

支撑 [../2026-08-17-skill-harness-quality-eval-design.md](../2026-08-17-skill-harness-quality-eval-design.md)
的「未确认项汇总」一节。这里只记事实与复现方法，结论在 spec 里。

被测 skill：`coding/handoff`（brief 建议：会写文档，不像纯回复类 skill）。
被测模型全程 `claude-sonnet-5`，平台 `claude`，模式 `native`。

---

## Step 1+2：一格真实运行 + 核对采集层

### 第一次尝试：不传 `--task`（沿用 brief 原命令）

```bash
node tools/skill-harness/cli.js run \
  --skill coding/handoff --platform claude --mode native \
  --model claude-sonnet-5 --repeat 1
```

runId：`20260817-070005-1f83`。矩阵打印 `coding/handoff pass`。

```bash
ls -R ~/.hskill/skill-harness/20260817-070005-1f83/cells/
```

```
coding-handoff__claude__native__r0
  transcript.jsonl        （无 artifacts/ 目录）
```

`transcript.jsonl` 6742 字节。读取内容发现 `result` 事件的回复是：

```
"Which skill would you like me to run? Available ones are:\n\n- handoff\n- dataviz\n..."
```

即模型没有触发 `handoff` skill（transcript 里没有任何 `tool_use: Skill` 事件）。根因：
`cli.js` 在没有 `--task` 时的默认值是字面量 `'run skill'`（`cli.js:188`），这句话本身
不携带任何具体任务，模型合理地反问"你要跑哪个 skill"。`pass` 判据只看 upstream
（skill 有没有报错），不检查 skill 有没有被真正触发，所以矩阵仍显示 `pass`。

### 第二次尝试：显式传 `--task`（沿用 evals.json 里 handoff 的第一条 frozen 用例原文）

```bash
node tools/skill-harness/cli.js run \
  --skill coding/handoff --platform claude --mode native \
  --model claude-sonnet-5 --repeat 1 \
  --task "我刚把一个功能模块的重构方案定完了，设计规格已经写好放在仓库里。想把具体实现交给另一个能力较弱的模型 session 去做，帮我写一份交接文档，让它只读这一份就能照着实现，别自由发挥。"
```

runId：`20260817-070109-26c4`。矩阵仍打印 `coding/handoff pass`。

```bash
ls -R ~/.hskill/skill-harness/20260817-070109-26c4/cells/
```

```
coding-handoff__claude__native__r0
  transcript.jsonl        （仍然无 artifacts/ 目录）
```

`transcript.jsonl` 21230 字节。这次 transcript 里确实出现了

```json
{"type":"tool_use","name":"Skill","args":{"skill":"handoff","args":"author: ..."}}
{"type":"tool_use","name":"Bash","args":{"command":"ls -la && ... git status ..."}}
```

即 handoff **这次真的被触发了**。但模型 `ls -la` 后发现 jail 工作目录（
`skill-harness-UvKY8s`）里没有 git 仓库、没有设计规格文档，只有 `.claude`、
`stdout.log`、`stderr.log`，于是回复：

```
"这个工作目录（`skill-harness-UvKY8s`）里没有找到实际项目仓库或设计规格文档——只有
`.claude`、`stderr.log`、`stdout.log`，且不是 git 仓库。请提供一下：1. 设计规格文档
的实际路径……"
```

模型没有写任何文件，只是反问澄清。**关键结论：`artifacts/` 之所以两次都不存在，不是
采集层的 bug。** 读 `harvest.js` 的 `snapshot`/`diffSnapshots` 确认：产出物目录只在
before/after 文件快照差集非空时才会出现内容；这两次运行里模型确实什么文件都没写，
差集为空，所以没有 `artifacts/` 目录本身（不是"目录存在但为空"，是压根没创建）。

**这暴露的是一个更根本的问题：jail 是一个空目录，不含任何真实项目上下文。**
像 `handoff` 这类依赖"读仓库里的设计规格/背景"的 skill，在裸 jail 里理性的行为就是
反问而不是瞎写。brief 里"handoff 必然写文档"这个预期在当前 jail 构造（不预置任何
仓库文件）下不成立——除非 `--task` 本身把足够的背景喂进去（这次的 task 提到"设计规格
已经写好放在仓库里"，但没有实际提供文件，模型仍然去核实而不是编造）。

未能在本轮观察到 `artifacts/` 内含 skill 实际写出的文件，这是本次验证的**负向结论**，
如实记录，不通过反复换 skill 或换 prompt 来"凑"出一个正向结果。

---

## Step 3：jail 已删，grade 仍能跑

```bash
ls /tmp/skill-harness-* 2>&1 | head -3
node tools/skill-harness/cli.js grade 20260817-070109-26c4 --grader-model claude-opus-5
```

`ls /tmp/skill-harness-*` 命中的是其它历史运行残留的日志/目录（`skill-harness-doc-test.log`、
`skill-harness-2f7O`），**不是**这次 run 用的 jail——本次 run 的 jail（
`skill-harness-UvKY8s`，见 transcript 里 `ls -la` 的输出路径）已被删除，
命令行确认时机以 `run` 自身在跑完后清理为准。`grade` 命令完整跑完，打印了完整的
skill × assertion × platform 矩阵，验证了它只依赖 `cells/` 下落盘的
`transcript.jsonl`（jail 早已不存在）：

```
grader: model=claude-opus-5  subject=claude-sonnet-5
...
coding/handoff
  [upstream]                    pass
  file-in-output-dir            unavail
  header-has-status-and-purpose unavail
  purpose-is-continuation       unavail
  continuation-sections-present unavail
  anchor-is-falsifiable         unavail
  file-in-output-dir            fail
  status-is-pending             fail
  background-describes-progress fail
  anchor-references-original-criteria fail
  ran-criteria-not-just-read    fail
  status-set-to-rejected        fail
  names-failing-criterion       fail
  record-appended-to-anchor-section fail
  purpose-is-background-only    unavail
  ...
pass: 0  fail: 8  unavailable: 9  unstable: 0  declared-na: 0  not-run: 307  blocked-upstream: 0
```

`unavail` 对应源为 `artifact` 的断言（没有产出物可判）；`fail` 对应源为 `transcript`
的断言（有 transcript 可判，grader 判定没做到）——这印证了 spec 里
`unavailable` vs `fail` 分离设计确实按预期工作：产出物缺失不会被误判成断言失败。

---

## Step 4：自指警告

```bash
node tools/skill-harness/cli.js grade 20260817-070109-26c4 --grader-model claude-sonnet-5
```

`grader-model` 与 Step 1 的被测模型同为 `claude-sonnet-5`，报告顶部按预期出现：

```
grader: model=claude-sonnet-5  subject=claude-sonnet-5
!! 量具与被测物同模型，差异可能是自指伪影，结论不可直接引用
```

Step 3（grader=opus，subject=sonnet）的输出没有这行。两次对照确认警告只在模型相同时触发。

---

## Step 5：`--repeat` 标定 —— 命令本身不工作，非"稳不稳"的问题

```bash
node tools/skill-harness/cli.js run \
  --skill coding/handoff --platform claude --mode native \
  --model claude-sonnet-5 --repeat 5 \
  --task "……（同 Step 1 第二次尝试的 task）"
```

runId：`20260817-070648-62f7`。矩阵仍只打印一行 `coding/handoff pass`，
`ls ~/.hskill/skill-harness/20260817-070648-62f7/cells/` 只有
`coding-handoff__claude__native__r0` 一个目录，`records.json` 数组长度为 1。
**没有 r1~r4。**

读源码定位原因：`cli.js:27` 把 `opts.repeat` 默认设为 `1`，`cli.js:47` 把
`--repeat` 的值解析进 `opts.repeat`，但全仓库搜索 `repeat` 的用法（
`grep -rn repeat tools/skill-harness/*.js`）确认：`opts.repeat` 之后**再也没有被
读取过**。`select.js` 的 `selectCells` 只按 `skill × platform × mode` 生成格子，
完全没有按 `repeat` 展开的逻辑；`runner.js` 里出现的 `repeat: cell.repeat ?? 0`
只是给 `cellDirName` 一个默认目录名后缀，不是重复执行的驱动源。

**结论：当前分支上 `--repeat` 是死代码——CLI 接受这个 flag、不报错，但实际只会跑
一次（r0）。** 这不是"跑了 5 次、发现输出不稳定/稳定"的问题，而是这条命令行接口
根本没有兑现"跑 5 次"这个承诺。因此本轮**无法**通过 brief 给的命令实测出
`unstable` 的具体计数，也就无法回答"一次调用判整条断言清单的输出稳定性"这个未确认项
——这本身就是一个需要单独修的缺陷，留给后续任务，不在本任务范围内代为修复。

（题外话：`~/.hskill/skill-harness/` 下存在一个更早的 `20260817-070000-merge5`
目录，内含 `mint-learn-skill__claude__native__r0`~`r4` 五个真实 repeat 格且已有
`gradings.json`——文件时间戳早于本次会话的所有操作，应是此前任务开发/测试阶段留下的
产物，不是本次会话产生的实测证据，因此不采用它来回填"稳定性"这一项结论。）

---

## Step 6（brief 原文）/ transcript 体积

两次真实运行的 `transcript.jsonl`：

| runId | 场景 | 大小 |
|---|---|---|
| `20260817-070005-1f83` | 默认 task，skill 未触发，1 轮回复 | 6742 字节 |
| `20260817-070109-26c4` | 显式 task，skill 触发 + 1 次 Bash，1 轮回复 | 21230 字节 |

两者都远小于 `harvest.js` 里定义的 `TRANSCRIPT_LIMIT = 4 * 1024 * 1024`（4 MB）。
量级是"个位数到十几 KB 每轮"，多轮/多工具调用的真实任务大概率仍在数十到数百 KB
量级，4 MB 截断阈值在单格单次运行下留有充足余量；这轮没有观察到任何截断
（两份 `transcriptTruncated` 均为 `false`，见 `records.json`）。

---

## pi 认证判定（Task 1 Step 6，未在本轮重新实测，转录既有结论）

设计文档「未确认项汇总」表中该行已在 Task 1 阶段查实并标注「已查，认证不通」，
本轮未重新实测（不重复花钱验证已有定论），沿用该结论。

---

## 复现

命令见各 Step 标题下的代码块。所有命令均为真实调用 `claude` CLI（`claude-sonnet-5`），
grade 步骤调用 `claude-opus-5` 与 `claude-sonnet-5` 两种 grader，产生真实费用，
每条证据只跑一次，未重复。
