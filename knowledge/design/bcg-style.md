# BCG 设计系统

> **文件用途：** 跨格式设计单一真相来源。供 `/design-derive` skill 读取后推导各输出格式的具体配置。
> **生成方式：** 由 `/style-scout` 调查官网自动生成。
> **来源页面：** https://www.bcg.com（主页）+ https://www.bcg.com/publications/2026/ai-the-answer-to-process-industries-talent-cliff（报告页）

---

## 1. 品牌概述

**设计哲学：** 以明亮的石灰绿为唯一动作色，配合深午夜绿的标题，在白色大留白版面上形成高对比度的现代专业感。

**气质关键词：** 大胆对比 / 极简现代 / 绿色优先 / 专业权威 / 留白充足

**适用场景：** 报告文档 / 官网 / 演示文稿 / 数据看板

---

## 2. 色彩 Token 体系

> 采用三层模型：**Primitive**（是什么）→ **Semantic**（做什么）→ **Component**（用在哪）。

---

### 2.1 Primitive Tokens（原始色板）

| Token | 色值 | 视觉描述 |
|-------|------|---------|
| `green-900` | `#0B3B23` | 极深绿（logo 底色）|
| `green-800` | `#144622` | BCG logo 绿 |
| `green-700` | `#0C2B15` | 午夜绿（midnight-green，H1/H2 文字色）|
| `green-600` | `#0E3E1B` | 深绿（brand dark） |
| `green-500` | `#197A56` | 中深绿（hover 态） |
| `green-400` | `#21BF61` | 中绿 |
| `green-300` | `#A8F0B8` | 浅绿 |
| `green-200` | `#E3FDDB` | 极浅绿（success 背景）|
| `green-100` | `#D8F4EF` | 薄荷绿（轻背景）|
| `lime-400` | `#96F878` | 主品牌石灰绿（accent-200，主 CTA）|
| `lime-300` | `#71DC68` | 次级石灰绿（accent-300）|
| `black` | `#212427` | 近黑（H3/正文）|
| `charcoal` | `#232326` | 深炭灰 |
| `gray-700` | `#323232` | 深灰 |
| `gray-500` | `#696969` | 中灰 |
| `gray-450` | `#898888` | 中浅灰 |
| `gray-300` | `#D4D4D4` | 浅灰（分隔线）|
| `gray-200` | `#F2F2F2` | 极浅灰（section 背景）|
| `neutral-700` | `#856E57` | 暖中棕 |
| `neutral-500` | `#AB947E` | 暖浅棕 |
| `neutral-400` | `#C4B5A4` | 暖灰 |
| `neutral-300` | `#DFD7CD` | 暖浅灰 |
| `neutral-250` | `#DCD5CE` | 暖灰白 |
| `neutral-200` | `#F1EEEA` | 暖白（quote 背景、subscribe 背景）|
| `red-500` | `#A1150C` | 深红（alert） |
| `red-400` | `#D82216` | 红（danger）|
| `red-300` | `#FF5B4D` | 浅红 |
| `red-200` | `#FCE1DC` | 极浅红（alert 背景）|
| `white` | `#FFFFFF` | 白 |

---

### 2.2 Semantic Tokens（语义角色）

#### Interactive（交互色）

| Token | → Primitive | 说明 |
|-------|------------|------|
| `color.interactive.primary` | `{lime-400}` | 主 CTA 按钮背景（#96F878，石灰绿）|
| `color.interactive.primary-fg` | `{black}` | 主 CTA 上的文字（深近黑 #212427）|
| `color.interactive.secondary` | `{green-700}` | 次级按钮、强调链接色 |
| `color.interactive.hover` | `{green-500}` | hover / active 态（#197A56）|

#### Text（文字色）

| Token | → Primitive | 视觉近黑？ | 用途 |
|-------|------------|----------|------|
| `color.text.heading` | `{green-700}` | 是 [视觉近黑] | H1 / H2（#0C2B15，RGB 和 = 74）|
| `color.text.subheading` | `{black}` | 是 [视觉近黑] | H3 / H4（#212427，RGB 和 = 99）|
| `color.text.body` | `{black}` | — | 正文段落（#212427）|
| `color.text.muted` | `{gray-500}` | — | 辅助信息 / meta / 日期（#696969）|
| `color.text.link` | `{black}` | — | 链接（带下划线）|
| `color.text.inverse` | `{white}` | — | 深色背景上的文字 |

#### Surface（背景 / 表面色）

