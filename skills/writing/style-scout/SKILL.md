---
name: style-scout
description: "Survey a brand's visual design style from their official website and derive doc-forge style configs. Trigger when the user wants to analyze a company's design style, extract brand colors/fonts, or generate document style configs based on a real website — e.g. 'analyze McKinsey style', 'survey BCG design', 'extract style from URL'."
user_invocable: true
version: "1.1.0"
---

## 概述

给定一个公司官网 URL，分两个阶段执行：

**阶段一（调查）：** 浏览报告页面，提取色彩体系、字体、排版规则，输出 `knowledge/design/<brand>-style.md` 品牌设计文档，等待用户确认。

**阶段二（推导）：** 用户确认知识文档后，从中推导 `doc-forge` 样式配置（`<brand>-style.json` + `<brand>.css`）。

> **依赖：** 必须先通过 `/browse` skill 完成 browse 初始化。

---

## 阶段一：调查品牌设计

### Step 1 — 确认目标 URL

从对话上下文获取目标 URL。若未提供，询问：

> 请提供要分析的公司官网 URL（如 https://www.mckinsey.com）

---

### Step 2 — 浏览首页，寻找报告入口

```bash
$B goto <URL>
$B screenshot /tmp/scout-homepage.png
```

用 Read 工具展示截图。然后寻找报告/出版物入口（关键词：Reports / Publications / Insights / Research / Knowledge / Thinking / 研究报告 / 白皮书）：

```bash
$B snapshot -i
$B click @eN   # 点击找到的入口链接
```

---

### Step 3 — 进入具体报告正文页

在报告列表页，点击进入**有 HTML 正文的报告页**（非 PDF 下载）。

判断标准：页面有标题 + 正文段落 + 至少一张图或表格。

```bash
$B screenshot /tmp/scout-report-page.png
```

用 Read 工具展示截图，记录当前 URL。

---

### Step 4 — 提取色彩体系（三维分类）

色彩必须按**用途角色**分类，不能只按频次排序。三个维度：

| 维度 | 定义 | 提取方法 |
|------|------|---------|
| **品牌动作色** | CTA 按钮、hover 状态、标签徽章的背景色 | 查找 `button`, `a[class*=btn]`, `[class*=cta]` 的 `backgroundColor` |
| **文字色** | 标题、正文、辅助文字的 `color` | 查 h1/h2/h3/p 的 computed `color` |
| **装饰/线条色** | 下划线、左色条、分隔线、边框 | 查 `borderLeftColor`, `borderBottomColor`, `borderTopColor` |

> **关键认知：装饰线的颜色决定文档的品牌感知，而非标题文字色。**
> 深色标题（如 BCG `#0C2B15`）在文档里视觉上近黑，品牌色必须出现在线条/色条上才能被感知。
> 品牌动作色（CTA 按钮色）往往是装饰线的最佳候选。

**4a. 提取品牌动作色（最重要）：**

```bash
$B js "
  const actionEls = [...document.querySelectorAll('button, a, [class*=btn], [class*=cta], [class*=tag], [class*=badge], [class*=label]')];
  const map = new Map();
  for (const el of actionEls) {
    const bg = window.getComputedStyle(el).backgroundColor;
    if (!bg || bg === 'rgba(0, 0, 0, 0)' || bg === 'rgb(255, 255, 255)') continue;
    map.set(bg, (map.get(bg)||0) + 1);
  }
  [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,8).map(([c,n]) => {
    const m = c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    const hex = m ? '#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase() : c;
    return hex + ' x' + n;
  }).join('\n')
"
```

**4b. 提取文字色（按元素语义）：**

```bash
$B js "
  const tags = {h1:null, h2:null, h3:null, p:null, a:null};
  for (const tag of Object.keys(tags)) {
    const el = document.querySelector(tag);
    if (!el) continue;
    const s = window.getComputedStyle(el);
    const px = parseFloat(s.fontSize);
    tags[tag] = {
      color: s.color,
      hex: (()=>{ const m=s.color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():s.color; })(),
      font: s.fontFamily.split(',')[0].replace(/[\"']/g,'').trim(),
      size: (px*0.75).toFixed(1)+'pt',
      weight: s.fontWeight,
    };
  }
  JSON.stringify(tags, null, 2)
"
```

