# fork-topic 实施计划

**目标：** 新增 `fork-topic` skill（把讨论中的支线话题写成精简的可粘贴 prompt），并把 handoff 里"只带背景、不验收"的场景迁出。

**架构：** 纯指令型 skill：一个 `SKILL.md`（流程 + 判据 + 候选项清单）加一份 `evals/evals.json` 行为声明。handoff 只删不加：删讨论型例子、背景传递型举例、eval #3，并在 author 第 2 步指向 fork-topic。注册走 `skills-index.json` + `package.json` 的 `files`。

**技术栈：** Markdown skill、JSON eval 声明、bats/node 测试（`npm test`）。

**规格：** `docs/superpowers/specs/2026-10-11-fork-topic-design.md`

**工作区：** `.claude/worktrees/feature+fork-topic`，分支 `feature/fork-topic`。所有命令在这里跑。

---

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `skills/coding/fork-topic/SKILL.md` | 创建 | skill 本体 |
| `skills/coding/fork-topic/evals/evals.json` | 创建 | 两条行为 eval |
| `skills-index.json` | 修改 | 登记 fork-topic；更新 handoff 的 contentHash/contentVersion |
| `package.json` | 生成 | `files` 加入 fork-topic 目录 |
| `docs/reference/skill-spec.md` | 修改 | 动词表加 `fork` |
| `skills/coding/handoff/SKILL.md` | 修改 | 第 33 行删例子、加指向；版本 1.13.0 |
| `skills/coding/handoff/assets/handoff-template.md` | 修改 | 第 42 行删"背景传递型"举例 |
| `skills/coding/handoff/evals/evals.json` | 修改 | 删 eval #3 |

---

### Task 0: 基线

- [ ] **Step 1: 跑一遍现有测试，记录基线**

运行: `npm test`
预期: 全绿。若有红，记下哪几条，后续任务只对新增的红负责。

---

### Task 1: fork-topic 的行为 eval（先写判据）

**文件：**
- 创建: `skills/coding/fork-topic/evals/evals.json`

- [ ] **Step 1: 写 evals.json**

```json
{
  "skill_name": "fork-topic",
  "evals": [
    {
      "id": 0,
      "name": "fork-side-discussion-awaited",
      "prompt": "我们在讨论新的缓存方案。已经定了：用进程内 LRU，不上 Redis——Redis 被否决是因为单机部署、多一个运维依赖不值。我说过不接受引入新的外部服务。讨论中冒出一个支线：缓存失效策略到底用 TTL 还是事件驱动，这个要单独讨论；主讨论里“要不要给缓存加预热”这个决定得等它的结论。现有缓存实现在 src/cache/lru.js，之前关于失效的讨论记在 docs/adr/0007-cache.md。帮我把失效策略这个支线分出去。",
      "expected_output": "只输出一段放在代码块里的 prompt，不写任何文件。prompt 的目标是失效策略（TTL vs 事件驱动）并说明它从缓存方案讨论分出；写全已定结论（进程内 LRU）、否决方案及理由（Redis：单机部署、多一个运维依赖）、用户约束（不引入新外部服务）；两个文件只以路径+用途作为线索出现，不摘要其内容；末尾要求结束时交回一段可贴回主讨论的结论，因为主讨论的预热决定在等它。",
      "files": [],
      "assertions": [
        { "id": "no-files-written", "source": "transcript", "text": "整个过程没有创建或修改任何文件" },
        { "id": "prompt-in-code-block", "source": "reply", "text": "prompt 放在一个代码块里，代码块外最多一句说明" },
        { "id": "goal-present", "source": "reply", "text": "prompt 写明支线目标是失效策略（TTL 还是事件驱动），并说明它从缓存方案讨论分出" },
        { "id": "rejected-with-reason", "source": "reply", "text": "prompt 写出 Redis 被否决，且带着理由（单机部署 / 多一个运维依赖）" },
        { "id": "user-constraint", "source": "reply", "text": "prompt 写出用户约束：不引入新的外部服务" },
        { "id": "pointers-not-content", "source": "reply", "text": "src/cache/lru.js 与 docs/adr/0007-cache.md 以路径加用途的线索形式出现，prompt 中没有对这两个文件内容的摘要、推测或代码片段" },
        { "id": "return-requested", "source": "reply", "text": "prompt 要求接手方结束时交回一段可贴回主讨论的结论" }
      ]
    },
    {
      "id": 1,
      "name": "fork-background-new-topic",
      "prompt": "我们刚才把新缓存方案的取舍定下来了：进程内 LRU，否决 Redis（单机部署，多一个运维依赖不值）。接下来我要开个新 session 讨论日志采集方案，跟缓存无关，但想让它带着这次的结论当背景，万一涉及到能对上。帮我开个新话题。",
      "expected_output": "只输出一段放在代码块里的 prompt，不写任何文件。目标是日志采集方案；缓存结论（进程内 LRU、否决 Redis 及理由）作为背景出现；不要求交回结论（主讨论不在等它）；不出现 status、最小验收锚点、worktree 一类交接文档元素。",
      "files": [],
      "assertions": [
        { "id": "no-files-written", "source": "transcript", "text": "整个过程没有创建或修改任何文件" },
        { "id": "goal-is-new-topic", "source": "reply", "text": "prompt 的目标是讨论日志采集方案" },
        { "id": "carries-conclusions", "source": "reply", "text": "prompt 带着缓存结论作为背景：进程内 LRU，否决 Redis 及其理由" },
        { "id": "no-return-request", "source": "reply", "text": "prompt 不要求接手方交回结论" },
        { "id": "no-handoff-artifacts", "source": "reply", "text": "输出中没有 status、最小验收锚点、worktree、验收一类交接文档元素" }
      ]
    }
  ]
}
```

