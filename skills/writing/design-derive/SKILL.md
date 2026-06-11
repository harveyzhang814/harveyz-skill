---
name: design-derive
description: "Derive format-specific configs from a brand design knowledge doc. Trigger when the user wants to generate doc-forge JSON/CSS, HTML CSS variables, Mermaid color scheme, or PPT theme from a design system. E.g. 'derive configs for BCG', 'generate doc-forge style for rb', 'create HTML theme from custom-style'."
user_invocable: true
version: "1.1.0"
---

## 概述

读取 `knowledge/design/<brand>-style.md`，按第 9 节"各格式推导指南"推导各输出格式的具体配置。

**只做推导，不调查官网。** 官网调查由 `/style-scout` 负责。

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

> 请提供品牌名（如 bcg / rb / custom），或完整路径（如 knowledge/design/bcg-style.md）

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

用 Read 工具读取 `$KNOWLEDGE_FILE`。

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

### Step 3 — 推导 DOCX 配置（按需）

生成 `skills/writing/doc-forge/assets/<brand>-style.json`：

```json
{
  "_source": "<knowledge 文件路径>",
  "_comment": "<品牌名> brand style. Fonts: <官方字体> — proprietary, fall back to <降级字体>.",
  "page": {
    "top_cm": PAGE_TOP_CM,
    "bottom_cm": PAGE_BOTTOM_CM,
    "left_cm": PAGE_LEFT_CM,
    "right_cm": PAGE_RIGHT_CM
  },
  "body": {
    "font": "<中文字体>",
    "font_en": "FONT_BODY_EN",
    "size_pt": BODY_PT,
    "line_spacing_pt": LINE_SPACING_PT,
    "space_before_pt": 0,
    "space_after_pt": PARA_SPACE_AFTER,
    "first_line_indent_chars": FIRST_LINE_INDENT
  },
  "headings": {
    "h1": {
      "font": "<中文字体>",
      "font_en": "FONT_HEADING_EN",
      "size_pt": H1_PT,
      "bold": H1_BOLD,
      "color": "HEADING_COLOR（去掉 #）",
      "align": "left",
      "space_before_pt": H1_SPACE_BEFORE,
      "space_after_pt": H1_SPACE_AFTER
    },
    "h2": { ... },
    "h3": { ... },
    "h4": { ... }
  },
  "code_block": {
    "font": "Courier New",
    "size_pt": 10,
    "bg_color": null
  },
  "blockquote": {
    "font": "<中文字体>",
    "font_en": "FONT_HEADING_EN",
    "size_pt": H3_PT 或 13,
    "color": "HEADING_COLOR（去掉 #）",
    "left_indent_cm": 1.0
  },
  "table": {
    "font": "<中文字体>",
    "font_en": "FONT_BODY_EN",
    "size_pt": 11,
    "header_bold": true,
    "header_bg_color": TABLE_HEADER_BG,
    "border_mode": "TABLE_MODE",
    "rule_color": "TABLE_RULE_COLOR（去掉 #）",
    "border_color": "BORDER_COLOR（去掉 #）",
    "accent_color": "TABLE_ACCENT_COLOR（去掉 #，rb 模式填）",
    "row_sep_color": "TABLE_ROW_SEP_COLOR（去掉 #，rb 模式填）",
    "cell_padding_pt": 4,
    "space_before_pt": 8,
    "space_after_pt": 8
  }
}
```

---

### Step 4 — 推导 PDF CSS（按需）

生成 `skills/writing/doc-forge/assets/<brand>.css`：

**模板（按实际值替换占位符）：**

