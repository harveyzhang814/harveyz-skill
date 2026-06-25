---
migrated: 2026-06-21
implemented_in:
  - skills/research/survey-skillrepo/SKILL.md  # 实现时命名为 survey-skillrepo
---

# analyze-skill 通用化设计 spec

## 背景

`analyze-skill` 当前版本（v1.0.0）是针对 gstack 仓库定制的分析器，内嵌了大量硬编码数字、路径和 skill 列表。本次改造目标：使其能分析任意遵循 harveyz-skill 格式的 skill 仓库（`skills/` 目录 + SKILL.md），同时与 `learn-skill` 共享输出路径，形成两步式完整分析流程。

---

## 核心定位

- **`analyze-skill`**：仓库级别总结，输出 `analysis-{date}.md`
- **`learn-skill`**：逐个 skill 深度解读，输出 `{skill-name}.md`
- **关系**：同一分析过程的两步，共享 `{skillDir}/{repo-name}/` 输出目录

---

## 执行流程

### Step 0 — 读取配置（完全复用 learn-skill 逻辑）

读取 `$HOME/.hskill/config.json`，检查是否存在 `skillDir` 字段。

- **已存在**：直接使用，不打扰用户
- **不存在**：询问用户目标目录路径（建议默认值：`$HOME/Documents/skill-library`），写入 config.json

---

### Step 1 — 定位目标仓库

优先级顺序：

1. **带路径参数**（如 `/analyze-skill ~/path/to/skill-repo`）→ 直接使用该路径
2. **无参数**：检测当前目录是否包含 `skills/` 子目录且其中有 SKILL.md 文件 → 是则直接使用
3. **检测不到**：询问用户输入目标仓库路径

路径确定后，取 `basename` 作为 `repo-name`，用于后续输出路径。

---

### Step 2 — 类型检测

检查目标路径下是否存在包含 `SKILL.md` 的 `skills/` 目录结构。

- **是 skill 仓库** → 继续
- **不是** → 报告类型并退出，不强行套用 skill 仓库框架

---

### Step 3 — 四层洋葱分析

#### Layer 1 — 设计意图（哲学视角）

目标：理解这个仓库"为什么存在"、核心设计原则是什么。

**搜索顺序**（每级先检查文件是否存在，存在才读；读完判断是否含实质性设计意图）：

**第一优先级 — 明确的哲学/架构文档**（在根目录和 `docs/` 下查找）：
```
ETHOS.md / ARCHITECTURE.md / DESIGN.md / PHILOSOPHY.md / OVERVIEW.md
```

**第二优先级 — 项目级约定文档**：
```
README.md          # 通常含"为什么做这个"
CLAUDE.md          # 对 AI 的项目级指令，反映作者对系统的理解
AGENTS.md / GEMINI.md
```

**第三优先级 — 结构性元数据**：
```
skills-index.json / package.json   # name、description、keywords 体现定位
CHANGELOG.md                        # 版本演进反推设计决策变化
```

**第四优先级 — 全仓库扫描**：

不假设文件名，扫描根目录及所有子目录下的 `.md` 文件，按文件名判断相关性（含 `design`、`arch`、`ref`、`guide`、`intro`、`ethos`、`philosophy` 关键词的优先读）。设计意图文档不一定在 `docs/` 下，可能在任意位置。

读取后提炼：系统定位、核心设计原则（以表格形式呈现）。已检查但无实质内容的文件记录"已检查，无相关内容"，不遗漏也不过度解读。

---

#### Layer 2 — 组件目录（结构视角）

目标：建立客观的结构清单，不带解释，只陈述事实。

- 动态运行 `find` / `ls` 命令，发现所有 skill 目录（含 flat skill 和 skill group 两种结构）
- 逐目录列出实际文件清单，不估算，必须实际计数
- 识别 flat skill（单 `SKILL.md` + 可选 `references/`）和 skill group（子目录含多个 skill）
- 记录每个 skill 的基础元数据：name、version、user_invocable（从 frontmatter 读取）

