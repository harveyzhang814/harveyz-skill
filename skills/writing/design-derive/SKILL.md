---
name: design-derive
description: "Derive format-specific configs from a brand design knowledge doc. Trigger when the user wants to generate doc-forge JSON/CSS, HTML CSS variables, Mermaid color scheme, or PPT theme from a design system. E.g. 'derive configs for BCG', 'generate doc-forge style for rb', 'create HTML theme from custom-style'."
user_invocable: true
version: "1.4.0"
---

## 概述

读取 `knowledge/design/<brand>-style.md`，推导各输出格式的具体配置。

**只做推导，不调查官网。** 官网调查由 `/style-scout` 负责。

**映射标准：** 格式字段 ↔ Token 的完整映射规则定义在 `skills/writing/design-derive/references/FORMAT-MAPPING.md`，推导时以该文件为权威依据。品牌文件提供 Token 值，FORMAT-MAPPING.md 提供映射规则，两者分离。

支持输出格式：
- **DOCX** — `doc-forge/<brand>-style.json`
- **PDF** — `doc-forge/<brand>.css`
- **HTML** — CSS 变量块（打印到对话或写入文件）
- **Mermaid** — 图表配色方案
- **PPT** — 演示文稿主题描述

---

## 执行步骤

### Step 1 — 确认目标

从对话上下文推断品牌名（用于文件命名和路径查找）。若未提供，询问：

> 请提供品牌名（如 bain / custom），或完整路径（如 knowledge/design/bain-style.md）

确认目标格式（若未指定，默认推导 DOCX + PDF）：

> 需要推导哪些格式？
> 1. DOCX（doc-forge JSON）
> 2. PDF（doc-forge CSS）
> 3. HTML CSS 变量
> 4. Mermaid 配色
> 5. PPT 主题
> 6. 全部

---

### Step 2 — 读取设计文档并解析 Token 链

```bash
BRAND="<brand>"
KNOWLEDGE_FILE="knowledge/design/${BRAND}-style.md"
```

用 Read 工具读取 `$KNOWLEDGE_FILE` 和 `skills/writing/design-derive/references/FORMAT-MAPPING.md`。

**Token 解析方式（三层引用链）：**

值格式为 `{token-name}` 时，顺着引用链向上查，直到得到原始 hex：

```
comp.heading.h1.deco-line
  → {color.interactive.primary}   (2.2 Semantic)
    → {lime-400}                   (2.1 Primitive 引用名)
      → #96F878                    ← 最终写入配置的值
```

若 style.md 按旧格式写成（直接写 hex 而非 token 引用），直接读取对应 hex。

**从文档提取以下变量：**

**色彩（通过 Token 链解析到 hex）：**

| 变量名 | 来源 Token | 备注 |
|-------|-----------|------|
| `H1_DECO_COLOR` | `comp.heading.h1.deco-line` → resolve | H1/H2 装饰线颜色 |
| `H3_BAR_COLOR` | `comp.heading.h3.left-bar` → resolve | H3 左色条颜色 |
| `H1_COLOR` | `comp.heading.h1.color` → resolve | H1 文字色 |
| `H2_COLOR` | `comp.heading.h2.color` → resolve | H2 文字色 |
| `H3_COLOR` | `comp.heading.h3.color` → resolve | H3 文字色 |
| `H4_COLOR` | `comp.heading.h4.color` → resolve | H4 文字色 |
| `BODY_COLOR` | `comp.body.color` → resolve | 正文色 |
| `LINK_COLOR` | `comp.link.color` → resolve | 链接色 |
| `BQ_BAR_COLOR` | `comp.blockquote.left-bar` → resolve | 引用块左色条 |
| `BQ_COLOR` | `comp.blockquote.color` → resolve | 引用文字色 |
| `TABLE_HEADER_LINE` | `comp.table.border-header` → resolve | 表头横线色 |
| `TABLE_ROW_LINE` | `comp.table.border-row` → resolve | 行分隔线色 |
| `TABLE_ACCENT` | `comp.table.accent-line` → resolve | 表头强调线（rb） |
| `CODE_BG` | `comp.code.bg` → resolve | 代码块背景 |
| `CODE_BAR` | `comp.code.left-bar` → resolve | 代码块左色条 |
| `HR_COLOR` | `comp.hr.color` → resolve | 水平线色 |
| `BG_SECTION` | `color.surface.section` → resolve | 分区背景 |
| `BG_DARK` | `color.surface.dark` → resolve | 深色块背景 |
| `VIZ_1..5` | `color.dataviz.1..5` → resolve | 数据可视化色序 |

