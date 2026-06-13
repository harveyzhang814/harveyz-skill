---
name: add-todo
version: "4.5.0"
user_invocable: true
description: "Add a new requirement, task, or feature request to any project's TODO.md — from any working directory. Triggers whenever the user wants to capture a new need — even phrased casually like 'we should do X later', 'add this to the backlog', 'note this down', 'remember to build X', 'we need to do Y at some point', or 'record this for later'."
---

# 写入 TODO

快速捕获需求：先用 2-3 个问题把需求说清楚，再根据完整的需求信息匹配项目、生成标题，最后写入 TODO.md。

## 核心原则

**先把需求说清楚，再定项目归属。** 完整的需求描述是项目匹配最好的材料。问题只聚焦需求本身，不聚焦方案。够写一条清晰的任务条目就停，不要拖长。

---

## 阶段一 — 需求确认（2-3 轮）

**按需提问，已从上下文明确的直接跳过：**

1. **需求** — 要解决什么问题、实现什么功能？（用户已清晰描述则复述确认即可）
2. **紧急程度** — 有多急？（默认 P2，只在用户暗示紧急或不重要时调整）
3. **背景** — 为什么现在提出来？（可选，有助于写出有上下文的描述）

**提问方式：**
- 每次只问一个问题
- 优先给选项而非开放题："这个更像 (A) 缺失功能 还是 (B) 现有功能的问题？"
- 2 轮够用时不要凑到 3 轮

---

## 阶段二 — 确认项目归属

需求收集完毕后，用 Read 工具读取项目注册表：

```
~/.hskill/todo-tool/PROJECTS.md
```

同时用 Bash 运行 `pwd` 获取当前目录。

### 匹配逻辑

综合以下信号推断候选项目：

1. **当前目录**：`pwd` 输出是否是某个项目 `local_path` 的子路径 → 强信号
2. **需求关键词 + 项目描述**：需求描述中的词汇是否与项目名或描述匹配 → 中信号
3. **语义推断**：需求内容在哪个项目的业务范围内 → 弱信号

### 确认策略

| 情况 | 行动 |
|------|------|
| 唯一高置信匹配 | 告知并请确认："这是 **[项目名]** 的需求，对吗？" |
| 2-3 个候选 | 列出候选，请用户选择 |
| 无匹配或不确定 | 展示完整项目列表，让用户选 |

> **谨慎原则**：宁可多问一次，不写入错误项目。

### 生成标题

项目确认后，根据完整需求生成任务标题：

- 祈使句，动词开头，直接说明要做什么
- ≤20 字，超出则提炼核心、去掉修饰语
- 足够具体，让人一眼看出任务核心，避免泛泛的"优化"、"修复"
- 不堆砌细节，只抓最关键的区分点

**示例：**
- ✗ "优化系统" → ✓ "重构视频解析模块以支持多格式输入"
- ✗ "修复 bug" → ✓ "修复字幕导出时 UTF-8 编码乱码"
- ✗ "添加功能" → ✓ "为 add-todo skill 添加 SQLite 持久化层"

展示摘要等用户确认：
> "记录为：**[项目名]** — [生成的标题]，[优先级]。确认吗？"

---

## 阶段三 — 写入 TODO.md

### 确定文件路径

从阶段二确认的项目的 `local_path` 取出路径，TODO.md 位于 `{local_path}/TODO.md`。

若该项目无 `local_path`，询问用户本地目录，写入后提示注册：
```bash
todo project set-path [项目名] [本地路径]
```

### 切换到 chore/todo 分支

在写入前，在项目目录操作 git：

```bash
cd {local_path}

# 1. 记录当前分支
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# 2. 确定 staging 基准分支（用于创建 chore/todo 及事后合并目标）
if git show-ref --verify --quiet refs/heads/staging; then
  BASE_BRANCH=staging
else
  BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
                | sed 's@^refs/remotes/origin/@@' || echo "main")
fi

# 3. 切换到 chore/todo（不存在则从 BASE_BRANCH 创建）
if git show-ref --verify --quiet refs/heads/chore/todo; then
  git checkout chore/todo
else
  git checkout -b chore/todo "$BASE_BRANCH"
fi
```

**非 git 仓库**：若 `local_path` 不在 git 仓库中，跳过此步骤，直接写入文件。

**BRANCH_GUARD hook**：执行 `git checkout -b chore/todo` 时，BRANCH_GUARD hook 可能会提示与其他分支语义相似。`chore/todo` 是永久追踪分支，不是功能分支，**直接确认新建，忽略相似分支警告**，继续执行后续步骤。

### 重复检查

加载文件，扫描是否有语义重叠的已有条目。若有：
> "发现可能重叠的条目：**[已有标题]**。这是同一件事还是独立需求？"

由用户决定：跳过、替换或独立写入。

### 写入格式

追加到 `## 🚧 待开发` 末尾：

```markdown
### [任务标题（≤20 字）]
**优先级**: P? | **日期**: YYYY-MM-DD

[描述：做什么、为什么。不写怎么做。篇幅以说清楚为准，不限长短。]

---
```

文件不存在则创建，初始结构：

```markdown
# TODO / Backlog

## 🚧 待开发

## ✅ 已完成
```

### 提交、合并到 staging、切回原分支

写入后在项目目录执行：

```bash
cd {local_path}

# 1. 在 chore/todo 上提交
git add TODO.md
git commit -m "todo: add [任务标题]"

# 2. 合并到 staging（或主分支）
git checkout "$BASE_BRANCH"
git merge --no-ff chore/todo -m "Merge chore/todo: add [任务标题]"

# 3. 切回原分支
git checkout "$ORIGINAL_BRANCH"
```

完成后确认：

> "✅ 已将 **[任务标题]** 写入 `{local_path}/TODO.md`，提交到 `chore/todo`，合并到 `$BASE_BRANCH`，当前回到 `$ORIGINAL_BRANCH`。"
