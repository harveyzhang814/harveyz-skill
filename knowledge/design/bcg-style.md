# BCG 设计系统

> **文件用途：** 跨格式设计单一真相来源。供 `/design-derive` skill 读取后推导各输出格式的具体配置。
> **生成方式：** 由 `/style-scout` v2.1.0 调查官网自动生成（两阶段：主页 + 报告页）。
> **来源页面：**
> - 主页：https://www.bcg.com/
> - 报告页：https://www.bcg.com/publications/2026/from-ai-skills-to-business-performance

---

## 1. 品牌概述

**设计哲学：** 极简留白，深墨绿权威感配合亮青柠点缀；衬线大标题传达专业性，亮绿 CTA 突出行动指引。

**气质关键词：** 极简现代 / 深色权威 / 留白充足 / 亮点缀强识别

**适用场景：** 报告文档 / 官网 / 演示文稿 / 数据看板

---

## 2. 色彩 Token 体系

> 三层模型：**Primitive**（是什么）→ **Semantic**（做什么）→ **Component**（用在哪）。
> Primitive 来源：CSS 变量完整提取（`--bcg-*` / `--accent-*` / `--green-*` / `--neutral-*` / `--gray-*`）+ 渲染层 JS 提取。

---

### 2.1 Primitive Tokens（原始色板）

| Token | 色值 | 视觉描述 |
|-------|------|---------|
| `green-700` / `midnight-green` | `#0C2B15` | 深森林绿（BCG 品牌绿） |
| `green-500` | `#197A56` | 深中绿 |
| `green-400` | `#21BF61` | 中绿 |
| `green-300` | `#A8F0B8` | 浅绿 |
| `green-200` | `#E3FDDB` | 极浅薄荷绿（BCG Answer 区块背景） |
| `green-100` | `#D8F4EF` | 极浅青绿 |
| `accent-200` | `#96F878` | 亮青柠绿（主 CTA 色，x66 渲染频次） |
| `accent-300` | `#71DC68` | 中青柠绿（hover 态） |
| `neutral-900` / `black` | `#212427` | 近黑（正文 / H3） |
| `neutral-500` | `#AB947E` | 中暖棕 |
| `neutral-400` | `#C4B5A4` | 浅暖棕 |
| `neutral-300` | `#DFD7CD` | 极浅暖棕（暖色边框） |
| `neutral-250` | `#DCD5CE` | 暖灰 |
| `neutral-200` | `#F1EEEA` | 暖米白（section 背景 / 代码块） |
| `gray-700` | `#323232` | 深灰 |
| `gray-500` | `#696969` | 中灰（辅助文字） |
| `gray-400` | `#B1B1B1` | 浅灰 |
| `gray-300` | `#D4D4D4` | 极浅灰（通用分隔线，x111 最高频） |
| `gray-200` | `#F2F2F2` | 近白灰（section 交替背景） |
| `alert-400` | `#D82216` | 红（危险 / 次 CTA） |
| `alert-200` | `#FCE1DC` | 浅粉红 |
| `warning-400` | `#FFCF24` | 黄（警告） |
| `white` | `#FFFFFF` | 白 |

---

### 2.2 Semantic Tokens（语义角色）

#### Interactive（交互色）

> 主 CTA 按钮 `#96F878` 在主页出现 66 次、报告页 62 次，是品牌最强识别色。
> **是文档装饰线（H1/H2 下划线、H3 左色条）的来源。**

| Token | → Primitive | 说明 |
|-------|------------|------|
| `color.interactive.primary` | `{accent-200}` = `#96F878` | 主 CTA 按钮背景；文档装饰线首选 |
| `color.interactive.primary-fg` | `{neutral-900}` = `#212427` | CTA 按钮上的文字（黑色） |
| `color.interactive.secondary` | `{green-700}` = `#0C2B15` | 次级链接、链接色 |
| `color.interactive.hover` | `{accent-300}` = `#71DC68` | Hover 态 |

#### Text（文字色）

> `#0C2B15`：RGB(12,43,21)，三通道和 = 76 → **视觉近黑**，在文档中接近纯黑，不适合做彩色装饰线。
> `#212427`：RGB(33,36,39)，三通道和 = 108 → **视觉近黑**。