**字体（直接读 3 节）：**
- `FONT_HEADING_EN` — 3.2 标题降级字体第一项
- `FONT_HEADING_STACK` — 3.2 标题完整字体栈
- `FONT_BODY_EN` — 3.2 正文降级字体第一项
- `FONT_BODY_STACK` — 3.2 正文完整字体栈
- `FONT_MONO_STACK` — 3.2 等宽字体栈

**字号（直接读 3.3）：**
- `H1_PT`, `H2_PT`, `H3_PT`, `H4_PT`, `BODY_PT`
- `LINE_SPACING_PT` — 正文行距
- `H1_BOLD`, `H2_BOLD`, `H3_BOLD` — 是否加粗

**间距（直接读 4 节）：**
- `PAGE_TOP_CM`, `PAGE_BOTTOM_CM`, `PAGE_LEFT_CM`, `PAGE_RIGHT_CM`
- `H1_SPACE_BEFORE`, `H1_SPACE_AFTER`, `H2_SPACE_BEFORE`, `H2_SPACE_AFTER`
- `PARA_SPACE_AFTER`, `FIRST_LINE_INDENT`

**组件（直接读 5.2）：**
- `TABLE_MODE` — grid / mckinsey / rb / 无框
- `TABLE_HEADER_BG` — 表头背景（null = 无）
- `H3_HAS_LEFT_BAR` — H3 是否有左色条（从 5.1 读取）

---

### Step 2b — 网页尺度 → 文档尺度换算

品牌知识文档的字号来自官网 CSS 测量，往往是面向全屏 display 的展示尺度，**不能直接用于 A4 文档**，需换算后再写入配置。

**触发条件（全部满足时执行）：**
- `H1_PT > 28`
- `BODY_PT ≤ 14`

**换算算法（等比双锚点插值）：**

以 H1=24pt 为上锚点，H4 为下锚点（若 H4 已合理 ≤ 14 则保留，否则取 11pt）：

```
H4_doc = H4_PT  if H4_PT ≤ 14,  else 11
ratio  = (24 / H4_doc) ^ (1/3)       # 三步等比
H3_doc = round(H4_doc × ratio)
H2_doc = round(H3_doc × ratio)
H1_doc = 24
```

**安全检查（换算后验证）：**
- `H1_doc > H2_doc > H3_doc > H4_doc`
- `H3_doc ≥ BODY_PT`（H3 不应小于正文）

若 H3_doc < BODY_PT，将 H3_doc 设为 `BODY_PT + 2`，并重新向上推导 H2_doc。

**换算完成后，用 `H1_doc / H2_doc / H3_doc / H4_doc` 替换 Step 2 提取的 `H1_PT / H2_PT / H3_PT / H4_PT`**，后续 Step 3–4 统一使用换算后的值。

**BCG 示例：** H1=42, H4=11 → ratio=(24/11)^(1/3)≈1.30 → H3=round(11×1.30)=14, H2=round(14×1.30)=18, H1=24 → **24/18/14/11pt**

---

### Step 3 — 推导 DOCX 配置（按需）

生成 `skills/writing/doc-forge/assets/<brand>-style.json`。

