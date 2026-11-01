---
name: draw-diagram
description: "Professional Mermaid diagramming standards. Triggers immediately when the user mentions drawing diagrams, flowcharts, sequence diagrams, state machines, Gantt charts, quadrant charts, mind maps, or needs to embed any Mermaid chart in a Markdown document. Supports flowchart, sequenceDiagram, stateDiagram, timeline, gantt, quadrantChart, and mindmap."
user_invocable: true
version: "1.5.0"
---

# Mermaid 专业作图标准

> **按需读取对应文件，不要一次性全部读入：**
> - flowchart / 产业链 / 板块地图 → `references/flowchart.md`
> - sequenceDiagram / 时序图 / 接口调用 → `references/sequence.md`
> - stateDiagram / 状态机 / 周期图 → `references/statediagram.md`
> - gantt / timeline → `references/gantt-timeline.md`
> - quadrantChart / mindmap → `references/other-charts.md`
> - Python 批量检测 → `scripts/check_mermaid.py`（直接运行，无需读入）

---

## 1. 图类型选择矩阵（最关键一步）

### 按语义选型

| 要表达的语义 | 正确图类型 | 错误选择 | 理由 |
|------------|----------|---------|------|
| 产业链 / 供应链（有方向的流动） | `flowchart TD`（3 个 subgraph，UP -> MID -> DOWN 层间箭头） | `mindmap` | mindmap 是放射状从属关系，无法表达方向性流动 |
| 层级树形结构（无流向） | `mindmap` | `flowchart` | mindmap 的分支布局更自然 |
| 循环状态转换 | `stateDiagram-v2` | `flowchart` | stateDiagram 语义最精确 |
| 时间轴事件 | `timeline` | `gantt` | timeline 按时间节点列举，无时段重叠 |
| 并行时间段 / 甘特 | `gantt` | `timeline` | gantt 能展示多条目时间段重叠 |
| 二维象限定位 | `quadrantChart` | 自制坐标 | 原生支持，配置简单 |
| 系统 / 服务间有时序的调用链 | `sequenceDiagram` | `flowchart` | sequenceDiagram 原生支持激活框、条件块、并行 |
| 流程 / 资金流 / 数据流（可有环路） | `flowchart TD` | `sequenceDiagram` | flowchart 支持循环箭头 |
| 板块地图（股票/行业） | `flowchart TD` + subgraph | `mindmap` / 表格 | subgraph 支持分组+颜色+箭头 |
| 时间轮动 / 波浪 | `timeline` | `graph LR` | timeline 语义直接对应时序 |

---

## 2. 布局原则

### 宽度控制（窄页优先）

Markdown 渲染器页面宽度通常 700–900px，图表必须适配：

| 场景 | 规则 |
|------|------|
| 主流方向 | 优先 `flowchart TD`（纵向），避免 `flowchart LR` |
| subgraph 内节点 | **最多 2–3 个节点并排**；超过则用 `---` 配对 |
| stateDiagram | 使用 `direction TB`，不用 `direction LR` |
| 不可用横向LR的场景 | 产业链、板块地图、状态机、节奏图 |

### 禁止的布局写法

```
❌ direction TB in flowchart subgraph   # 仅 v10+ 支持，兼容性差
❌ 4+ 孤立节点在同一 subgraph           # 全部横向排开，过宽
❌ flowchart LR 用于产业链              # 三列并排超出页面
❌ nested subgraph（嵌套子图）          # Mermaid 渲染不稳定
```

> `---` 矩阵配对、subgraph 间箭头写法见 `references/flowchart.md`。

---

## 3. 配色主题系统

配色从品牌主题文件读取，**不在图中硬编码**。生成图表前先读取对应文件：

| 品牌 | 主题文件 | 默认 |
|------|---------|:----:|
| Bain & Company | `themes/bain.json` | ✓ |
| BCG | `themes/bcg.json` | |
| Roland Berger | `themes/rolandberger.json` | |

用户未指定品牌时默认使用 Bain 主题。

### 图类型 → 样式机制

每种图类型使用不同的样式机制，主题文件按图类型分区存储配置：

| 图类型 | 样式机制 | 主题路径 |
|--------|---------|---------|
| `flowchart` | 内联 `style` 声明（**禁用** `%%{init}%%`） | `flowchart.*` |
| `stateDiagram-v2` | `classDef` + `class` | `stateDiagram.classDef.*` |
| `sequenceDiagram` | `%%{init}%%` themeVariables | `sequenceDiagram.init` |
| `gantt` | `%%{init}%%` themeVariables | `gantt.init` |
| `timeline` | `%%{init}%%` themeVariables | `timeline.init` |
| `quadrantChart` | 库默认（控制极度有限，不强制品牌色） | — |

