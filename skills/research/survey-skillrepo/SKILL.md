---
name: survey-skillrepo
description: "Analyzes any skill repository (skills/ directory + SKILL.md format) using the 4-layer onion model. Produces a repo-level summary at {skillDir}/{repo-name}/analysis-{YYYY-MM-DD}.md, complementing learn-skill which handles per-skill deep analysis. Triggers: 'analyze this skill repo', 'do a systematic study of the skill repo', 'output skill repo analysis report', 'understand the design intent of this skill system'. Accepts optional path argument: /survey-skillrepo ~/path/to/repo."
user_invocable: true
version: "2.0.1"
---

# survey-skillrepo

> **版本：** v2.0.0
> **定位：** 对任意 skill 仓库进行系统性分析的工具 Skill
> **关系：** 与 `learn-skill` 共享输出目录，两者是同一分析过程的两步

---

## 触发条件

- `/survey-skillrepo ~/path/to/repo`（带路径参数）
- "分析这个 skill 仓库"
- "对这个 skill 仓库做系统性研究"
- "输出 skill 仓库的分析报告"
- "理解这个 skill 系统的设计意图"

---

## Step 0 — 读取或初始化配置

读取 `$HOME/.hskill/config.json`，检查是否存在 `skillDir` 字段。

**如果不存在**：
1. 询问用户目标目录路径（建议默认值：`$HOME/Documents/skill-library`）
2. 将用户输入的路径解析为绝对路径（展开 `~` 和 `$HOME`）
3. 若目录不存在则创建
4. 将解析后的绝对路径写入 `$HOME/.hskill/config.json`（文件不存在则新建）

**如果已存在**：直接使用，不打扰用户。

---

## Step 1 — 定位目标仓库

按以下优先级确定目标路径：

1. **带路径参数**（如 `/analyze-skill ~/path/to/skill-repo`）→ 直接使用该路径
2. **无参数**：检测当前目录是否包含 `skills/` 子目录且其中有 SKILL.md 文件 → 是则直接使用
3. **检测不到**：询问用户输入目标仓库路径

路径确定后，执行 `basename $(git rev-parse --show-toplevel)` 取得 `repo-name`（非 git 仓库则使用目录名）。

---

## Step 2 — 类型检测

检查目标路径下是否存在包含 `SKILL.md` 的 `skills/` 目录结构。

- **是 skill 仓库** → 继续
- **不是** → 报告类型，提示用户确认路径是否正确，退出分析

---

## ⚠️ 必检清单

执行分析前完成以下检查，结果记录在报告元信息中：

### 版本信息
- [ ] VERSION 文件内容（若存在）
- [ ] package.json version（若存在）
- [ ] CHANGELOG 最新版本（若存在）
- [ ] 三者是否一致；不一致时探讨根因

### 文件数量（必须实际计数，不得估算）
- [ ] `skills/` 下的 skill 总数（逐目录计数）
- [ ] flat skill 数量 vs skill group 数量

### 目录覆盖
- [ ] 所有子目录均已列出实际文件清单

**执行前必须读取 `references/prohibitions.md`**

---

## Step 3 — 四层洋葱分析

### Layer 1 — 设计意图（哲学视角）

目标：理解这个仓库"为什么存在"、核心设计原则是什么。

按以下顺序搜索。每级先检查文件是否存在，存在才读；读完判断是否含实质性设计意图，有则纳入分析，无则记录"已检查，无相关内容"：

**第一优先级** — 明确的哲学/架构文档（根目录及 `docs/` 下查找）：
```
ETHOS.md / ARCHITECTURE.md / DESIGN.md / PHILOSOPHY.md / OVERVIEW.md
```

**第二优先级** — 项目级约定文档：
```
README.md
CLAUDE.md / AGENTS.md / GEMINI.md
```

**第三优先级** — 结构性元数据：
```
skills-index.json / package.json   （name、description、keywords 体现定位）
CHANGELOG.md                        （版本演进反推设计决策变化）
```

**第四优先级** — 全仓库扫描：

不假设文件名，扫描根目录及所有子目录的 `.md` 文件，按文件名判断相关性（含 `design`、`arch`、`ref`、`guide`、`intro`、`ethos`、`philosophy` 关键词的优先读）。设计意图文档不一定在 `docs/` 下，可能在任意位置。

提炼输出：
- 系统定位（一句话概括）
- 核心设计原则（表格：原则名 | 含义）

---

### Layer 2 — 组件目录（结构视角）

目标：建立客观的结构清单，不带解释，只陈述事实。

- 动态运行 `find` / `ls` 命令，发现所有 skill 目录
- 识别两种结构：
  - **flat skill**：单 SKILL.md + 可选 `references/`
  - **skill group**：子目录含多个 skill，每个 skill 有自己的 SKILL.md
- 逐目录列出实际文件清单，不得只报总数
- 记录每个 skill 的基础元数据（从 frontmatter 读取）：name、version、user_invocable

**本层产物**：发现的所有 skill 列表，供 Layer 3 逐个处理。

---

### Layer 3 — 交互关系（系统视角）

目标：理解 skill 之间的关系、工具权限分布。

**对 Layer 2 发现的每个 skill，调用 `learn-skill` 进行深度解读。**

`learn-skill` 会将每个 skill 的分析保存至 `{skillDir}/{repo-name}/{skill-name}.md`。

基于 `learn-skill` 的输出，聚合以下分析：

**工具权限矩阵**：从每个 skill 的 SKILL.md `allowed-tools` 字段动态读取，构建矩阵表格。数据必须从实际文件读取，不得推断。

| Skill | Bash | Read | Write | Edit | Glob | Grep | Agent | AskUserQ | WebSearch |
|-------|------|------|-------|------|------|------|-------|---------|-----------|

**三类交互关系**：
- **自动触发**：某 skill 执行时确定性地调用另一个 skill
- **建议序列**：推荐的 skill 使用顺序
- **前置配置**：运行时依赖（如 config 文件、已安装工具等）

**依赖结构图**：skill 之间的调用关系（如 `analyze-skill` → `learn-skill`）

---

### Layer 4 — 使用场景（用户视角）

目标：基于前三层提炼 3-5 个典型工作流场景，验证设计意图是否落地。

每个场景格式：
```
场景名称（预估使用频率）
用户输入 → 步骤1 → 步骤2 → 结果
覆盖的 skill：[列表]
```

同时列出降级矩阵：当某个 skill 不可用时，用户的替代路径。

---

## Step 4 — 保存报告

将报告保存至 `{skillDir}/{repo-name}/analysis-{YYYY-MM-DD}.md`，同名文件存在时直接覆盖。

- `skillDir`：config.json 中的绝对路径
- `repo-name`：`basename $(git rev-parse --show-toplevel)` 取得；非 git 仓库则使用目录名
- `date`：YYYY-MM-DD 格式

文件结构：

```markdown
---
repo: {repo-name}
path: {仓库绝对路径}
version: {VERSION 或 package.json 中的版本号，若两者都无则省略}
analyzed_at: {YYYY-MM-DD}
skills_count: {发现的 skill 总数}
---

{四层洋葱分析报告正文，使用 references/output-template.md 中的结构}
```

保存完成后，在对话中告知用户：
- 报告路径
- 发现的 skill 数量
- learn-skill 已生成的个别分析文件列表

---

*survey-skillrepo v2.0.0 | 2026-06-19*
