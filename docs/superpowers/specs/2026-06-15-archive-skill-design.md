---
title: archive-skill design
date: 2026-06-15
status: approved
migrated: 2026-06-21
implemented_in:
  - skills/meta/archive-skill/SKILL.md
---

# archive-skill — 设计文档

## 概览

`archive-skill` 是一个 meta skill，用于将已退役的 skill 从活跃注册表移入 `skills/archived/`，并自动完成 git 提交与合并。

- **位置**：`skills/meta/archive-skill/SKILL.md`
- **bundle**：`meta`
- **触发**：用户指令含 skill 名，如 "archive article-fetcher"、"归档 url-extract"、"retire this skill"

---

## 执行流程

### Step 1 — 模糊匹配

从用户指令中提取 skill 名关键字，在 `skills-index.json` 的 `skills[]` 中搜索：

| 匹配结果 | 行为 |
|---------|------|
| 完全匹配 path 末段 | 直接进 Step 2 |
| 部分匹配（1 个） | 展示候选，用户确认后进 Step 2 |
| 部分匹配（多个） | 列出候选列表，用户选择后进 Step 2 |
| 0 匹配 | 报错退出 |

### Step 2 — 确认摘要

展示以下操作预览，**等待用户明确确认**：

```
即将归档 <name>：

  移动：skills/<category>/<name>/ → skills/archived/<name>/
  从 skills-index.json 移除：{ "path": "<category>/<name>", "bundle": "<bundle>" }
  更新 bundleMeta.<bundle>：去掉 "<name>" 描述
  重新生成：package.json files[] 和 .npmignore

确认继续？(y/n)
```

用户输入 `n` 则中止，不做任何修改。

### Step 3 — 文件移动

```bash
# 记录当前分支
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# 检查目标路径是否已存在
if [ -d "skills/archived/<name>" ]; then
  # 报错，提示用户手动处理后重试
  exit 1
fi

mv skills/<category>/<name>/ skills/archived/<name>/
```

### Step 4 — 更新 skills-index.json

- 从 `skills[]` 移除对应条目
- 从 `bundleMeta.<bundle>` 的描述字符串中删除该 skill 名
  - 描述格式：`"研究工具（a + b + c）"` → 去掉 `" + <name>"` 或 `"<name> + "`

### Step 5 — 重新生成打包配置

```bash
node scripts/generate-npmignore.js
```

验证输出中 `skills/archived/<name>/` 出现在 `.npmignore` 排除列表。

### Step 6 — Git commit

```bash
git checkout -b chore/archive-<name>
git add skills/archived/<name>/
git add skills/<category>/<name>/   # 记录删除
git add skills-index.json package.json .npmignore
git commit -m "chore: archive <name> skill"
```

### Step 7 — 合并回原分支

```bash
git checkout <ORIGINAL_BRANCH>
git merge --no-ff chore/archive-<name>
```

完成后提示：
```
✓ <name> 已归档
  archived 路径：skills/archived/<name>/
  分支 chore/archive-<name> 可手动删除（git branch -d chore/archive-<name>）
```

---

## 边界情况

| 情况 | 处理 |
|------|------|
| `skills/archived/<name>/` 已存在 | Step 3 前报错退出，提示用户手动处理 |
| skill 在磁盘但不在 index | 提示"未在 index 中找到，仅做文件移动"，跳过 Step 4 |
| `generate-npmignore.js` 执行失败 | 报错，不执行 git 操作，保留文件供用户检查 |
| 当前有未提交变更 | Step 6 前检测，提示用户先 commit 或 stash |
| bundleMeta 描述中无该 skill 名 | 跳过描述更新，不报错 |

---

## 不在范围内

- 批量归档多个 skill
- 自动删除归档分支
- 恢复（un-archive）操作
