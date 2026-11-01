# capture-intent 实施计划

**目标：** 新增 `capture-intent` skill，把随口提出的需求立成 Agent Canvas 需求节点；同时把 `capture-todo` 收窄为只能人工调用。

**架构：** `capture-intent` 是一份纯 SKILL.md，调用 `agent-canvas-ctl` 完成全部操作。字段名、参数名、枚举每次运行时用 `describe-action` 实时读取，skill 里只写各字段的语义。`capture-todo` 正文不动，只改 frontmatter 与 description，并新增 Codex 侧的 `agents/openai.yaml`。

**技术栈：** Markdown skill、`agent-canvas-ctl`、`skills-index.json` 登记、`npm test`（bats + node --test）。

**依据：** `docs/superpowers/specs/2026-10-27-capture-intent-design.md`

---

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `skills/creative/capture-todo/SKILL.md` | 修改 frontmatter | 关闭模型隐式调用，改 description，升版本 4.6.0 |
| `skills/creative/capture-todo/agents/openai.yaml` | 创建 | Codex 侧关闭隐式调用 |
| `skills/agent-canvas/capture-intent/SKILL.md` | 创建 | 新 skill 本体 |
| `skills-index.json` | 修改 | 新登记 capture-intent；更新 capture-todo 的 hash/版本；更新 `bundleMeta.agent-canvas` 和 `bundleMeta.creative` 描述 |
| `package.json` | 由脚本重新生成 `files` | 把新 skill 打进 npm 包 |
| `CHANGELOG.md` | 修改 `[Unreleased]` | 记录两项变更 |

`contentHash` 算法（已用现有条目核对过，与 `tests/skill-portability.test.mjs` 一致）：

```bash
node -e "const c=require('crypto'),f=require('fs');const b=f.readFileSync(process.argv[1],'utf8');console.log(c.createHash('sha256').update(b.replace(/^version:.*\$/m,'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0,16))" <SKILL.md 路径>
```

---

### Task 1: capture-todo 收窄为人工调用

**文件：**
- 修改: `skills/creative/capture-todo/SKILL.md:1-6`（frontmatter）
- 创建: `skills/creative/capture-todo/agents/openai.yaml`

- [ ] **Step 1: 写失败检查**

```bash
grep -q '^disable-model-invocation: true$' skills/creative/capture-todo/SKILL.md \
  && test -f skills/creative/capture-todo/agents/openai.yaml \
  && grep -q '^version: "4.6.0"$' skills/creative/capture-todo/SKILL.md \
  && echo PASS || echo FAIL
```

- [ ] **Step 2: 运行确认失败**

预期输出: `FAIL`

- [ ] **Step 3: 改 frontmatter**

把 `skills/creative/capture-todo/SKILL.md` 开头的 frontmatter 整段替换为（正文一字不改）：

```yaml
---
name: capture-todo
version: "4.6.0"
user_invocable: true
description: "Manual invocation only: '/capture-todo'. Add a requirement, task, or feature request to a project's TODO.md from any working directory. In Agent Canvas projects use capture-intent instead, which files the need as a requirement node."
disable-model-invocation: true
---
```

- [ ] **Step 4: 创建 `agents/openai.yaml`**

```yaml
policy:
  allow_implicit_invocation: false
```

- [ ] **Step 5: 运行确认通过**

重跑 Step 1 的命令，预期输出: `PASS`

- [ ] **Step 6: 更新索引里 capture-todo 的 hash 与版本**

用上面的算法算 `skills/creative/capture-todo/SKILL.md` 的 hash，把 `skills-index.json` 中 `"path": "creative/capture-todo"` 条目的 `contentHash` 改为算出值、`contentVersion` 改为 `"4.6.0"`。

核对：

```bash
node -e "const i=require('./skills-index.json');console.log(JSON.stringify(i.skills.find(s=>s.path==='creative/capture-todo')))"
```

预期：`contentVersion` 为 `4.6.0`，`contentHash` 与刚算出的值相同。

- [ ] **Step 7: 提交**

```bash
git add skills/creative/capture-todo/SKILL.md skills/creative/capture-todo/agents/openai.yaml skills-index.json
git commit -m "feat(capture-todo): restrict to manual invocation (4.6.0)"
```

---

### Task 2: 编写 capture-intent SKILL.md

**文件：**
- 创建: `skills/agent-canvas/capture-intent/SKILL.md`

- [ ] **Step 1: 写失败检查**

