---
migrated: 2026-06-21
implemented_in:
  - skills/experiment/init-skill/SKILL.md
  - skills/experiment/init-skill/references/skill-authoring-guide.md  # skill-authoring-guide 内容设计
---

# init-skill 设计文档

**日期：** 2026-06-16
**状态：** 已批准，待实现

---

## 背景

`harveyz-skill` 仓库的 skill 生命周期已覆盖：导入（`contribute-skill`）、校验注册（`publish-skill`）、分析（`analyze-skill`）、归档（`archive-skill`）等环节。

缺口是：**从零创建一个新 skill 的起点**。目前用户需要手动建目录、写 SKILL.md、对照规范检查，流程散且容易出错。

---

## 目标

提供一个 `init-skill`，能够：

1. 从设计文档（结构化 spec 或自由格式笔记）中提炼 skill 的核心要素
2. 对照最佳实践给出建议，与用户确认后生成完整 SKILL.md
3. 创建目录结构和功能分支，交棒给 `publish-skill` 完成注册

核心价值不只是脚手架，而是在生成时**主动传递 skill 编写标准**，让每个新 skill 从起点就符合质量要求。

---

## 不在范围内

- 注册到 `skills-index.json`（由 `publish-skill` 负责）
- 修改或更新已有 skill
- 批量创建多个 skill

---

## 方案选择

**选定：两段式——先提炼确认，后生成**

从设计文档提炼核心要素后，与用户逐字段确认，同时给出适用的最佳实践提示，确认通过后一次性生成文件。

理由：description 字段质量要求高（需含精确触发短语），自由格式文档直接生成容易出错；中间确认步骤把质量卡住，避免事后大量修改。

---

## 执行流程（6 步）

### Step 0 — 需求澄清

在任何操作之前，先确认用户意图是否完整。逐一检查以下信息是否清晰：

- 要创建的 skill 的**核心用途**是否已描述（哪怕一句话）
- 是否有**设计文档**（spec 文件或粘贴文本）可供读取，还是完全从对话描述出发
- 是否有**命名偏好**，或希望 Claude 根据内容推断

**澄清策略：**
- 每次只问一个问题，不要一次性列出所有疑问
- 只在信息确实缺失时提问；如果上下文已足够推断，不要多余确认
- 持续提问直到 Claude 认为需求完整、无歧义为止

只有需求明确后才进入 Step 1。

### Step 1 — 定位设计文档

按优先级：
1. 用户在对话中粘贴的描述文本（直接使用）
2. 用户指定的文件路径
3. 自动扫描 `docs/superpowers/specs/` 下最近修改的 `.md` 文件，列出候选供选择

### Step 2 — 提炼要素 + 最佳实践检查

从设计文档提取以下字段，读取 `references/skill-authoring-guide.md` 后，以表格 + 建议形式展示：

**提炼结果：**

| 字段 | 提取值 | 规范约束 |
|------|--------|---------|
| `name` | `<verb>-<noun>` 格式 | 动词必须在规范词表中 |
| `bundle` | 从现有 bundleMeta 中选 | 可新建 |
| `description` | 英文，含触发短语 | ≥ 10 字符，不含中文 |
| 正文大纲 | 中文，核心步骤列表 | — |
| `category` 目录 | 对应 bundle 的目录名 | — |

**适用的最佳实践提示（按 authoring guide 逐条检查，只列出适用的）：**

```
[✓] / [!] <实践条目> — <具体建议>
```

**等用户明确确认后才进入 Step 3。**

### Step 3 — 生成 SKILL.md

按规范格式生成完整文件：

```yaml
---
name: <name>
description: "<英文，含触发短语>"
user_invocable: true
version: "1.0.0"
---

# <正文标题（中文）>

## 触发条件
...

## 执行步骤
...

## 不在范围内
...
```

### Step 4 — 创建目录结构

```bash
mkdir -p skills/<category>/<name>/
# 写入 SKILL.md
```

若目标路径已存在：停止并报错，不覆盖。

### Step 5 — 创建功能分支并初始 commit

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

## skill-authoring-guide.md 内容设计

init-skill 携带 `references/skill-authoring-guide.md`，汇集两类知识：

### 显性规范（来自 skill-spec.md）

- 命名：`<verb>-<noun>`，动词必须在词表中（extract / learn / forge / draw / manage / migrate / scout / build / sync / publish / archive / contribute / analyze / clean / release / validate / init / dispatch / close / setup / capture / runby / dedup）
- frontmatter 必填字段：name / description / user_invocable / version
- description：英文，≥ 10 字符，含触发短语
- 正文：至少含一个中文字符
- version：初始 `"1.0.0"`

### 隐性模式（从现有优质 skill 提炼）

**正文结构**
- 推荐节顺序：触发条件 → 执行步骤（分 Step N） → 边界说明（不在范围内）
- 每个 Step 对应一个可验证的原子操作，不要把两个动作塞进一步

**description 写法**
- 格式：`"<动词短语说明功能>. Triggers: <触发场景列表，用逗号分隔>."` 或 `"<功能描述>. 触发场景：<列表>."`
- 触发词宁宽勿窄，但要避免与现有 skill 重叠
- 举例比描述更精确：`"Triggers: 'create new skill', 'scaffold skill', 'bootstrap skill from notes'"`

**references/ 子目录**
- 当 skill 需要携带查找表、模板、禁忌清单或长篇参考材料时，放入 `references/`
- 小规模内容（< 20 行）直接内联在 SKILL.md 中

**边界说明**
- 必须有"不在范围内"节，明确列出 2-4 个常见误用场景
- 防止 skill 在对话中被过度扩展

**触发条件与其他 skill 的区分**
- 若功能与现有 skill 有重叠，在 description 中明确区分触发场景
- 例：`init-skill` vs `contribute-skill`：前者从零创建，后者从其他项目导入

---

## 文件结构

```
skills/meta/init-skill/
  SKILL.md
  references/
    skill-authoring-guide.md
```

---

## 与现有 skill 的关系

| skill | 职责 | 交接点 |
|-------|------|--------|
| `init-skill` | 从设计文档生成 SKILL.md + 目录 + 分支 | 生成后交给 publish-skill |
| `publish-skill` | 格式校验（F1–F8）+ skills-index.json 注册 | init-skill 输出的文件 |
| `contribute-skill` | 从其他项目导入已有 skill | 互不重叠：init 从零建，contribute 从外部导入 |
