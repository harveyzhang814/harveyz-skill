# 研究：三个 Skill 生态对"运行时文件存储"的实践

> 关联文档：[[principle]]
>
> 研究对象：
> - G stack → `context-save`（最直接管理 session 状态文件的 skill）
> - Superpowers → `writing-skills` + `brainstorming`（writing-skills 定义存储约定；brainstorming 展示运行时产物路径）
> - MSkill → `teach`（多 session 有状态 skill，必须在跨会话间保留完整状态）
>
> 示例场景：一个需要跨 session 积累状态的 skill（如"学习类"或"项目跟踪类"）

---

## 一、三个来源的逐一解剖

### 1. G stack — `context-save`

**核心定位**：保存当前工作 session 的完整状态，让下一个 session 能无缝接续。

**存储层级——完整图谱：**

```
~/.gstack/                              ← GSTACK_HOME（可通过环境变量覆盖）
  sessions/                             ← 活跃 session 追踪（touch 文件，120 分钟过期自动清理）
  analytics/
    skill-usage.jsonl                   ← 技能使用遥测
    eureka.jsonl                        ← 洞见记录
    .pending-{session_id}               ← 挂起的遥测（skill 完成后清理）
  projects/{SLUG}/                      ← 项目隔离（SLUG 由 git repo 名生成）
    checkpoints/
      {TIMESTAMP}-{TITLE_SLUG}.md       ← 保存的 session 上下文
    ceo-plans/                          ← 设计文档
    timeline.jsonl                      ← session 历史
    decisions.active.json               ← 活跃架构决策
    {BRANCH}-reviews.jsonl              ← 分支 review 记录
    learnings.jsonl                     ← 运营经验积累
  .brain-last-pull                      ← 同步时间戳
  .brain-queue.jsonl                    ← 同步队列
  .proactive-prompted                   ← 功能提示标记（空文件）
  .telemetry-prompted                   ← 同上
  .completeness-intro-seen              ← 同上
```

**关键设计决策（明确写出的）：**
- `GSTACK_HOME="${GSTACK_HOME:-$HOME/.gstack}"` → 用户主目录为根，可通过环境变量覆盖
- `projects/${SLUG}` → SLUG 由 `gstack-slug` 工具从 git repo 名派生，实现项目隔离
- 状态文件路径：`~/.gstack/projects/$SLUG/checkpoints/${TIMESTAMP}-${TITLE_SLUG}.md`
- `gstack-config get/set` → 配置通过专用 binary 读写，不直接操作文件
- `artifacts_sync_mode` → 是否将 `~/.gstack/` 变成 git repo 进行跨机器同步（可选）

