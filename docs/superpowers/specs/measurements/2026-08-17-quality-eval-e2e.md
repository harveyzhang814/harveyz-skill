# 质量评估端到端实测记录 · 2026-08-17

支撑 [../2026-08-17-skill-harness-quality-eval-design.md](../2026-08-17-skill-harness-quality-eval-design.md)
的「未确认项汇总」与验收判据 1/2/9/10。这里只记事实与复现方法，结论在 spec 里。

跑在 worktree `feature/harness-quality-eval`，真实模型：被测 `claude-sonnet-5`，量具（grader）按步骤分别用
`claude-opus-5` / `claude-sonnet-5`。所有 `runId` 均在 `~/.hskill/skill-harness/<runId>/`。

> 本文档取代同名文件更早的一版内容（对应提交 `b96840a`，用 `coding/handoff` 跑 Step 1-4，
> Step 2 两次尝试均未捕获到产出物，Step 5 因 `--repeat` 死代码判定为无法实测、未完成）。
> 两版独立发现了同一个 `--repeat` 缺陷（互相印证，非巧合）；本版额外做到：Step 2 换用更完整的
> 单轮任务描述后成功捕获到真实产出物，Step 5 用不改代码的合并法完成了真实的 unstable 标定。

---

## Step 1: 一格真实运行

```bash
node tools/skill-harness/cli.js run \
  --skill mint/learn-skill --platform claude --mode native \
  --model claude-sonnet-5 --repeat 1
```

`runId: 20260817-063628-30f4`。输出：`mint/learn-skill claude/native pass`（exitCode 0）。

## Step 2: 核对采集层

```bash
ls -R ~/.hskill/skill-harness/20260817-063628-30f4/cells/
```

`cells/mint-learn-skill__claude__native__r0/` 下有 `transcript.jsonl`（6465 字节），但 `artifacts/`
只有 claude 自己的状态文件（`.claude/policy-limits.json`、`.claude/.claude.json`、
`.claude/backups/*`、`.claude/projects/*/<sessionId>.jsonl`），没有 learn-skill 写出的任何报告文件——
`learn-skill` 是纯聊天回复型 skill，符合 brief 预告的场景。**换 `coding/handoff` 重跑本步骤**：

第一次换用默认 `--task "run skill"` 直接问出了 `coding-handoff__claude__native__r0` 的 reply：模型
反问"你要跑哪个 skill？"——**默认任务文案太泛，连 skill 都没触发**（`triggered: false`）。

第二次给出具体但仍笼统的 `--task`（"帮我写份交接文档，代码已改完还没测试……"），skill 真的被
`Skill` 工具触发了，但因为是单轮调用没有追问机会，模型只反问了三个信息缺口，仍未写文件
（`runId 20260817-063730-d675`，transcript 37149 字节）。

第三次把 bug 症状、改动、验收判据一次性喂全、并显式要求"直接起草、不要反问、跳过 git 现状核实"：

```bash
node tools/skill-harness/cli.js run \
  --skill coding/handoff --platform claude --mode native \
  --model claude-sonnet-5 --repeat 1 \
  --task "author 阶段，直接起草，不要反问。任务一句话：登录页密码字段有前导空格未 trim 导致校验失败。……"
```

`runId: 20260817-063820-9bb8`。`artifacts/docs/commute/2026-08-17-login-password-trim-handoff.md`
真实生成，内容含状态字段、交接目的、最小验收锚点、背景与现状、关键决定、范围铁律、受影响文件——
和 `coding/handoff` skill 自身对 author phase 的产出要求一致。`transcript.jsonl` 53258 字节。

**结论：采集层工作正常，`artifacts/` 为空不是采集层的问题，是被测 skill 本身不写文件，或者单轮
调用给的上下文不够、模型理性地反问而不是瞎编。换一个会写文件的 skill（`coding/handoff`）并把
背景一次性喂全，即可验证捞取真实生效。**

## Step 3: jail 已删、grade 仍能跑

