# 跨格式 Token 映射标准

> **文件用途：** 设计 Token → 各输出格式的权威映射规则。
> **使用者：** `/design-derive` skill 读取本文件作为推导依据。
> **与品牌文件的关系：** 本文件定义**映射规则**（通用），品牌文件定义**Token 值**（品牌特定），两者分离。

---

## 一、编码规则（Format Encoding Rules）

各格式对色值、字体、尺寸的编码方式不同，生成前必须先转换：

| 数据类型 | DOCX（JSON） | PDF（CSS） | HTML（CSS var） | Mermaid | PPT |
|---------|------------|-----------|----------------|---------|-----|
| 颜色 hex | 去掉 `#`，如 `0C2B15` | 保留 `#`，如 `#0C2B15` | 保留 `#` | 保留 `#` | 保留 `#` |
| 中文字体 | `font` 字段（PingFang SC） | 字体栈第一项 | 字体栈字符串 | 不区分 | 分开设 |
| 英文字体 | `font_en` 字段（Georgia） | 字体栈内 | 字体栈字符串 | 不区分 | 分开设 |
| 字号 | 数字，单位省略（`12`） | 带单位（`12pt`）| 带单位（`12pt`） | 不设 | 点数 |
| 行距 | 绝对值 pt（`18`） | 无单位倍数（`1.65`）| 无单位倍数 | 不设 | 倍数 |
| 页边距 | cm 数字（`2.5`） | `@page margin`（`2.5cm`）| 不适用 | 不适用 | 页面设置 |

---

## 二、颜色 Token → 各格式映射表

### 2.1 Component Token 映射

> `—` 表示该格式不需要此 token；`(via semantic)` 表示由上层 Semantic token 覆盖。

| Component Token | DOCX JSON 路径 | PDF CSS 属性 | HTML CSS 变量名 | Mermaid themeVariables | PPT 色槽 |
|----------------|--------------|------------|----------------|----------------------|---------|
| `comp.heading.h1.color` | `headings.h1.color` | `h1 { color }` | `--color-text-heading` | `titleColor` | Text 1 |
| `comp.heading.h1.deco-line` | — | `h1 { border-bottom-color }` | `--color-border-accent` | — | — |
| `comp.heading.h2.color` | `headings.h2.color` | `h2 { color }` | — | — | — |
| `comp.heading.h2.deco-line` | — | `h2 { border-bottom-color }` | — | — | — |
| `comp.heading.h3.color` | `headings.h3.color` | `h3 { color }` | — | — | — |
| `comp.heading.h3.left-bar` | — | `h3 { border-left-color }` | — | — | — |
| `comp.heading.h4.color` | `headings.h4.color` | `h4 { color }` | `--color-text-muted` | — | — |
| `comp.body.color` | — *(via body font)* | `body { color }` | `--color-text-body` | — | Text 2 |
| `comp.link.color` | — | `a { color }` | `--color-text-link` | — | Hyperlink |
| `comp.blockquote.left-bar` | — | `blockquote { border-left-color }` | — | — | — |
| `comp.blockquote.color` | `blockquote.color` | `blockquote { color }` | — | — | — |
| `comp.table.border-header` | `table.rule_color` | `thead tr { border-top-color, border-bottom-color }` | — | — | — |
| `comp.table.border-row` | `table.border_color` | `tbody td { border-bottom-color }` | — | — | — |
| `comp.table.accent-line` | `table.accent_color` | `thead tr { border-bottom-color }` *(rb 模式)* | — | — | — |
| `comp.code.bg` | — *(code_block.bg_color)* | `pre { background-color }` | — | — | — |
| `comp.code.left-bar` | — | `pre { border-left-color }` | — | — | — |
| `comp.hr.color` | — | `hr { border-top-color }` | — | — | — |
| `comp.button.primary.bg` | — | — | `--color-interactive` | `primaryColor` | Accent 1 |
| `comp.button.primary.fg` | — | — | `--color-interactive-fg` | `primaryTextColor` | — |
| `comp.tag.bg` | — | — | — | — | — |

### 2.2 Semantic Token 映射（直接到格式）

> 当 Component Token 未覆盖时，用 Semantic Token 补充。