### flowchart — 内联 style

subgraph 使用**弱色背景**（浅灰梯度）作为分组底色，节点色编码实体**类型**，不跟随 subgraph 层编号：

| 场景 | 用法 |
|------|------|
| 同类实体（如供应链企业） | 全部用 `flowchart.node.neutral`（白色卡片） |
| 不同实体类型 | `node.primary` / `node.secondary` 区分类型 |
| 投资信号 / 风险状态 | `semantic.opportunity` / `semantic.alert` / `semantic.hold` |

节点文字色：fill 浅于 `rules.dark_text_threshold` → `color:#212427`；否则 `color:#fff`。

### stateDiagram-v2 — classDef

从 `stateDiagram.classDef` 读取，逐行写入图顶部：

```
classDef neutral     fill:#EBEBEB,stroke:#C8C8C8,color:#212427
classDef opportunity fill:#E87722,stroke:#BA5F1B,color:#fff
classDef hold        fill:#666666,stroke:#525252,color:#fff
classDef danger      fill:#CC0000,stroke:#A30000,color:#fff
```

### sequenceDiagram / gantt / timeline — %%{init}%%

从各自 `<type>.init` 字段读取 themeVariables，写入图**首行**（仅这三种图类型允许 `%%{init}%%`）：

```
%%{init: {"theme":"base","themeVariables":{...}}}%%
```

完整键值见主题文件对应分区。

### 语义辅助色（跨图类型共享）

`semantic.*` 在所有图类型中语义一致：

| 键 | 用途 | Bain 颜色 |
|----|------|-----------|
| `alert` | 风险 / 规避 | `#CC0000` 红 |
| `opportunity` | 机会 / 买入 | `#E87722` 橙 |
| `hold` | 中性 / 观察 | `#666666` 灰 |
| `speculative` | 主题 / 高波动 | `#2E0078` 紫 |
| `value` | 权威 / 核心配置 | `#1A1A1A` 近黑 |

> 完整 Bain 配色示例 → `tests/bain-style-test.md`

---

## 4. 语法禁区（Syntax Forbidden Zone）

### 禁用字符（Fatal Characters）

| 字符 | Unicode | 替换方案 |
|------|---------|---------|
| `·` 中点 | U+00B7 | 用 `/` 或空格 |
| `→` 右箭头 | U+2192 | 用 `->` 或 `to` |
| `—` 破折号 | U+2014 | 用 `-` |
| `"` `"` | U+201C/D | 用 `"` 标准双引号 |
| emoji | >U+1F000 | 完全删除 |

### 禁用语法

```
❌ \n 换行符在节点标签内        → 改用 <br/>
❌ / 在 quadrant 标签内        → 改用空格或删除
❌ + 在 timeline key 内         → 改用 "以后" 或文字后缀
❌ 中文作为 stateDiagram stateID → 用 ASCII ID + as 别名
❌ YYYY-Q 日期格式在 gantt      → 改用 YYYY-MM-DD
❌ direction TB 在 flowchart subgraph → 改为全局 TD，删除子图内 direction
❌ 多行 edge label（|"line1\nline2"|）→ 改为单行短语
❌ sequenceDiagram 中文/空格参与者名不加处理 → 用 alias 或引号
❌ sequenceDiagram activate 未配对 deactivate → 必须一一对应
❌ sequenceDiagram 消息文本内换行 → 不支持，保持单行
❌ %%{init:...}%% 多行块在 flowchart 中 → 导致渲染失败、颜色全部丢失；flowchart 配色只用 style 声明
```

---

## 5. 渲染前强制检查清单

每张图输出前逐项检查以下各项，全部通过才输出：

```
□ 1.  图类型与语义匹配（见第 1 节选型矩阵）
□ 2.  主方向为 TD 或纵向（非 LR，除非有充分理由）
□ 3.  subgraph 内每行 ≤ 3 个节点（超过已用 --- 配对）
□ 4.  无 emoji 字符（在任何标签/子图/边中）
□ 5.  无 · 中点符（全文替换为 /）
□ 6.  无 → 箭头字符（替换为 -> 或文字）
□ 7.  节点标签换行使用 <br/>，不使用 \n
□ 8.  stateDiagram state ID 全为 ASCII
□ 9.  gantt 日期格式为 YYYY-MM-DD
□ 10. quadrantChart 标签无 /
□ 11. timeline key 无 + % & 特殊字符
□ 12. fill 深于主题 rules.dark_text_threshold 的节点已设 color:#fff
□ 13. sequenceDiagram 参与者名含中文/空格时已用 alias 或引号
□ 14. sequenceDiagram 每个 activate 有对应 deactivate
```

> 批量自动检测 → 运行 `scripts/check_mermaid.py`