| Token | → Primitive | 视觉近黑？ | 用途 |
|-------|------------|----------|------|
| `color.text.heading` | `{green-700}` = `#0C2B15` | 是（和=76） | H1 / H2 标题 |
| `color.text.subheading` | `{neutral-900}` = `#212427` | 是（和=108） | H3 / H4 |
| `color.text.body` | `{neutral-900}` = `#212427` | 是 | 正文段落 |
| `color.text.muted` | `{gray-500}` = `#696969` | — | 辅助信息 / meta / 日期 |
| `color.text.link` | `{green-700}` = `#0C2B15` | — | 链接 |
| `color.text.inverse` | `{white}` = `#FFFFFF` | — | 深色背景上的文字 |

#### Surface（背景 / 表面色）

| Token | → Primitive | 用途 |
|-------|------------|------|
| `color.surface.page` | `{white}` = `#FFFFFF` | 页面底色（body） |
| `color.surface.section` | `{gray-200}` = `#F2F2F2` | 交替 section 背景（灰）|
| `color.surface.section-warm` | `{neutral-200}` = `#F1EEEA` | 暖米色 section 背景（订阅区等）|
| `color.surface.section-mint` | `{green-200}` = `#E3FDDB` | 薄荷绿 section 背景（BCG Answer）|
| `color.surface.card` | `{white}` = `#FFFFFF` | 卡片背景 |
| `color.surface.dark` | `{green-700}` = `#0C2B15` | Hero / 深色强调区 |
| `color.surface.code` | `{neutral-200}` = `#F1EEEA` | 代码块背景 |

#### Border（边框 / 分隔线）

| Token | → Primitive / Semantic | 说明 |
|-------|----------------------|------|
| `color.border.default` | `{gray-300}` = `#D4D4D4` | 通用分隔线（x111 最高频） |
| `color.border.warm` | `{neutral-300}` = `#DFD7CD` | 暖色分隔线（x8） |
| `color.border.accent` | `{color.interactive.primary}` | 强调线 → **指向 Interactive，不写 hex** |
| `color.border.strong` | `{neutral-900}` = `#212427` | 重边框（表格外框） |

#### Status（语义状态色）

| Token | 色值 | 用途 |
|-------|------|------|
| `color.status.success` | `#21BF61` | 正向 / 完成 |
| `color.status.warning` | `#FFCF24` | 警告 |
| `color.status.danger` | `#D82216` | 危险 / 错误 |
| `color.status.info` | `#73859F` | 中性信息 |

#### DataViz（数据可视化序列）

| 序号 | Token | → Primitive / Semantic |
|------|-------|----------------------|
| 1 | `color.dataviz.1` | `{accent-200}` = `#96F878` |
| 2 | `color.dataviz.2` | `{green-700}` = `#0C2B15` |
| 3 | `color.dataviz.3` | `{green-400}` = `#21BF61` |
| 4 | `color.dataviz.4` | `{gray-500}` = `#696969` |
| 5 | `color.dataviz.5` | `{neutral-200}` = `#F1EEEA` |

---

### 2.3 Component Tokens（组件引用）

> BCG 网页文章**不使用** heading 装饰线（无 border-bottom / border-left）。
> 在**文档输出**（DOCX/PDF）中，为传递品牌感，使用 `{color.interactive.primary}` 作为装饰线色。

