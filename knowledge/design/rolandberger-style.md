# Roland Berger 设计系统

> **文件用途：** 跨格式设计单一真相来源。供 `/design-derive` skill 读取后推导各输出格式的具体配置。
> **生成方式：** 由 `/style-scout` 调查官网自动生成。
> **来源页面：** https://www.rolandberger.com/en/ | https://www.rolandberger.com/en/Insights/Publications/AI-The-new-market-maker.html

---

## 1. 品牌概述

**设计哲学：** 大胆对比 + 高识别度色彩点缀——大量留白与纯白底衬托 RBDesign 定制无衬线字体，以红色作为唯一强交互锚点，黄色 `#F6F600` 作为低调但一致的装饰线系统贯穿全站。

**气质关键词：** 现代精简 / 专业克制 / 鲜明对比 / 编辑感 / 定制字体主导

**适用场景：** 报告文档 / 官网 / 演示文稿 / 数据看板

---

## 2. 色彩 Token 体系

> 采用三层模型：**Primitive**（是什么）→ **Semantic**（做什么）→ **Component**（用在哪）。

---

### 2.1 Primitive Tokens（原始色板）

| Token | 色值 | 视觉描述 |
|-------|------|---------|
| `red-500` | `#FF3532` | 鲜红，主 CTA 按钮 / Jobs 徽章 |
| `blue-700` | `#004AC2` | 中蓝，pull quote 文字色 |
| `blue-500` | `#156C9C` | 中等咨询蓝，报告页 Hero 背景 |
| `navy-900` | `#000082` | 深海军蓝，全局话题卡片背景 |
| `wine-800` | `#84003A` | 深酒红，部分专题卡片背景 |
| `teal-500` | `#00AAC9` | 青蓝，CSS 中定义（数据可视化） |
| `yellow-400` | `#F6F600` | 亮黄，链接装饰线 / 页脚链接底边 |
| `green-100` | `#D1FCDE` | 薄荷绿，Contact Us 区块背景 |
| `pink-500` | `#E6006E` | 品红，CSS 定义（数据可视化） |
| `orange-500` | `#E6593F` | 橙红，CSS 定义（数据可视化） |
| `olive-400` | `#CDD400` | 橄榄黄绿，CSS 定义（数据可视化） |
| `lime-500` | `#72B656` | 草绿，CSS 定义（数据可视化） |
| `neutral-900` | `#000000` | 纯黑，正文 / 导航文字 |
| `neutral-700` | `#666666` | 中深灰，辅助文字 |
| `neutral-600` | `#8D9399` | 中灰，meta 信息 |
| `neutral-500` | `#C8C8C8` | 中浅灰，结构分隔线 |
| `neutral-400` | `#CED2D5` | 浅灰，细边框 |
| `neutral-300` | `#EFF0F1` | 极浅灰，交替 section 背景 |
| `neutral-200` | `#F0F0F0` | 近白灰，卡片 / 页脚背景 |
| `white` | `#FFFFFF` | 白，页面底色 |

---

### 2.2 Semantic Tokens（语义角色）

#### Interactive（交互色）

> 主 CTA 按钮（newsletter 订阅、PDF 获取、Jobs 徽章）均为红色 `#FF3532`。
> 黄色 `#F6F600` 作为链接 box-shadow 下划线，属于装饰性 interactive 层。

| Token | → Primitive | 说明 |
|-------|------------|------|
| `color.interactive.primary` | `{red-500}` | 主 CTA 按钮背景（红色） |
| `color.interactive.primary-fg` | `{white}` | 主 CTA 按钮文字 |
| `color.interactive.secondary` | `{neutral-900}` | 次级按钮（CONTACT / OUR CONSULTING APPROACH） |
| `color.interactive.accent` | `{yellow-400}` | 链接悬浮/装饰下划线（box-shadow inset 技术） |
| `color.interactive.hover` | `{neutral-900}` | hover 态（按钮变黑） |