```bash
ls /tmp/skill-harness-* 2>&1 | head -3
node tools/skill-harness/cli.js grade 20260817-063820-9bb8 --grader-model claude-opus-5
```

`ls /tmp/skill-harness-*` **不是有效判据**：macOS 上 `os.tmpdir()`（jail 实际创建的位置）解析到
`$TMPDIR`，即 `/private/var/folders/.../T/`，根本不是 `/private/tmp`（`/tmp` 的目标）。该命令
在这台机器上恒定报 "No such file or directory"，与 jail 是否被删无关（`/tmp/skill-harness-*`
下还留着两个八月十五的旧文件，与本次运行无关）。真实判据改用 Python 读 4 个 transcript 的
`system.init` 事件里的 `cwd`（即 jail 路径），逐个 `os.path.exists`：

```
20260817-063628-30f4 /private/var/.../T/skill-harness-fbHURg False
20260817-063651-743a /private/var/.../T/skill-harness-N7Pthk False
20260817-063730-d675 /private/var/.../T/skill-harness-UrLSwr False
20260817-063820-9bb8 /private/var/.../T/skill-harness-Bmwadd False
```

四个 jail 全部已删（`False`）。`grade` 命令随后完整跑完，打印出断言矩阵（`coding/handoff` 一行
9 pass / 8 fail，其余无声明 skill 留空），**证明 grade 阶段确实只读落盘产物，不依赖已删除的 jail**。

> **2026-08-17 事后作废声明（task-15）**：上面「9 pass / 8 fail」这个具体计数是
> 一个已确认缺陷的产物，不是真实测量结果——**Step 3 本身要验证的结论（grade
> 阶段不依赖已删除的 jail）依然成立**，作废的只是这个计数的数值。
> 根因：`coding/handoff` 声明了 4 个 eval 场景（各自独立的 prompt + 断言），
> 但 run 阶段在这次实测时没有 eval 维度——整个 skill 只跑了 `runId
> 20260817-063820-9bb8` 这一次运行（`--task` 手填的那句 author 阶段任务）。
> `grade/index.js` 的 `selectGradeCells` 却对每条 record 循环声明里的全部
> `evals[]`（`for (const evalDef of decl.evals ?? [])`），把 4 个场景共 17
> 条断言（5+4+4+4）全部扣到这唯一一次运行的产出物上去判——包括另外三个从未
> 被执行过的场景（跨设备续做、验收打回、纯背景交接）。"9 pass / 8 fail" 因此
> 是"用一次 author 场景的产物去回答四个场景的断言"拼出来的数字，不是四个场景
> 各自真实运行后的结果。已在同任务里修复：run 阶段现在按声明的 eval 数量展开
> cell（每个场景一次独立运行、自己的 prompt），`selectGradeCells` 只判
> record 自己实际运行的那个 evalId，不再逐条 record 循环全部声明的 eval。
> 本记录只重跑代码，不重跑真实模型（本任务禁止真实模型调用），因此没有可
> 替换的新计数——留空比编一个数字更诚实。

## Step 4: 自指警告

```bash
node tools/skill-harness/cli.js grade 20260817-063820-9bb8 --grader-model claude-sonnet-5
```

首行输出：

```
grader: model=claude-sonnet-5  subject=claude-sonnet-5
!! 量具与被测物同模型，差异可能是自指伪影，结论不可直接引用
```

按预期出现。Step 3 用 `claude-opus-5` 时该行不出现。

## Step 5: unstable 标定

**发现一个阻塞性缺陷：`--repeat` 旗标被解析但从未被消费。**

`cli.js` 的 `parseArgs` 把 `--repeat N` 存进 `opts.repeat`（默认 1），但 `opts.repeat` 在
`main()` 里再未被读取；`select.js` 的 `selectCells`/`selectProbeCells` 都不接收也不产出
`repeat` 字段；`runner.js` 的 `runMatrix` 只对 `cells.filter(c => c.state === 'run')` 各跑一次
（`cell.repeat ?? 0` 恒为 `0`）。三处代码逐一确认过，不是猜测。实测复核：