| Component Token | → Semantic | 用途 |
|----------------|-----------|------|
| `comp.heading.h1.color` | `{color.text.heading}` = `#0C2B15` | H1 文字色 |
| `comp.heading.h1.deco-line` | `{color.interactive.primary}` = `#96F878` | H1 下划线（文档）|
| `comp.heading.h2.color` | `{color.text.heading}` = `#0C2B15` | H2 文字色 |
| `comp.heading.h2.deco-line` | `{color.interactive.primary}` = `#96F878` | H2 下划线（文档）|
| `comp.heading.h3.color` | `{color.text.subheading}` = `#212427` | H3 文字色 |
| `comp.heading.h3.left-bar` | `{color.interactive.primary}` = `#96F878` | H3 左色条（文档）|
| `comp.heading.h4.color` | `{color.text.muted}` = `#696969` | H4 文字色 |
| `comp.body.color` | `{color.text.body}` = `#212427` | 正文 |
| `comp.link.color` | `{color.text.link}` = `#0C2B15` | 链接 |
| `comp.blockquote.left-bar` | `{color.border.accent}` = `#96F878` | 引用块左色条 |
| `comp.blockquote.color` | `{color.text.heading}` = `#0C2B15` | 引用文字色 |
| `comp.table.border-header` | `{color.border.strong}` = `#212427` | 表头上下横线 |
| `comp.table.border-row` | `{color.border.default}` = `#D4D4D4` | 行间分隔线 |
| `comp.table.accent-line` | `{color.interactive.primary}` = `#96F878` | 表头强调线（rb 模式）|
| `comp.code.bg` | `{color.surface.code}` = `#F1EEEA` | 代码块背景 |
| `comp.code.left-bar` | `{color.interactive.secondary}` = `#0C2B15` | 代码块左色条 |
| `comp.hr.color` | `{color.border.default}` = `#D4D4D4` | 水平分隔线 |
| `comp.button.primary.bg` | `{color.interactive.primary}` = `#96F878` | 主按钮背景 |
| `comp.button.primary.fg` | `{color.interactive.primary-fg}` = `#212427` | 主按钮文字 |
| `comp.tag.bg` | `{color.interactive.primary}` = `#96F878` | 标签 / 徽章背景 |
| `comp.tag.fg` | `{color.interactive.primary-fg}` = `#212427` | 标签文字 |

---

## 3. 字体体系

### 3.1 官方字体（专有，需授权）

| 场景 | 字体名 | 字重 | 类型 |
|------|--------|------|------|
| H1 / H2 大标题 | `henderson-bcg-serif` | 300（Light） | 衬线 |
| H3 / 正文 / UI | `henderson-bcg-sans` | 300 / 400 | 无衬线 |

### 3.2 降级字体栈

| 场景 | 字体栈 |
|------|--------|
| 标题（衬线） | `"Georgia", "STSong", "Songti SC", "SimSun", serif` |
| 标题（无衬线） | `"Helvetica Neue", "Arial", "PingFang SC", "STHeiti", sans-serif` |
| 正文 | `"PingFang SC", "Helvetica Neue", "Arial", "STHeiti", "Microsoft YaHei", sans-serif` |
| 等宽 | `"JetBrains Mono", "Cascadia Code", "Courier New", monospace` |

### 3.3 字号尺度（Type Scale）

实测自 `bcg.com/publications/2026/meet-the-new-generation-of-ai-disruptors`：

| 元素 | 字号 | 行距 | 字重 | 颜色 |
|------|------|------|------|------|
| H1 | 30pt | 1.00 | 300 | `#0C2B15` |
| H2 | 18pt（推算） | 1.10 | 300 | `#0C2B15` |
| H3 | 14pt（推算） | 1.20 | 400 | `#212427` |
| H4 | 11pt | 1.20 | 700 | `#696969` uppercase |
| 正文 | 12pt | 1.30 | 400 | `#212427` |
| 小字 / 注释 | 9pt | 1.40 | 400 | `#696969` |
| 表格 | 11pt | — | 400（表头加粗） | `#212427` |
| 代码 | 9pt | 1.50 | 400 | `#0C2B15` |

### 3.4 中英文混排规则

- 中文字体：`PingFang SC`（macOS）
- 英文字体：`henderson-bcg-sans`（降级：Helvetica Neue）
- 混排间距：无自动空格
- 标点处理：标准

---

## 4. 间距体系

### 4.1 基础单位

- 网格单位：`8px`（8px grid）
- 间距尺度：`8 / 16 / 24 / 32 / 48 / 64px`

### 4.2 版面参数

| 参数 | 值 | 说明 |
|------|------|------|
| 页边距（上/下） | 2.0cm | 文档上下边距 |
| 页边距（左/右） | 2.5cm | 文档左右边距 |
| 正文区最大宽度 | 760px（估） | 网页正文列宽 |

### 4.3 组件间距

| 场景 | 值 |
|------|------|
| H1 下方间距 | 24pt（实测 32px） |
| H2 上方间距 | 20pt |
| H3 上方间距 | 14pt |
| 段落间距 | 7pt |
| 首行缩进 | 0 |

---

## 5. 组件规则

### 5.1 标题装饰