**映射规则参考 `skills/writing/design-derive/references/FORMAT-MAPPING.md`：**
- 颜色字段 → 第二节 2.1（DOCX JSON 路径列）
- 字体 → 第三节（CJK 始终为 `PingFang SC`，英文取降级栈第一项）
- 尺度 → 第四节 4.1/4.2（JSON 路径列）
- 表格模式 → 第五节（`border_mode` 对应规则）
- **编码规则** → 第一节：颜色去掉 `#`；字号数字无单位

**输出结构（按 Step 2 提取的变量填入）：**

```json
{
  "_source": "knowledge/design/<brand>-style.md",
  "_comment": "<品牌名> brand style. Fonts: <官方字体> → <FONT_HEADING_EN> / <FONT_BODY_EN>",
  "page": {
    "top_cm": PAGE_TOP_CM, "bottom_cm": PAGE_BOTTOM_CM,
    "left_cm": PAGE_LEFT_CM, "right_cm": PAGE_RIGHT_CM
  },
  "body": {
    "font": "PingFang SC", "font_en": "FONT_BODY_EN",
    "size_pt": BODY_PT, "line_spacing_pt": LINE_SPACING_PT,
    "space_before_pt": 0, "space_after_pt": PARA_SPACE_AFTER,
    "first_line_indent_chars": FIRST_LINE_INDENT
  },
  "headings": {
    "h1": { "font": "PingFang SC", "font_en": "FONT_HEADING_EN", "size_pt": H1_PT, "bold": H1_BOLD, "color": "H1_COLOR（无#）", "align": "left", "space_before_pt": H1_SPACE_BEFORE, "space_after_pt": H1_SPACE_AFTER },
    "h2": { "font": "PingFang SC", "font_en": "FONT_HEADING_EN", "size_pt": H2_PT, "bold": H2_BOLD, "color": "H2_COLOR（无#）", "align": "left", "space_before_pt": H2_SPACE_BEFORE, "space_after_pt": H2_SPACE_AFTER },
    "h3": { "font": "PingFang SC", "font_en": "FONT_BODY_EN", "size_pt": H3_PT, "bold": H3_BOLD, "color": "H3_COLOR（无#）", "space_before_pt": 16, "space_after_pt": 5 },
    "h4": { "font": "PingFang SC", "font_en": "FONT_BODY_EN", "size_pt": H4_PT, "bold": true, "color": "H4_COLOR（无#）", "space_before_pt": 12, "space_after_pt": 4 }
  },
  "code_block": { "font": "Courier New", "size_pt": 10, "bg_color": null },
  "blockquote": { "font": "PingFang SC", "font_en": "FONT_BODY_EN", "size_pt": "BODY_PT+1（略大于正文；若品牌文件有明确 blockquote 字号则以文件为准）", "color": "BQ_COLOR（无#）", "left_indent_cm": 1.0 },
  "table": {
    "font": "PingFang SC", "font_en": "FONT_BODY_EN", "size_pt": 11,
    "header_bold": true, "header_bg_color": TABLE_HEADER_BG,
    "border_mode": "TABLE_MODE",
    "rule_color": "TABLE_HEADER_LINE（无#）",
    "border_color": "TABLE_ROW_LINE（无#）",
    "accent_color": "TABLE_ACCENT（无#，rb 模式才填）",
    "row_sep_color": "TABLE_ROW_LINE（无#，rb 模式才填）",
    "cell_padding_pt": 4, "space_before_pt": 8, "space_after_pt": 8
  }
}
```

---

### Step 4 — 推导 PDF CSS（按需）

生成 `skills/writing/doc-forge/assets/<brand>.css`。

**映射规则参考 `skills/writing/design-derive/references/FORMAT-MAPPING.md`：**
- 颜色属性 → 第二节 2.1（PDF CSS 属性列）
- 字体栈 → 第三节（格式：`"官方字体", FONT_STACK`）
- 尺度 → 第四节 4.1/4.2（CSS 属性列）
- 表格 CSS → 第五节（`border_mode` 对应 CSS 规则全文）
- **编码规则** → 第一节：颜色保留 `#`；字号带 `pt` 单位；行距用倍数

