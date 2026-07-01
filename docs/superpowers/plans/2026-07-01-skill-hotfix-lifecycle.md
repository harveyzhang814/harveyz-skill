# Skill Hotfix 生命周期管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 skill hotfix 记录与合并回源仓库的完整机制：fix-skill 成功修复后自动写 HOTFIXES.md，新增 sync-hotfix skill 引导用户逐条合并未同步的 hotfix。

**Architecture:** fix-skill Step 3a 新增一个 append 动作，将修复记录写入安装版 skill 的 `references/HOTFIXES.md`；sync-hotfix 读取该文件，逐条展示未合并条目，引导用户将改动应用到源仓库。两个 skill 共享同一个 HOTFIXES.md 格式规范，单一来源。

**Tech Stack:** Markdown skill files（LLM instructions）、JSON config、bats-core 测试

## Global Constraints

- SKILL.md frontmatter 必须包含 `name`、`version`、`description`、`user_invocable` 字段
- 新 skill 注册到 `skills-index.json` 的 `meta` bundle
- `npm test` 全程保持绿色
- fix-skill 改动范围仅限 Step 3a，其他步骤内容不变
- `merged_back` 只有 `false` / `true` 两个值，无其他状态
- HOTFIXES.md 仅存在于安装版，源仓库不含此文件

---

## File Map

| 操作 | 文件 | 说明 |
|------|------|------|
| Modify | `skills/meta/fix-skill/SKILL.md` | Step 3a 末尾新增 HOTFIXES.md append 逻辑；新增可选输入字段 `platform` |
| Create | `skills/meta/sync-hotfix/SKILL.md` | 新 skill，含完整 4-step 流程 |
| Modify | `skills-index.json` | 注册 sync-hotfix 到 meta bundle |
| Modify | `tests/install.bats` | 新增 sync-hotfix 安装验证测试 |

---

### Task 1：扩展 fix-skill Step 3a，写入 HOTFIXES.md

**Files:**
- Modify: `skills/meta/fix-skill/SKILL.md`

**Interfaces:**
- Consumes: 现有 fix-skill 输入字段 `skill_dir`、`file`、`error`；新增可选 `platform`
- Produces: 安装版 `<skill_dir>/references/HOTFIXES.md` 追加结构化条目

- [ ] **Step 1：在"输入上下文"表格新增 `platform` 字段**

在 `skills/meta/fix-skill/SKILL.md` 的输入表格末尾追加一行：

```markdown
| `platform` | 否 | 当前平台标识（如 `claude`、`codex`、`hermes`），不传则写 `unknown` |
```

完整表格改后：

```markdown
## 输入上下文

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill` | 是 | 调用方 skill 名称 |
| `skill_dir` | 是 | 调用方 skill 绝对路径 |
| `file` | 是 | 出错文件绝对路径（任意类型） |
| `error` | 是 | stderr 原文 + returncode |
| `call_args` | 否 | 验证时重跑脚本所需参数；无则做内容自洽检查 |
| `platform` | 否 | 当前平台标识（如 `claude`、`codex`、`hermes`），不传则写 `unknown` |
```

- [ ] **Step 2：在 Step 3a 末尾追加 HOTFIXES.md append 步骤**

定位 `## Step 3a：成功` 章节，在"删除 `backup_path`"之后、输出 `FIX_RESULT` 之前，追加以下内容：

```markdown
**写入 HOTFIXES.md：**

1. 检查 `skill_dir/references/HOTFIXES.md` 是否存在：
   - 不存在 → 创建文件，写入首行 `# HOTFIXES`
2. 统计文件中现有 `## HF-` 条目数量，记为 `n`，新编号为 `HF-{n+1:03d}`（如 `HF-001`）
3. 根据本轮修复内容生成条目并 append 到文件末尾：
   - `platform`：来自输入字段，未传则 `unknown`
   - `date`：`date +%Y-%m-%d` 输出
   - `file`：`file` 输入字段的文件名部分（`basename $file`）
   - `section`：从本轮实际修改位置推断最近的 markdown 章节标题（如 `## Step 2：...`）；无法定位则写 `unknown`
   - `change`：用一段话描述改前状态和改后状态（根据 diff 内容生成）
   - `reason`：`error` 字段的单句摘要
   - `merged_back: false`