```bash
node tools/skill-harness/cli.js run \
  --skill mint/learn-skill --platform claude --mode native \
  --model claude-sonnet-5 --repeat 5
```

`runId: 20260817-064432-4f9d`，`cells/` 下**只有一个** `mint-learn-skill__claude__native__r0`
目录，不是 5 个。控制台汇总也只打一行 `pass: 1`。单测里 `--repeat` 只在 `cli.test.mjs` 测了
`parseArgs` 把它解析成数字，从未测过它真的让 `cli.js run` 跑 N 次——这正是本任务（真实链路
E2E）该抓到、以往 mock 测试抓不到的那类缺陷，类似上一轮抓到的 `--skill` 硬编码。此缺陷已记在
案但**未修**：本任务范围是验证，不含实现改动；是否修交由后续任务决定。

**替代做法（不改代码）**：既然 `aggregateVerdicts`（`variance.js`）按
`(skill, platform, mode, evalId, assertionId)` 聚合、不认 `repeat`，只要 `records.json` 里有
5 条同格记录、`cells/` 下有 5 个 `__r0..r4` 目录，grade 阶段就能像 `--repeat 5` 原本设计的那样
工作。于是手动跑 5 次独立的 `cli.js run`（同一 skill/platform/mode/model），用固定的具体任务
文案触发 skill：

```
帮我分析一下 contribute-skill 这个 skill，它有什么问题，有没有什么需要改进的地方？
目录在 /Users/harveyzhang96/Projects/harveyz-skill/skills/mint/contribute-skill/
```

（改自 `evals/evals.json` eval id=1 的原文——原文路径 `skills/meta/contribute-skill/` 已不存在，
skill 目前实际在 `skills/mint/contribute-skill/`，属于声明陈旧的又一例，未去改声明本身。）

5 次独立 runId：`20260817-064834-bfad` `20260817-064853-9a42` `20260817-065313-f8a6`
`20260817-065637-4880` `20260817-065932-f7eb`。全部 `exitCode: 0`。把每次的
`cells/mint-learn-skill__claude__native__r0/`（transcript + artifacts）与 `records.json` 里的
唯一记录，按顺序重命名/改写 `repeat: 0..4`，合并进合成 `runId: 20260817-070000-merge5`
（脚本见下方复现），再对合成 runId 跑一次真实 grade：

```bash
node tools/skill-harness/cli.js grade 20260817-070000-merge5 --grader-model claude-opus-5
```

**结果：`unstable: 14`（15 个 `skill×evalId×assertionId` 组合里 14 个不稳，1 个稳）。**

```
pass: 0  fail: 1  unavailable: 0  unstable: 14  declared-na: 0  not-run: 309  blocked-upstream: 0

unstable assertions (14):
  mint/learn-skill/philosophy-first@claude/native        (evalId 1)
  mint/learn-skill/no-score-labels@claude/native          (evalId 1)
  mint/learn-skill/no-extra-review-sections@claude/native (evalId 1)
  mint/learn-skill/zh-body@claude/native                  (evalId 1)
  mint/learn-skill/closing-question@claude/native         (evalId 1)
  mint/learn-skill/no-score-labels@claude/native          (evalId 2)
  mint/learn-skill/no-extra-review-sections@claude/native (evalId 2)
  mint/learn-skill/zh-body@claude/native                  (evalId 2)
  mint/learn-skill/closing-question@claude/native         (evalId 2)
  mint/learn-skill/philosophy-first@claude/native         (evalId 3)
  mint/learn-skill/no-score-labels@claude/native          (evalId 3)
  mint/learn-skill/no-extra-review-sections@claude/native (evalId 3)
  mint/learn-skill/zh-body@claude/native                  (evalId 3)
  mint/learn-skill/closing-question@claude/native         (evalId 3)
```

唯一稳定的是 `philosophy-first@evalId2`（5 次一致 `fail`）。**这是有效的非零结果，如实记录，
未调整任何断言或 prompt 去驱使它趋近 0**（任务要求）。

**分维度看不稳的成因**（读 `gradings.json` 逐格对比）：