#### Text（文字色）

| Token | → Primitive | 视觉近黑？ | 用途 |
|-------|------------|----------|------|
| `color.text.heading` | `{neutral-900}` | 是 [视觉近黑] | H1（正文区）/ H2 / H3 |
| `color.text.subheading` | `{neutral-900}` | 是 [视觉近黑] | H3 / H4 |
| `color.text.body` | `{neutral-900}` | — | 正文段落 |
| `color.text.muted` | `{neutral-600}` | — | meta / 日期 / 地点 |
| `color.text.link` | `{neutral-900}` | — | 正文链接（黄色 box-shadow 下划线 via inset） |
| `color.text.pullquote` | `{blue-700}` | 否 [有色] | Pull quote 文字（Arnhem Semi Bold） |
| `color.text.inverse` | `{white}` | — | 深色背景上的文字（Hero / 导航） |

#### Surface（背景 / 表面色）

| Token | → Primitive | 用途 |
|-------|------------|------|
| `color.surface.page` | `{white}` | 页面底色（body） |
| `color.surface.section` | `{neutral-200}` | 交替 section / 卡片区背景 |
| `color.surface.card` | `{white}` | 内容卡片背景 |
| `color.surface.muted` | `{neutral-300}` | 较浅交替背景 |
| `color.surface.contact` | `{green-100}` | Contact Us 薄荷绿区块 |
| `color.surface.hero` | `{blue-500}` | 报告页蓝色 Hero（`#156C9C`） |
| `color.surface.dark` | `{neutral-900}` | sticky 导航 / 深色强调区 |
| `color.surface.code` | `{neutral-200}` | 代码块背景 |

#### Border（边框 / 分隔线）

| Token | → Primitive / Semantic | 说明 |
|-------|----------------------|------|
| `color.border.default` | `{neutral-500}` | 通用分隔线（`#C8C8C8`） |
| `color.border.light` | `{neutral-400}` | 细边框（`#CED2D5`） |
| `color.border.accent` | `{color.interactive.primary}` | 强调线 → 指向 Interactive（红色） |
| `color.border.deco` | `{yellow-400}` | 装饰性底边线（`#F6F600`，页脚链接 / section 标题） |
| `color.border.strong` | `{neutral-900}` | 重边框（表头上下线） |

#### Status（语义状态色）

| Token | 色值 | 用途 |
|-------|------|------|
| `color.status.success` | `#72B656` | 正向 / 完成 |
| `color.status.warning` | `#CDD400` | 警告 |
| `color.status.danger` | `#FF3532` | 危险 / 错误 |
| `color.status.info` | `#156C9C` | 中性信息 |

#### DataViz（数据可视化序列）

> Roland Berger 官网 CSS bundle 定义了完整的可视化调色盘。第 1 色沿用 RB 蓝而非 CTA 红，以便在图表中保持专业感。

| 序号 | Token | → Primitive |
|------|-------|------------|
| 1 | `color.dataviz.1` | `{blue-500}` (`#156C9C`) |
| 2 | `color.dataviz.2` | `{teal-500}` (`#00AAC9`) |
| 3 | `color.dataviz.3` | `{olive-400}` (`#CDD400`) |
| 4 | `color.dataviz.4` | `{lime-500}` (`#72B656`) |
| 5 | `color.dataviz.5` | `{pink-500}` (`#E6006E`) |
| 6 | `color.dataviz.6` | `{orange-500}` (`#E6593F`) |

---

### 2.3 Component Tokens（组件引用）