检查三件事：文件存在且 `name` 等于目录名；description 不含中文（F3）；正文没有写死字段名、参数名和枚举值（spec「测试」一节）。

```bash
f=skills/agent-canvas/capture-intent/SKILL.md
test -f "$f" \
  && grep -q '^name: capture-intent$' "$f" \
  && perl -CSD -ne 'exit 1 if /^description:.*\p{Han}/' "$f" \
  && perl -ne 'if (/--(title|description|priority|status|acceptance-criteria)\b|\b(low|medium|high|open|in_progress)\b/) { print "$.: $_"; $hit=1 } END { exit($hit ? 1 : 0) }' "$f" \
  && echo PASS || echo FAIL
```

- [ ] **Step 2: 运行确认失败**

预期输出: `FAIL`（文件不存在）

- [ ] **Step 3: 写入 SKILL.md**

完整内容：

````markdown
---
name: capture-intent
description: "Capture a need the user mentions for later as an Agent Canvas requirement node. Triggers on casual phrasing like 'we should do X later', 'note this requirement', 'add this to the backlog', 'remember to build X'. Writes to the current canvas by default, or to another project's running canvas when the user names it. Not for the requirement the current session is implementing (use capture-requirement)."
user_invocable: true
version: "1.0.0"
---

# 记录意图（capture-intent）

如果 `agent-canvas-ctl` 命令不存在，这个 skill 不适用，直接跳过。

把用户随口提出、以后要做的需求立成一个需求节点。顺序：澄清 → 定画布 → 查 schema → 查重 → 确认 → 写入。完整的需求描述是查重和起标题的依据，顺序不能反。

与 `capture-requirement` 的分界：那个记的是本会话**正在实现**、已经有 spec 的需求，并连 `implements`；本 skill 记以后要做的需求，**不连任何关系边，也不放上画布**。

## 1. 澄清需求（2-3 轮）

只问需求、不问方案；上下文里已经明确的直接跳过。每次只问一个问题，优先给选项。

1. **需求**——要解决什么问题、实现什么功能？用户已说清楚就复述确认。
2. **紧急程度**——默认不问；用户暗示紧急或不重要时据此定档。
3. **背景**——为什么现在提出来（可选）。

不主动问验收。用户描述里已经带了完成标准（"做完应该能……"），拆出来留作验收文字。

## 2. 确定目标画布

- 用户没点名别的项目 → 当前画布，后面的命令不带 `--canvas`。
- 用户点名了别的项目：
  1. 跑 `agent-canvas-ctl --canvas /nonexistent resolve-canvas`。它必然以退出码 1 失败，stderr 逐行列出当前可用画布的绑定路径。
  2. 按项目名匹配其中一条路径；有多条候选就让用户选。
  3. 跑 `agent-canvas-ctl --canvas <路径> resolve-canvas`，退出码为 0 才算定下来。之后每条命令都在子命令**之前**带同一个 `--canvas <路径>`。
- 清单里没有该项目 → 报告「<项目> 的画布没开，记不进去」，然后停止。不改写到别的画布，也不直接改 `~/.agent-canvas/` 下的文件。

## 3. 查 schema

每次都查，不凭记忆：

```bash
agent-canvas-ctl describe-action create_requirement_node
```

从 `inputSchema` 取字段、类型、枚举和必填项；从 `bindings` 里 `surface` 为 `cli` 的那条取 `usage` 和 `args.flags`。本 skill 不写字段名和取值，只在下一节写各字段的语义；按 schema 里的字段名和 `description` 把语义对到字段上。

- 某条语义对不上任何字段 → 跳过它，在最终报告里说明。
- schema 有必填字段，而下一节没有对应的语义 → 停止，报告这个字段，不去猜。
- 枚举档数和下一节描述的不一样 → 按相对位置映射，在确认摘要里标出来。

## 4. 各字段的写法

- **标题**：`<对象> <类型> <描述>`，与画布上已有的需求标题一致，例如「feed feat 实现 Creator/Channel 名册架构」「publish-skill fix 命名检查由阻断改为建议」。
  - 对象：受影响的 skill、模块或子系统名。
  - 类型：feat / fix / refactor / docs / chore。
  - 描述：写出关键区分点，不用「优化」「修复」这类泛词，也不堆细节。
- **需求正文**：写做什么、为什么。**不写怎么做**。篇幅以说清楚为准。
- **优先级**：默认取中间档；用户表示紧急取最高档，表示不重要取最低档。
- **验收文字**：只在第 1 步拆出了完成标准时才填，照用户原意写，不替用户补全。
- **状态**：不传，取缺省值。
- **验收依据文件**：不传（没有 spec）。

