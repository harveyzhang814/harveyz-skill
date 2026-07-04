# domain-vocab Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a project-level domain vocabulary skill that lets users and agents add, query, update, and remove business terms stored in `hskill/domain-vocab/vocab.md`.

**Architecture:** A single SKILL.md file under `skills/coding/domain-vocab/` containing all skill instructions. No executable code — the skill is pure AI instructions that drive Claude to read/write `vocab.md` in the current project's `hskill/domain-vocab/` directory.

**Tech Stack:** Markdown (SKILL.md), JSON (skills-index.json registration), bats-core (test validation via existing `tests/skills.bats`)

## Global Constraints

- `name` field in SKILL.md frontmatter must equal directory name: `domain-vocab`
- `version` must be valid semver: `1.0.0`
- `bundle` must be `coding` (already in bundleMeta)
- `installScope` must be `project` (vocabulary is per-project, not global)
- No contentHash or contentVersion needed at authoring time — the installer generates these

---

### Task 1: Write SKILL.md

**Files:**
- Create: `skills/coding/domain-vocab/SKILL.md`

**Interfaces:**
- Produces: a SKILL.md that `tests/skills.bats` can validate (frontmatter with name/description/version matching constraints above)

- [ ] **Step 1: Create the directory**

```bash
mkdir -p skills/coding/domain-vocab
```

- [ ] **Step 2: Write SKILL.md**

Create `skills/coding/domain-vocab/SKILL.md` with this exact content:

```markdown
---
name: domain-vocab
version: "1.0.0"
description: Use when you need to add, query, update, or remove project-specific domain terms — invoke with /domain-vocab add|query|update|remove <term> to manage a shared vocabulary file at hskill/domain-vocab/vocab.md
user_invocable: true
---

# Domain Vocabulary

## 概述

管理项目级领域术语字典。词汇表存于 `hskill/domain-vocab/vocab.md`，供用户和 agent 定义、查询业务专有名词。每个术语包含：规范名称、定义、Avoid 列表。

词汇表只存业务领域概念（跨前后端、跨 AI/人类对话都会出现的词）。函数名、变量名等技术命名不进词汇表。

## 用法

```
/domain-vocab add <term>
/domain-vocab query <term>
/domain-vocab update <term>
/domain-vocab remove <term>
```

## 词汇文件

`<project-root>/hskill/domain-vocab/vocab.md`

```markdown
# Domain Vocabulary

## 术语名
定义文本（一到两句话，说清楚概念是什么）。
_Avoid_: 旧叫法, 混用词
```

## 操作

### add `<term>`

1. 检查 `hskill/domain-vocab/vocab.md` 是否存在 `## <term>` section（大小写不敏感匹配）
2. 若已存在：输出"术语 '<term>' 已存在，请用 `update` 修改"并退出
3. 若不存在：
   - 提示"请输入 **<term>** 的定义："，等待用户输入
   - 提示"请输入 Avoid 列表（逗号分隔，可留空）："，等待用户输入
   - 若目录 `hskill/domain-vocab/` 不存在，创建它
   - 若 `vocab.md` 不存在，创建并写入 `# Domain Vocabulary\n`
   - 在文件末尾追加：
     ```
     \n## <term>\n<定义>\n_Avoid_: <avoid列表>
     ```
     若 Avoid 为空，省略 `_Avoid_:` 行

### query `<term>`

1. 检查 `hskill/domain-vocab/vocab.md` 是否存在；若不存在，输出"词汇表尚未初始化，请先用 `add` 添加术语"并退出
2. 按 `## <term>` 标题匹配（大小写不敏感），读取该 section 直到下一个 `##` 或文件末尾
3. 返回该 section 的完整内容（定义 + Avoid）
4. 若未找到，输出"未找到术语 '<term>'"，然后列出 vocab.md 中所有 `##` 标题作为已有术语名

### update `<term>`

1. 检查词汇表存在且包含该术语；若文件不存在或术语不存在，输出对应错误后退出
2. 展示当前条目的完整内容
3. 提示"新定义（留空保持不变）："，等待用户输入
4. 提示"新 Avoid 列表（留空保持不变）："，等待用户输入
5. 用新值替换该 section 内容，写回文件；留空的字段保持原值不变

### remove `<term>`

1. 检查词汇表存在且包含该术语；若不存在，输出对应错误后退出
2. 展示该术语的当前条目
3. 提示"确认删除 '<term>'？(y/N)"，等待用户输入
4. 若输入 `y`：删除该 section（含前后空行），写回文件
5. 若输入其他：输出"已取消"并退出

## Agent 加载约定

本 Skill 不自动注入词汇表到 session 上下文。如需在每次 session 开始时加载术语，在项目 `CLAUDE.md` 中加入：

```markdown
每次 session 开始，读取 `hskill/domain-vocab/vocab.md`（如存在）。
```
```

- [ ] **Step 3: Verify file exists and frontmatter is correct**

```bash
head -6 skills/coding/domain-vocab/SKILL.md
```

Expected output:
```
---
name: domain-vocab
version: "1.0.0"
description: Use when you need to add, query, update, or remove project-specific domain terms...
user_invocable: true
---
```

- [ ] **Step 4: Commit**

```bash
git add skills/coding/domain-vocab/SKILL.md
git commit -m "feat(domain-vocab): add domain-vocab skill SKILL.md"
```

---

### Task 2: Register in skills-index.json and verify tests pass

**Files:**
- Modify: `skills-index.json`

**Interfaces:**
- Consumes: `skills/coding/domain-vocab/SKILL.md` from Task 1
- Produces: `skills-index.json` with `domain-vocab` registered; `npm test` passes

- [ ] **Step 1: Add entry to skills-index.json**

Open `skills-index.json` and add this entry to the `skills` array after the `coding/question-me` entry:

```json
{
  "path": "coding/domain-vocab",
  "bundle": "coding",
  "installScope": "project"
}
```

Also update the `bundleMeta.coding` description to include `domain-vocab`:

```json
"coding": "程序工具（init-workflow + setup-debug + init-goal + question-me + domain-vocab）"
```

- [ ] **Step 2: Verify JSON is valid**

```bash
node -e "JSON.parse(require('fs').readFileSync('skills-index.json','utf8')); console.log('valid')"
```

Expected: `valid`

- [ ] **Step 3: Run tests**

```bash
npm test
```

Expected: all `tests/skills.bats` checks pass for `coding/domain-vocab` — SKILL.md exists, frontmatter has name/description/version, name matches directory, bundle is valid.

- [ ] **Step 4: Commit**

```bash
git add skills-index.json
git commit -m "chore(domain-vocab): register domain-vocab in skills-index.json"
```