**文件头注释格式：**

```css
/* ─────────────────────────────────────────────
   <品牌名> brand style
   Heading : H1_COLOR（视觉描述）
   Body    : BODY_COLOR（视觉描述）
   Accent  : H1_DECO_COLOR（用途）
   Fonts   : <官方字体> → FONT_HEADING_EN (headlines)
             <官方字体> → FONT_BODY_EN (body)
   ───────────────────────────────────────────── */
```

写入前**对比检查**：
- `h1/h2 border-bottom-color`、`h3 border-left-color`、`blockquote border-left-color` 是否均来自 `H1_DECO_COLOR`（动作色），而非 `H1_COLOR`（标题文字色）？
- `pre border-left` 可例外使用标题色（代码块左色条）

---

### Step 5 — 推导 HTML CSS 变量（按需）

**变量名查阅 `skills/writing/design-derive/references/FORMAT-MAPPING.md` 第六节（HTML CSS 变量完整列表）。**

按 Step 2 提取的 Semantic Token 值填入，打印完整 `:root { }` 块输出到对话，供用户粘贴使用。

---

### Step 6 — 推导 Mermaid 主题并写入配置文件（按需）

**themeVariables 键名查阅 `skills/writing/design-derive/references/FORMAT-MAPPING.md` 第七节。**

写入 `skills/writing/mermaid-diagram/themes/<brand>.json`，同时在对话中打印可直接嵌入的 `%%{init}%%` 块。

主题文件按图类型分区存储，不同图类型使用不同样式机制。

#### 6.1 flowchart — subgraph / node 推导

`flowchart.subgraph` 以 H1_COLOR 为基准推算三层弱背景色（RGB 各通道独立，上限 255，结果转 hex）。

**目标：** 三层浅灰梯度，最深层差 ≈ 15%，提供可见但不抢视觉的分组底色。

**标准路径**（H1_COLOR RGB 三通道均值 ≥ 128，属亮色）：

| 字段 | 规则 |
|------|------|
| `flowchart.subgraph.layer1.fill` | 白色 `#FFFFFF` 与 H1_COLOR 按 80:20 混合后再向灰偏移，取 `#E8E8E8` 段 |
| `flowchart.subgraph.layer2.fill` | 同上向浅推 → `#F0F0F0` 段 |
| `flowchart.subgraph.layer3.fill` | 同上继续 → `#F5F5F5` 段 |
| `flowchart.subgraph.*.stroke` | 同层 fill × 0.85（略深） |
| `flowchart.subgraph.*.text` | `#212427`（固定深色） |

> 简化规则：无论品牌色如何，subgraph 固定使用 `#E8→#F0→#F5` 浅灰梯度，保持弱背景特性。

**深色品牌基准**（H1_COLOR RGB 均值 < 128）同上，不从 H1_COLOR 推导，直接用固定浅灰。

**flowchart.node 推导：**

| 字段 | 规则 |
|------|------|
| `node.neutral.fill` | `#FFFFFF`（固定白色卡片） |
| `node.neutral.stroke` | `#BBBBBB` |
| `node.neutral.text` | `#212427` |
| `node.primary.fill` | H1_COLOR（品牌主色，关键节点） |
| `node.primary.stroke` | H1_COLOR × 0.80 |
| `node.primary.text` | H1_COLOR 深于 `rules.dark_text_threshold` → `#FFFFFF`，否则 `#212427` |
| `node.secondary.fill` | `color.text.primary` 或深灰 `#555555` |
| `node.secondary.stroke` | 同上 × 0.70 |
| `node.secondary.text` | `#FFFFFF` |

#### 6.2 stateDiagram — classDef 推导

从 semantic 色直接映射，`neutral` 取固定浅灰：

