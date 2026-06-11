# <品牌名> 设计系统

> **文件用途：** 跨格式设计单一真相来源。供 `/design-derive` skill 读取后推导各输出格式的具体配置。
> **生成方式：** 由 `/style-scout` 调查官网自动生成，或手动维护。
> **来源页面：** <调查所用的主页 + 报告页 URL>

---

## 1. 品牌概述

**设计哲学：** （一句话描述核心设计原则）

**气质关键词：** （3–5 个词，如：极简现代 / 保守专业 / 大胆对比 / 留白充足）

**适用场景：** 报告文档 / 官网 / 演示文稿 / 数据看板

---

## 2. 色彩 Token 体系

> 采用三层模型：**Primitive**（是什么）→ **Semantic**（做什么）→ **Component**（用在哪）。
>
> - **Primitive**：调查得到的原始色值，按色相分组，不赋予语义
> - **Semantic**：将 Primitive 映射到功能角色（交互 / 文字 / 表面 / 边框 / 状态 / 数据可视化）
> - **Component**：将 Semantic 映射到具体组件属性，是 `/design-derive` 的直接读取来源
>
> 值使用 `{token-name}` 格式引用上层，避免重复写 hex。

---

### 2.1 Primitive Tokens（原始色板）

> 品牌拥有的所有颜色。命名格式：`色相-明度`（如 `green-900`、`lime-400`）。
> 按色相分组，每组从深到浅排列。不赋予任何语义。

| Token | 色值 | 视觉描述 |
|-------|------|---------|
| `<hue>-900` | `#XXXXXX` | 深色 |
| `<hue>-700` | `#XXXXXX` | |
| `<hue>-500` | `#XXXXXX` | 中色 |
| `<hue>-200` | `#XXXXXX` | 浅色 |
| `<hue2>-500` | `#XXXXXX` | 第二色相 |
| `neutral-900` | `#XXXXXX` | 近黑 |
| `neutral-500` | `#XXXXXX` | 中灰 |
| `neutral-200` | `#XXXXXX` | 浅灰 |
| `white` | `#FFFFFF` | 白 |

---

### 2.2 Semantic Tokens（语义角色）

> 颜色"做什么"。值用 `{primitive}` 引用 2.1，不写原始 hex。

#### Interactive（交互色）

> 出现在 CTA 按钮、链接、选中态、hover 状态。
> **是文档装饰线（H1/H2 下划线、H3 左色条）的来源**——见 2.3 Component Tokens。

| Token | → Primitive | 说明 |
|-------|------------|------|
| `color.interactive.primary` | `{XXXXXX}` | 主 CTA 按钮背景 |
| `color.interactive.primary-fg` | `{XXXXXX}` | 主 CTA 上的文字（黑或白） |
| `color.interactive.secondary` | `{XXXXXX}` | 次级按钮、链接色 |
| `color.interactive.hover` | `{XXXXXX}` | hover / active 态 |

#### Text（文字色）

> `[视觉近黑]`：RGB 三通道之和 < 150，在文档中视觉上近似纯黑，**不适合做彩色装饰线**。

| Token | → Primitive | 视觉近黑？ | 用途 |
|-------|------------|----------|------|
| `color.text.heading` | `{XXXXXX}` | 是 / 否 | H1 / H2 |
| `color.text.subheading` | `{XXXXXX}` | 是 / 否 | H3 / H4 |
| `color.text.body` | `{XXXXXX}` | — | 正文段落 |
| `color.text.muted` | `{XXXXXX}` | — | 辅助信息 / meta / 日期 |
| `color.text.link` | `{XXXXXX}` | — | 链接 |
| `color.text.inverse` | `{white}` | — | 深色背景上的文字 |

#### Surface（背景 / 表面色）

