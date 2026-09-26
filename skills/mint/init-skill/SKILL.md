---
name: init-skill
description: "Initialize a new skill from scratch in the harveyz-skill repo — scaffolds SKILL.md, directory structure, and a feature branch from a design spec or free-form notes. Applies the condensed skill design standard (16 philosophies + system mechanisms). Triggers: 'create new skill', 'scaffold a skill', 'init skill', 'bootstrap skill from notes', 'create skill from spec', 'help me start a new skill', 'initialize a skill'."
user_invocable: true
version: "1.3.0"
---
<!-- platform-standard-sha256: ad3d2f32f40cc282ef20bd3a19631a16f079839cc3e086a09b99011cc201fa2a -->

# 从设计文档初始化新 Skill

将设计文档（结构化 spec 或自由格式笔记）转化为符合规范的 SKILL.md，创建目录结构和功能分支，交棒给 `publish-skill` 完成注册。

---

## 触发条件

触发本 skill：
- "创建新 skill"、"初始化一个 skill"、"新建 skill"
- "从这份 spec 生成 skill"、"help me start a new skill"
- "scaffold skill"、"bootstrap skill"

不触发（其他 skill 负责）：
- 从其他项目**导入**已有 skill → 使用 `contribute-skill`
- **校验格式或注册** index → 使用 `publish-skill`
- **修改**已有 skill 内容 → 直接编辑对应 SKILL.md

---

## 参考标准

Step 2 从当前已安装的 skill 目录读取两份本地标准：`references/skill-standard.md`（设计哲学与系统机制）和 `references/platform-adaptation.md`（跨宿主判定边界）。两者随本 skill 安装，不依赖源仓库的 `docs/` 路径。

---

## 执行流程（6 步）

### Step 0 — 需求澄清

在任何操作之前，确认以下信息是否完整：

- **核心用途**：要创建的 skill 做什么？（哪怕一句话）
- **设计文档**：是否有 spec 文件路径或可粘贴的描述？还是完全从对话出发？
- **命名偏好**：是否有指定名称，或由当前 agent 根据内容提出候选？
- **目标宿主／有意限定范围**：是跨宿主使用，还是有意只服务某个宿主或研究对象？

澄清策略：
- 每次只问一个问题，不堆叠
- 上下文能推断的不再问
- 持续提问直到需求完整、无歧义为止

只有需求明确后才进入 Step 1。

### Step 1 — 定位设计文档

按优先级定位输入来源：

1. 用户在对话中粘贴的描述文本 → 直接使用
2. 用户指定的文件路径 → 用当前宿主可用的文件读取能力读取
3. 自动扫描最近修改的 spec：
   ```bash
   ls -t docs/superpowers/specs/*.md | head -5
   ```
   列出候选文件供用户选择。

### Step 2 — 提炼要素 + 标准检查

**2a. 加载标准：** 从本 skill 的实际安装目录读取 `references/skill-standard.md` 与 `references/platform-adaptation.md`；若任一文件缺失，停止并报告装机不完整，不从个人固定目录猜测。读取路径由当前 skill 目录确定，不把字面量 `SKILL_DIR` 当路径执行。

**2b. 提炼要素：** 从设计文档中提取以下字段：

| 字段 | 提取值 | 规范约束 |
|------|--------|---------|
| `name` | `<verb>-<noun>` 格式 | 动词必须在标准词表中 |
| `bundle` | 从现有 bundleMeta 中选 | 可新建 |
| `description` | 英文，含触发短语 | ≥ 10 字符，仅英文 |
| 正文大纲 | 中文，核心步骤列表 | — |
| `category` 目录 | 对应 bundle 的目录名 | — |
| 目标宿主／有意限定范围 | 明确支持范围 | 有意限定可保留，不冒称通用 |
| 核心能力 | 提问、委派、浏览、调度、worktree 等 | 运行时确认可用性 |
| 路径来源 | 当前 skill 目录、用户显式配置或工具查询 | 不假定 Claude 目录 |
| 适配点与回退 | 宿主调用差异、能力缺失时的替代或停止 | 保留共享语义 |
| 验证状态 | 静态审查／当前宿主实跑／未验证 | 不把可安装写成已实测 |

读取现有 bundle 列表：
```bash
node -e "const i=JSON.parse(require('fs').readFileSync('skills-index.json','utf8')); Object.entries(i.bundleMeta).forEach(([k,v])=>console.log(k+': '+v))"
```

**2c. 适用哲学识别：** 对照标准的 16 条哲学，识别本 skill 涉及的（通常 3–10 条）。每条按"触发"条件判断是否成立。

**2d. 标准检查：** 逐条核对相关哲学的"必做"和"检查"项，输出：