- [ ] **Step 2: 声明校验**

运行: `node --test tests/harness/declarations.test.mjs`
预期: PASS（`skill_name` 与目录名 `fork-topic` 一致，断言 id 不重复，source 合法）。此时 SKILL.md 还不存在，若该测试因缺 SKILL.md 报错，记下错误信息，Task 2 后再跑。

---

### Task 2: RED——不带 skill 的基线行为

- [ ] **Step 1: 派一个 general-purpose subagent 跑 eval 0，不加载任何 skill**

subagent prompt：

```
你在一个讨论中，用户对你说了下面这段话。按你通常的做法回应，不要调用任何 skill，不要读写文件。
---
<eval 0 的 prompt 原文>
```

- [ ] **Step 2: 按 eval 0 的 7 条断言逐条判定，记录哪些不过**

预期: 至少一条不过（常见：对两个文件内容做了推测性摘要、漏否决理由、没有交回要求或无条件加交回要求、输出冗长）。若 7 条全过，记下来——说明 skill 的增量主要在一致性，不影响继续，但要在最终汇报里说明。

---

### Task 3: 写 fork-topic SKILL.md

**文件：**
- 创建: `skills/coding/fork-topic/SKILL.md`

- [ ] **Step 1: 写入以下内容**

````markdown
---
name: fork-topic
description: "Fork a side topic out of the current discussion into a concise, paste-ready prompt for another agent session. Writes in full only what the receiver cannot find on its own (the goal, conclusions reached, rejected options and why, the user's stated preferences); for anything findable in files or the repo, gives a pointer to where to look instead of the content. Outputs text only: no files, branches, or acceptance. Use handoff instead when the work must come back for formal acceptance. Triggers: '/fork-topic', 'fork this topic', 'split this off into a new session', 'spin off a side discussion', 'take these conclusions into a new topic'."
user_invocable: true
version: "1.0.0"
---

# fork-topic — 把支线话题分出去

讨论中冒出一个支线话题，要交给另一个 agent 单独展开。本 skill 把它写成一段**精简的可粘贴 prompt**。

主次：目的是把支线分出去；约束是 prompt 尽可能精简；手段是接手方**查不出**的写全，**查得出**的只给线索。

只输出文本：不落文件、不建分支或工作区、不验收、不替用户派给其他 agent。结果要回来被正式验收 → 用 handoff。

## 流程

