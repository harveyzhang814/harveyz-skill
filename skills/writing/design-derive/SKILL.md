---
name: design-derive
description: "Derive format-specific configs from a brand design knowledge doc. Trigger when the user wants to generate doc-forge JSON/CSS, HTML CSS variables, Mermaid color scheme, or PPT theme from a design system. E.g. 'derive configs for BCG', 'generate doc-forge style for rb', 'create HTML theme from custom-style'."
user_invocable: true
version: "1.2.0"
---

## 概述

读取 `knowledge/design/<brand>-style.md`，推导各输出格式的具体配置。

**只做推导，不调查官网。** 官网调查由 `/style-scout` 负责。

**映射标准：** 格式字段 ↔ Token 的完整映射规则定义在 `knowledge/design/FORMAT-MAPPING.md`，推导时以该文件为权威依据。品牌文件提供 Token 值，FORMAT-MAPPING.md 提供映射规则，两者分离。

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

用 Read 工具读取 `$KNOWLEDGE_FILE` 和 `knowledge/design/FORMAT-MAPPING.md`。

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

生成 `skills/writing/doc-forge/assets/<brand>-style.json`。

**映射规则参考 `knowledge/design/FORMAT-MAPPING.md`：**
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
  "blockquote": { "font": "PingFang SC", "font_en": "FONT_HEADING_EN", "size_pt": H3_PT, "color": "H1_COLOR（无#）", "left_indent_cm": 1.0 },
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

**映射规则参考 `knowledge/design/FORMAT-MAPPING.md`：**
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

**变量名查阅 `knowledge/design/FORMAT-MAPPING.md` 第六节（HTML CSS 变量完整列表）。**

按 Step 2 提取的 Semantic Token 值填入，打印完整 `:root { }` 块输出到对话，供用户粘贴使用。

---

### Step 6 — 推导 Mermaid 配色（按需）

**themeVariables 键名查阅 `knowledge/design/FORMAT-MAPPING.md` 第七节（Mermaid themeVariables 完整映射）。**

按 Step 2 提取的 `VIZ_1..5`、`BG_PAGE`、`H1_COLOR`、`HR_COLOR` 填入，生成：

```
%%{init: {"theme": "base", "themeVariables": { ... }}}%%
```

深色节点（dataviz 色深）→ `color:#FFFFFF`；浅色节点（dataviz 色浅）→ `color:#000000`。

同时输出 subgraph 三层配色建议（前三色）和语义节点颜色。

---

### Step 7 — 推导 PPT 主题（按需）

**色槽对应查阅 `knowledge/design/FORMAT-MAPPING.md` 第八节（PPT 色槽完整映射）。**

以文字形式输出 PPT 主题配置（标题幻灯片 + 内容幻灯片 + 主题色板槽位）。

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
