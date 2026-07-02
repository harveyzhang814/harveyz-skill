---
name: dedup-skill
description: "Detect semantic overlap between two or more skills at the logical-block level. Use this skill whenever someone wants to compare skills for duplication, find overlapping steps between skills, check if two skills share logic, or audit skill responsibilities. Triggers: 'compare X and Y skills', 'find overlap between X and Y', 'do X and Y duplicate logic', 'audit skill duplication'."
user_invocable: true
version: "1.0.0"
---

检测两个或多个 skill 之间的语义重复内容，粒度为语义块级别（不依赖标题结构）。发现重叠后给出职责归属建议，由用户决定最终处置方式。

## 触发方式

### 方式 A：指定 skill（主流程）

用户指令中给出 2 个或多个 skill 名时，执行以下流程：

**1. 提取 skill 名**
从用户输入中提取所有 skill 名（支持带或不带路径前缀）。

**2. 模糊匹配**
读取 `skills-index.json` 获取所有已注册 skill 的 path 末段：

```bash
node -e "const idx=require('./skills-index.json'); idx.skills.forEach(s=>console.log(s.path.split('/').pop()+'\t'+s.path));"
```

匹配规则：

| 情况 | 处理方式 |
|------|----------|
| 完全匹配 | 直接使用 |
| 部分匹配 1 个 | 提示用户确认 "是否指 X？" |
| 部分匹配多个 | 列出候选项，请用户选择 |
| 0 匹配 | 提示 skill 不存在，询问是否重新输入 |

**3. 确认列表**
所有 skill 名匹配完成后，展示确认列表，等待用户确认后继续。

### 方式 B：未指定 skill

若用户未在指令中给出 skill 名，提示：

> 请告知需要对比的 skill 名称（至少 2 个）。
> 如需批量扫描全库，请参考 `references/auto-scan.md`。

---

## Step 1 — 语义块提取

读取每个 skill 的 `SKILL.md` 正文（frontmatter 之后的内容）。

对每个 skill，将正文划分为独立语义块：
- 不依赖标题层级，纯语义切分
- 每块应表达一个完整的独立意图（步骤、规则、模板、判断逻辑等）

每块记录以下信息：

| 字段 | 说明 |
|------|------|
| skill | skill 名称 |
| 位置描述 | 在文件中的相对位置（如"第 2 段"、"触发规则部分"） |
| 原文摘要 | 该块核心内容，50 字以内 |

提取完成后，在内部维护一份块清单，供 Step 2 使用（不向用户展示原始清单）。整个分析过程（Step 1-3）均在内部完成，仅在最终输出阶段呈现报告。

---

## Step 2 — 跨 skill 块聚类

将所有 skill 的块放在一起分析，找出"描述同一件事"的块组（聚类）。

聚类维度：
- **逻辑等价**：两个块表达完全相同的操作或规则
- **逻辑交叉**：两个块有部分重叠，但各自包含对方没有的内容

注意事项：
- 不做 N² 逐对比较，整体语义聚类
- 只聚类有实质重叠的块；相似的触发词或元数据不算重叠
- 若无任何聚类，跳过 Step 3，直接输出无重叠结果

---

## Step 3 — 职责边界分析

对每个聚类，分析以下内容：

1. **各 skill 整体定位**：该 skill 的核心职责是什么
2. **块的性质**：该重叠块是核心逻辑还是附带步骤
3. **归属建议**：哪个 skill 更适合作为该逻辑的权威来源

归属建议原则：
- 该逻辑与哪个 skill 的核心目标最对齐，归属于该 skill
- 附带步骤（如"保存文件"、"确认用户输入"）不作为重叠标记，除非两个 skill 都将其作为核心流程
- 若归属不明确，标记为"待定"，并列出两种方案供用户选择

---

## 输出

### 确定输出目录

1. 从仓库根目录的 `docs/skill-analysis/` 开始，逐级向上查找 `DIR_METHOD.md`，查找上限为仓库根目录（不超出 git rev-parse --show-toplevel 所在目录）
2. 若找到，调用 `dir-manage` skill 处理目录路径
3. 若未找到，默认使用 `docs/skill-analysis/`（执行 `mkdir -p`）

### 报告文件名

格式：`dedup-<YYYYMMDD-HHMMSS>.md`

示例：`dedup-20260615-143022.md`

### 报告结构模板

```markdown
# Skill 重叠分析报告

**分析时间：** YYYY-MM-DD HH:MM:SS
**对比 skill：** skill-A、skill-B（...）

---

## 重叠清单

### 重叠 1：<简短描述>

**类型：** 逻辑等价 / 逻辑交叉

| Skill | 位置 | 摘要 |
|-------|------|------|
| skill-A | 第 N 段 | ... |
| skill-B | 第 N 段 | ... |

**职责归属建议：** 建议归属于 `skill-A`，原因：...

---

（重复以上结构）

## 汇总

| 重叠编号 | 类型 | 建议归属 |
|----------|------|----------|
| 重叠 1 | 逻辑等价 | skill-A |
| 重叠 2 | 逻辑交叉 | 待定 |

---
## 未发现重叠的范围
<列出已对比但未发现重叠的领域>

---

## 建议后续操作

- [ ] ...
```

### 无重叠情况

若 Step 2 未发现任何聚类，输出：

```
对比完成：skill-A 与 skill-B 之间未发现语义重叠。
无需生成报告文件。
```

直接回复用户，不生成文件。

---

## 边界情况

| 情况 | 处理方式 |
|------|----------|
| 某个 skill 的 SKILL.md 不存在 | 报错提示，跳过该 skill，继续处理其他 skill |
| 用户指定了 3 个以上 skill | 正常处理，聚类时同时考虑所有 skill |
| 两个 skill 共享同一个 references 文件 | 不算重叠，references 是共享资源 |
| 重叠块仅为模板/示例内容 | 标记为低优先级，单独列出，不混入主重叠清单 |
| skill 正文极短（< 3 个语义块） | 正常处理，说明块数量有限 |
| skill 名在 index 中 0 匹配 | 报错，列出所有可用 skill 名后退出 |
| 对比同一个 skill 与自身 | 报错："请指定不同的 skill" |

---

## 不在范围内

- 不自动修改任何 skill 文件（仅分析，不执行）
- 不对比 skill 的 frontmatter 字段（name、description、version 等）
- 不扫描全库 skill（如需批量扫描，参考 `references/auto-scan.md`）