条目格式：

~~~markdown
## HF-001
- platform: claude
- date: 2026-07-01
- file: SKILL.md
- section: "## Step 2：尝试修复"
- change: "原：... 改后：..."
- reason: "..."
- merged_back: false
~~~
```

- [ ] **Step 3：本地人工验证改动范围**

阅读修改后的 `skills/meta/fix-skill/SKILL.md`，确认：
- 输入表格新增了 `platform` 行，其他行未变
- Step 3a 末尾新增了"写入 HOTFIXES.md"段落
- Step 1、Step 2、Step 3b 内容完全未改动

- [ ] **Step 4：运行格式检验**

```bash
npm test
```

期望：全部通过，无新增失败

- [ ] **Step 5：提交**

```bash
git add skills/meta/fix-skill/SKILL.md
git commit -m "feat(fix-skill): Step 3a 成功后写入 HOTFIXES.md"
```

---

### Task 2：创建 sync-hotfix skill

**Files:**
- Create: `skills/meta/sync-hotfix/SKILL.md`

**Interfaces:**
- Consumes: 安装版 `<skill_dir>/references/HOTFIXES.md`；`~/.hskill/sync-hotfix/config.json`；源仓库对应 skill 文件
- Produces: 源仓库文件改动（用户确认后）；HOTFIXES.md 中 `merged_back` 更新为 `true`

- [ ] **Step 1：创建目录**

```bash
mkdir -p skills/meta/sync-hotfix
```

- [ ] **Step 2：写入 SKILL.md**

创建 `skills/meta/sync-hotfix/SKILL.md`，内容如下：

```markdown
---
name: sync-hotfix
version: "1.0.0"
description: "将安装版 skill 中记录的 hotfix 合并回源仓库。读取安装版 references/HOTFIXES.md，逐条展示未合并（merged_back: false）条目，引导用户将改动应用到源仓库对应文件，完成后标记 merged_back: true。"
user_invocable: true
---

# sync-hotfix

## 输入

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill_name` | 是 | 目标 skill 名称（如 `extract-url`） |

---

## 路径解析

**`skill_dir`（安装版路径）** 根据当前平台自动推断，无需用户传入：

| 平台 | skill_dir |
|------|-----------|
| Claude Code | `~/.claude/skills/<skill_name>` |
| Codex | `~/.codex/skills/<skill_name>` |
| Hermes | `~/.hermes/skills/<skill_name>` |

**`source_dir`（源仓库路径）** 从 `~/.hskill/sync-hotfix/config.json` 读取，首次运行时引导初始化。

---

## 初始化流程

检查 `~/.hskill/sync-hotfix/config.json` 是否存在，或 `skills.<skill_name>` 字段是否缺失。若任一条件满足，引导用户填写：

1. **源仓库根目录路径**（如 `/Users/you/Projects/harveyz-skill`）
2. **`<skill_name>` 所在 category**（如 `research`、`meta`、`writing`）

写入配置（合并已有内容，不覆盖其他 skill 的记录）：

```json
{
  "source_root": "/Users/you/Projects/harveyz-skill",
  "skills": {
    "extract-url": "research"
  }
}
```

`source_dir` = `source_root/skills/<category>/<skill_name>`

---

## Step 1：扫描未合并条目

读取 `skill_dir/references/HOTFIXES.md`：

- 文件不存在 → 输出"HOTFIXES.md 不存在，无记录"并退出
- 文件存在但无 `merged_back: false` 条目 → 输出"无待合并条目"并退出
- 筛出所有 `merged_back: false` 的条目，记为待处理列表

输出待处理条目数量及编号列表，供用户了解规模。

---

## Step 2：逐条处理

对待处理列表中每条条目依次执行：

**① 展示条目信息：**

```
[HF-NNN] platform: <platform> | date: <date>
file: <file> | section: <section>
change: <change 全文>
reason: <reason 全文>
```

**② 读取源仓库对应章节：**

打开 `source_dir/<file>`，定位 `section` 字段对应的章节标题，读取该章节全部内容并展示给用户。

**③ 用户选择（三选一）：**

- **应用（A）**：根据 `change` 描述，修改源仓库该章节内容，展示修改结果请用户确认，确认后写入文件 → 进入 Step 3 标记
- **跳过（S）**：本次不处理，`merged_back` 保持 `false`，下次调用时继续出现 → 跳至下一条
- **作废（D）**：源仓库已有相同改动或该 hotfix 不再需要 → 进入 Step 3 标记

---

## Step 3：更新标记

每条处理完（应用或作废）后，立即将 `skill_dir/references/HOTFIXES.md` 中该条目的 `merged_back: false` 改为 `merged_back: true`。

跳过的条目不修改标记。

---

## Step 4：收尾

输出处理摘要：

```
sync-hotfix 完成
已应用：N 条
已作废：N 条
已跳过：N 条
```

若有"已应用"条目，提示用户在源仓库提交改动：

```
请在源仓库提交变更：
  cd <source_root>
  git add skills/<category>/<skill_name>/
  git commit -m "fix(<skill_name>): backport hotfix from <platform>"