| Token | → Primitive | 用途 |
|-------|------------|------|
| `color.surface.page` | `{white}` | 页面底色（body） |
| `color.surface.section` | `{XXXXXX}` | 交替 section 背景 |
| `color.surface.card` | `{XXXXXX}` | 卡片背景 |
| `color.surface.dark` | `{XXXXXX}` | Hero / 导航 / 深色强调区 |
| `color.surface.code` | `{XXXXXX}` | 代码块背景 |

#### Border（边框 / 分隔线）

| Token | → Primitive / Semantic | 说明 |
|-------|----------------------|------|
| `color.border.default` | `{XXXXXX}` | 通用分隔线、表格行线 |
| `color.border.accent` | `{color.interactive.primary}` | 强调线 → **指向 Interactive，不指向文字色** |
| `color.border.strong` | `{XXXXXX}` | 重边框（表格外框、表头上下线） |

#### Status（语义状态色）

| Token | 色值 | 用途 |
|-------|------|------|
| `color.status.success` | `#XXXXXX` | 正向 / 完成 |
| `color.status.warning` | `#XXXXXX` | 警告 |
| `color.status.danger` | `#XXXXXX` | 危险 / 错误 |
| `color.status.info` | `#XXXXXX` | 中性信息 |

#### DataViz（数据可视化序列）

> 按使用优先级排列，至少 5 色。第 1 色通常来自 Interactive。

| 序号 | Token | → Primitive / Semantic |
|------|-------|----------------------|
| 1 | `color.dataviz.1` | `{color.interactive.primary}` |
| 2 | `color.dataviz.2` | `{XXXXXX}` |
| 3 | `color.dataviz.3` | `{XXXXXX}` |
| 4 | `color.dataviz.4` | `{XXXXXX}` |
| 5 | `color.dataviz.5` | `{XXXXXX}` |

---

### 2.3 Component Tokens（组件引用）

> 颜色"用在哪"。**是 `/design-derive` 的直接读取来源。**
> 值引用 2.2 Semantic Tokens。
>
> **装饰线规则硬编码于此层：** heading 装饰线 → `{color.interactive.primary}`，
> 不依赖文字色，无需在推导时再判断。

| Component Token | → Semantic | 用途 |
|----------------|-----------|------|
| `comp.heading.h1.color` | `{color.text.heading}` | H1 文字色 |
| `comp.heading.h1.deco-line` | `{color.interactive.primary}` | H1 下划线装饰色 |
| `comp.heading.h2.color` | `{color.text.heading}` | H2 文字色 |
| `comp.heading.h2.deco-line` | `{color.interactive.primary}` | H2 下划线装饰色 |
| `comp.heading.h3.color` | `{color.text.subheading}` | H3 文字色 |
| `comp.heading.h3.left-bar` | `{color.interactive.primary}` | H3 左色条 |
| `comp.heading.h4.color` | `{color.text.muted}` | H4 文字色（uppercase 辅助） |
| `comp.body.color` | `{color.text.body}` | 正文 |
| `comp.link.color` | `{color.text.link}` | 链接 |
| `comp.blockquote.left-bar` | `{color.border.accent}` | 引用块左色条 |
| `comp.blockquote.color` | `{color.text.heading}` | 引用文字色 |
| `comp.table.border-header` | `{color.border.strong}` | 表头上下横线 |
| `comp.table.border-row` | `{color.border.default}` | 行间分隔线 |
| `comp.table.accent-line` | `{color.interactive.primary}` | 表头强调线（rb 模式） |
| `comp.code.bg` | `{color.surface.code}` | 代码块背景 |
| `comp.code.left-bar` | `{color.interactive.secondary}` | 代码块左色条 |
| `comp.hr.color` | `{color.border.default}` | 水平分隔线 |
| `comp.button.primary.bg` | `{color.interactive.primary}` | 主按钮背景 |
| `comp.button.primary.fg` | `{color.interactive.primary-fg}` | 主按钮文字 |
| `comp.tag.bg` | `{color.interactive.primary}` | 标签 / 徽章背景 |
| `comp.tag.fg` | `{color.interactive.primary-fg}` | 标签文字 |

