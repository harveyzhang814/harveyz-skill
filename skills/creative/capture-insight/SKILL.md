---
name: capture-insight
version: "2.0.2"
user_invocable: true
description: "Capture and record a fleeting insight or observation. Triggers immediately when the user expresses an observation, judgment, or idea — phrases like 'I noticed', 'just an observation', 'record this', 'insight', 'I have a judgment', or tossing out an opinionated thought. Distinct from 'I have an idea to execute' (that's a task). Clarifies the core with 2-3 quick Q&As, then saves to the Writing Agent project's insights/ folder. Trigger early — insights are fragile."
---

# Capture Insight

帮用户把一闪而过的灵感、观察、判断，变成结构清晰、可以回溯的 insight 记录。

## 核心原则

目标是**快速固定核心**，不是完整分析：让用户三个月后翻到这条记录，还能找回当时的思路。

**一次只问一个问题**，等用户回答完再问下一个。不要用列表提问（比如"你能说说背景、动机和应用场景吗"）。

---

## 流程

### 第〇步：确定写入项目路径

在开始澄清前，先读取配置：

```
~/.hskill/capture-insight/config.json
```

**配置格式：**
```json
{ "writing_agent_path": "/path/to/writing-agent" }
```

**若配置文件不存在：** 询问 Writing Agent 项目路径（默认 `/Users/harveyzhang96/Projects/writing-agent`），把**用户确认的路径**写进 `~/.hskill/capture-insight/config.json` 的 `writing_agent_path` 字段（目录不存在就先 `mkdir -p ~/.hskill/capture-insight`）。

配置确认后，将 `writing_agent_path` 记为 `{project_path}`，insight 写入目标为 `{project_path}/insights/`。

---

### 第一步：捕捉原始 insight

用户说出 insight 后，**先用一句话复述你理解的核心**，让用户确认或纠正方向（不计入澄清问题）。

示例：
> 你说的核心是：[你对 insight 的提炼]，对吗？

### 第二步：2-3 个澄清问题

按优先级依次问：

1. **触发**：这个 insight 是被什么触发的？（某个产品/对话/现象）
2. **张力**：为什么这个观察有意思？哪里跟直觉相悖，或者跟常识不一样？
3. **方向**（可选，如果 insight 已经比较清晰可以跳过）：你觉得这个观察会往哪里走？有什么潜在的推论或应用？

> 如果用户的描述已经包含了某个问题的答案，跳过那个问题，直接进入下一个。

### 第三步：确认 & 保存

澄清完成后：

1. 给出一段 **insight 摘要**（3-5 句话），让用户确认是否准确捕捉到了核心
2. 用户确认后，生成文件名，按「写入 & Git 操作」依次执行：切到 `chore/insight` → 写文件 → 提交并合并 → 切回原分支。

---

## 文件格式

**文件命名：** `YYYY-MM-DD-<slug>.md`，slug 用英文，简短描述核心概念（如 `agents-commoditization`、`trust-asymmetry`）

**文件内容：**

```markdown
# [Insight 的核心判断，用中文，一句话]

> 记录于 YYYY-MM-DD

## 原始触发

[是什么触发了这个观察——某个产品、对话、现象、数据点]

## 核心观察

[insight 的主体，2-4 句话，聚焦于"我注意到/我发现"的那件事]

## 为什么有意思

[张力在哪里，跟直觉或常识的分歧是什么]

## 潜在方向

[只记录用户自己提到的推论或应用方向。如果用户没说，留空，不要补充]

## 关键词

[2-4 个词，方便未来检索]
```

---

## 写入 & Git 操作

确认写入 `{project_path}/insights/YYYY-MM-DD-<slug>.md` 后：

### 切换到 chore/insight 分支

```bash
cd {project_path}

# 1. 记录当前分支
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# 2. 确定基准分支
if git show-ref --verify --quiet refs/heads/staging; then
  BASE_BRANCH=staging
else
  BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null \
                | sed 's@^refs/remotes/origin/@@')
  BASE_BRANCH=${BASE_BRANCH:-main}
fi

# 3. 切换到 chore/insight（不存在则从 BASE_BRANCH 创建）
if git show-ref --verify --quiet refs/heads/chore/insight; then
  git checkout chore/insight
else
  git checkout -b chore/insight "$BASE_BRANCH"
fi
```

**非 git 仓库**：若 `{project_path}` 不在 git 仓库中，跳过 git 步骤，直接写入文件。

### 写入文件

将 insight 内容写入 `{project_path}/insights/YYYY-MM-DD-<slug>.md`。

### 提交、合并、切回

```bash
cd {project_path}

# 1. 在 chore/insight 上提交
git add insights/YYYY-MM-DD-<slug>.md
git commit -m "insight: add YYYY-MM-DD-<slug>"

# 2. 合并到基准分支
git checkout "$BASE_BRANCH"
git merge --no-ff chore/insight -m "Merge chore/insight: YYYY-MM-DD-<slug>"

# 3. 切回原分支
git checkout "$ORIGINAL_BRANCH"
```

---

## 注意事项

- 不替用户升格判断：保留"感觉/好像/也许"这类不确定的措辞（摘要写"你观察到 XX 可能是个趋势"，不写"XX 是个重要趋势"）。
- 始终写入配置里的 `{project_path}`，不受当前工作目录影响。

---

## 保存后告诉用户

```
✓ 已保存到 {project_path}/insights/YYYY-MM-DD-<slug>.md
  提交到 chore/insight，合并到 {BASE_BRANCH}，当前回到 {ORIGINAL_BRANCH}。
```
