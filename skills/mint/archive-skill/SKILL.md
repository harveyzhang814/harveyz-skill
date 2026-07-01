---
name: archive-skill
description: "Archive, retire, deprecate, or sunset a skill from the active registry. Use this skill whenever someone wants to remove a skill from active use — even if they don't use the word 'archive'. Moves it to skills/archived/, removes it from skills-index.json, regenerates packaging config, and commits on a chore branch merged back to the original branch. Triggers: 'archive X skill', 'retire X', 'deprecate X', 'remove X from bundle', 'sunset X skill'."
user_invocable: true
version: "1.1.1"
---

# archive-skill

将一个已退役的 skill 从活跃注册表移入 `skills/archived/`，自动完成文件操作、index 更新、打包配置重新生成，并提交到 git。

---

## Step 1 — 匹配 skill

从用户指令中提取 skill 名关键字，读取 `skills-index.json` 获取所有已注册 skill：

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
node -e "
  const idx = JSON.parse(require('fs').readFileSync('${REPO_ROOT}/skills-index.json','utf8'));
  idx.skills.forEach(s => console.log(s.path));
"
```

在 path 末段（`<category>/<name>` 的 `<name>` 部分）中搜索关键字：

| 匹配结果 | 行为 |
|---------|------|
| 完全匹配 1 个 | 直接进 Step 2 |
| 部分匹配 1 个 | 展示候选并问用户："是否归档 `<name>`？(y/n)" — 确认后进 Step 2 |
| 部分匹配多个 | 列出所有候选，让用户选择编号后进 Step 2 |
| 0 匹配 | 报错：`未找到匹配的 skill，请检查名称后重试。` 退出 |

---

## Step 2 — 前置检查

在执行任何操作前，检查三个条件，任一不满足则中止：

**1. 不在 detached HEAD 状态**
```bash
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
```
若结果为 `HEAD`（detached），提示：
`当前处于 detached HEAD 状态，无法确定要 merge 回的目标分支。请先切换到一个具名分支后重试。`
然后退出。

**2. 无未提交变更**
```bash
git status --short
```
若有未提交修改，提示：`存在未提交的变更，请先 commit 或 stash 后重试。` 退出。

**3. 归档目标不冲突**
```bash
ls "${REPO_ROOT}/skills/archived/<name>" 2>/dev/null
```
若已存在，提示：`skills/archived/<name>/ 已存在，请手动处理后重试。` 退出。

---

## Step 3 — 确认摘要

展示操作预览，**等待用户明确确认后再执行**：

```
即将归档 <name>（bundle: <bundle>）：

  移动：skills/<category>/<name>/ → skills/archived/<name>/
  从 skills-index.json 移除该条目
  更新 bundleMeta.<bundle>：去掉描述中的 "<name>"
  重新生成：package.json files[] 和 .npmignore
  Git：chore/archive-<name> → merge 回 <ORIGINAL_BRANCH>

确认继续？(y/n)
```

用户输入 `n` 则中止，不做任何修改。

---

## Step 4 — 创建分支并移动文件

```bash
git checkout -b chore/archive-<name>
mkdir -p "${REPO_ROOT}/skills/archived"
git mv "skills/<category>/<name>" "skills/archived/<name>"
```

> 若创建分支时看到 check-similar-branch hook 的相似分支警告，可忽略——archive 分支之间相似是正常现象。

---

## Step 5 — 更新 skills-index.json

读取并修改 `skills-index.json`，写回文件：

**移除 skills[] 条目：** 删除 `path` 末段为 `<name>` 的对象。

**更新 bundleMeta 描述：** 描述格式为 `"研究工具（a + b + c）"`，从中删除 `<name>`：
- 若在中间：删除 ` + <name>` 或 `<name> + `
- 若为最后一项：删除 ` + <name>`
- 若括号内只剩该项：将整个 `（<name>）` 删除，或保留空括号（均可）
- 若描述中无该 skill 名：跳过，不报错

---

## Step 6 — 重新生成打包配置

```bash
node scripts/generate-npmignore.js
```

若脚本失败，报错并中止，不执行 git 操作，保留已修改的文件供用户检查。

---

## Step 7 — Git commit

`git mv` 已自动 stage 了文件移动，只需 add 配置文件的修改：

```bash
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
  已 merge 回 <ORIGINAL_BRANCH>

  分支 chore/archive-<name> 可手动删除：
    git branch -d chore/archive-<name>
```

---

## 边界情况汇总

| 情况 | 处理 |
|------|------|
| Detached HEAD | Step 2 中止，提示切换到具名分支 |
| 有未提交变更 | Step 2 中止，提示 commit 或 stash |
| `skills/archived/<name>/` 已存在 | Step 2 中止，提示手动处理 |
| `generate-npmignore.js` 失败 | Step 6 中止，不执行 git 操作 |
| skill 在磁盘但不在 index | 提示"仅做文件移动"，跳过 Step 5 |
| bundleMeta 描述无该 skill 名 | 跳过描述更新，继续 |

---

## 不在范围内

- 批量归档多个 skill
- 自动删除归档分支
- 恢复（un-archive）操作
