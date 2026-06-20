---
name: init-skill
description: "Initialize a new skill from scratch in the harveyz-skill repo — scaffolds SKILL.md, directory structure, and a feature branch from a design spec or free-form notes. Supports two reference standards (rule-based guide vs philosophy-based) for A/B experiments. Triggers: 'create new skill', 'scaffold a skill', 'init skill', 'bootstrap skill from notes', 'create skill from spec', 'help me start a new skill', 'initialize a skill', 'switch reference mode'."
user_invocable: true
version: "1.1.0"
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

## 参考标准（两份竞品，A/B 实验中）

本 skill 支持两份等价参考标准，由 `.hskill/init-skill/reference-mode.txt` 配置切换：

| mode | 文件 | 风格 |
|------|------|------|
| `guide` | `references/skill-authoring-guide.md` | 规则优先（R001-R120 编号规则） |
| `philosophy` | `references/skill-design-philosophies.md` | 哲学优先（16 条哲学 + 反例假设） |

两份文档覆盖同一规范领域但组织轴不同。用户可通过显式指令切换：

- "用哲学版" / "philosophy mode" / "切换到哲学" → 写入 `philosophy`
- "用规则版" / "guide mode" / "切换到规则" → 写入 `guide`

配置文件不存在时，Step 2a 会询问一次并保存。

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

### Step 2 — 选择参考标准 + 提炼要素 + 最佳实践检查

**2a. 确定参考标准 mode：**

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
MODE=$(cat "${REPO_ROOT}/.hskill/init-skill/reference-mode.txt" 2>/dev/null || echo "MODE_NOT_SET")
echo "Current mode: ${MODE}"
```

判定逻辑（按优先级）：

1. **用户在本次对话中明确指定** → 立即写入配置：
   - 消息含 "用哲学版" / "philosophy mode" / "切换到哲学" → `MODE=philosophy`
   - 消息含 "用规则版" / "guide mode" / "切换到规则" → `MODE=guide`
2. **配置文件存在且 mode 合法** → 使用该 mode
3. **配置文件不存在或损坏** → 询问用户一次：

   ```
   本 skill 支持两种参考标准（A/B 实验中）：
     [1] guide      — 规则优先（R001-R120 编号规则）
     [2] philosophy — 哲学优先（16 条哲学 + 反例假设）
   选择哪种？（输入 1 / 2 或 guide / philosophy）
   ```

确定 mode 后写入：

```bash
mkdir -p "${REPO_ROOT}/.hskill/init-skill"
echo "${MODE}" > "${REPO_ROOT}/.hskill/init-skill/reference-mode.txt"
```

**2b. 加载参考标准：**

根据 mode 用 Read 工具加载对应文件：

| mode | 文件路径 |
|------|---------|
| `guide` | `references/skill-authoring-guide.md` |
| `philosophy` | `references/skill-design-philosophies.md` |

向用户输出确认：`使用参考标准: ${MODE}（<对应文件>）`。

**2c. 提炼要素：** 从设计文档中提取以下字段，以表格 + 建议形式展示给用户：

| 字段 | 提取值 | 规范约束 |
|------|--------|---------|
| `name` | `<verb>-<noun>` 格式 | 动词必须在规范词表中 |
| `bundle` | 从现有 bundleMeta 中选 | 可新建 |
| `description` | 英文，含触发短语 | ≥ 10 字符，不含中文 |
| 正文大纲 | 中文，核心步骤列表 | — |
| `category` 目录 | 对应 bundle 的目录名 | — |

读取现有 bundle 列表：
```bash
node -e "const i=JSON.parse(require('fs').readFileSync('skills-index.json','utf8')); Object.entries(i.bundleMeta).forEach(([k,v])=>console.log(k+': '+v))"
```

**2d. 适用规范检查**（从 2b 加载的参考标准逐条检查，只列出适用的）：

```
[✓] <规范通过>  — <说明>
[!] <需要注意>  — <具体建议>
```

提示中明确标注本次使用的 mode，便于实验追溯：

```
（参考标准：${MODE}）
[✓] R001 name 与目录名一致     — 已通过
[!] R015 description 缺少 Triggers — 建议改为...
```

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

若 skill 有参考材料（查找表、模板、禁忌清单）且超过 20 行，按 Step 2 加载的参考标准提取到 `references/` 子目录，而非全部内联在 SKILL.md 中。

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

输出摘要（含 mode，便于实验追溯）：
```
✓ SKILL.md 已生成：skills/<category>/<name>/SKILL.md
✓ 分支：feature/init-<name>
✓ 参考标准：<mode>（guide / philosophy）
下一步：运行 /publish-skill 完成格式校验和 skills-index.json 注册
```

---

## 不在范围内

- 注册到 `skills-index.json`（由 `publish-skill` 负责）
- 修改或更新已有 skill（目标路径已存在时直接报错）
- 批量创建多个 skill（每次只处理一个）
- 编写 skill 的实际业务逻辑（只生成符合规范的骨架）