| Component Token | → Semantic | 用途 |
|----------------|-----------|------|
| `comp.heading.h1.color` | `{color.text.inverse}` | H1 文字色（Hero 白字） |
| `comp.heading.h1.deco-line` | `{color.interactive.accent}` | H1 下划线装饰色（黄色） |
| `comp.heading.h2.color` | `{color.text.heading}` | H2 文字色 |
| `comp.heading.h2.deco-line` | `{color.border.deco}` | H2 装饰底线（黄色 `#F6F600`） |
| `comp.heading.h3.color` | `{color.text.heading}` | H3 文字色 |
| `comp.heading.h3.left-bar` | `{color.interactive.primary}` | H3 左色条（红色，若有） |
| `comp.heading.h4.color` | `{color.text.muted}` | H4 文字色（uppercase 辅助） |
| `comp.body.color` | `{color.text.body}` | 正文 |
| `comp.link.color` | `{color.text.link}` | 链接文字色（黑）|
| `comp.link.deco` | `{color.interactive.accent}` | 链接装饰（黄色 box-shadow inset） |
| `comp.blockquote.left-bar` | `none` | **无**左色条（RB blockquote 无边框） |
| `comp.blockquote.color` | `{color.text.pullquote}` | Pull quote 文字色（`#004AC2` 蓝） |
| `comp.blockquote.font` | `Arnhem Semi Bold` | Pull quote 专用衬线字体 |
| `comp.table.border-header` | `{color.border.strong}` | 表头上下横线（黑） |
| `comp.table.border-row` | `{color.border.default}` | 行间分隔线（灰） |
| `comp.table.accent-line` | `{color.interactive.primary}` | 表头强调线（红，rb 模式） |
| `comp.code.bg` | `{color.surface.code}` | 代码块背景 |
| `comp.code.left-bar` | `{color.interactive.secondary}` | 代码块左色条 |
| `comp.hr.color` | `{color.border.default}` | 水平分隔线 |
| `comp.button.primary.bg` | `{color.interactive.primary}` | 主按钮背景（红） |
| `comp.button.primary.fg` | `{color.interactive.primary-fg}` | 主按钮文字（白） |
| `comp.tag.bg` | `{color.interactive.primary}` | 标签 / 徽章背景（红） |
| `comp.tag.fg` | `{color.interactive.primary-fg}` | 标签文字（白） |

---

## 3. 字体体系

### 3.1 官方字体（专有，需授权）

| 场景 | 字体名 | 字重说明 | 类型 |
|------|--------|------|------|
| 标题 / 强调 | `RBDesign Bold` | 400（粗体内嵌在字体文件名中） | 无衬线，定制 |
| 正文 | `RBDesign Regular` | 400 | 无衬线，定制 |
| 副文字 / 轻量 | `RBDesign Light` | 400 | 无衬线，定制 |
| Pull Quote | `Arnhem Semi Bold` | 400 | 衬线，编辑风格 |

> **注：** RBDesign 字体系列通过 MyFonts 授权（CSS bundle 引用 `//hello.myfonts.net/count/2e39e3`）。
> 文档输出时应使用下方降级字体栈。

### 3.2 降级字体栈

| 场景 | 字体栈 |
|------|--------|
| 标题（无衬线，对应 RBDesign） | `"Helvetica Neue", "Arial", "PingFang SC", "STHeiti", sans-serif` |
| Pull Quote（衬线，对应 Arnhem） | `"Georgia", "STSong", "Songti SC", "SimSun", serif` |
| 正文 | `"Helvetica Neue", "Arial", "PingFang SC", "STHeiti", sans-serif` |
| 等宽 | `"JetBrains Mono", "Cascadia Code", "Courier New", monospace` |

### 3.3 字号尺度（Type Scale）

| 元素 | 字号 | 行距 | 字重（font-weight） | 颜色 |
|------|------|------|------|------|
| Hero H1 | 48pt | 1.13 | 400（RBDesign Bold） | white（Hero 上） |
| H3（正文主标题） | 21pt | 1.07 | 400（RBDesign Bold） | `#000000` |
| Pull Quote | 21pt | 1.50 | 400（Arnhem Semi Bold） | `#004AC2` |
| 正文 / H2-label | 10.5pt | 1.36 | 400（RBDesign Regular） | `#000000` |
| 链接 | 13.5pt | 1.56 | 400（RBDesign Light） | `#000000` |
| 小字 / meta | 10.5pt | 1.36 | 400 | `#8D9399` |