| Token | → Primitive | 用途 |
|-------|------------|------|
| `color.surface.page` | `{white}` | 页面底色（body）|
| `color.surface.section` | `{gray-200}` | 交替 section 背景（#F2F2F2）|
| `color.surface.warm` | `{neutral-200}` | 暖色区块背景（subscribe 区、quote 背景 #F1EEEA）|
| `color.surface.card` | `{white}` | 卡片背景（白底，有边框）|
| `color.surface.dark` | `{green-700}` | Hero 深色图片背景 / 相关内容深绿区 #0C2B15 |
| `color.surface.code` | `{gray-200}` | 代码块背景（#F2F2F2）|

#### Border（边框 / 分隔线）

| Token | → Primitive / Semantic | 说明 |
|-------|----------------------|------|
| `color.border.default` | `{gray-300}` | 通用分隔线、表格行线（#D4D4D4）|
| `color.border.accent` | `{color.interactive.primary}` | 强调线 → 指向石灰绿 #96F878 |
| `color.border.strong` | `{black}` | 重边框（#212427）|

#### Status（语义状态色）

| Token | 色值 | 用途 |
|-------|------|------|
| `color.status.success` | `{green-400}` (#21BF61) | 正向 / 完成 |
| `color.status.warning` | `#FFCF24` | 警告 |
| `color.status.danger` | `{red-400}` (#D82216) | 危险 / 错误 |
| `color.status.info` | `{green-300}` (#A8F0B8) | 中性信息 |

#### DataViz（数据可视化序列）

> 参照报告页柱状图实际配色（深绿→中绿→浅绿 渐变序列）

| 序号 | Token | → Primitive / Semantic |
|------|-------|----------------------|
| 1 | `color.dataviz.1` | `{green-700}` (#0C2B15) 深绿 |
| 2 | `color.dataviz.2` | `{green-500}` (#197A56) 中深绿 |
| 3 | `color.dataviz.3` | `{green-400}` (#21BF61) 中绿 |
| 4 | `color.dataviz.4` | `{green-300}` (#A8F0B8) 浅绿 |
| 5 | `color.dataviz.5` | `{lime-400}` (#96F878) 石灰绿（强调/高亮）|

---

### 2.3 Component Tokens（组件引用）

| Component Token | → Semantic | 用途 |
|----------------|-----------|------|
| `comp.heading.h1.color` | `{color.text.heading}` | H1 文字色（#0C2B15 深绿）|
| `comp.heading.h1.deco-line` | `{color.interactive.primary}` | H1 下划线装饰色（石灰绿）|
| `comp.heading.h2.color` | `{color.text.heading}` | H2 文字色（#0C2B15 深绿）|
| `comp.heading.h2.deco-line` | `{color.interactive.primary}` | H2 下划线装饰色（石灰绿）|
| `comp.heading.h3.color` | `{color.text.subheading}` | H3 文字色（#212427 近黑）|
| `comp.heading.h3.left-bar` | `{color.interactive.primary}` | H3 左色条（石灰绿）|
| `comp.heading.h4.color` | `{color.text.muted}` | H4 文字色（uppercase 辅助）|
| `comp.body.color` | `{color.text.body}` | 正文 |
| `comp.link.color` | `{color.text.link}` | 链接 |
| `comp.blockquote.left-bar` | `{color.border.accent}` | 引用块左色条（石灰绿）|
| `comp.blockquote.color` | `{color.text.heading}` | 引用文字色（深绿）|
| `comp.blockquote.bg` | `{color.surface.warm}` | BCG 实际引用块使用暖白背景（#F1EEEA），非左色条 |
| `comp.table.border-header` | `{color.border.strong}` | 表头上下横线（#212427）|
| `comp.table.border-row` | `{color.border.default}` | 行间分隔线（#D4D4D4）|
| `comp.table.accent-line` | `{color.interactive.primary}` | 表头强调线（rb 模式，石灰绿）|
| `comp.code.bg` | `{color.surface.code}` | 代码块背景（#F2F2F2）|
| `comp.code.left-bar` | `{color.interactive.secondary}` | 代码块左色条（深绿）|
| `comp.hr.color` | `{color.border.default}` | 水平分隔线（#D4D4D4）|
| `comp.button.primary.bg` | `{color.interactive.primary}` | 主按钮背景（石灰绿 #96F878）|
| `comp.button.primary.fg` | `{color.interactive.primary-fg}` | 主按钮文字（近黑）|
| `comp.tag.bg` | `{color.interactive.primary}` | 标签 / 徽章背景（石灰绿）|
| `comp.tag.fg` | `{color.interactive.primary-fg}` | 标签文字（近黑）|

> **BCG 引用块特殊说明：** BCG 的 Quote 组件（`.Quote-content`）使用暖白背景 `#F1EEEA`（`{color.surface.warm}`），而非左色条。`comp.blockquote.bg` 覆盖了默认的左色条映射。

---

## 3. 字体体系

### 3.1 官方字体（BCG 专有，需授权）

| 场景 | 字体名 | 字重 | 类型 |
|------|--------|------|------|
| H1 / H2 标题 | `henderson-bcg-serif` | 300 | 衬线 |
| H3 / 正文 / UI | `henderson-bcg-sans` | 300 / 400 | 无衬线 |
| 品牌大标题（Hero） | `henderson-bcg-headline` | — | 衬线（重装饰）|
| 特殊排版 | `henderson-bcg-mod` | — | 衬线变体 |

### 3.2 降级字体栈

| 场景 | 字体栈 |
|------|--------|
| 标题（衬线，H1/H2） | `"Palatino Linotype", "Palatino", "Garamond", "Georgia", serif` |
| 标题（无衬线，H3） | `"Helvetica Neue", "Helvetica", "Arial", sans-serif` |
| 正文 / UI | `"Helvetica Neue", "Helvetica", "Arial", sans-serif` |
| 等宽 | `"JetBrains Mono", "Cascadia Code", "Courier New", monospace` |

### 3.3 字号尺度（Type Scale）

网站测量值（web display）：

| 元素 | 网页字号 | 行距 | 字重 | 字间距 |
|------|---------|------|------|--------|
| Display / Hero | 待补充 | — | 300 | — |
| H1 | 42pt | 1.00 | 300 | — |
| H2 | 36pt | 1.00 | 300 | — |
| H3 | 30pt | 1.00 | 300 | — |
| H4 | 11pt | — | 700 | uppercase |
| 正文 | 12pt | 1.30 | 400 | — |
| 小字 / 注释 | 待补充 | — | 400 | — |
| 表格 | 10pt | — | 400（表头加粗）| — |
| 代码 | 10pt | 1.5 | 400 | — |

文档输出推荐值（经 design-derive Step 2b 等比换算，H4=11 为锚点，ratio≈1.30）：

| 元素 | 文档字号 |
|------|---------|
| H1 | 24pt |
| H2 | 18pt |
| H3 | 14pt |
| H4 | 11pt |
| 正文 | 12pt |

### 3.4 中英文混排规则

- 中文字体：无专用 BCG 中文字体，降级到 PingFang SC / STHeiti
- 英文字体：henderson-bcg-sans（无衬线）或 henderson-bcg-serif（标题）
- 混排间距：无自动空格，建议手动加细空格
- 标点处理：英文标点风格

---

## 4. 间距体系

### 4.1 基础单位

- 网格单位：`8px`（8px grid）
- 间距尺度：`8 / 16 / 24 / 32 / 40 / 56 / 112px`

### 4.2 版面参数

| 参数 | 值 | 说明 |
|------|------|------|
| 页边距（上/下） | 约 2.5cm | 文档页面边距 |
| 页边距（左/右） | 约 2.0cm | 文档页面边距 |
| 正文区内边距 | 56px 上下 / 40px 左右 | 网页正文列（`.ReadingExperience-articleBody`）|
| 正文区最大宽度 | ~900px（居中）| 实测 1280px 视窗下正文列宽约 900px |

### 4.3 组件间距

| 场景 | 值 |
|------|------|
| H1 下方间距 | 32px (≈24pt) |
| H2 上方间距 | 112px (≈84pt) |
| H3 上方间距 | 待补充 |
| 段落间距 | 0（靠 line-height 区分）|
| 首行缩进 | 0 |

---

## 5. 组件规则

### 5.1 标题装饰

| 级别 | 装饰方式 | 颜色 Token | 粗细 |
|------|---------|-----------|------|
| H1 | 无装饰线（大字号 serif 自带权重，简洁） | — | — |
| H2 | 无装饰线 | — | — |
| H3 | 无左色条（BCG 用字号区分层级，不用色条）| — | — |
| H4 | uppercase + letter-spacing | `{comp.heading.h4.color}` | — |

> **BCG 实际不使用 H1/H2/H3 色条装饰。** 层级通过字号差（42/36/30pt）和字体差（serif vs sans-serif）区分。`comp.heading.*.deco-line` 保留为推导占位，实际 CSS 输出时设为 `none`。

### 5.2 表格

- **边框模式：** mckinsey（仅头尾横线）
- **表头上下线颜色：** `{comp.table.border-header}` (#212427，黑色细线)
- **行间分隔线颜色：** `{comp.table.border-row}` (#D4D4D4，浅灰)
- **强调线（rb 模式）：** `{comp.table.accent-line}` (石灰绿，如需强调表头)
- **表头：** 无背景；加粗（font-weight: 600）；左对齐
- **数据行：** 无底色（白底）
- **竖线：** 无

### 5.3 引用块 / Callout

- **样式：** 背景色块（暖白 `{comp.blockquote.bg}` = #F1EEEA），无左色条
- **文字色：** `{comp.blockquote.color}` (#0C2B15 深绿)
- **字体：** 无衬线（henderson-bcg-sans）；正体
- **字号：** 略大（约 14-16pt）
- **图标：** BCG 使用大引号图标（"）而非左色条

### 5.4 代码块

- **背景：** `{comp.code.bg}` (#F2F2F2)；**左色条：** `{comp.code.left-bar}` (#0C2B15)，3px；**圆角：** 4px
- **字体：** 等宽，10pt
- **行内代码背景：** `{comp.code.bg}` (#F2F2F2)

### 5.5 列表

- **无序列表符号：** • （标准圆点）
- **有序列表样式：** 数字
- **缩进：** 1.5em

### 5.6 分隔线

- **颜色：** `{comp.hr.color}` (#D4D4D4)；**粗细：** 1px；**样式：** solid

### 5.7 按钮（供 HTML / PPT 参考）

| 类型 | 背景色 | 文字色 | 边框 | 圆角 | Hover |
|------|--------|--------|------|------|-------|
| 主要 | `{comp.button.primary.bg}` (#96F878) | `{comp.button.primary.fg}` (#212427) | 无 | 15px（pill）| `{color.interactive.hover}` (#197A56) |
| 次要 | 透明 | `{color.interactive.secondary}` (#0C2B15) | 1px solid #0C2B15 | 15px | — |
| Ghost | 透明 | `{color.text.body}` | `{color.border.default}` (#D4D4D4) | 15px | — |

### 5.8 标签 / 徽章

- **背景：** 透明；**文字色：** `{black}` (#212427)；**边框：** 1px solid #212427；**圆角：** 20px；**字号：** 9pt uppercase；**字距：** 0.05em

> BCG 的 category tag（如 "INDUSTRIAL GOODS"）是空心圆角标签（outline pill），不填充石灰绿背景。

### 5.9 卡片

- **背景：** `{color.surface.card}` (#FFFFFF)；**边框：** 无（或极细 #D4D4D4 1px）；**阴影：** 无；**圆角：** 0px（方角）

---

## 6. 视觉层级逻辑

- **层级数量：** 共使用 4 级标题（H1/H2/H3/H4）
- **层级区分方式：** 字号差 + 字体差（H1/H2 用 serif，H3 用 sans-serif）
- **最大层级视觉权重：** 字号 42pt，字重 300，字体 henderson-bcg-serif，颜色 #0C2B15
- **层级色彩策略：** H1/H2 同色（深绿 #0C2B15）；H3/H4 近黑（#212427）

---

## 7. 图像处理

- **图片风格：** 彩色写实摄影为主 + 品牌绿色渐变叠加；部分使用绿色线条插画风格（技术图解）
- **惯用宽高比：** 16:9（报告 Hero）；3:2（卡片）
- **深色蒙版：** 颜色 #0C2B15（midnight-green），透明度 40-60%
- **图片叠文字时：** 白色文字（`{color.text.inverse}`）或直接深绿蒙版叠加

---

## 8. 数据可视化 / 图表

- **图表配色顺序：** 深绿 → 中绿 → 浅绿渐变（单色调为主，见 2.2 DataViz）
- **BCG 图表惯用：** 单一色系渐变（深绿 / 中绿 / 浅绿柱状图），用明度区分数据系列
- **统计数字高亮：** 大号统计数字用石灰绿圆形背景（`{lime-400}`）或深绿色（`{green-700}`）标注
- **图表背景：** 白色或 `{color.surface.warm}` (#F1EEEA)
- **图表字体：** 同正文（henderson-bcg-sans / Helvetica Neue）
- **坐标轴 / 网格线颜色：** `{color.border.default}` (#D4D4D4)
- **Mermaid 节点颜色映射：** 见 9 节推导指南

---

## 9. 各格式推导指南

### → DOCX（doc-forge style.json）

| JSON 字段 | 读取 Token | 备注 |
|-----------|-----------|------|
| `headings.h1.color` | `comp.heading.h1.color` → `green-700` → `0C2B15` | |
| `headings.h1.font_en` | 3.2 标题降级字体栈第一项 | Palatino Linotype |
| `headings.h2.font_en` | 同上 | Palatino Linotype |
| `body.font` / `body.font_en` | 3.2 正文降级字体栈 | Helvetica Neue |
| `table.border_mode` | mckinsey | 仅头尾横线 |
| `table.rule_color` | `comp.table.border-header` → `black` → `212427` | |
| `table.accent_color` | `comp.table.accent-line` → `lime-400` → `96F878` | rb 模式 |
| `table.row_sep_color` | `comp.table.border-row` → `gray-300` → `D4D4D4` | |
| `blockquote.color` | `comp.blockquote.color` → `green-700` → `0C2B15` | |
| `body.first_line_indent_chars` | 0 | 无首行缩进 |

### → PDF（doc-forge CSS）

| CSS 属性 | 读取 Token | 备注 |
|----------|-----------|------|
| `h1 border-bottom color` | 无（BCG H1 无装饰线）| 设为 none |
| `h2 border-bottom color` | 无（BCG H2 无装饰线）| 设为 none |
| `h3 border-left color` | 无（BCG H3 无左色条）| 设为 none |
| `blockquote background` | `comp.blockquote.bg` → `neutral-200` → `F1EEEA` | 背景块 |
| `blockquote border-left color` | 无（用背景块替代）| 设为 none |
| `pre background` | `comp.code.bg` → `gray-200` → `F2F2F2` | |
| `pre border-left color` | `comp.code.left-bar` → `green-700` → `0C2B15` | |
| `body font-family` | Helvetica Neue, Arial, sans-serif | |
| `h1/h2 font-family` | Palatino Linotype, Palatino, Georgia, serif | |

### → HTML（CSS 自定义属性）

```css
:root {
  --color-interactive:        #96F878;  /* lime-400 */
  --color-interactive-fg:     #212427;  /* black */
  --color-text-heading:       #0C2B15;  /* green-700, midnight-green */
  --color-text-body:          #212427;  /* black */
  --color-text-muted:         #696969;  /* gray-500 */
  --color-text-link:          #212427;  /* black, underlined */
  --color-surface-page:       #FFFFFF;
  --color-surface-section:    #F2F2F2;  /* gray-200 */
  --color-surface-warm:       #F1EEEA;  /* neutral-200 */
  --color-surface-card:       #FFFFFF;
  --color-surface-dark:       #0C2B15;  /* midnight-green */
  --color-border:             #D4D4D4;  /* gray-300 */
  --color-border-accent:      #96F878;  /* lime-400 */
  --font-heading:             "Palatino Linotype", "Palatino", "Georgia", serif;
  --font-body:                "Helvetica Neue", "Helvetica", "Arial", sans-serif;
  --font-mono:                "JetBrains Mono", "Courier New", monospace;
  --button-radius:            15px;
  --space-unit:               8px;
}
```

### → Mermaid（图表配色）

```
%%{init: {"theme": "base", "themeVariables": {
  "primaryColor":        "#0C2B15",
  "primaryBorderColor":  "#0B3B23",
  "primaryTextColor":    "#FFFFFF",
  "secondaryColor":      "#197A56",
  "tertiaryColor":       "#A8F0B8",
  "background":          "#FFFFFF",
  "clusterBkg":          "#F2F2F2",
  "titleColor":          "#0C2B15",
  "lineColor":           "#D4D4D4",
  "nodeBorder":          "#0C2B15",
  "mainBkg":             "#96F878",
  "edgeLabelBackground": "#F1EEEA"
}}}%%
```

- 深色节点（dataviz.1/2 深绿）：`color:#FFFFFF`
- 浅色节点（dataviz.4/5 浅绿/石灰绿）：`color:#0C2B15`
- 强调节点：`fill:#96F878,color:#212427`

### → PPT（演示文稿主题）

| 槽位 | 读取 Token | 色值 |
|------|-----------|------|
| Color 1（深/文字）| `color.text.heading` | #0C2B15 |
| Color 2（浅/背景）| `color.surface.page` | #FFFFFF |
| Accent 1（主动作）| `color.interactive.primary` | #96F878 |
| Accent 2 | `color.dataviz.2` | #197A56 |
| Accent 3 | `color.dataviz.3` | #21BF61 |
| Accent 4 | `color.surface.warm` | #F1EEEA |
| 超链接 | `color.text.link` | #212427 |

- **标题幻灯片：** `#0C2B15` 背景 + `#FFFFFF` 文字 + `#96F878` 石灰绿装饰线
- **内容幻灯片：** 白色背景 + `#212427` 正文 + 石灰绿小面积点缀（按钮、数字高亮）