```css
/* ─────────────────────────────────────────────
   <品牌名> brand style
   Source: <knowledge 文件来源 URL>
   Heading : ACTION_COLOR（标注视觉描述）
   Body    : BODY_COLOR（标注视觉描述）
   Accent  : ACTION_COLOR（标注用途）
   Fonts   : <官方字体> → FONT_HEADING_EN (headlines)
             <官方字体> → FONT_BODY_EN (body)
   ───────────────────────────────────────────── */

@page {
  size: A4;
  margin: PAGE_TOP_CM PAGE_RIGHT_CM PAGE_BOTTOM_CM PAGE_LEFT_CM;
}

body {
  font-family: FONT_BODY_STACK;
  font-size: BODY_PT;
  line-height: 1.65;
  color: BODY_COLOR;
  max-width: 100%;
}

h1 {
  font-family: FONT_HEADING_SERIF;
  font-size: H1_PT;
  font-weight: 300（或 700，按 H1_BOLD）;
  color: HEADING_COLOR;
  margin-top: 0;
  margin-bottom: H1_SPACE_AFTER;
  padding-bottom: 8pt;
  border-bottom: 2px solid ACTION_COLOR;  /* ← 必须用动作色 */
}

h2 {
  font-family: FONT_HEADING_SERIF;
  font-size: H2_PT;
  font-weight: 300;
  color: HEADING_COLOR;
  margin-top: H2_SPACE_BEFORE;
  margin-bottom: H2_SPACE_AFTER;
  padding-bottom: 4pt;
  border-bottom: 1.5px solid ACTION_COLOR;  /* ← 必须用动作色 */
}

h3 {
  font-family: FONT_BODY_STACK（无衬线）;
  font-size: H3_PT;
  font-weight: 400;
  color: BODY_COLOR;
  margin-top: 16pt;
  margin-bottom: 5pt;
  /* 若 H3_LEFT_BAR = true */
  padding-left: 8pt;
  border-left: 3px solid ACTION_COLOR;  /* ← 必须用动作色 */
}

h4 {
  font-family: FONT_BODY_STACK;
  font-size: H4_PT;
  font-weight: 700;
  color: MUTED_COLOR;
  margin-top: 12pt;
  margin-bottom: 4pt;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

p {
  text-indent: 0;
  margin-top: 0;
  margin-bottom: PARA_SPACE_AFTER;
}

/* 表格样式按 TABLE_MODE 选择 */

/* mckinsey 模式 */
table { border-collapse: collapse; width: 100%; font-size: 10pt; }
thead tr { border-top: 1.5px solid TABLE_RULE_COLOR; border-bottom: 0.75px solid TABLE_RULE_COLOR; }
th { background-color: transparent; font-weight: 700; border: none; padding: 5pt 8pt; }
tbody tr:last-child td { border-bottom: 0.75px solid TABLE_RULE_COLOR; }
td { border: none; padding: 4.5pt 8pt; }

/* rb 模式（额外替换上面的 table 规则）*/
/* thead tr { border-top: 2px solid #000; border-bottom: 2px solid TABLE_ACCENT_COLOR; } */
/* tbody tr td { border-bottom: 0.5px solid TABLE_ROW_SEP_COLOR; } */
/* tbody tr:last-child td { border-bottom: 1px solid #000; } */

pre {
  background-color: CODE_BG;
  border: none;
  border-left: 3px solid ACTION_COLOR;
  border-radius: 0 3px 3px 0;
  padding: 8pt 12pt;
  font-family: FONT_MONO_STACK;
  font-size: 9pt;
  line-height: 1.5;
}

code {
  font-family: FONT_MONO_STACK;
  font-size: 9pt;
  background-color: CODE_BG;
  color: HEADING_COLOR;
  padding: 1px 4px;
  border-radius: 2px;
}

pre code { background-color: transparent; color: inherit; padding: 0; border-radius: 0; }

blockquote {
  font-family: FONT_HEADING_SERIF;
  font-size: H3_PT;
  font-style: italic;
  font-weight: 300;
  color: HEADING_COLOR;
  border-left: 3.5px solid ACTION_COLOR;
  margin: 12pt 0;
  padding: 6pt 0 6pt 16pt;
  background-color: transparent;
}

blockquote p { margin: 0; text-indent: 0; }

ul, ol { margin-top: 3pt; margin-bottom: 3pt; padding-left: 1.6em; }
li { margin-bottom: 3pt; line-height: 1.6; }

hr { border: none; border-top: 1px solid BORDER_COLOR; margin: 14pt 0; }

a { color: LINK_COLOR; text-decoration: underline; text-underline-offset: 2px; }

img { max-width: 100%; height: auto; display: block; margin: 10pt auto; }

pre.mermaid {
  background-color: transparent;
  border: none;
  text-align: center;
  margin: 14pt auto;
  padding: 0;
}

pre.mermaid svg { max-width: 92%; height: auto; }
```

写入前**对比检查**：
- 所有 `border` 颜色是否来自动作色（`ACTION_COLOR`），而非标题文字色？
- `pre border-left` 可例外使用标题色（代码块左色条常用深色）

---

### Step 5 — 推导 HTML CSS 变量（按需）