| classDef 名 | 来源 |
|------------|------|
| `neutral` | `fill:#EBEBEB,stroke:#C8C8C8,color:#212427`（固定） |
| `opportunity` | `semantic.opportunity`（fill / stroke / `color:#fff`） |
| `hold` | `semantic.hold` |
| `danger` | `semantic.alert` |

输出为可直接粘贴的 classDef 字符串（如 `fill:#E87722,stroke:#BA5F1B,color:#fff`）。

#### 6.3 sequenceDiagram — themeVariables 推导

| themeVariables 键 | 规则 |
|------------------|------|
| `actorBkg` | `#FFFFFF`（固定白色） |
| `actorBorder` | H1_COLOR（品牌主色边框） |
| `actorTextColor` | `#212427` |
| `actorLineColor` | `color.text.muted` 或 `#888888` |
| `noteBkg` | `#F0F0F0` |
| `noteTextColor` | `#212427` |
| `activationBkgColor` | H1_COLOR 加白至 95% 亮度（极浅品牌色调） |
| `activationBorderColor` | H1_COLOR |
| `signalColor` | `#333333` |
| `signalTextColor` | `#212427` |

#### 6.4 gantt — themeVariables 推导

| themeVariables 键 | 规则 |
|------------------|------|
| `taskBkgColor` | `#E8E8E8`（中性任务） |
| `taskBorderColor` | `#BBBBBB` |
| `taskTextColor` | `#212427` |
| `activeTaskBkgColor` | H1_COLOR（当前进行任务） |
| `activeTaskBorderColor` | H1_COLOR × 0.80 |
| `critBkgColor` | `semantic.alert.fill`（关键路径） |
| `critBorderColor` | `semantic.alert.stroke` |
| `doneTaskBkgColor` | `#F5F5F5` |
| `sectionBkgColor` | `#FFFFFF` |
| `altSectionBkgColor` | `#F8F8F8` |
| `gridColor` | `#DDDDDD` |
| `titleColor` | `#212427` |

#### 6.5 timeline — themeVariables 推导

`cScale0–11` 按双色交替，保持阅读节奏：

| cScale | 规则 |
|--------|------|
| 偶数位（0/2/4...） | H1_COLOR（品牌主色） |
| 奇数位（1/3/5...） | `color.text.secondary` 或 `#666666`（中性灰） |
| `titleColor` | `#212427` |

#### 6.6 semantic 色推导

| 字段 | 首选来源 | 无值时默认 |
|------|---------|----------|
| `semantic.alert` | `color.status.danger` | `#CC0000` / `#A30000`（Bain Red） |
| `semantic.opportunity` | `color.status.success` 或 VIZ_3 | `#E87722` / `#BA5F1B` |
| `semantic.hold` | VIZ_4 或 `color.text.muted` | `#666666` / `#525252` |
| `semantic.speculative` | VIZ_5 或 `color.interactive.secondary` | `#2E0078` / `#5A20A0` |
| `semantic.value` | `color.surface.dark` 或 VIZ_2 | `#1A1A1A` / `#222222` |

semantic 的 `text` 字段：fill 深于 `rules.dark_text_threshold` → `#FFFFFF`。

#### 6.7 输出文件结构

