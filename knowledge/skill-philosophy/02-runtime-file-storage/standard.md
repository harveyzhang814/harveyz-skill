---
title: Skill 运行时文件存储规范
version: 1.0.0
source: "[[research]] · 02-runtime-file-storage"
---

# Skill 运行时文件存储规范

> 适用于：需要在 session 之间持久化文件的 Skill

---

## 核心原则

**文件类型决定存储位置。** 同一个 Skill 的不同类型文件可以存放在不同位置。

| 文件类型 | 存储位置 | 理由 |
|----------|----------|------|
| config / cache / session 状态 | 全局目录（`~/.hskill/<skill-name>/`） | 不污染项目，跨 session 积累 |
| 输出产物（规格、报告、文档） | 项目目录内（`docs/<skill-name>/`） | 属于项目，应进 git，用户在项目里找 |
| 工作区状态（有明确"进入"语义） | 当前目录（CWD） | 用户用 cd 选择上下文 |

---

## 三种存储策略

| 策略 | 根位置 | 项目隔离方式 | 适用场景 |
|------|--------|-------------|----------|
| **全局集中分层** | `~/.hskill/<skill-name>/` | 子目录（git repo slug 或全局） | config、session、analytics |
| **项目内命名空间** | `docs/<skill-name>/` | 文件系统位置（在哪个项目目录内） | 输出产物、可进 git 的文件 |
| **工作目录即工作区** | CWD | 用户 cd 到哪里 | 有明确工作区语义的 skill |

---

## 创建时：每类文件的存储决策

每新增一类文件前问：

1. **这个文件属于项目还是用户？** 属于项目（换个项目就没用了）→ 项目目录内；属于用户（跨项目通用）→ 全局目录
2. **这个文件应该进 git 吗？** 是 → 项目目录内；否 → 全局目录或 gitignore
3. **用户会在哪里找这个文件？** 在项目里找 → 项目目录；在工具状态里找 → 全局目录

---

## Review 时：存储设计的问题信号

| 信号 | 处理方式 |
|------|----------|
| 把 config/cache 写进项目目录 | 移至全局目录，或加 .gitignore |
| 把输出产物存在隐藏全局目录 | 移至项目内 `docs/<skill-name>/` |
| 文件名没有携带任何元数据 | 加时间戳或序号（`YYYYMMDD-` 或 `0001-`） |
| 多种文件类型混放在同一目录 | 按关注点分子目录（`sessions/`、`notes/`、`outputs/` 等） |
| 没有项目隔离机制 | 加 slug 或工作区路径隔离，防止跨项目污染 |

---

## 文件命名规则

文件名本身是隐性的分类工具——当某类文件数量少时，命名规则可以替代子目录：

| 场景 | 推荐命名格式 | 示例 |
|------|-------------|------|
| 按时间排序的记录 | `YYYYMMDDTHHMMSS-{slug}.md` | `20250615T143022-auth-spec.md` |
| 按顺序积累的内容 | `{0001}-{dash-case-name}.md` | `0003-database-schema.md` |
| 带主题的输出产物 | `YYYY-MM-DD-{topic}-{type}.md` | `2025-06-15-auth-design.md` |

---

## 可直接复制的起始模板

**使用时需要替换的占位符：**
- `{skill-name}` — 这个 Skill 的名称（用于目录命名）
- `{文件类型 N}` — 这个 Skill 会产生哪几类文件
- `{子目录名}` — 每类文件对应的子目录名称

**使用时需要删除的内容：**
- 不适用于这个 Skill 的存储层（例如没有输出产物就删掉项目目录部分）
- `← 注释` 行

---

### 全局集中分层（config / session / cache）

```markdown
## 存储初始化（run first）

```bash
# 全局根目录，可通过环境变量覆盖
SKILL_HOME="${HSKILL_HOME:-$HOME/.hskill}/{skill-name}"

# 项目隔离：从 git repo 名派生 slug
PROJECT_SLUG=$(basename $(git rev-parse --show-toplevel 2>/dev/null) || echo "global")
PROJECT_DIR="$SKILL_HOME/projects/$PROJECT_SLUG"

# 按文件类型分子目录
mkdir -p \
  "$PROJECT_DIR/{子目录名 1}" \     # ← {文件类型 1}
  "$PROJECT_DIR/{子目录名 2}" \     # ← {文件类型 2}
  "$SKILL_HOME/analytics"           # ← 全局遥测（不按项目隔离）
```

文件命名约定：
- {文件类型 1}：`$PROJECT_DIR/{子目录名 1}/$(date +%Y%m%dT%H%M%S)-{slug}.md`
- {文件类型 2}：`$PROJECT_DIR/{子目录名 2}/{0001}-{slug}.md`（序号递增）
```

---

### 项目内命名空间（输出产物 / 可进 git 的文件）

```markdown
## 输出产物路径约定

所有输出文件存放在项目内的命名空间路径下：

```
docs/{skill-name}/
  {子目录名 1}/       ← {文件类型 1}
  {子目录名 2}/       ← {文件类型 2}
```

文件命名约定：`$(date +%Y-%m-%d)-{topic}-{type}.md`

```bash
OUTPUT_DIR="docs/{skill-name}/{子目录名 1}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/$(date +%Y-%m-%d)-${TOPIC_SLUG}.md"
```

这些文件应进入版本控制。如有不应进 git 的临时文件，存入全局目录而非此处。
```

---

### 工作目录即工作区（有明确"进入"语义的 Skill）

```markdown
## 工作区约定

当前目录即为本次工作区。用户通过 `cd` 到对应目录来选择工作上下文。

工作区目录结构：
```
./                              ← 用户 cd 到此处启动 Skill
  {ANCHOR_FILE}.md              ← 工作区锚点文件（记录目标/使命）
  {子目录名 1}/                 ← {文件类型 1}，编号命名
    0001-{dash-case-name}.md
  {子目录名 2}/                 ← {文件类型 2}
  assets/                      ← 跨文件可复用的组件（可选）
```

```bash
# 确保工作区目录存在
mkdir -p "{子目录名 1}" "{子目录名 2}" "assets"

# 序号递增命名
NEXT_NUM=$(ls {子目录名 1}/ 2>/dev/null | wc -l | xargs printf "%04d")
NEW_FILE="{子目录名 1}/${NEXT_NUM}-${TOPIC_SLUG}.md"
```

注意：多个 Skill 同时使用工作区模式时，锚点文件名须不同，避免冲突。
```