```
[✓] Φ1 可回退      — 破坏性 step 前有 y/n 确认
[✓] Φ5 配置就地    — 路径 .hskill/<name>/ 正确
[!] Φ12 输入清洁化 — URL 输入缺少控制字符剥离，建议加 re.sub(...)
```

涉及多哲学冲突时查标准末尾"张力点"表消歧。

**2e. 平台适配检查：** 按本地 `platform-adaptation.md` 区分共享任务语义、安装时已知值、宿主调用接口和运行时能力。对每个适用项报告“通过／缺口／不适用”及理由；缺少目标宿主、能力、路径来源、回退或验证信息时按 Step 0 一次一问澄清。宿主专有命令若是核心流程必经且无可执行回退，标为缺口；有意限定且明确说明范围则不算缺陷。未经运行验证的宿主标为未验证。

**等用户明确确认后才进入 Step 3。**

### Step 3 — 生成 SKILL.md

根据确认后的要素，生成完整 SKILL.md，遵循以下结构：

```
---
name: <name>
description: "<英文，含触发短语列表>"
user_invocable: true
version: "1.0.0"
---

# <正文标题（中文）>

## 触发条件
（覆盖"触发"和"不触发"两种情况）

## 执行步骤（Step 0 — Step N）

### Step 0 — 需求澄清
（如适用）

### Step 1 — ...
...

## 不在范围内
（2-4 条明确边界）
```

若 skill 有领域或技术栈参考材料（查找表、模板、禁忌清单）且超过 20 行，按标准 Φ18 提取到 `references/<dim>/`；短小宿主差异写在共享正文的明确适配章节，较长的宿主工具、委派或 worktree 调用放 `platforms/SKILL.<host>.md`。共享正文保留任务顺序、授权点、失败条件以及能力缺失时的回退或安全停止；适配文件不得改写这些语义。没有真实差异就不创建空适配器，也不机械生成七份宿主文件。

将生成内容展示给用户预览。**等用户明确确认后才进入 Step 4。**

### Step 4 — 建立隔离工作区（仍不写 skill）

先确认 Step 3 的完整预览已获用户明确同意。随后以仓库根目录为基准做只读检查：当前工作区必须干净，`staging` 必须可解析为明确提交，目标路径与目标分支不得已存在；脏工作区停止，目标路径已存在停止并提示更新已有 skill。宿主原生 worktree 入口只有能指定 `staging` 基线、独立分支和目标路径时才可使用；不能指定或绑定基线则回退到下列显式路径 Git 命令，回退也不可用时停止，不在当前 checkout 写入。

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
BRANCH="feature/init-<name>"
WT="${REPO_ROOT}/.worktrees/feature-init-<name>"
git -C "$REPO_ROOT" status --porcelain
git -C "$REPO_ROOT" rev-parse --verify 'staging^{commit}'
git -C "$REPO_ROOT" branch --list "$BRANCH"
git -C "$REPO_ROOT" check-ignore -q .worktrees/
git -C "$REPO_ROOT" worktree add "$WT" -b "$BRANCH" staging
git -C "$WT" config core.hooksPath .githooks
git -C "$WT" config merge.ff false
```

`status` 必须为空、`branch --list` 必须为空，`check-ignore` 必须成功；任一条件不满足即停止。创建 worktree 后重新确认其分支名和 `skills/<category>/<name>/` 不存在。若创建或配置失败，保留现场并报告，不回到 `staging` 写文件。

### Step 5 — 在独立工作区写入并初始 commit

仅在 Step 4 全部通过后，用当前宿主可用的文件写入能力，将 Step 3 预览确认过的 `SKILL.md` 和必要 `references/`、`platforms/` 文件写入新 worktree 的 `skills/<category>/<name>/`。写入新 skill 之前再次核对目标路径；任何文件写入或 Git 命令失败都停止并保留现场，不自动覆盖、不自动合并或推送。

```bash
git -C "$WT" add "skills/<category>/<name>/"
git -C "$WT" commit -m "feat(skill): scaffold <name>"
```

输出摘要：
```
✓ SKILL.md 已生成：<worktree>/skills/<category>/<name>/SKILL.md
✓ 分支：feature/init-<name>（从 staging 明确基线创建）
✓ 平台检查：通过／缺口／不适用及未验证项
下一步：运行 publish-skill 完成格式校验和 skills-index.json 注册
```

---

## 不在范围内

- 注册到 `skills-index.json`（由 `publish-skill` 负责）
- 修改或更新已有 skill（目标路径已存在时直接报错）
- 批量创建多个 skill（每次只处理一个）
- 编写 skill 的实际业务逻辑（只生成符合规范的骨架）