> **覆盖规则：** 若品牌实际组件样式与上方默认映射不同（如 blockquote 用标题色而非动作色），
> 直接修改此表对应行的 Semantic 引用，推导结果自动更新。

---

## 3. 字体体系

### 3.1 官方字体（专有，需授权）

| 场景 | 字体名 | 字重 | 类型 |
|------|--------|------|------|
| 主标题 | `font-name` | 300 / 700 | 衬线 / 无衬线 |
| 正文 | `font-name` | 400 | |
| 中文 | `font-name` | — | 专有中文字体 |

### 3.2 降级字体栈

| 场景 | 字体栈 |
|------|--------|
| 标题（衬线） | `"Georgia", "STSong", "Songti SC", "SimSun", serif` |
| 标题（无衬线） | `"Helvetica Neue", "Arial", "PingFang SC", "STHeiti", sans-serif` |
| 正文 | `"PingFang SC", "Helvetica Neue", "Arial", "STHeiti", "Microsoft YaHei", sans-serif` |
| 等宽 | `"JetBrains Mono", "Cascadia Code", "Courier New", monospace` |

### 3.3 字号尺度（Type Scale）

| 元素 | 字号 | 行距 | 字重 | 字间距 |
|------|------|------|------|--------|
| Display / Hero | Xpt | X倍 | X | — |
| H1 | Xpt | X倍 | X | X |
| H2 | Xpt | X倍 | X | X |
| H3 | Xpt | X倍 | X | — |
| H4 | Xpt | X倍 | X | uppercase |
| 正文 | Xpt | X倍 | 400 | — |
| 小字 / 注释 | Xpt | X倍 | 400 | — |
| 表格 | Xpt | — | 400（表头加粗） | — |
| 代码 | Xpt | 1.5 | 400 | — |

### 3.4 中英文混排规则

- 中文字体：
- 英文字体：
- 混排间距：（中英文之间是否自动加空格）
- 标点处理：

---

## 4. 间距体系

### 4.1 基础单位

- 网格单位：`Xpx`（4px / 8px grid）
- 间距尺度：`X / 2X / 4X / 8X / 16X`

### 4.2 版面参数

| 参数 | 值 | 说明 |
|------|------|------|
| 页边距（上/下） | Xcm | 文档上下边距 |
| 页边距（左/右） | Xcm | 文档左右边距 |
| 正文区最大宽度 | Xpx | 网页正文列宽 |
| 列间距 | Xpx | 多列布局 |

### 4.3 组件间距

| 场景 | 值 |
|------|------|
| H1 下方间距 | Xpt |
| H2 上方间距 | Xpt |
| H3 上方间距 | Xpt |
| 段落间距 | Xpt |
| 首行缩进 | 0 / 2字符 |

---

## 5. 组件规则

> 颜色字段引用 2.3 Component Tokens，不写原始 hex。

### 5.1 标题装饰

| 级别 | 装饰方式 | 颜色 Token | 粗细 |
|------|---------|-----------|------|
| H1 | 下划线 / 左色条 / 背景色块 / 无 | `{comp.heading.h1.deco-line}` | Xpx |
| H2 | 下划线 / 无 | `{comp.heading.h2.deco-line}` | Xpx |
| H3 | 左色条 / 无 | `{comp.heading.h3.left-bar}` | Xpx |
| H4 | uppercase + letter-spacing / 无 | `{comp.heading.h4.color}` | — |

### 5.2 表格

- **边框模式：** grid（全框） / mckinsey（仅头尾横线） / rb（头尾+行间线） / 无框
- **表头上下线颜色：** `{comp.table.border-header}`
- **行间分隔线颜色：** `{comp.table.border-row}`
- **强调线（rb 模式）：** `{comp.table.accent-line}`
- **表头：** 无背景 / 背景色 `#XXXXXX`；加粗；对齐方式
- **数据行：** 无底色 / 斑马纹（`{color.surface.section}`）
- **竖线：** 有 / 无

