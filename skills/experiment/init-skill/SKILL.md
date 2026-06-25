---
name: init-skill
description: "Initialize a new skill from scratch in the harveyz-skill repo — scaffolds SKILL.md, directory structure, and a feature branch from a design spec or free-form notes. Applies the condensed skill design standard (16 philosophies + system mechanisms). Triggers: 'create new skill', 'scaffold a skill', 'init skill', 'bootstrap skill from notes', 'create skill from spec', 'help me start a new skill', 'initialize a skill'."
user_invocable: true
version: "1.2.0"
---

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

本 skill 使用 `references/skill-standard.md` 作为单一标准——精简版（约 200 行），含 16 条设计哲学 + 系统机制 + 张力点。Step 2 加载该文件并对照检查。

---

## 执行流程（6 步）

### Step 0 — 需求澄清

在任何操作之前，确认以下信息是否完整：

- **核心用途**：要创建的 skill 做什么？（哪怕一句话）
- **设计文档**：是否有 spec 文件路径或可粘贴的描述？还是完全从对话出发？
- **命名偏好**：是否有指定名称，或由 Claude 根据内容推断？

澄清策略：
- 每次只问一个问题，不堆叠
- 上下文能推断的不再问
- 持续提问直到需求完整、无歧义为止

只有需求明确后才进入 Step 1。

### Step 1 — 定位设计文档

按优先级定位输入来源：

1. 用户在对话中粘贴的描述文本 → 直接使用
2. 用户指定的文件路径 → 用 Read 工具读取
3. 自动扫描最近修改的 spec：
   ```bash
   ls -t docs/superpowers/specs/*.md | head -5
   ```
   列出候选文件供用户选择。

### Step 2 — 提炼要素 + 标准检查

**2a. 加载标准：** 用 Read 工具读取 `references/skill-standard.md`（精简版，约 200 行）。

**2b. 提炼要素：** 从设计文档中提取以下字段：

| 字段 | 提取值 | 规范约束 |
|------|--------|---------|
| `name` | `<verb>-<noun>` 格式 | 动词必须在标准词表中 |
| `bundle` | 从现有 bundleMeta 中选 | 可新建 |
| `description` | 英文，含触发短语 | ≥ 10 字符，仅英文 |
| 正文大纲 | 中文，核心步骤列表 | — |
| `category` 目录 | 对应 bundle 的目录名 | — |

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

若 skill 有参考材料（查找表、模板、禁忌清单）且超过 20 行，按标准 Φ18 提取到 `references/` 子目录，而非全部内联在 SKILL.md 中。

将生成内容展示给用户预览。**等用户明确确认后才进入 Step 4。**

### Step 4 — 创建目录并写入文件

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
mkdir -p "${REPO_ROOT}/skills/<category>/<name>/"
```

若目标路径已存在：停止并报错，提示用户使用 `publish-skill` 更新已有 skill，不覆盖任何文件。

用 Write 工具写入 `skills/<category>/<name>/SKILL.md`。

### Step 5 — 创建功能分支并初始 commit

执行前检查：
```bash
git status --short
```
若有未提交的修改（输出非空）：停止并提示用户先提交或暂存当前变更，再重新运行 Step 5。

```bash
git checkout -b feature/init-<name>
git add skills/<category>/<name>/
git commit -m "feat(skill): scaffold <name>"
```

输出摘要：
```
✓ SKILL.md 已生成：skills/<category>/<name>/SKILL.md
✓ 分支：feature/init-<name>
下一步：运行 /publish-skill 完成格式校验和 skills-index.json 注册
```

---

## 不在范围内

- 注册到 `skills-index.json`（由 `publish-skill` 负责）
- 修改或更新已有 skill（目标路径已存在时直接报错）
- 批量创建多个 skill（每次只处理一个）
- 编写 skill 的实际业务逻辑（只生成符合规范的骨架）