| Semantic Token | DOCX JSON 路径 | PDF CSS 属性 | HTML CSS 变量名 | Mermaid themeVariables | PPT 色槽 |
|---------------|--------------|------------|----------------|----------------------|---------|
| `color.interactive.primary` | `table.accent_color` *(rb)* | *(via comp)* | `--color-interactive` | `primaryColor` | Accent 1 |
| `color.interactive.primary-fg` | — | — | `--color-interactive-fg` | `primaryTextColor` | — |
| `color.interactive.secondary` | — | *(via comp.link)* | — | `secondaryColor` | Accent 2 |
| `color.text.heading` | `headings.h1.color` `headings.h2.color` | `h1,h2 { color }` | `--color-text-heading` | `titleColor` | Text 1 |
| `color.text.subheading` | `headings.h3.color` | `h3 { color }` | — | — | — |
| `color.text.body` | — | `body { color }` `td { color }` | `--color-text-body` | — | Text 2 |
| `color.text.muted` | `headings.h4.color` | `h4 { color }` | `--color-text-muted` | — | — |
| `color.text.link` | — | `a { color }` | `--color-text-link` | — | Hyperlink |
| `color.text.inverse` | — | — | — | — | — |
| `color.surface.page` | — | — | `--color-surface-page` | `background` | — |
| `color.surface.section` | — | — | `--color-surface-section` | `clusterBkg` | Accent 4 |
| `color.surface.card` | — | — | `--color-surface-card` | — | — |
| `color.surface.dark` | — | — | `--color-surface-dark` | — | Color 1 *(标题幻灯片背景)* |
| `color.surface.code` | — | `pre { background-color }` | — | — | — |
| `color.border.default` | `table.border_color` | `hr { border-top-color }` `td { border-bottom-color }` | `--color-border` | `lineColor` | — |
| `color.border.accent` | — | `blockquote { border-left-color }` | `--color-border-accent` | — | — |
| `color.border.strong` | `table.rule_color` *(mckinsey/rb)* | `thead tr { border-top-color }` | — | — | — |
| `color.status.success` | — | — | — | *(success 节点)* | — |
| `color.status.warning` | — | — | — | *(warning 节点)* | — |
| `color.status.danger` | — | — | — | *(danger 节点)* | — |
| `color.status.info` | — | — | — | *(info 节点)* | — |
| `color.dataviz.1` | — | — | — | `primaryColor` | Accent 1 |
| `color.dataviz.2` | — | — | — | `secondaryColor` | Accent 2 |
| `color.dataviz.3` | — | — | — | `tertiaryColor` | Accent 3 |
| `color.dataviz.4` | — | — | — | *(第 4 色)* | Accent 4 |
| `color.dataviz.5` | — | — | — | *(第 5 色)* | — |

---

## 三、字体 Token → 各格式映射表

| 字体角色 | 来源（设计文档） | DOCX | PDF CSS | HTML CSS 变量 | PPT |
|---------|--------------|------|---------|--------------|-----|
| 标题字体（拉丁） | 3.2 标题降级栈第一英文字体 | `headings.h1.font_en` `headings.h2.font_en` | `h1,h2 { font-family: <stack> }` | `--font-heading` | 标题字体 |
| 标题字体（CJK） | 始终为 `PingFang SC` | `headings.h1.font` | 字体栈内第一位 | `--font-heading` 前置 | 中文字体 |
| 正文字体（拉丁） | 3.2 正文降级栈第一英文字体 | `body.font_en` | `body { font-family: <stack> }` | `--font-body` | 正文字体 |
| 正文字体（CJK） | 始终为 `PingFang SC` | `body.font` | 字体栈内第一位 | `--font-body` 前置 | 中文字体 |
| 等宽字体 | 3.2 等宽字体栈 | `code_block.font`（取第一项）| `pre,code { font-family: <stack> }` | `--font-mono` | — |

---

## 四、尺度 Token → 各格式映射表

### 4.1 字号与行距

| 尺度项 | 来源 | DOCX JSON 路径 | PDF CSS 属性 |
|-------|------|--------------|------------|
| H1 字号 | 3.3 H1 字号 | `headings.h1.size_pt` | `h1 { font-size: Xpt }` |
| H1 字重 | 3.3 H1 字重 | `headings.h1.bold`（true/false）| `h1 { font-weight: 300/700 }` |
| H2 字号 | 3.3 H2 字号 | `headings.h2.size_pt` | `h2 { font-size: Xpt }` |
| H3 字号 | 3.3 H3 字号 | `headings.h3.size_pt` | `h3 { font-size: Xpt }` |
| H4 字号 | 3.3 H4 字号 | `headings.h4.size_pt` | `h4 { font-size: Xpt }` |
| 正文字号 | 3.3 正文字号 | `body.size_pt` | `body { font-size: Xpt }` |
| 正文行距 | 3.3 正文行距 | `body.line_spacing_pt`（绝对 pt）| `body { line-height: X }` *(倍数)* |

### 4.2 间距

| 间距项 | 来源 | DOCX JSON 路径 | PDF CSS 属性 |
|-------|------|--------------|------------|
| H1 前间距 | 4.3 | `headings.h1.space_before_pt` | `h1 { margin-top: Xpt }` |
| H1 后间距 | 4.3 | `headings.h1.space_after_pt` | `h1 { margin-bottom: Xpt }` |
| H2 前间距 | 4.3 | `headings.h2.space_before_pt` | `h2 { margin-top: Xpt }` |
| H2 后间距 | 4.3 | `headings.h2.space_after_pt` | `h2 { margin-bottom: Xpt }` |
| 段落后间距 | 4.3 | `body.space_after_pt` | `p { margin-bottom: Xpt }` |
| 首行缩进 | 4.3 | `body.first_line_indent_chars` | `p { text-indent: X }` |
| 页边距上下 | 4.2 | `page.top_cm` `page.bottom_cm` | `@page { margin-top: Xcm; margin-bottom: Xcm }` |
| 页边距左右 | 4.2 | `page.left_cm` `page.right_cm` | `@page { margin-left: Xcm; margin-right: Xcm }` |