1. **确定支线话题**：以用户说的为准。说不清要分出去的是哪个话题 → 问一句，不猜。
2. **抽取**：从当前对话里挑出与这个支线相关的信息，逐条判接手方查不查得出（判据见下）。与支线无关的主讨论内容不进 prompt。
3. **判断回流**：主讨论在等这个支线的结论吗（比如主讨论的某个决定被它卡住）？在等 → 写「交回要求」；不等 → 不写。
4. **起草**：按「候选项」顺序组织，语言跟随当前对话。
5. **自检**，两道都过才输出：
   - 查不出的写全了吗？漏了，接手方会重新纠结已定的事、重提已否决的方案、或违背用户偏好。
   - 查得出的是不是只给了线索？逐条找有没有文件内容、代码结构、仓库文档的摘要或推测被写进来，有就删到只剩位置和用途。
6. **输出**：prompt 放在一个代码块里。代码块外最多一句说明。

## 判据：查不查得出

| 信息在哪 | 处理 |
|---|---|
| 磁盘、仓库、接手方能访问的系统 | **线索**：位置 + 为什么相关，不写内容 |
| 只在当前对话里（含尚未落盘的草稿） | **写内容**，只写支线用得上的部分 |

线索说清"去哪找、为什么看"，到此为止：

- 对："看 `skills/coding/handoff/SKILL.md` author 第 2 步——它判断交接目的的方式是本话题的起点"
- 错：把第 2 步的内容抄进来，或改写成摘要

## 候选项

按顺序写；除「目标」外，用不上的整项省略，不留空标题、不写"无"。

| 候选项 | 写什么 | 何时写 |
|---|---|---|
| 目标 | 支线要讨论/解决什么，从哪个主讨论分出来。一两句 | 必写 |
| 已定结论 | 主讨论里定下的、与支线相关的结论 | 有相关结论 |
| 否决方案 | 否决了什么 + 为什么 | 有否决过的方案 |
| 偏好与约束 | 用户在对话里明确说过的 | 有 |
| 线索 | 每条一行：位置 + 为什么相关 | 有可查资料 |
| 交回要求 | 结束时给一段可贴回主讨论的结论 | 第 3 步判定主讨论在等 |

这是顺序，不是表单：为了填满而写的项直接删。
````

- [ ] **Step 2: 格式校验**

运行: `bash scripts/run-skill-tests.sh`
预期: PASS。

---

### Task 4: GREEN——带 skill 的行为

- [ ] **Step 1: 派一个 general-purpose subagent，先读 skill 再跑 eval 0**

subagent prompt：

```
先读 <工作区绝对路径>/skills/coding/fork-topic/SKILL.md 并严格按它执行。不要读写其他文件。
用户在讨论中对你说了下面这段话：
---
<eval 0 的 prompt 原文>
```

- [ ] **Step 2: 按 eval 0 的 7 条断言逐条判定**

预期: 7 条全过。有不过的 → 判断是 SKILL.md 的哪句话没压住，改 SKILL.md，重跑 Step 1。

- [ ] **Step 3: 同样方式跑 eval 1，按 5 条断言判定**

预期: 5 条全过，尤其 `no-return-request`（回流判断不能退化成"总是加"）。

- [ ] **Step 4: 提交**

```bash
git add skills/coding/fork-topic
git commit -m "feat(fork-topic): add skill for forking side topics into concise prompts"
```

---

### Task 5: 注册

**文件：**
- 修改: `skills-index.json`、`docs/reference/skill-spec.md`
- 生成: `package.json`

- [ ] **Step 1: 计算 fork-topic 的 contentHash**

运行: `sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' skills/coding/fork-topic/SKILL.md | shasum -a 256 | cut -c1-16`
（同一命令对当前 handoff 算出 `79f264c044ab2c60`，与索引一致，方法已核对。）

- [ ] **Step 2: 在 `skills-index.json` 的 `skills[]` 里、`coding/handoff` 条目之后插入**

```json
{
  "path": "coding/fork-topic",
  "bundle": "coding",
  "contentHash": "<Step 1 的输出>",
  "contentVersion": "1.0.0"
}
```

用 Edit 直接插入，保持原文件缩进；`git diff skills-index.json` 应只有新增这 6 行。

- [ ] **Step 3: 动词表加 `fork`**