| 级别 | 网页实际样式 | 文档推荐 | 颜色 Token |
|------|------------|---------|-----------|
| H1 | 无装饰（纯衬线大字） | 下划线 2px | `{comp.heading.h1.deco-line}` = `#96F878` |
| H2 | 无装饰 | 下划线 1.5px | `{comp.heading.h2.deco-line}` = `#96F878` |
| H3 | 无装饰 | 左色条 3px | `{comp.heading.h3.left-bar}` = `#96F878` |
| H4 | uppercase + letter-spacing | 同网页 | `{comp.heading.h4.color}` = `#696969` |

### 5.2 表格

- **边框模式：** `mckinsey`（仅头尾横线，无竖线，无行底色）
- **表头上下线颜色：** `{comp.table.border-header}` = `#212427`
- **行间分隔线：** 无（mckinsey 模式）
- **表头背景：** 无
- **竖线：** 无

### 5.3 引用块 / Callout

- **BCG 网页实际：** Key Takeaways 用 `rgba(255,255,255,0.7)` 白色半透明块，无左色条，无边框
- **文档推荐：** 左色条 `{comp.blockquote.left-bar}` = `#96F878`，3.5px
- **字体：** 衬线（Georgia 降级）；斜体；Light 字重
- **字号：** 略大（13pt）
- **文字色：** `{comp.blockquote.color}` = `#0C2B15`

### 5.4 代码块

- **背景：** `{comp.code.bg}` = `#F1EEEA`；**左色条：** `{comp.code.left-bar}` = `#0C2B15`，3px；**圆角：** 3px
- **字体：** 等宽，9pt
- **行内代码背景：** `#F1EEEA`；**文字色：** `#0C2B15`

### 5.5 列表

- **无序列表符号：** •（标准圆点）
- **有序列表样式：** 数字
- **缩进：** 1.6em

### 5.6 分隔线

- **颜色：** `{comp.hr.color}` = `#D4D4D4`；**粗细：** 1px；**样式：** solid

### 5.7 按钮（供 HTML / PPT 参考）

| 类型 | 背景色 | 文字色 | 样式 |
|------|--------|--------|------|
| 主要 | `{comp.button.primary.bg}` = `#96F878` | `{comp.button.primary.fg}` = `#212427` | 无边框，含箭头 → |
| 次要 | 透明 | `#0C2B15` | 无背景，纯文字 |

### 5.8 标签 / 徽章

- **背景：** `{comp.tag.bg}` = `#96F878`；**文字色：** `#212427`；**圆角：** 4px；**字号：** 9pt uppercase

### 5.9 卡片

- **背景：** `{color.surface.card}` = `#FFFFFF`；**边框：** 无；**阴影：** 轻微；**圆角：** 8px

---

## 6. 视觉层级逻辑

- **层级数量：** 4 级（H1–H4）
- **层级区分方式：** 字号差 + **字体差**（衬线/无衬线）+ 颜色差（深森林绿/近黑/灰）
- **最大层级视觉权重：** 30pt，300 Light，衬线，`#0C2B15`
- **层级色彩策略：** H1/H2 同色（`#0C2B15`），H3 变色（`#212427`），H4 再变（`#696969` uppercase）

---

## 7. 图像处理

- **图片风格：** 彩色写实（摄影），部分深色蒙版叠加
- **惯用宽高比：** 16:9 / 3:2
- **深色蒙版：** `{color.surface.dark}` = `#0C2B15`，约 40%
- **图片叠文字时：** 白色文字（`{color.text.inverse}`）/ 渐变蒙版

---

## 8. 数据可视化 / 图表

- **图表配色顺序：** `#96F878` → `#0C2B15` → `#21BF61` → `#696969` → `#F1EEEA`（见 2.2 DataViz）
- **图表背景：** 白色
- **图表字体：** `henderson-bcg-sans`（降级：Helvetica Neue）
- **坐标轴 / 网格线颜色：** `{color.border.default}` = `#D4D4D4`

---

## 9. 各格式推导指南

> `/design-derive` 读取 2.3 Component Tokens，顺引用链解析至 hex。

### 解析引用链示例（BCG）

```
comp.heading.h1.deco-line
  → {color.interactive.primary}
    → {accent-200}
      → #96F878   ← 写入 CSS / JSON 的值
```

---

### → DOCX（doc-forge style.json）