**关键设计决策（隐含的）：**
- **永不写入项目目录**：所有状态都在 `~/.gstack/`，项目目录保持干净
- **按关注点分子目录**：`checkpoints/`、`ceo-plans/`、`analytics/`、`sessions/` 分开存放——类型决定路径，不是时间
- **功能标记用空文件**：已看到某功能介绍 → touch 一个 `.xxx-prompted` 空文件，而不是写配置值
- **遥测和状态混放在 analytics/**：skill 使用记录和洞见都在这里，不是专门的 log 目录

**原文关键句：**

> `eval "$(~/.claude/skills/gstack/bin/gstack-slug 2>/dev/null)" && mkdir -p ~/.gstack/projects/$SLUG`

→ 每个 skill 运行时都先确保项目目录存在，slug 是统一的项目标识符。

> `CHECKPOINT_DIR="$GSTACK_STATE_ROOT/projects/$SLUG/checkpoints"`
> `FILE="${CHECKPOINT_DIR}/${TIMESTAMP}-${TITLE_SLUG}.md"`

→ 文件命名包含时间戳和用户提供的标题 slug，同一项目下可以有多个历史记录。

**边界（什么情况下这种方式会失效）：**
- 同一 git repo 在不同路径 clone 两份时，SLUG 相同会产生状态混用（极少见但存在）
- 多人协作项目中，每个人的 `~/.gstack/` 完全独立，无法共享决策/学习记录
- 无 git repo 时（裸目录），SLUG 回退到 `unknown`，所有无 git 项目共用一个状态桶

---

### 2. Superpowers — `writing-skills` + `brainstorming`

**核心定位**：`writing-skills` 定义 skill 本身的存储约定；`brainstorming` 展示运行时输出文件的存储约定。

**两层约定：**

**层一：Skill 定义文件**（来自 writing-skills）
```
~/.agents/skills/              ← 跨 runtime 别名（Claude Code、Codex、Copilot CLI、Gemini CLI 通用）
  skill-name/
    SKILL.md                   ← 主文件（必须）
    supporting-file.*          ← 仅在需要时
```

**层二：运行时输出文件**（来自 brainstorming）
```
{项目根}/
  docs/
    superpowers/
      specs/
        YYYY-MM-DD-{topic}-design.md    ← 设计规格文档
```

**关键设计决策（明确写出的）：**
- `~/.agents/skills/` → 明确定义为跨 runtime 的通用别名路径
- `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` → 项目内路径，带日期和主题的命名规则
- writing-skills 明确声明"personal skills live in your runtime's skills directory"，但对运行时 config/cache 无约定

**关键设计决策（隐含的）：**
- **输出文件进项目，定义文件进全局**：这是两个不同层次的文件用两种不同策略
- **项目内用 namespace 前缀避免冲突**：`docs/superpowers/` 而不是 `docs/`——用生态名称作前缀
- **运行时状态（config/cache/session）无显式约定**：Superpowers 没有对这类文件的明确规定——这本身是一个设计选择（依赖平台/宿主来处理）

**原文关键句：**

> "Personal skills live in your runtime's skills directory — see claude-code-tools.md, codex-tools.md, copilot-cli-tools.md, or gemini-tools.md for the path on your runtime. Codex, Copilot CLI, and Gemini CLI all also recognize `~/.agents/skills/` as a cross-runtime alias."

→ 跨 runtime 兼容性是第一设计约束——所以用户主目录别名，而不是 runtime-specific 路径。

**边界（什么情况下这种方式会失效）：**
- `docs/superpowers/specs/` 约定仅覆盖输出文件，对 config/cache/session 状态无指导
- 多个 Superpowers skill 的输出都放在 `docs/superpowers/` 下，长期使用后文件数量难以管理（没有按 skill 再分子目录）
- 跨 runtime 的 `~/.agents/skills/` 路径约定只对 skill 定义生效，运行时状态仍然各 runtime 自行决定

---

### 3. MSkill — `teach`

**核心定位**：在当前目录建立一个持久的"教学工作区"，跨 session 积累学习状态。

**存储约定——当前目录即工作区：**

```
{用户选择的任意目录}/          ← 用户通过 cd 到此目录来"选择"工作区
  MISSION.md                   ← 学习使命（为什么要学这个）
  RESOURCES.md                 ← 参考资源列表
  NOTES.md                     ← 用户偏好和工作笔记
  reference/
    *.html                     ← 参考手册（可重复查阅的知识提炼）
  learning-records/
    0001-{dash-case-name}.md   ← 学习记录（编号递增）
  lessons/
    0001-{dash-case-name}.html ← 课程文件（编号递增）
  assets/
    *                          ← 可复用组件（样式表、quiz widgets 等）
```

**关键设计决策（明确写出的）：**
- `"Treat the current directory as a teaching workspace."` → CWD 即工作区，无全局状态
- 文件命名：`0001-<dash-case-name>.md` → 编号递增确保有序，dash-case 确保可读
- `assets/` 中存放跨 lesson 的可复用组件 → 相同类型文件汇聚在一起，不分散
- `NOTES.md` 是 AI 的便签本（用户偏好、工作笔记），与内容文件明确区分

**关键设计决策（隐含的）：**
- **用户用 cd 来切换上下文**：不同主题的学习放在不同目录，隔离靠文件系统位置而非 skill 内部逻辑
- **按文件类型分子目录，不按时间**：`reference/`、`lessons/`、`learning-records/` 按关注点分，而不是 `2025-01/`、`2025-02/`
- **MISSION.md 是所有文件的锚点**：不同于 gstack 的 slug，这里用一个描述性的目标文件作为工作区的核心标识

**原文关键句：**

> "Treat the current directory as a teaching workspace. The state of their learning is captured in this directory in several files."

→ 最简洁的存储哲学：工作区在哪，状态就在哪。用户控制了目录，就控制了上下文。

> `./learning-records/*.md`：`0001-<dash-case-name>.md`，where the number increments each time.

→ 文件命名包含序号，在不引入数据库或元数据文件的情况下实现了有序性。

**边界（什么情况下这种方式会失效）：**
- 没有项目目录概念的场景（如临时任务），用户不知道应该在哪个目录里运行
- 多台机器同步时，需要对整个工作区目录进行 git 管理或手动同步
- 多个 skill 如果都在 CWD 存文件，容易产生命名冲突（如 NOTES.md）

---

## 二、三种核心思路提炼

### 思路 A：全局集中分层式（G stack context-save）

**核心逻辑**：所有运行时文件集中在用户主目录的一个根目录（`~/.gstack/`）下，通过 slug 实现项目隔离，通过子目录类型分层。项目目录永远干净。

**特征：**
- 根目录可通过环境变量覆盖（`GSTACK_HOME`），保留灵活性
- 项目隔离靠 slug（从 git repo 名派生），不靠文件系统位置
- 类型分层明确：sessions/、analytics/、projects/$SLUG/checkpoints/ 各司其职
- 配置通过专用 binary 读写（`gstack-config get/set`），不直接操作文件
- 跨机器同步是内置可选能力（把 `~/.gstack/` 变成 git repo）
- 功能标记用空 touch 文件而不是配置键值

**适用场景**：跨项目通用的 skill（如 session 保存、遥测、配置），用户数据需要跨 session 积累，且有潜在跨机器同步需求。

**广度/深度策略**：广度优先——先确定所有类型的分层，再在每层内深化（如 checkpoints 的命名规则）。

**边界**：多 clone 同一 repo 时 slug 冲突；多人协作无法共享状态；无 git repo 时 slug 退化。

**示例写法：**

```
# 在 skill 开始时初始化状态目录
SKILL_STATE_DIR="${HSKILL_HOME:-$HOME/.hskill}/learn-framework"
PROJECT_DIR="$SKILL_STATE_DIR/projects/$(basename $(git rev-parse --show-toplevel 2>/dev/null || echo global))"
mkdir -p "$PROJECT_DIR/sessions" "$PROJECT_DIR/notes"

# 保存 session 状态
SESSION_FILE="$PROJECT_DIR/sessions/$(date +%Y%m%dT%H%M%S)-${TITLE_SLUG}.md"
```

---

### 思路 B：项目内命名空间前缀式（Superpowers）

**核心逻辑**：输出文件存在项目目录内，用生态/工具名称作路径前缀避免与项目文件冲突。Skill 定义文件用跨 runtime 的全局路径。两个层次，两种策略。

**特征：**
- 输出文件路径：`docs/{ecosystem}/` → 明确的命名空间隔离
- 文件命名包含日期和主题：`YYYY-MM-DD-<topic>-design.md`
- Skill 定义用跨 runtime 别名 `~/.agents/skills/`，最大化兼容性
- 运行时 config/cache/session 状态无显式约定（依赖平台处理）
- 输出文件在项目目录内，自然感知项目上下文，可以进 git

**适用场景**：Skill 的主要产物是文档/规格/报告，且这些产物属于项目本身（应该被版本控制）。

**广度/深度策略**：广度优先——先在 `docs/superpowers/specs/` 建立统一入口，不按 skill 再细分。

**边界**：运行时 config/cache 没有约定，各 skill 自行决定；spec 文件长期积累后无分类管理；不适合纯状态类文件（这类文件不应进 git）。

**示例写法：**

```
# 输出文件存入项目内命名空间路径
SPEC_DIR="docs/hskill/specs"
mkdir -p "$SPEC_DIR"
SPEC_FILE="$SPEC_DIR/$(date +%Y-%m-%d)-${TOPIC_SLUG}-design.md"

# Skill 定义安装在跨 runtime 路径
# ~/.agents/skills/learn-framework/SKILL.md
```

---

### 思路 C：工作目录即工作区式（MSkill teach）

**核心逻辑**：当前目录就是这个 skill 的完整工作区。用户通过选择目录来选择上下文。所有文件扁平地分布在 CWD 的几个固定子目录下，没有全局状态。

**特征：**
- 零全局状态：所有文件都在 CWD 内，换目录就换上下文
- 用户通过 `cd` 来"选择"或"切换"工作区——这是隐式的设计
- 按关注点分子目录：`reference/`、`learning-records/`、`lessons/`、`assets/`
- 文件命名带递增序号（`0001-`）实现有序性，不依赖元数据文件
- 顶层保留几个特殊文件（`MISSION.md`、`NOTES.md`）作为工作区锚点
- 跨 session 共享靠目录内的文件，不靠全局存储

**适用场景**：任务本身天然有"工作区"概念（如学习特定主题、处理特定项目），用户能明确地"进入"和"离开"这个工作区。

**广度/深度策略**：广度优先但扁平——顶层固定几个文件/目录，不嵌套更深层级。

**边界**：无工作区概念的通用 skill 无法套用；多 skill 共存于同一目录时可能命名冲突（NOTES.md）；跨机器同步需要整个目录的版本控制。

**示例写法：**

```
# 工作区就是当前目录——无需任何初始化全局路径
# 用户用 cd ~/learning/react 来"选择"这个工作区

# 状态文件直接存当前目录
MISSION_FILE="MISSION.md"
NOTES_FILE="NOTES.md"

# 按类型分子目录，用编号序列保持有序
NEXT_NUM=$(ls learning-records/ 2>/dev/null | wc -l | xargs printf "%04d")
RECORD_FILE="learning-records/${NEXT_NUM}-${TOPIC_SLUG}.md"
```

---

## 三、三种思路的对比

| 维度 | 思路 A（全局集中分层） | 思路 B（项目内命名空间前缀） | 思路 C（工作目录即工作区） |
|------|---------------------|--------------------------|------------------------|
| 存储根位置 | `~/.gstack/`（用户主目录） | 项目目录内（`docs/{eco}/`） | CWD（用户选择的任意目录） |
| 项目隔离方式 | Slug（git repo 名） | 文件系统位置（在哪个项目内） | Cd 到哪里（用户隐式选择） |
| 文件类型分层 | 是（按关注点分子目录） | 否（统一放在 specs/） | 是（reference/, lessons/ 等） |
| 全局 vs 项目 | 全局，但按 slug 关联项目 | 项目内，可进 git | 工作区内，可选进 git |
| 跨机器同步 | 内置可选（git repo） | 跟随项目 git | 跟随工作区目录 git |
| Config/cache 约定 | 有（binary 读写） | 无显式约定 | 无（靠 CWD 隐式） |
| 项目目录是否干净 | 是 | 否（有 docs/eco/ 目录） | 取决于工作区选择 |

---

## 四、对原始哲学问题的回答

### 关于"全局目录还是项目目录"

研究未收敛，三种实践都有充分理由：

- **全局目录**（G stack）：适合跨 session 积累、跨项目通用的 config/cache/analytics 类文件。关键好处：项目目录保持干净，不需要 gitignore 处理。
- **项目目录内**（Superpowers）：适合输出产物类文件（规格、报告）——这类文件本来就属于项目，应该进 git，用户也期待在项目里找到它。
- **工作目录即工作区**（MSkill）：适合有明确"工作区"语义的 skill——用户理解自己在一个特定的上下文里工作。

**新发现**：G stack 实际上融合了两种策略——按文件「是否跟特定项目绑定」来选择子路径：
- 全局类（sessions/、analytics/）→ `~/.gstack/` 直接子目录
- 项目类（checkpoints/、decisions/）→ `~/.gstack/projects/$SLUG/` 子目录

这个"同一根目录下，按绑定关系分层"的策略是三者中最细腻的。

### 关于"是否需要按类型分子目录"

G stack 和 MSkill teach 都明确分了类型子目录，且都是按**关注点**分（不是按时间分）。Superpowers 没有在 `docs/superpowers/specs/` 内进一步分层。

可以得出结论：**按类型分子目录是普遍实践**，但粒度取决于文件数量预期——如果 skill 只会产生 1-2 种文件，扁平即可；如果会产生多种类型，按类型分目录能大幅提升可维护性。

### 新发现：命名规则是隐形的分类工具

三个来源都用文件名本身来携带元数据：
- G stack：`{TIMESTAMP}-{TITLE_SLUG}.md`（时间 + 内容描述）
- MSkill teach：`{0001}-{dash-case-name}.md`（序号 + 内容描述）
- Superpowers：`{YYYY-MM-DD}-{topic}-design.md`（日期 + 主题 + 类型）

这是"不用子目录分类，用文件名排序/归类"的隐性约定。当 skill 的某类文件较少时，命名规则可以替代子目录，降低结构复杂度。

---

研究完成 → [[principle]]