**4c. 提取装饰/线条色：**

```bash
$B js "
  const map = new Map();
  const all = [...document.querySelectorAll('*')];
  for (const el of all) {
    const s = window.getComputedStyle(el);
    for (const prop of ['borderLeftColor','borderBottomColor','borderTopColor','outlineColor']) {
      const v = s[prop];
      const w = parseFloat(s[prop.replace('Color','Width')] || '0');
      if (!v || v==='rgba(0, 0, 0, 0)' || v==='rgb(0,0,0)' || v==='rgb(255,255,255)' || w < 0.5) continue;
      map.set(v, (map.get(v)||0) + 1);
    }
  }
  [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10).map(([c,n]) => {
    const m = c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    const hex = m ? '#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase() : c;
    return hex + ' x' + n;
  }).join('\n')
"
```

**4d. 从 CSS bundle 补充（捕捉未渲染状态的色值）：**

```bash
$B js "[...document.styleSheets].map(s=>s.href).filter(Boolean)"
$B download "<主CSS_URL>" /tmp/scout-bundle.css
grep -oE '#[0-9a-fA-F]{6}\b' /tmp/scout-bundle.css | tr '[:lower:]' '[:upper:]' | \
  sort | uniq -c | sort -rn | grep -vE '#(FFFFFF|000000)' | head -20
```

---

### Step 5 — 提取字体体系

```bash
$B js "
  const els = {
    h1: document.querySelector('h1'),
    h2: document.querySelector('h2'),
    h3: document.querySelector('h3'),
    body: document.body,
    p: document.querySelector('p'),
    code: document.querySelector('code, pre'),
  };
  Object.entries(els).filter(([,el])=>el).map(([name,el]) => {
    const s = window.getComputedStyle(el);
    const px = parseFloat(s.fontSize);
    const pt = (px*0.75).toFixed(1);
    return name.padEnd(6) + s.fontFamily.split(',')[0].replace(/[\"']/g,'').trim().padEnd(30) + pt+'pt  w:'+s.fontWeight;
  }).join('\n')
"
```

---

### Step 6 — 截图关键元素

```bash
$B viewport 1280x900
# 关闭 cookie 弹窗（若存在）
$B snapshot -i   # 找到 accept/close 按钮
$B click @eN     # 关闭

# 截图标题区
$B screenshot /tmp/scout-heading.png --clip 0,0,1280,500

# 截图正文段落（含小标题）
$B js "window.scrollTo(0, 600)"
$B screenshot /tmp/scout-body.png --clip 0,0,1280,500

# 截图表格（若有）
$B screenshot /tmp/scout-table.png --selector "table"

# 截图引用块（若有）
$B screenshot /tmp/scout-quote.png --selector "blockquote, [class*=callout], [class*=pull-quote]"
```

用 Read 工具逐一展示给用户。

---

### Step 7 — 输出品牌设计知识文档

将以上调查结果整理，**直接写入** `knowledge/design/<brand>-style.md`，格式如下：

```markdown
# <公司名> 品牌设计标准

> 本文件由 `/style-scout` 自动分析 <domain> 报告页面生成。
> 来源：<报告页 URL>

---

## 1. 品牌概述

（3–5 句话描述整体设计气质：颜色基调、字体风格、装饰风格、设计关键词）

---

## 2. 色彩体系

### 2.1 品牌动作色（装饰线首选）

> 这些颜色出现在按钮、CTA、标签等"品牌动作"元素上，是文档装饰线（H1 下划线、H3 左色条）的首选色。

| 角色 | 色值 | 来源元素 |
|------|------|---------|
| 主动作色 | `#XXXXXX` | button/CTA 背景 |
| 次动作色 | `#XXXXXX` | tag/badge 背景 |

### 2.2 文字色