### 5.3 引用块 / Callout

- **左色条：** `{comp.blockquote.left-bar}`，Xpx；或 背景色块 / 无
- **文字色：** `{comp.blockquote.color}`
- **字体：** 衬线 / 无衬线；斜体 / 正体
- **字号：** 略大 / 略小 / 同正文

### 5.4 代码块

- **背景：** `{comp.code.bg}`；**左色条：** `{comp.code.left-bar}`，Xpx；**圆角：** Xpx
- **字体：** 等宽，Xpt
- **行内代码背景：** `{comp.code.bg}`；**文字色：** `{comp.heading.h1.color}`（或指定）

### 5.5 列表

- **无序列表符号：** • / ▸ / — / 自定义
- **有序列表样式：** 数字 / 字母 / 罗马数字
- **缩进：** Xem

### 5.6 分隔线

- **颜色：** `{comp.hr.color}`；**粗细：** Xpx；**样式：** solid / dashed

### 5.7 按钮（供 HTML / PPT 参考）

| 类型 | 背景色 | 文字色 | 边框 | Hover |
|------|--------|--------|------|-------|
| 主要 | `{comp.button.primary.bg}` | `{comp.button.primary.fg}` | 无 | `{color.interactive.hover}` |
| 次要 | 透明 | `{color.interactive.secondary}` | `{color.interactive.secondary}` | — |
| Ghost | 透明 | `{color.text.body}` | `{color.border.default}` | — |

### 5.8 标签 / 徽章

- **背景：** `{comp.tag.bg}`；**文字色：** `{comp.tag.fg}`；**圆角：** Xpx；**字号：** Xpt uppercase

### 5.9 卡片

- **背景：** `{color.surface.card}`；**边框：** `{color.border.default}` Xpx / 无；**阴影：** 有 / 无；**圆角：** Xpx

---

## 6. 视觉层级逻辑

- **层级数量：** 共使用 X 级标题
- **层级区分方式：** 字号差 / 字重差 / 颜色差 / 装饰差（勾选实际使用的）
- **最大层级视觉权重：** 字号 Xpt，字重 X，装饰线颜色 `{comp.heading.h1.deco-line}`
- **层级色彩策略：** 统一同色 / 逐级递浅 / H1H2 同色 H3 变色

---

## 7. 图像处理

- **图片风格：** 彩色写实 / 深色蒙版 / 黑白 / 插画风格
- **惯用宽高比：** 16:9 / 3:2 / 1:1 / 自由
- **深色蒙版：** 颜色 `{color.surface.dark}`，透明度 X%
- **图片叠文字时：** 白色文字（`{color.text.inverse}`）/ 黑色文字 / 渐变蒙版

---

## 8. 数据可视化 / 图表

- **图表配色顺序：** 见 2.2 DataViz（`color.dataviz.1` 到 `.5`）
- **图表背景：** 白色 / 透明 / `{color.surface.section}`
- **图表字体：** 同正文 / 专用
- **坐标轴 / 网格线颜色：** `{color.border.default}`
- **Mermaid 节点颜色映射：** 见 9 节推导指南

---

## 9. 各格式推导指南

> `/design-derive` skill 读取 **2.3 Component Tokens** 解析色值（顺着引用链向上查）。
> Primitive hex 是最终输出值，Semantic / Component 层只是引用路径。

### 解析引用链示例

```
comp.heading.h1.deco-line
  → {color.interactive.primary}
    → {<hue>-400}
      → #96F878   ← 最终写入 CSS / JSON 的值
```

---

### → DOCX（doc-forge style.json）