## 5. 查重

```bash
agent-canvas-ctl [--canvas <路径>] search-nodes <需求关键词> --limit 5
```

只看结果里 `kind` 为 requirement 的节点。有语义重叠时问：

> 发现可能重叠的需求 **[标题]（[编号]）**，跳过还是仍然新建？

用户选跳过就到此结束。

## 6. 确认摘要

> 记录为：**[项目/画布]** — [标题]，[优先级]。确认吗？

有枚举映射或被跳过的字段，一并列出。用户确认后才写入。

## 7. 写入与报告

按第 3 步取到的 `usage` 拼出 `create-requirement-node` 命令，只传第 4 步对得上的字段；点名了别的项目时，`--canvas <路径>` 放在子命令之前。

- 成功：报告需求编号（返回里的 `requirementId`，形如 YYMMDD-XX）和标题。
- 失败：把 stderr 原样报出，不重试，也不改参数重跑。
````

- [ ] **Step 4: 运行确认通过**

重跑 Step 1 的命令，预期输出: `PASS`

- [ ] **Step 5: 提交**

```bash
git add skills/agent-canvas/capture-intent/SKILL.md
git commit -m "feat(capture-intent): add skill to file casual needs as requirement nodes"
```

---

### Task 3: 登记到 skills-index 与 npm 包

**文件：**
- 修改: `skills-index.json`（`bundleMeta.agent-canvas`、`bundleMeta.creative`、`skills[]` 中 capture-requirement 之后）
- 重新生成: `package.json` 的 `files`

- [ ] **Step 1: 写失败检查**

```bash
node -e "
const i=require('./skills-index.json');
const e=i.skills.find(s=>s.path==='agent-canvas/capture-intent');
const p=require('./package.json');
const ok=e&&e.bundle==='agent-canvas'&&e.installScope==='project'&&e.contentVersion==='1.0.0'
  &&i.bundleMeta['agent-canvas'].includes('capture-intent')
  &&p.files.includes('skills/agent-canvas/capture-intent/');
console.log(ok?'PASS':'FAIL')"
```

- [ ] **Step 2: 运行确认失败**

预期输出: `FAIL`

- [ ] **Step 3: 加索引条目**

算 `skills/agent-canvas/capture-intent/SKILL.md` 的 hash，在 `skills-index.json` 的 `"path": "agent-canvas/capture-requirement"` 条目之后插入：

```json
    {
      "path": "agent-canvas/capture-intent",
      "bundle": "agent-canvas",
      "installScope": "project",
      "contentHash": "<算出的 16 位 hash>",
      "contentVersion": "1.0.0"
    },
```

- [ ] **Step 4: 更新 bundleMeta 描述**

`bundleMeta.agent-canvas` 改为：

```
"Agent Canvas 内置 skill（agent-canvas-control — 节点与画布操控；describe-node/relate-node/capture-requirement/relation-review/close-node — 画布节点生命周期治理；capture-intent — 随口需求立成需求节点；judge-release — 对照验收标准逐条取证并写结论）"
```

`bundleMeta.creative` 改为：

```
"创意工具（capture-todo（仅人工调用）+ capture-insight）"
```

- [ ] **Step 5: 重新生成打包清单**

```bash
node scripts/generate-npmignore.js
git diff --stat package.json
```

预期：`package.json` 的 `files` 多出 `skills/agent-canvas/capture-intent/`，没有别的变化。

- [ ] **Step 6: 运行确认通过**

重跑 Step 1 的命令，预期输出: `PASS`

- [ ] **Step 7: 提交**

```bash
git add skills-index.json package.json
git commit -m "chore(capture-intent): register in skills-index and npm files"
```

---

### Task 4: CHANGELOG

**文件：**
- 修改: `CHANGELOG.md`（`## [Unreleased]` 一节）

- [ ] **Step 1: 写入条目**

在 `## [Unreleased]` 下加一个 `### Added` 小节（放在已有的 `### Changed` 之前），并在 `### Changed` 末尾追加一条：

```markdown
### Added
- `capture-intent`：1.0.0，新 skill。把随口提出、以后要做的需求立成 Agent Canvas 需求节点（取代 capture-todo 在画布项目里的角色）：2-3 轮澄清 → 定目标画布（默认当前画布，点名别的项目时写到它已打开的画布，没开就停止）→ 运行时用 `describe-action` 读需求节点 schema，skill 里只写字段语义、不写死字段名和枚举 → `search-nodes` 查重 → 确认 → 写入。不连关系边、不放上画布
```