```
```

- [ ] **Step 3：人工审阅 SKILL.md 内容**

通读写入的 `skills/meta/sync-hotfix/SKILL.md`，确认：
- frontmatter 四个必填字段齐全
- 路径解析表覆盖三个平台
- 初始化流程说明了 config.json 合并写入（不覆盖其他 skill）
- Step 2 三个选项（A/S/D）逻辑完整
- Step 3 标记更新时机正确（应用和作废立即更新，跳过不更新）

- [ ] **Step 4：运行格式检验**

```bash
npm test
```

期望：全部通过

- [ ] **Step 5：提交**

```bash
git add skills/meta/sync-hotfix/SKILL.md
git commit -m "feat(sync-hotfix): 新增 skill hotfix 合并回源仓库 skill"
```

---

### Task 3：注册 sync-hotfix 并验证安装

**Files:**
- Modify: `skills-index.json`
- Modify: `tests/install.bats`

**Interfaces:**
- Consumes: Task 2 产出的 `skills/meta/sync-hotfix/SKILL.md`
- Produces: `hskill install --skill sync-hotfix` 可正常安装

- [ ] **Step 1：在 skills-index.json 注册**

在 `skills-index.json` 的 `skills` 数组中，紧跟 `meta/fix-skill` 条目之后插入：

```json
{
  "path": "meta/sync-hotfix",
  "bundle": "meta",
  "installScope": "global",
  "contentHash": "",
  "contentVersion": "1.0.0"
}
```

`contentHash` 留空字符串，安装时由 CLI 自动计算（与其他新 skill 同等处理）。

- [ ] **Step 2：写入安装测试**

在 `tests/install.bats` 末尾追加：

```bash
@test "install --skill: sync-hotfix installs SKILL.md to claude skills dir" {
  _install --skill sync-hotfix --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/sync-hotfix/SKILL.md" ]
  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/sync-hotfix/SKILL.md")" = "1.0.0" ]
}
```

- [ ] **Step 3：运行测试确认新测试失败（TDD 红阶段）**

```bash
npm test -- --filter "sync-hotfix"
```

期望：FAIL — 因为 `skills-index.json` 虽已注册但 contentHash 为空，或安装逻辑尚未执行。若 CLI 直接支持空 hash，测试可能已通过，跳至 Step 4 确认。

- [ ] **Step 4：运行完整测试套件**

```bash
npm test
```

期望：全部通过，包含新增的 sync-hotfix 安装测试

- [ ] **Step 5：人工验证安装**

```bash
hskill install --skill sync-hotfix --target claude --scope user --force
ls ~/.claude/skills/sync-hotfix/SKILL.md
```

期望：文件存在

- [ ] **Step 6：提交**

```bash
git add skills-index.json tests/install.bats
git commit -m "chore(sync-hotfix): 注册到 skills-index 并添加安装测试"
```