| repeat | 触发方式 | 5 条断言判定（evalId 1/2/3 通用模式） |
|---|---|---|
| r0 | 正式走了 `Skill` 工具（`triggered: true`），但回复只有 134 字符 | 全部 `unavailable`（材料不足以判） |
| r1 | 未见 `Skill` 工具调用，但做了 8-20 次 Bash/Read 真实调查，回复 2400-3100 字符 | `fail pass fail pass fail`（三个 evalId 一致） |
| r2 | 同 r1 | 同 r1 |
| r3 | 同 r1 | 同 r1，唯独 `no-score-labels`：evalId 1/2 判 `pass`，evalId 3 判 `fail` |
| r4 | 同 r1 | 同 r1 |

即 14 个 unstable 里，**多数（≈12/14）来自 r0 与 r1-r4 之间材料质量的真实差异**——r0 触发了正式
`Skill` 机制但输出过短，grader 判不了；r1-r4 没有 `Skill` 工具调用记录、却做了与 learn-skill
说明书高度吻合的深度调查（读 `docs/reference/skill-spec.md`、`installer.js`、`CHANGELOG.md` 等），
这是 `triggered` 启发式判据（只认 `{type:"tool_use", name:"Skill"}`）的一个假阴性场景：模型可能
不经过正式的 Skill 工具调用、仅凭已安装的 skill 与任务文案吻合，就直接照着 SKILL.md 的做法执行。
**剩下 1 处（`no-score-labels`@evalId3@r3）是真正意义上的量具噪声**——同一份材料，仅换了 grading
prompt 里裹着的 eval 场景文本（`evalDef.prompt`/`expected_output`），grader 的判定就翻了面。

**结论：`unstable` 非零是真实结果，不是伪影；但本次样本混入了"是否走了 Skill 工具"这一额外
自变量，使得 14 里的具体归因主要指向"运行行为本身不稳"而非单纯"grader 读同一份材料读出两种
意思"。若要单独标定纯 grader 噪声，需要先把 5 次重复的输入材料控制到行为一致（比如都不触发
`Skill` 工具，或都触发），这正是任务要求"不为了让 N 变成 0 去改断言"的边界之外、可以做但本轮
没做的事——留给下一轮，不在这里追加干预。**

## 附：Task 1 Step 6 pi 认证判定

已在更早的提交 `530831c`（`feat(harness): profile 声明 artifactChannel，pi 认证不通不重定向 HOME`）
中实测完成，非本次新查：pi 凭证存于 `$HOME/.pi/agent/auth.json`，重定向 `HOME` 到空 jail 后
`minimax-cn` 认证失败（`exitCode 1`）；真实 `HOME` 下同一命令能拿到 `reply`，确认问题出在重定向
本身。结论已反映在 `piProfile.artifactChannel = 'none'` 与 spec 未确认项汇总表中，本记录仅引用，
不重复实测。

## 附：transcript 单份体积

| 场景 | 字节数 |
|---|---|
| learn-skill，任务文案泛化未触发，纯聊天回复 | 6,465 |
| handoff，任务触发但单轮内被反问，1 次 Bash + 1 次 Read | 6,530 / 37,149 |
| handoff，任务信息给足，完整走完 author 流程并落盘 | 53,258 |
| learn-skill，Skill 工具触发但回复过短（Step 5 r0） | 24,986 |
| learn-skill，未见 Skill 工具调用但做了 8-20 次工具调查（Step 5 r1-r4） | 259,929 / 193,195 / 177,466 / 170,102 |

全部 `transcriptTruncated: false`（`TRANSCRIPT_LIMIT` 4 MB 未触发）。观测范围从数 KB（无实质
执行的纯聊天）到约 250 KB（真实多工具调查），量级比 4 MB 上限低 1-2 个数量级，尚未接近截断。

## Step 8: 全量测试

```bash
npm test
```

`tests 279  pass 272  fail 0  skipped 7`，全绿。

---

## 复现所需脚本

Step 5 的合并（把 5 个独立 `runId` 的单条记录改写 `repeat` 并拼成一个可 grade 的合成 runId）：