| JSON 字段 | 读取 Token | 备注 |
|-----------|-----------|------|
| `headings.h1.color` | `comp.heading.h1.color` → resolve | hex，去掉 # |
| `headings.h1.font_en` | 3.2 标题降级字体栈第一项 | |
| `body.font` / `body.font_en` | 3.2 正文降级字体栈 | |
| `table.border_mode` | 5.2 边框模式 | |
| `table.rule_color` | `comp.table.border-header` → resolve | |
| `table.accent_color` | `comp.table.accent-line` → resolve | rb 模式 |
| `table.row_sep_color` | `comp.table.border-row` → resolve | rb 模式 |
| `blockquote.color` | `comp.blockquote.color` → resolve | |
| `body.first_line_indent_chars` | 4.3 首行缩进 | |

### → PDF（doc-forge CSS）

| CSS 属性 | 读取 Token | 备注 |
|----------|-----------|------|
| `h1 border-bottom color` | `comp.heading.h1.deco-line` → resolve | **非文字色** |
| `h2 border-bottom color` | `comp.heading.h2.deco-line` → resolve | |
| `h3 border-left color` | `comp.heading.h3.left-bar` → resolve | |
| `blockquote border-left color` | `comp.blockquote.left-bar` → resolve | |
| `pre background` | `comp.code.bg` → resolve | |
| `pre border-left color` | `comp.code.left-bar` → resolve | |
| `body font-family` | 3.2 正文降级栈 | |
| `h1/h2 font-family` | 3.2 标题降级栈 | |

### → HTML（CSS 自定义属性）

```css
:root {
  /* Semantic 层直接导出为 CSS 变量 */
  --color-interactive:     /* color.interactive.primary → resolve */;
  --color-interactive-fg:  /* color.interactive.primary-fg → resolve */;
  --color-text-heading:    /* color.text.heading → resolve */;
  --color-text-body:       /* color.text.body → resolve */;
  --color-text-muted:      /* color.text.muted → resolve */;
  --color-text-link:       /* color.text.link → resolve */;
  --color-surface-page:    #FFFFFF;
  --color-surface-section: /* color.surface.section → resolve */;
  --color-surface-card:    /* color.surface.card → resolve */;
  --color-surface-dark:    /* color.surface.dark → resolve */;
  --color-border:          /* color.border.default → resolve */;
  --color-border-accent:   /* color.border.accent → resolve */;
  --font-heading:          "...";  /* 3.2 标题降级栈 */
  --font-body:             "...";  /* 3.2 正文降级栈 */
  --font-mono:             "...";  /* 3.2 等宽栈 */
  --space-unit:            8px;
}
```

### → Mermaid（图表配色）

```
%%{init: {"theme": "base", "themeVariables": {
  "primaryColor":        color.dataviz.1 → resolve,
  "primaryBorderColor":  color.dataviz.1 略深 10%,
  "secondaryColor":      color.dataviz.2 → resolve,
  "tertiaryColor":       color.dataviz.3 → resolve,
  "background":          color.surface.page → resolve,
  "clusterBkg":          color.surface.section → resolve,
  "titleColor":          color.text.heading → resolve,
  "lineColor":           color.border.default → resolve
}}}%%
```

- 深色节点（dataviz.1 若为深色）：`color:#fff`
- 浅色节点（dataviz.1 若为浅色）：`color:#000`
- 语义节点：`color.status.*` → resolve

### → PPT（演示文稿主题）

| 槽位 | 读取 Token |
|------|-----------|
| Color 1（深/文字） | `color.text.heading` → resolve |
| Color 2（浅/背景） | `color.surface.page` |
| Accent 1（主动作） | `color.interactive.primary` → resolve |
| Accent 2 | `color.dataviz.2` → resolve |
| Accent 3 | `color.dataviz.3` → resolve |
| Accent 4 | `color.surface.section` → resolve |
| 超链接 | `color.text.link` → resolve |

- **标题幻灯片：** `color.surface.dark` 背景 + `color.text.inverse` 文字 + `color.interactive.primary` 装饰线
- **内容幻灯片：** `color.surface.page` 背景 + `color.text.body` 正文 + `color.interactive.primary` 小面积点缀