```json
{
  "_brand": "<品牌名>",
  "_source": "knowledge/design/<brand>-style.md",
  "_derived_by": "design-derive v1.5.0",

  "flowchart": {
    "subgraph": {
      "layer1": { "fill": "#E8E8E8", "stroke": "#C8C8C8", "text": "#212427", "note": "..." },
      "layer2": { "fill": "#F0F0F0", "stroke": "#D0D0D0", "text": "#212427", "note": "..." },
      "layer3": { "fill": "#F5F5F5", "stroke": "#D8D8D8", "text": "#212427", "note": "..." }
    },
    "node": {
      "neutral":   { "fill": "#FFFFFF", "stroke": "#BBBBBB", "text": "#212427", "note": "..." },
      "primary":   { "fill": "H1_COLOR", "stroke": "...", "text": "...", "note": "..." },
      "secondary": { "fill": "#555555", "stroke": "#3A3A3A", "text": "#FFFFFF", "note": "..." }
    }
  },

  "stateDiagram": {
    "classDef": {
      "neutral":     "fill:#EBEBEB,stroke:#C8C8C8,color:#212427",
      "opportunity": "fill:...,stroke:...,color:#fff",
      "hold":        "fill:...,stroke:...,color:#fff",
      "danger":      "fill:...,stroke:...,color:#fff"
    }
  },

  "sequenceDiagram": {
    "init": {
      "theme": "base",
      "themeVariables": { "actorBkg": "#FFFFFF", "actorBorder": "H1_COLOR", "..." : "..." }
    }
  },

  "gantt": {
    "init": {
      "theme": "base",
      "themeVariables": { "taskBkgColor": "#E8E8E8", "activeTaskBkgColor": "H1_COLOR", "..." : "..." }
    }
  },

  "timeline": {
    "init": {
      "theme": "base",
      "themeVariables": { "cScale0": "H1_COLOR", "cScale1": "#666666", "..." : "..." }
    }
  },

  "semantic": {
    "alert":       { "fill": "...", "stroke": "...", "text": "#FFFFFF", "note": "..." },
    "opportunity": { "fill": "...", "stroke": "...", "text": "#FFFFFF", "note": "..." },
    "hold":        { "fill": "...", "stroke": "...", "text": "#FFFFFF", "note": "..." },
    "speculative": { "fill": "...", "stroke": "...", "text": "#FFFFFF", "note": "..." },
    "value":       { "fill": "...", "stroke": "...", "text": "#FFFFFF", "note": "..." }
  },

  "edge": {
    "primary":   "H1_COLOR",
    "secondary": "#888888"
  },

  "rules": {
    "dark_text_threshold": "#808080",
    "dark_node_text":      "#FFFFFF",
    "light_node_text":     "#212427"
  }
}
```

---

### Step 7 — 推导 PPT 主题（按需）

**色槽对应查阅 `skills/writing/design-derive/references/FORMAT-MAPPING.md` 第八节（PPT 色槽完整映射）。**

以文字形式输出 PPT 主题配置（标题幻灯片 + 内容幻灯片 + 主题色板槽位）。

---

### Step 8 — 写入文件并确认

对于 DOCX 和 PDF 格式，写入文件后展示摘要：

> `doc-forge/<brand>-style.json` 已生成  
> `doc-forge/<brand>.css` 已生成  
> `mermaid-diagram/themes/<brand>.json` 已生成（若包含 Step 6）
>
> 请重点核查：
> 1. **装饰线颜色** — H1/H2 border-bottom、H3 border-left 是否都使用了动作色（非文字色）？
> 2. **字体降级** — 中文字体是否为 `PingFang SC`（macOS）或合适替代？
> 3. **表格模式** — `border_mode` 是否与设计文档一致？
> 4. **Mermaid 深色节点** — subgraph/node 所有 fill 深于 `#4A4A4A` 的是否都有 `color:#fff`？
>
> 确认后可运行 `/doc-forge` 生成测试文档，或用 `/mermaid-diagram` 测试配色效果。

---

## 注意事项

- **动作色优先原则**：装饰线（heading borders、blockquote 左色条、list markers）必须使用动作色；若动作色视觉近黑（RGB 三通道之和 < 200），改用显色装饰线色或留空
- **无值字段**：知识文档中标注为 `待补充` 的字段，使用合理默认值并在输出中注明
- **rb 模式特殊处理**：`TABLE_ACCENT_COLOR` 和 `TABLE_ROW_SEP_COLOR` 只在 `border_mode: "rb"` 时填写
- **字体中文名**：`font` 字段填 `PingFang SC`（macOS），对应英文字体在 `font_en` 字段
- **颜色格式**：JSON 中颜色去掉 `#`，CSS 中保留 `#`