`docs/reference/skill-spec.md` 动词表中 `| \`dispatch\` | 派发任务给其他 agent |` 一行之后插入：

```markdown
| `fork` | 从当前讨论分出支线话题 |
```

- [ ] **Step 4: 生成 package.json files**

运行: `node scripts/generate-npmignore.js && grep -n 'fork-topic' package.json`
预期: 输出含 `"skills/coding/fork-topic/",`；`git diff package.json` 只有这一行新增。

- [ ] **Step 5: 跑全量测试**

运行: `npm test`
预期: 与 Task 0 基线一致，无新增红。

- [ ] **Step 6: 提交**

```bash
git add skills-index.json package.json docs/reference/skill-spec.md
git commit -m "chore(fork-topic): register skill and add fork to verb table"
```

---

### Task 6: handoff 迁出背景传递场景

**文件：**
- 修改: `skills/coding/handoff/SKILL.md:4`（version）、`:33`
- 修改: `skills/coding/handoff/assets/handoff-template.md:42`
- 修改: `skills/coding/handoff/evals/evals.json`（删 id 3）
- 修改: `skills-index.json`（handoff 条目）

- [ ] **Step 1: SKILL.md 第 33 行**

原文：

```
2. **判断目的**：从当前对话判断这次交接是为了什么——不套预设分类，一句自然语言判断即可（例如"接手方续做同一个实现任务"或"把讨论结论作为背景传给接手方去开展新话题"）。这句话会写进文档开头的"交接目的"，且始终存在，不可省略。
```

改为：

```
2. **判断目的**：从当前对话判断这次交接是为了什么——不套预设分类，一句自然语言判断即可（例如"接手方续做同一个实现任务"）。这句话会写进文档开头的"交接目的"，且始终存在，不可省略。只是带着讨论结论去开新话题、结果不需要回来验收的，不走 handoff，用 fork-topic。
```

- [ ] **Step 2: SKILL.md 版本**

`version: "1.12.0"` → `version: "1.13.0"`

- [ ] **Step 3: 模板第 42 行**

原文中的这一段：

```
任务续做型写成可证伪的硬判据（逐条对/错，如 "slugify('Hello World') === 'hello-world'"）；背景传递型可以是软判据（如"接手方理解背景并能基于此推进新话题"）。
```

改为：

```
实现类任务写成可证伪的硬判据（逐条对/错，如 "slugify('Hello World') === 'hello-world'"）；产出难以逐条判定的（如文档、调研结论）可以是软判据。
```

- [ ] **Step 4: 删 eval #3**

从 `skills/coding/handoff/evals/evals.json` 删掉 `"id": 3, "name": "author-background-only-handoff"` 整个对象（含其后逗号）。其余 eval 的 id 不重排。

运行: `python3 -c "import json;print([e['id'] for e in json.load(open('skills/coding/handoff/evals/evals.json'))['evals']])"`
预期: `[0, 1, 2, 4]`

- [ ] **Step 5: 更新 handoff 的索引条目**

运行: `sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' skills/coding/handoff/SKILL.md | shasum -a 256 | cut -c1-16`
把输出写进 `skills-index.json` 中 `coding/handoff` 的 `contentHash`，`contentVersion` 改为 `"1.13.0"`。

- [ ] **Step 6: 确认没有残留引用**

运行: `grep -rn '背景传递\|讨论结论作为背景' skills/coding/handoff`
预期: 无输出。

- [ ] **Step 7: 跑全量测试**

运行: `npm test`
预期: 与基线一致，无新增红。

- [ ] **Step 8: 提交**

```bash
git add skills/coding/handoff skills-index.json
git commit -m "feat(handoff): route background-only handoffs to fork-topic (1.13.0)"
```

---

### Task 7: 收尾核对

- [ ] **Step 1: 规格逐节对照**

对照规格每一节，确认有对应改动：定位/边界/流程/判据/候选项 → Task 3；命名 → Task 5；handoff 同步 → Task 6；测试 → Task 1/2/4/5/6。

- [ ] **Step 2: 汇报**

汇报 RED/GREEN 两轮的断言结果、`npm test` 结果、未验证项（触发词是否与 handoff 互撞，本计划未做触发测试）。不合并；合并等用户明确说。