> 标题和正文的 color 值。注意：深色标题色（如深墨绿、深海军蓝）在文档中视觉上接近黑色，
> 不能作为品牌识别色，须结合 2.1 的动作色使用。

| 元素 | 色值 | 备注 |
|------|------|------|
| H1/H2 标题 | `#XXXXXX` | （是否视觉可见为"有色"？） |
| H3/H4 | `#XXXXXX` | |
| 正文 | `#XXXXXX` | |
| 辅助/meta | `#XXXXXX` | |
| 链接 | `#XXXXXX` | |

### 2.3 装饰/线条色

| 用途 | 色值 | 位置 |
|------|------|------|
| 主分隔线 | `#XXXXXX` | 标题下方 / 行间 |
| 辅助分隔线 | `#XXXXXX` | 表格行间 |
| 左色条 | `#XXXXXX` | blockquote / H3 |

### 2.4 背景色

| 用途 | 色值 |
|------|------|
| 页面背景 | `#FFFFFF` |
| 分区背景 | `#XXXXXX` |
| 卡片/深色背景 | `#XXXXXX` |
| 代码块背景 | `#XXXXXX` |

---

## 3. 字体体系

### 3.1 官方字体（专有，需授权）

| 场景 | 字体名 | 说明 |
|------|--------|------|
| 标题 | `<font-name>` | 衬线/无衬线，字重 |
| 正文 | `<font-name>` | |

### 3.2 降级字体栈

**标题：** `"<fallback>", ..., serif/sans-serif`
**正文：** `"PingFang SC", "Helvetica Neue", "Arial", "STHeiti", sans-serif`

### 3.3 字号体系

| 元素 | 字号 | 字重 | 颜色 |
|------|------|------|------|
| H1 | Xpt | 300/400/700 | `#XXXXXX` |
| H2 | Xpt | | |
| H3 | Xpt | | |
| 正文 | Xpt | 400 | |

---

## 4. 组件规则

### 4.1 标题装饰

| 级别 | 装饰 | 颜色 |
|------|------|------|
| H1 | 下划线 / 左色条 / 无 | `#XXXXXX`（来自 2.1 动作色） |
| H2 | | |
| H3 | | |

### 4.2 表格

- 边框模式：grid / 水平线(mckinsey) / 水平线+行间线(rb) / 无
- 表头背景：有（`#XXXXXX`）/ 无
- 斑马纹：有 / 无

### 4.3 引用块

- 装饰：左色条（`#XXXXXX`）/ 背景色块 / 无
- 字体：衬线 / 无衬线，斜体 / 正体

### 4.4 代码块

- 背景：`#XXXXXX`，左色条：`#XXXXXX`

---

## 5. 格式推导指南

### → DOCX（`<brand>-style.json`）

- 标题文字色：`<2.2 的标题色 hex，去掉 #>`
- H1/H2 装饰线（在代码里不直接支持，用颜色参考）
- 表格 border_mode：`<grid/mckinsey/rb>`，rule_color：`<hex>`
- 正文无/有首行缩进

### → PDF（`<brand>.css`）