---

## 五、表格模式映射规则

表格样式由 `5.2 边框模式` 决定，对应不同 CSS 和 JSON 规则：

| `border_mode` | DOCX JSON 效果 | PDF CSS 规则 |
|--------------|--------------|-------------|
| `mckinsey` | 头部上下线用 `rule_color`；数据行无边框；最后行下线用 `rule_color` | `thead tr { border-top: 1.5px solid <rule_color>; border-bottom: 0.75px solid <rule_color> }` `tbody tr:last-child td { border-bottom: 0.75px solid <rule_color> }` |
| `rb` | 头部上线黑色（`rule_color`），头部下线用 `accent_color`；数据行下线用 `row_sep_color`；最后行下线黑色 | `thead tr { border-top: 2px solid <rule_color>; border-bottom: 2px solid <accent_color> }` `tbody td { border-bottom: 0.5px solid <row_sep_color> }` `tbody tr:last-child td { border-bottom: 1px solid <rule_color> }` |
| `grid` | 所有格全框，颜色用 `border_color` | `table { border: 1px solid <border_color> }` `td, th { border: 1px solid <border_color> }` |
| `none` | 无边框 | `table, td, th { border: none }` |

---

## 六、HTML CSS 变量完整列表

以下是标准 HTML 输出包含的所有 CSS 变量及其 Semantic Token 来源：

```css
:root {
  /* ── 交互色 ── */
  --color-interactive:       /* color.interactive.primary */;
  --color-interactive-fg:    /* color.interactive.primary-fg */;

  /* ── 文字色 ── */
  --color-text-heading:      /* color.text.heading */;
  --color-text-body:         /* color.text.body */;
  --color-text-muted:        /* color.text.muted */;
  --color-text-link:         /* color.text.link */;

  /* ── 背景色 ── */
  --color-surface-page:      /* color.surface.page */;
  --color-surface-section:   /* color.surface.section */;
  --color-surface-card:      /* color.surface.card */;
  --color-surface-dark:      /* color.surface.dark */;

  /* ── 边框色 ── */
  --color-border:            /* color.border.default */;
  --color-border-accent:     /* color.border.accent → color.interactive.primary */;

  /* ── 字体 ── */
  --font-heading:            /* 3.2 标题降级字体栈 */;
  --font-body:               /* 3.2 正文降级字体栈 */;
  --font-mono:               /* 3.2 等宽字体栈 */;

  /* ── 间距 ── */
  --space-unit:              /* 4.1 基础单位，通常 8px */;
}
```

---

## 七、Mermaid themeVariables 完整映射

```
primaryColor        ← color.dataviz.1（主节点填充色）
primaryBorderColor  ← color.dataviz.1 略深 10%
primaryTextColor    ← color.interactive.primary-fg（主节点文字色）
secondaryColor      ← color.dataviz.2（次节点填充色）
tertiaryColor       ← color.dataviz.3（三级节点填充色）
background          ← color.surface.page
mainBkg             ← color.dataviz.1（同 primaryColor）
clusterBkg          ← color.surface.section（子图背景）
titleColor          ← color.text.heading
lineColor           ← color.border.default
edgeLabelBackground ← color.surface.page
```

深色节点（dataviz 色深）→ `color:#FFFFFF`；浅色节点（dataviz 色浅）→ `color:#000000`。

---

## 八、PPT 色槽完整映射

PowerPoint/Keynote 主题颜色槽：

| 槽位 | 名称 | 来源 Token |
|------|------|-----------|
| Color 1 | 深色（文字/背景深） | `color.text.heading` |
| Color 2 | 浅色（文字/背景浅） | `color.surface.page`（`#FFFFFF`）|
| Accent 1 | 主强调色 | `color.interactive.primary` |
| Accent 2 | 次强调色 | `color.dataviz.2`（或 `color.interactive.secondary`）|
| Accent 3 | 第三强调色 | `color.dataviz.3` |
| Accent 4 | 第四强调色 | `color.surface.section` |
| Accent 5 | 第五强调色 | `color.status.success` |
| Accent 6 | 第六强调色 | `color.status.danger` |
| 超链接 | 链接颜色 | `color.text.link` |
| 已访问链接 | 已访问 | `color.text.muted` |

幻灯片类型规则：
- **标题幻灯片：** `color.surface.dark` 背景 + `color.text.inverse` 文字 + `color.interactive.primary` 装饰线
- **内容幻灯片：** `color.surface.page` 背景 + `color.text.body` 正文 + `color.interactive.primary` 小面积点缀

---

## 九、映射优先级规则

推导时若遇到冲突，按以下优先级：

1. **品牌文件 2.3 Component Tokens 的覆盖值** — 最高优先级（品牌个性）
2. **本文件映射表的默认值** — 通用规则
3. **格式本身的默认样式** — 最低优先级（浏览器/Word 默认）

例：若 `comp.blockquote.left-bar` 在品牌文件中被覆盖为 `#0C2B15`（而非默认的 `{color.interactive.primary}`），则 PDF CSS 的 `blockquote { border-left-color }` 输出 `#0C2B15`，不使用 `color.interactive.primary`。