> **注：** DOM 中 `h2` 首次出现为 10.5pt 的分类标签（如 STUDY / REPORT）；正文中的大节标题使用 `h3` 标签，21pt。Web 文档输出时建议将视觉层次映射到 h2=24pt, h3=18pt。

### 3.4 中英文混排规则

- 英文字体：RBDesign 系列（降级：Helvetica Neue / Arial）
- 中文字体：降级使用 PingFang SC / STHeiti
- 混排间距：网站以英文为主，无专门中文混排样式
- 标点处理：西文标点

---

## 4. 间距体系

### 4.1 基础单位

- 网格单位：`8px`（容器 padding 约 43px ≈ 5.5 × 8px）
- 间距尺度：`8 / 16 / 24 / 32 / 48 / 64px`

### 4.2 版面参数

| 参数 | 值 | 说明 |
|------|------|------|
| 容器最大宽度 | 1280px | `.container` max-width |
| 内容区宽度 | ~1204px | `.wrapper` 实际宽度（含 padding） |
| 内容区水平 padding | ~43px 左 / ~22px 右 | 略不对称（RB 独特排版） |
| 页边距（文档输出） | 2.5cm | 建议左右页边距 |

### 4.3 组件间距

| 场景 | 值 |
|------|------|
| 段落间距 | 0px（由行高自然分隔，body margin-bottom = 0） |
| 标题下方装饰线间距 | ~4px |
| 首行缩进 | 0 |

---

## 5. 组件规则

### 5.1 标题装饰

| 级别 | 装饰方式 | 颜色 Token | 粗细 |
|------|---------|-----------|------|
| H1 (Hero) | 白字，无额外装饰线 | — | — |
| H2 / Section Label | 黄色底边线（short bar） | `{comp.heading.h2.deco-line}` | 2px |
| H3 / 正文主标题 | 无装饰（可选黄色底线） | `{comp.heading.h2.deco-line}` | 2px |
| H4 | uppercase + letter-spacing | `{comp.heading.h4.color}` | — |

> **RB 特征：** 页面 section 标题（如"Meet our experts"、"Join the team"）下方有约 30–40px 宽的短黑线装饰，非彩色。导航/页脚链接 hover 时显示黄色 `#F6F600` 底边线。

### 5.2 表格

> RB 官网报告页无 HTML 表格（数据以 CSS Grid 信息图呈现）。文档输出推荐如下规范：

- **边框模式：** mckinsey（仅头尾横线，简洁专业）
- **表头上下线颜色：** `{comp.table.border-header}` → `#000000`
- **行间分隔线颜色：** `{comp.table.border-row}` → `#C8C8C8`
- **强调线（rb 模式）：** `{comp.table.accent-line}` → `#FF3532`（红色）
- **表头：** 无背景；加粗（RBDesign Bold）；左对齐
- **数据行：** 无底色，无斑马纹
- **竖线：** 无

### 5.3 引用块 / Pull Quote

> **RB 偏离模板默认：** blockquote 无左色条，改用彩色文字 + 衬线字体。

- **左色条：** 无
- **背景：** 透明
- **文字色：** `{comp.blockquote.color}` → `#004AC2`（中蓝）
- **字体：** Arnhem Semi Bold（衬线，对应降级：Georgia / STSong）
- **字号：** 21pt，比正文大一级
- **字形：** 正体（non-italic）

### 5.4 代码块

- **背景：** `{comp.code.bg}` → `#F0F0F0`；**左色条：** 待补充；**圆角：** 4px
- **字体：** 等宽，10.5pt
- **行内代码背景：** `#F0F0F0`；**文字色：** `#000000`

### 5.5 列表

- **无序列表符号：** • 实心圆点
- **有序列表样式：** 阿拉伯数字
- **缩进：** 1.5em

### 5.6 分隔线