**本层产物**：所有 skill 的列表，供 Layer 3 逐个处理。

---

#### Layer 3 — 交互关系（系统视角）

目标：理解 skill 之间的关系、工具权限分布。

**对 Layer 2 发现的每个 skill，调用 `learn-skill` 进行深度解读**（输出保存至 `{skillDir}/{repo-name}/{skill-name}.md`）。

基于 `learn-skill` 的输出，聚合以下分析：

**1. 工具权限矩阵**：从每个 skill 的 SKILL.md `allowed-tools` 字段动态读取，构建矩阵表格。数据必须从实际文件读取，不得推断。

**2. 三类交互关系**：
- **自动触发**：某 skill 执行时确定性地触发另一个 skill
- **建议序列**：推荐的 skill 使用顺序
- **前置配置**：运行时依赖（如 config 文件、已安装工具等）

**3. 依赖结构图**：skill 之间的调用关系（如 `analyze-skill` → `learn-skill`）

---

#### Layer 4 — 使用场景（用户视角）

目标：基于前三层提炼 3-5 个典型工作流场景，验证设计意图是否落地。

每个场景格式：
```
场景名称（预估使用频率）
用户输入 → 步骤1 → 步骤2 → 结果
覆盖的 skill：[列表]
```

同时列出降级矩阵：当某个 skill 不可用时，用户的替代路径是什么。

---

### Step 4 — 保存报告

**输出路径**：`{skillDir}/{repo-name}/analysis-{date}.md`

**Frontmatter 格式**（与 `learn-skill` 一致）：
```markdown
---
repo: {repo-name}
path: {仓库绝对路径}
version: {VERSION 文件或 package.json 中的版本号}
analyzed_at: {YYYY-MM-DD}
skills_count: {发现的 skill 总数}
---
```

报告正文使用 `references/output-template.md` 中的结构填写。

保存完成后，在对话中告知用户：
- 报告路径
- 发现的 skill 数量
- learn-skill 已生成的个别分析文件路径列表

---

## 触发条件变更

当前版本的触发短语仅有中文场景，新版本需支持带路径参数的调用方式：

- `analyze-skill ~/path/to/repo`
- "分析这个 skill 仓库"
- "对这个 skill 仓库做系统性研究"
- "输出 skill 仓库的分析报告"
- "理解这个 skill 系统的设计意图"

---

## references/ 文件改动

### `prohibitions.md` — 删除 gstack 专用规则，保留 8 条通用原则

保留：
1. 不能只统计 skill 数量，必须列出完整文件清单
2. 不能估算文件数量，必须实际运行命令计数
3. 每个列出的文件必须验证其确实存在，不得推断
4. 每个目录必须列出实际文件清单，不能只报总数
5. `allowed-tools` 必须从实际 SKILL.md 文件读取，不得从 `.tmpl` 或记忆推断
6. `allowed-tools` 描述不能与表格数据矛盾
7. 不能混淆三种关系类型（自动触发 / 建议序列 / 前置配置）
8. 不能在未完成类型检测的情况下假设目标是 skill 仓库

删除：所有 gstack 专用的文件数量（bin/ = 17 等）、skill 列表（WebSearch 12 个等）、路径约定（~/Repositories/gstack/）。

### `output-template.md` — 去掉 gstack 专用字段

删除：`browse/bin/` 与 `bin/` 的区分说明、gstack 专用目录结构、固定数量参考表。
保留：报告结构模板（元信息、四层分析、附录），占位符替换为通用格式。

### `evaluation-template.md` — 基本不变

已足够通用，只需将"幽灵文件"部分的说明去掉 gstack 专用示例。

---

## 不在本次改动范围内

- `learn-skill` 本身的逻辑（不修改）
- `output-template.md` 的整体结构（只去除 gstack 专用内容）
- `evaluation-template.md` 的评估框架