```markdown
- `capture-todo`：升至 4.6.0，改为只能人工调用（Claude 侧 `disable-model-invocation: true`，Codex 侧 `agents/openai.yaml` 关闭隐式调用），随口触发词移交 capture-intent。正文不变，后续走 archive-skill 退役
```

- [ ] **Step 2: 提交**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add capture-intent and capture-todo entries"
```

---

### Task 5: 全量测试

- [ ] **Step 1: 跑测试**

```bash
npm test
```

预期：全部通过。若有失败，先在 `staging` 的分叉点上跑同一条命令，归因是本次引入的还是既有的；本次引入的修掉再继续，既有的在汇报里写明。

- [ ] **Step 2: 发布前检查**

调用 `publish-skill` 检查 `agent-canvas/capture-intent` 和 `creative/capture-todo`。预期：F1–F6、R1–R3 全部通过，F8（hash/版本）通过；F7/F9 只是警告，不阻断。

---

### Task 6: 画布实跑验收（V1、V3）

在当前画布节点里执行，全部测试节点跑完后删掉。

- [ ] **Step 1: 查重路径**

1. 先手动建一条对照节点：`agent-canvas-ctl create-requirement-node --title "capture-intent test 对照需求 甲"`，记下返回的 `nodeId`（记为 A）。
2. 按新 SKILL.md 走流程，需求说成「capture-intent test 对照需求 甲的变体」。预期：第 5 步列出 A 并提问；选「跳过」，没有新节点建出来。

- [ ] **Step 2: 正常写入路径（V1）**

按新 SKILL.md 走一遍，需求用「capture-intent test 以后给 X 加导出功能，不急」。预期：
- 第 3 步实际跑了 `describe-action`；
- 确认摘要里优先级是最低档；
- 写入后返回 `requirementId`，记下 `nodeId`（记为 B）。

核对：

```bash
agent-canvas-ctl get-node <B>
agent-canvas-ctl node-relations <B>
```

预期：kind 为 requirement，status 为缺省的 open，标题符合 `<对象> <类型> <描述>`，priority 与确认摘要一致；关系为空。

- [ ] **Step 3: 未打开画布路径（V3）**

1. 跑 `agent-canvas-ctl list-nodes`，记下节点数 N。
2. 按 SKILL.md 走流程，点名一个不在 `resolve-canvas` 可用清单里的项目（例如 `Video-Learner`；先跑一次 `--canvas /nonexistent resolve-canvas` 确认它确实不在清单里）。预期：第 2 步报告「画布没开」后停止。
3. 再跑一次 `agent-canvas-ctl list-nodes`。预期：节点数仍为 N。

- [ ] **Step 4: 清理**

```bash
agent-canvas-ctl purge-node <A> --yes
agent-canvas-ctl purge-node <B> --yes
```

- [ ] **Step 5: 记录结果**

把 Step 1–3 的实际输出要点（命令、退出码、关键字段）写进汇报。V2（随口触发走 capture-intent，capture-todo 只能 `/capture-todo` 调用）需要人工裁决：在新会话里装上合并后的版本再测，在汇报里标为「待用户裁决」。

---

## 合并之后（不在本计划内执行，待用户说「合并」）

1. 在本 worktree 里 `git rev-parse --abbrev-ref HEAD` 核对是 `feature/capture-intent`，然后跑 `scripts/merge-to-staging.sh`。
2. 同步装机副本（从 staging 取，不从工作树 rsync）：

```bash
tmp=$(mktemp -d)
git archive staging skills/agent-canvas/capture-intent skills/creative/capture-todo | tar -x -C "$tmp"
rsync -a --exclude '.DS_Store' "$tmp/skills/agent-canvas/capture-intent/" ~/.claude/skills/capture-intent/
rsync -a --exclude '.DS_Store' "$tmp/skills/creative/capture-todo/" ~/.claude/skills/capture-todo/
grep '^version:' ~/.claude/skills/capture-intent/SKILL.md ~/.claude/skills/capture-todo/SKILL.md
```

预期：分别是 `1.0.0` 和 `4.6.0`。

3. 用 capture-intent 把「agent-canvas 离线画布写入」记到 agent-canvas 画布上（spec「未决与风险」第一条）。
