---
name: archive-skill
description: "Archive or retire a skill from the active registry. Moves it to skills/archived/, removes it from skills-index.json, regenerates packaging config, and commits on a chore branch merged back to the original branch. Triggers: archive skill, retire skill, 归档 skill, 退役 skill, deprecate skill."
user_invocable: true
version: "1.0.0"
---

# archive-skill

将一个已退役的 skill 从活跃注册表移入 `skills/archived/`，自动完成文件操作、index 更新、打包配置重新生成，并提交到 git。

---

## Step 1 — 模糊匹配

从用户指令中提取 skill 名关键字，在 `skills-index.json` 的 `skills[]` 中搜索 path 末段：

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
node -e "
  const idx = JSON.parse(require('fs').readFileSync('${REPO_ROOT}/skills-index.json','utf8'));
  idx.skills.forEach(s => console.log(s.path));
"
```

| 匹配结果 | 行为 |
|---------|------|
| 完全匹配 path 末段 | 直接进 Step 2 |
| 部分匹配（1 个） | 展示候选，用户确认后进 Step 2 |
| 部分匹配（多个） | 列出候选列表，用户选择后进 Step 2 |
| 0 匹配 | 报错退出 |

---

## Step 2 — 确认摘要

展示操作预览，**等待用户明确确认后再执行**：

```
即将归档 <name>：

  移动：skills/<category>/<name>/ → skills/archived/<name>/
  从 skills-index.json 移除：{ "path": "<category>/<name>", "bundle": "<bundle>" }
  更新 bundleMeta.<bundle>：去掉描述中的 "<name>"
  重新生成：package.json files[] 和 .npmignore
  Git：chore/archive-<name> → merge 回 <current-branch>

确认继续？(y/n)
```

用户输入 `n` 则中止，不做任何修改。

---

## Step 3 — 前置检查

执行前检查两个边界情况：

**1. 未提交变更**
```bash
git status --short
```
若有未提交修改，提示用户先 commit 或 stash，然后中止。

**2. 归档目标已存在**
```bash
ls skills/archived/<name>/ 2>/dev/null
```
若已存在，报错提示用户手动处理后重试，中止。

---

## Step 4 — 文件移动

记录当前分支，创建归档分支，移动目录：

```bash
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git checkout -b chore/archive-<name>

mv skills/<category>/<name>/ skills/archived/<name>/
```

---

## Step 5 — 更新 skills-index.json

**移除 skills[] 条目：**
读取 `skills-index.json`，删除 `path` 末段为 `<name>` 的条目，写回文件。

**更新 bundleMeta 描述：**
描述格式为 `"研究工具（a + b + c）"`，从中删除 `<name>`：
- 若在中间：`" + <name>"` 或 `"<name> + "` → 删除
- 若描述中无该 skill 名：跳过，不报错

---

## Step 6 — 重新生成打包配置

```bash
node scripts/generate-npmignore.js
```

验证输出包含 `skills/archived/<name>/` 已加入 `.npmignore` 排除列表。若脚本执行失败，报错并中止，不执行 git 操作，保留已修改的文件供用户检查。

---

## Step 7 — Git commit

```bash
git add skills/archived/<name>/
git add skills/<category>/<name>/
git add skills-index.json package.json .npmignore
git commit -m "chore: archive <name> skill"
```

---

## Step 8 — 合并回原分支

```bash
git checkout <ORIGINAL_BRANCH>
git merge --no-ff chore/archive-<name>
```

完成后输出摘要：

```
✓ <name> 已归档

  归档路径：skills/archived/<name>/
  已从 skills-index.json 移除
  已更新 package.json + .npmignore

  分支 chore/archive-<name> 可手动删除：
    git branch -d chore/archive-<name>
```

---

## 边界情况汇总

| 情况 | 处理 |
|------|------|
| `skills/archived/<name>/` 已存在 | Step 3 中止，提示手动处理 |
| 当前有未提交变更 | Step 3 中止，提示 commit 或 stash |
| skill 在磁盘但不在 index | 提示"仅做文件移动"，跳过 Step 5 |
| `generate-npmignore.js` 失败 | Step 6 中止，不执行 git 操作 |
| bundleMeta 描述无该 skill 名 | 跳过描述更新，继续 |

---

## 不在范围内

- 批量归档多个 skill
- 自动删除归档分支
- 恢复（un-archive）操作