- **颜色：** `{comp.hr.color}` → `#C8C8C8`；**粗细：** 1px；**样式：** solid

### 5.7 按钮

| 类型 | 背景色 | 文字色 | 边框 | Hover |
|------|--------|--------|------|-------|
| 主要（CTA） | `#FF3532` | `#FFFFFF` | 无 | 变深红或黑 |
| 次级（CONTACT） | `#000000` | `#FFFFFF` | 无 | — |
| Ghost | 透明 | `#000000` | `#C8C8C8` | — |

### 5.8 标签 / 徽章

- **背景：** `#FF3532`（红）/ `#000082`（深蓝，Global Topic）/ `#84003A`（酒红，专题）
- **文字色：** `#FFFFFF`（白）
- **圆角：** 0px（无圆角，矩形）
- **字号：** 约 9pt uppercase，字间距适当加宽

### 5.9 卡片

- **背景：** `#FFFFFF` 白；**边框：** 无；**阴影：** 无；**圆角：** 0px
- 卡片封面图占满卡片宽度，无内边距
- 标题 bold，正文 regular

### 5.10 链接装饰（RB 特有）

- **技术：** `box-shadow: rgb(246, 246, 0) 0px -4px 0px 0px inset`
- **效果：** 黄色 `#F6F600` 模拟 4px 底部下划线，不影响文字布局
- **适用：** 正文段落内超链接、页脚导航链接

---

## 6. 视觉层级逻辑

- **层级数量：** Web 使用 3 级（Hero H1 / 正文 H3 / 小标签 H2/H4）
- **层级区分方式：** 字号差（主）+ 字重差（副）+ 装饰差
- **最大层级视觉权重：** 48pt，RBDesign Bold，白字，蓝色 Hero 背景
- **层级色彩策略：** H1 白字（逆色）/ H2–H4 纯黑，无渐变

---

## 7. 图像处理

- **图片风格：** 彩色写实摄影（商业、工业、科技类题材）
- **惯用宽高比：** 16:9（首页 Hero）/ 3:2（卡片缩略图）
- **报告页 Hero：** 固定蓝色背景 `#156C9C` + RB 品牌字母"B"装饰图形
- **图片叠文字时：** 白色文字（`{color.text.inverse}`）
- **深色蒙版：** 当有覆盖文字时，使用半透明黑色蒙版（`rgba(0,0,0,0.5)`）

---

## 8. 数据可视化 / 图表

- **图表配色顺序：** 见 2.2 DataViz（`color.dataviz.1` 到 `.6`）
- **首选色：** `#156C9C`（RB 蓝）— 非 CTA 红，保持图表专业感
- **图表背景：** 白色 / `#F0F0F0`（浅灰）
- **图表字体：** 同正文（Helvetica Neue 降级）
- **坐标轴 / 网格线颜色：** `{color.border.default}` → `#C8C8C8`
- **矩阵/分类图：** 用虚线（dashed `#C8C8C8`）划分象限，类别标签用深色小矩形背景

---

## 9. 各格式推导指南

### → DOCX（doc-forge style.json）

| JSON 字段 | 读取 Token | 值 |
|-----------|-----------|------|
| `headings.h1.color` | `comp.heading.h3.color` → resolve | `000000` |
| `headings.h1.font_en` | 3.2 标题降级栈第一项 | `Helvetica Neue` |
| `body.font` / `body.font_en` | 3.2 正文降级栈 | `Helvetica Neue` |
| `table.border_mode` | 5.2 边框模式 | `mckinsey` |
| `table.rule_color` | `comp.table.border-header` → resolve | `000000` |
| `table.accent_color` | `comp.table.accent-line` → resolve | `FF3532` |
| `table.row_sep_color` | `comp.table.border-row` → resolve | `C8C8C8` |
| `blockquote.color` | `comp.blockquote.color` → resolve | `004AC2` |
| `body.first_line_indent_chars` | 4.3 首行缩进 | `0` |

### → PDF（doc-forge CSS）