- H1 `border-bottom: Xpx solid <2.1 动作色>`（用动作色，不用文字色）
- H2 `border-bottom: Xpx solid <2.1 动作色>`
- H3 `border-left: Xpx solid <2.1 动作色>`
- blockquote `border-left: <2.1 动作色 或 2.3 装饰色>`
- pre 背景：`<2.4 代码块背景>`，左色条：`<2.1 动作色>`
```

将文件保存后，**展示给用户确认**，询问：

> `knowledge/design/<brand>-style.md` 已生成，请确认色彩分类是否准确，特别是：
> 1. 品牌动作色（2.1）是否为品牌最具识别性的颜色？
> 2. 深色文字色（2.2）是否在截图中看起来接近黑色？
> 3. 如有疑问，我可以返回网页继续截图验证。
>
> 确认后进入阶段二，生成 doc-forge 配置。

**STOP — 等待用户确认后再执行阶段二。**

---

## 阶段二：推导 doc-forge 配置

### Step 8 — 从知识文档推导配置

读取 `knowledge/design/<brand>-style.md` 的第 5 节"格式推导指南"，生成：

**`skills/writing/doc-forge/assets/<brand>-style.json`**（DOCX）：

```json
{
  "_source": "<报告页 URL>",
  "_comment": "<公司名> brand style. Fonts: <官方字体> → fallback to <降级字体>.",
  "page": { "top_cm": 2.54, "bottom_cm": 2.54, "left_cm": 3.17, "right_cm": 3.17 },
  "body": {
    "font": "PingFang SC", "font_en": "<降级英文字体>",
    "size_pt": <正文字号>, "line_spacing_pt": 22,
    "space_before_pt": 0, "space_after_pt": 7,
    "first_line_indent_chars": <0 或 2>
  },
  "headings": {
    "h1": { "font": "PingFang SC", "font_en": "<标题降级字体>", "size_pt": <字号>, "bold": <true/false>, "color": "<标题文字色>", "align": "left", "space_before_pt": 24, "space_after_pt": 14 },
    "h2": { ... },
    "h3": { ... },
    "h4": { "font": "PingFang SC", "font_en": "<字体>", "size_pt": <字号>, "bold": true, "color": "<辅助色>", "align": "left", "space_before_pt": 10, "space_after_pt": 4 }
  },
  "code_block": { "font": "Courier New", "size_pt": 10, "bg_color": null },
  "blockquote": { "font": "PingFang SC", "font_en": "<字体>", "size_pt": 11, "color": "<文字色>", "left_indent_cm": 1.0 },
  "table": {
    "font": "PingFang SC", "font_en": "<字体>", "size_pt": 11,
    "header_bold": true, "header_bg_color": <null 或 "色值">,
    "border_mode": "<grid/mckinsey/rb>",
    "rule_color": "<表格线颜色>",
    "accent_color": "<动作色>",
    "row_sep_color": "<行间线色>",
    "cell_padding_pt": 4, "space_before_pt": 8, "space_after_pt": 8
  }
}
```

**`skills/writing/doc-forge/assets/<brand>.css`**（PDF）：

完整 CSS，**装饰线颜色必须来自知识文档 2.1 品牌动作色**，而非 2.2 文字色。结构参考 `skills/writing/doc-forge/assets/rb.css`。

---

### Step 9 — 生成测试样本并提交

```bash
python3 skills/writing/doc-forge/scripts/md_to_pdf.py \
  skills/writing/doc-forge/tests/fixtures/full-test.md \
  skills/writing/doc-forge/tests/fixtures/full-test-<brand>.pdf \
  --style skills/writing/doc-forge/assets/<brand>.css

python3 skills/writing/doc-forge/scripts/md_to_docx.py \
  skills/writing/doc-forge/tests/fixtures/full-test.md \
  skills/writing/doc-forge/tests/fixtures/full-test-<brand>.docx \
  --style skills/writing/doc-forge/assets/<brand>-style.json
```

打开 PDF 供用户预览，然后提交 commit（包含知识文档 + 配置文件）。

---

## 注意事项

- **不要下载 PDF** — 只分析 HTML 报告页
- **cookie 弹窗** — 先 `$B snapshot -i` 找到 accept 按钮并点击，再截图
- **字体回退** — 专有字体（如 `henderson-bcg-serif`、`RBDesign`）不可在 doc-forge 使用，记录后降级
- **色值去噪** — 忽略 `#fff`、`#000`、`rgba(0,0,0,0)`，聚焦品牌特征色
- **深色 ≠ 有色** — 深墨绿/深海军蓝在文档里视觉接近黑色，不能作为装饰线颜色；选用动作色（按钮色）
- **CSS 变量** — 如 bundle 色值稀少，说明该站用 CSS 变量，需用渲染层 API 补充
- **表格边框模式判断**：
  - 有竖线 → `grid`
  - 仅头尾横线 → `mckinsey`
  - 头尾横线 + 行间细线 → `rb`
  - 无线 → `grid`（用浅色 border_color）