| JSON 字段 | resolve 后的值 |
|-----------|--------------|
| `headings.h1.color` | `0C2B15` |
| `headings.h1.font_en` | `Georgia` |
| `headings.h1.bold` | `false`（300 Light）|
| `headings.h2.color` | `0C2B15` |
| `headings.h2.font_en` | `Georgia` |
| `headings.h2.bold` | `false` |
| `headings.h3.color` | `212427` |
| `headings.h3.font_en` | `Helvetica Neue` |
| `headings.h4.color` | `696969` |
| `body.font` | `PingFang SC` |
| `body.font_en` | `Helvetica Neue` |
| `body.size_pt` | `12` |
| `body.line_spacing_pt` | `18`（1.5倍）|
| `body.space_after_pt` | `7` |
| `body.first_line_indent_chars` | `0` |
| `table.border_mode` | `mckinsey` |
| `table.rule_color` | `212427` |
| `table.border_color` | `D4D4D4` |
| `blockquote.font_en` | `Georgia` |
| `blockquote.color` | `0C2B15` |
| `page.top_cm` | `2.0` |
| `page.bottom_cm` | `2.0` |
| `page.left_cm` | `2.5` |
| `page.right_cm` | `2.5` |

### → PDF（doc-forge CSS）

| CSS 属性 | resolve 后的值 |
|----------|--------------|
| `h1 border-bottom color` | `#96F878`（`comp.heading.h1.deco-line`）|
| `h2 border-bottom color` | `#96F878` |
| `h3 border-left color` | `#96F878` |
| `blockquote border-left color` | `#96F878`（`comp.blockquote.left-bar`）|
| `pre background` | `#F1EEEA` |
| `pre border-left color` | `#0C2B15`（代码块左条用深色）|
| `body font-family` | `"PingFang SC", "Helvetica Neue", ...` |
| `h1/h2 font-family` | `"Georgia", "STSong", ...` serif |
| `h1/h2 font-weight` | `300` |

### → HTML CSS 变量（已 resolve）

```css
:root {
  --color-interactive:      #96F878;
  --color-interactive-fg:   #212427;
  --color-text-heading:     #0C2B15;
  --color-text-body:        #212427;
  --color-text-muted:       #696969;
  --color-text-link:        #0C2B15;
  --color-surface-page:     #FFFFFF;
  --color-surface-section:  #F2F2F2;
  --color-surface-warm:     #F1EEEA;
  --color-surface-dark:     #0C2B15;
  --color-border:           #D4D4D4;
  --color-border-accent:    #96F878;
  --font-heading:           "Georgia", "STSong", "Songti SC", serif;
  --font-body:              "PingFang SC", "Helvetica Neue", "Arial", sans-serif;
  --font-mono:              "JetBrains Mono", "Cascadia Code", "Courier New", monospace;
  --space-unit:             8px;
}
```

### → Mermaid（图表配色）

```
%%{init: {"theme": "base", "themeVariables": {
  "primaryColor":        "#96F878",
  "primaryBorderColor":  "#71DC68",
  "primaryTextColor":    "#212427",
  "secondaryColor":      "#0C2B15",
  "tertiaryColor":       "#21BF61",
  "background":          "#FFFFFF",
  "clusterBkg":          "#F2F2F2",
  "titleColor":          "#0C2B15",
  "lineColor":           "#D4D4D4"
}}}%%
```

- dataviz.1 `#96F878`（浅色）→ 节点加 `color:#212427`（黑字）
- dataviz.2 `#0C2B15`（深色）→ 节点加 `color:#FFFFFF`（白字）
- 语义节点：success `#21BF61` / warning `#FFCF24` / danger `#D82216`

### → PPT（演示文稿主题）

| 槽位 | resolve 后的值 |
|------|--------------|
| Color 1（深/文字） | `#0C2B15` |
| Color 2（浅/背景） | `#FFFFFF` |
| Accent 1（主动作） | `#96F878` |
| Accent 2 | `#0C2B15` |
| Accent 3 | `#21BF61` |
| Accent 4 | `#F1EEEA` |
| 超链接 | `#0C2B15` |

- **标题幻灯片：** `#0C2B15` 背景 + `#FFFFFF` 文字 + `#96F878` 装饰线
- **内容幻灯片：** `#FFFFFF` 背景 + `#212427` 正文 + `#96F878` 小面积点缀（按钮 / 图表）