| CSS 属性 | 读取 Token | 值 |
|----------|-----------|------|
| `h1 border-bottom color` | `comp.heading.h1.deco-line` → resolve | `F6F600` |
| `h2 border-bottom color` | `comp.heading.h2.deco-line` → resolve | `F6F600` |
| `h3 border-left color` | `comp.heading.h3.left-bar` → resolve | `FF3532` |
| `blockquote color` | `comp.blockquote.color` → resolve | `004AC2` |
| `blockquote border-left` | `none`（RB 特有：无左色条） | — |
| `pre background` | `comp.code.bg` → resolve | `F0F0F0` |
| `a box-shadow` | `comp.link.deco` → resolve | `F6F600` |
| `body font-family` | 3.2 正文降级栈 | `"Helvetica Neue", Arial, sans-serif` |
| `h1/h2 font-family` | 3.2 标题降级栈 | `"Helvetica Neue", Arial, sans-serif` |

### → HTML（CSS 自定义属性）

```css
:root {
  --color-interactive:     #FF3532;   /* color.interactive.primary */
  --color-interactive-fg:  #FFFFFF;   /* color.interactive.primary-fg */
  --color-interactive-accent: #F6F600; /* 链接装饰黄 */
  --color-text-heading:    #000000;   /* color.text.heading */
  --color-text-body:       #000000;   /* color.text.body */
  --color-text-muted:      #8D9399;   /* color.text.muted */
  --color-text-link:       #000000;   /* color.text.link */
  --color-text-pullquote:  #004AC2;   /* color.text.pullquote */
  --color-surface-page:    #FFFFFF;
  --color-surface-section: #F0F0F0;   /* color.surface.section */
  --color-surface-card:    #FFFFFF;
  --color-surface-hero:    #156C9C;   /* 报告页蓝色 Hero */
  --color-surface-dark:    #000000;   /* sticky 导航 */
  --color-border:          #C8C8C8;   /* color.border.default */
  --color-border-accent:   #FF3532;   /* color.border.accent */
  --color-border-deco:     #F6F600;   /* 装饰黄线 */
  --font-heading:          "Helvetica Neue", Arial, sans-serif;
  --font-body:             "Helvetica Neue", Arial, sans-serif;
  --font-pullquote:        Georgia, "STSong", serif;
  --font-mono:             "JetBrains Mono", "Courier New", monospace;
  --space-unit:            8px;
}
```

### → Mermaid（图表配色）

```
%%{init: {"theme": "base", "themeVariables": {
  "primaryColor":        "#156C9C",
  "primaryBorderColor":  "#004775",
  "secondaryColor":      "#00AAC9",
  "tertiaryColor":       "#D1FCDE",
  "background":          "#FFFFFF",
  "clusterBkg":          "#F0F0F0",
  "titleColor":          "#000000",
  "lineColor":           "#C8C8C8"
}}}%%
```

- 深色节点（dataviz.1 `#156C9C`）：`color:#fff`
- 浅色节点：`color:#000`
- 状态节点：danger → `#FF3532`，info → `#156C9C`

### → PPT（演示文稿主题）

| 槽位 | 读取 Token | 值 |
|------|-----------|------|
| Color 1（深/文字） | `color.text.heading` | `#000000` |
| Color 2（浅/背景） | `color.surface.page` | `#FFFFFF` |
| Accent 1（主动作） | `color.interactive.primary` | `#FF3532` |
| Accent 2 | `color.dataviz.1` | `#156C9C` |
| Accent 3 | `color.dataviz.2` | `#00AAC9` |
| Accent 4 | `color.surface.section` | `#F0F0F0` |
| 超链接 | `color.text.link` | `#000000` |

- **标题幻灯片：** `#156C9C` 蓝背景 + 白字 + `#FF3532` 装饰线（仿报告 Hero）
- **内容幻灯片：** 白色背景 + 黑正文 + `#FF3532` 红色小面积强调
