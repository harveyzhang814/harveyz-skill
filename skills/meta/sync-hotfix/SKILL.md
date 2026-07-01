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