打印 CSS 变量块（可由用户粘贴到项目）：

```css
:root {
  --color-brand-primary:   HEADING_COLOR;
  --color-brand-action:    ACTION_COLOR;
  --color-text-heading:    HEADING_COLOR;
  --color-text-body:       BODY_COLOR;
  --color-text-muted:      MUTED_COLOR;
  --color-bg-page:         BG_PAGE;
  --color-bg-section:      BG_SECTION;
  --color-bg-card:         BG_CARD;
  --color-border:          BORDER_COLOR;
  --color-border-accent:   ACTION_COLOR;
  --font-heading:          "FONT_HEADING_SERIF";
  --font-body:             "FONT_BODY_STACK";
  --font-mono:             "FONT_MONO_STACK";
  --space-unit:            8px;
}
```

---

### Step 6 — 推导 Mermaid 配色（按需）

根据 2.7 数据可视化色序 `VIZ_COLORS[]` 生成 Mermaid 主题块：

```
%%{init: {"theme": "base", "themeVariables": {
  "primaryColor":       VIZ_COLORS[0],
  "primaryTextColor":   "#fff"（若深色）或"#000"（若浅色）,
  "primaryBorderColor": VIZ_COLORS[0] 略深 10%,
  "secondaryColor":     VIZ_COLORS[1],
  "tertiaryColor":      VIZ_COLORS[2],
  "background":         BG_PAGE,
  "mainBkg":            VIZ_COLORS[0],
  "nodeBorder":         VIZ_COLORS[0],
  "clusterBkg":         BG_SECTION,
  "titleColor":         HEADING_COLOR,
  "edgeLabelBackground": BG_PAGE,
  "lineColor":          BORDER_COLOR
}}}%%
```

同时输出 subgraph 三层配色建议（前三色）和语义节点颜色（来自 2.6）。

---

### Step 7 — 推导 PPT 主题（按需）

以文字形式输出 PPT 主题配置建议：

```
<品牌名> PPT 主题配置
─────────────────────
标题幻灯片：
  背景色     BG_DARK（深色块）
  标题字体   FONT_HEADING_SERIF（英文）/ PingFang SC（中文）
  标题颜色   #FFFFFF
  装饰线     ACTION_COLOR，2pt，标题下方
  副标题颜色 BG_SECTION（浅色）

内容幻灯片：
  背景色     BG_PAGE（白色）
  标题字体   FONT_HEADING_SERIF
  标题颜色   HEADING_COLOR
  正文字体   FONT_BODY_STACK
  正文颜色   BODY_COLOR
  强调色点缀 ACTION_COLOR（按钮、图标、线条）

主题色板（PowerPoint 主题色槽位）：
  Color 1（文字/背景深）  HEADING_COLOR
  Color 2（文字/背景浅）  #FFFFFF
  Accent 1               ACTION_COLOR
  Accent 2               VIZ_COLORS[1]
  Accent 3               VIZ_COLORS[2]
  Accent 4               BG_SECTION
  超链接                  LINK_COLOR
```

---

### Step 8 — 写入文件并确认

对于 DOCX 和 PDF 格式，写入文件后展示摘要：

> `doc-forge/<brand>-style.json` 已生成  
> `doc-forge/<brand>.css` 已生成  
>
> 请重点核查：
> 1. **装饰线颜色** — H1/H2 border-bottom、H3 border-left 是否都使用了动作色（非文字色）？
> 2. **字体降级** — 中文字体是否为 `PingFang SC`（macOS）或合适替代？
> 3. **表格模式** — `border_mode` 是否与设计文档一致？
>
> 确认后可运行 `/doc-forge` 生成测试文档验证效果。

---

## 注意事项

- **动作色优先原则**：装饰线（heading borders、blockquote 左色条、list markers）必须使用动作色；若动作色视觉近黑（RGB 三通道之和 < 200），改用显色装饰线色或留空
- **无值字段**：知识文档中标注为 `待补充` 的字段，使用合理默认值并在输出中注明
- **rb 模式特殊处理**：`TABLE_ACCENT_COLOR` 和 `TABLE_ROW_SEP_COLOR` 只在 `border_mode: "rb"` 时填写
- **字体中文名**：`font` 字段填 `PingFang SC`（macOS），对应英文字体在 `font_en` 字段
- **颜色格式**：JSON 中颜色去掉 `#`，CSS 中保留 `#`