```python
import json, os, shutil

BASE = os.path.expanduser('~/.hskill/skill-harness')
run_ids = [...]  # 5 个独立 runId，顺序即 repeat 0..4
merged_id = '20260817-070000-merge5'
merged_dir = os.path.join(BASE, merged_id)
os.makedirs(os.path.join(merged_dir, 'cells'), exist_ok=True)

records = []
for i, rid in enumerate(run_ids):
    src_dir = os.path.join(BASE, rid)
    rec = json.load(open(os.path.join(src_dir, 'records.json')))[0]
    old_repeat = rec['repeat']; rec['repeat'] = i
    records.append(rec)
    old_name = f"{rec['skill'].replace('/', '-')}__{rec['platform']}__{rec['mode']}__r{old_repeat}"
    new_name = f"{rec['skill'].replace('/', '-')}__{rec['platform']}__{rec['mode']}__r{i}"
    shutil.copytree(os.path.join(src_dir, 'cells', old_name), os.path.join(merged_dir, 'cells', new_name))

json.dump(records, open(os.path.join(merged_dir, 'records.json'), 'w'), indent=2, ensure_ascii=False)
```

这个合并动作只重排文件系统上已经真实产生的产物、只改 `repeat` 这一个字段，不生成、不篡改任何
grader 判定或断言内容。

---

## Step 6: hermes 产出物是否落在 jail 内（补测，2026-08-17）

Task 16 review 期间发现 `hermesProfile.artifactChannel: 'jail'` 是未经测量的断言（`profiles.js:39` 的 HOME
重定向只是推出来的，不是像 `pi` 那样被真实测量过——`pi` 恰恰是「isolation 设计看起来该生效，实测却不生效」
的反例，所以这条不能只靠代码读出来的意图定论）。用户裁定现在就做一次真实测量。

```bash
node tools/skill-harness/cli.js run \
  --skill research/extract-url --platform hermes --mode native \
  --model MiniMax-M2.7 --provider minimax-cn --repeat 1 \
  --task "直接执行，不要反问，不要使用 Skill 工具。用你可用的任意工具（写文件/执行 shell 命令均可）
在你当前用户主目录（\$HOME）下创建目录 .hskill/harness-probe/（如不存在则创建），并在其中写入文件
hermes-artifact-check.md，内容严格为下面两行：
HERMES-ARTIFACT-OK
<当前 UTC ISO8601 时间戳>
写完后只回复一行：DONE"
```

选 `research/extract-url`（无声明的普通 skill）而非四个已声明 skill 之一，是为了避免 Task 15 加的 eval
轴把这次探测性测量放大成多次真实调用——无声明 skill 只产出一个通用 cell，`--task` 直接生效。

`runId: 20260817-132628-fd4c`。`records.json` 里这一格：`exitCode: 0`、`reply: "DONE"`、
`harvestErrors: []`、`toolCalls` 里唯一一次 `execute_code` 调用的源码可读——模型自己写的是
`home = os.path.expanduser("~")`，即完全依赖 `HOME` 环境变量，没有硬编码真实用户路径。

采集结果：

```
cells/research-extract-url__hermes__native__r0/artifacts/.hskill/harness-probe/hermes-artifact-check.md
```

内容与要求的两行一致（`HERMES-ARTIFACT-OK` + 时间戳）。

**结论：`hermesProfile.artifactChannel: 'jail'` 成立，已从「推出来的」升级为「已查」。** hermes 在 HOME
重定向下不仅认证正常（这点从 seedJail 复制凭证的设计就能看出是预期行为，这次一并验证了运行时确实成立），
agent 用标准 `os.path.expanduser("~")` 写出的文件也确实落在 jail 内、被 harvest 的快照差集正确捞到，
没有被 `.hermes/` 前缀排除规则误伤（因为路径本身就不在 `.hermes/` 下）。与 `pi`（HOME 重定向后认证失败，
只能退化为 `artifactChannel: 'none'`）形成对比，不能把两者的 isolation 设计一概而论。
