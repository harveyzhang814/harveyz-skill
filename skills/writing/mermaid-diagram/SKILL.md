---
name: mermaid-diagram
description: >
  Mermaid 专业作图标准。只要用户提到"画图"、"mermaid"、"流程图"、"产业链"、
  "板块地图"、"时序图"、"序列图"、"状态机"、"甘特图"、"象限图"、"思维导图"、
  "接口调用"、"系统交互"，或需要在 Markdown 文档中嵌入任何 Mermaid 图表，
  立即调用本 skill。支持 flowchart / sequenceDiagram / stateDiagram / timeline /
  gantt / quadrantChart / mindmap 全类型。
user_invocable: true
version: "1.3.0"
---

# Mermaid 专业作图标准

> **按需读取对应文件，不要一次性全部读入：**
> - flowchart / 产业链 / 板块地图 → `references/flowchart.md` + `references/color-templates.md`
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
| 产业链 / 供应链（有方向的流动） | `flowchart TD` | `mindmap` | mindmap 是放射状从属关系，无法表达方向性流动 |
| 层级树形结构（无流向） | `mindmap` | `flowchart` | mindmap 的分支布局更自然 |
| 循环状态转换 | `stateDiagram-v2` | `flowchart` | stateDiagram 语义最精确 |
| 时间轴事件 | `timeline` | `gantt` | timeline 按时间节点列举，无时段重叠 |
| 并行时间段 / 甘特 | `gantt` | `timeline` | gantt 能展示多条目时间段重叠 |
| 二维象限定位 | `quadrantChart` | 自制坐标 | 原生支持，配置简单 |
| 系统 / 服务间有时序的调用链 | `sequenceDiagram` | `flowchart` | sequenceDiagram 原生支持激活框、条件块、并行 |
| 资金 / 数据流（有环路） | `flowchart TD` | `sequenceDiagram` | flowchart 支持循环箭头 |
| 板块地图（股票/行业） | `flowchart TD` + subgraph | `mindmap` / 表格 | subgraph 支持分组+颜色+箭头 |
| 时间轮动 / 波浪 | `timeline` | `graph LR` | timeline 语义直接对应时序 |

### 图类型速查

```
flowchart TD      → 产业链、流程、板块地图、资本流
flowchart LR      → 仅当内容天然横向（如横向对比）才用，否则用 TD
sequenceDiagram   → 系统/服务间交互、API 调用时序、接口联调
mindmap           → 纯树形知识结构，无需表达流向
timeline          → 历史事件/里程碑时间轴，每个时间点有多个条目
gantt             → 多轨道并行时间段（如技术迭代、项目计划）
stateDiagram-v2   → 状态机、周期轮动（如估值周期）
quadrantChart     → 2×2 矩阵定位（如确定性 vs 弹性）
```

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

> 矩阵布局 `---` 配对技法、subgraph 间箭头写法见 `references/flowchart.md 或对应图类型文件`。

---

## 3. Roland Berger 配色体系

### 核心色板

```
主色 Deep Navy   #00205B   用于最重要/最底层/上游  subgraph
主色 RB Blue     #003E96   用于中间层/平台层        subgraph
中蓝 Medium Blue #1E5C9E   用于应用层/下游          subgraph
节点 Navy Node   #0A2E7A   上游 subgraph 内节点
节点 Blue Node   #0050B8   中游 subgraph 内节点
节点 Mid Node    #2A6EAE   下游 subgraph 内节点
```

### 语义辅助色

```
预警 / 高风险    fill:#7B1010  stroke:#B52020
机会 / 买入      fill:#1A5E3A  stroke:#2A7E50
等待 / 持有      fill:#003E96  stroke:#1A6AC4
投机 / 主题      fill:#2E0078  stroke:#5A20A0
价值 / 配置      fill:#004060  stroke:#1A5E80
```

### 配色规则

- 深色背景（fill 暗于 `#4A4A4A`）**必须**加 `color:#fff`
- subgraph 背景比节点背景**深 10–15%**（提供层次感）
- 同一图内最多使用 **3 种主色** + 语义辅助色
- `quadrantChart` 的 quadrant 标签不加颜色（库自动渲染）
- `timeline` / `gantt` / `stateDiagram` 使用库默认颜色，不强制 RB 色

> 完整配色模板（含三层产业链示例）→ `references/color-templates.md`

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
```

---

## 5. 渲染前强制检查清单

每张图创建完毕后，**逐项检查**以下 12 项，全部通过才能输出：

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
□ 12. 所有深色节点（fill 深于 #4A4A4A）已设 color:#fff
□ 13. sequenceDiagram 参与者名含中文/空格时已用 alias 或引号
□ 14. sequenceDiagram 每个 activate 有对应 deactivate
```

> 批量自动检测 → 运行 `scripts/check_mermaid.py`

---

## 6. 快速参考卡

### 图类型 → 场景

```
产业链/供应链   → flowchart TD + 3个subgraph + UP→MID→DOWN 箭头
板块地图        → flowchart TD + subgraph per layer + --- 矩阵节点
资本/数据流     → flowchart TD + 有向链 + 反馈环
系统交互/时序   → sequenceDiagram + participant alias + activate/deactivate
状态周期        → stateDiagram-v2 direction TB + ASCII state ID
时间轴          → timeline（事件点）/ gantt（时间段）
象限定位        → quadrantChart
知识树          → mindmap
```

### RB 配色速查

```
上游子图   fill:#00205B  stroke:#1E4A9A
中游子图   fill:#003E96  stroke:#1A6AC4
下游子图   fill:#1E5C9E  stroke:#3A8ACC
上游节点   fill:#0A2E7A  stroke:#1E4A9A
中游节点   fill:#0050B8  stroke:#1A6AC4
下游节点   fill:#2A6EAE  stroke:#3A8ACC
预警红     fill:#7B1010  stroke:#B52020
机会绿     fill:#1A5E3A  stroke:#2A7E50
投机紫     fill:#2E0078  stroke:#5A20A0
价值蓝绿   fill:#004060  stroke:#1A5E80
所有深色背景加 color:#fff
```

### 禁用字符替换

```
·  (U+00B7)  → /
→  (U+2192)  → ->  或文字
—  (U+2014)  → -
"" (U+201C/D)→ "
emoji        → 删除
\n 在节点    → <br/>
```

### 矩阵布局模板

```
A["节点A"] --- B["节点B"]    ← 第一行（2列）
C["节点C"] --- D["节点D"]    ← 第二行（2列）
E["奇数节点"]                 ← 第三行（居中）
```
