---
name: style-scout
description: "Survey a brand's visual design style from their official website and derive doc-forge style configs. Trigger when the user wants to analyze a company's design style, extract brand colors/fonts, or generate document style configs based on a real website — e.g. 'analyze McKinsey style', 'survey BCG design', 'extract style from URL'."
user_invocable: true
version: "1.0.0"
---

## 概述

给定一个公司官网 URL，自动：
1. 浏览官网找到具体的报告/研究报告页面
2. 提取色值、字体、排版规则
3. 截图记录关键设计元素
4. 输出结构化品牌分析 + 可直接使用的 doc-forge 样式草稿

> **依赖：** 必须先调用 `/browse` skill 完成 browse 初始化，再执行本 skill 步骤。

---

## 执行步骤

### Step 1 — 确认目标 URL

从对话上下文获取目标 URL。若用户未提供，询问：

> 请提供要分析的公司官网 URL（如 https://www.mckinsey.com）

---

### Step 2 — 浏览首页，寻找报告入口

```bash
$B goto <URL>
$B screenshot /tmp/scout-homepage.png
```

用 Read 工具展示截图给用户，确认页面已加载。

然后在页面中寻找报告/出版物入口，优先查找以下导航链接（关键词匹配，不区分大小写）：

```
Reports / Publications / Insights / Research / Knowledge / Thinking /
思路洞见 / 研究报告 / 白皮书 / 出版物
```

```bash
$B snapshot -i
# 找到对应链接后点击
$B click @eN
```

---

### Step 3 — 进入具体报告页面

在报告列表页，点击进入**一篇具体报告的正文页面**（非 PDF 下载，要找有 HTML 正文的页面）。

判断标准：页面有标题 + 正文段落 + 至少一张图或一个表格。

```bash
$B screenshot /tmp/scout-report-page.png
```

用 Read 工具展示截图。记录当前页面 URL 备用。

---

### Step 4 — 提取色值

**4a. 从 CSS bundle 提取高频色值：**

```bash
# 找到所有外链 CSS
$B js "[...document.styleSheets].map(s=>s.href).filter(Boolean)"

# 下载主 CSS bundle（选文件名含 bundle/main/app 的那个）
$B download "<CSS_URL>" /tmp/scout-bundle.css

# 提取高频 hex 色值（前 30 名）
grep -oE '#[0-9a-fA-F]{3,6}' /tmp/scout-bundle.css | \
  awk '{print toupper($0)}' | sort | uniq -c | sort -rn | head -30
```

**4b. 从渲染页面提取实际用色（弥补 CSS 变量无法静态解析的情况）：**

```bash
$B js "
  const els = document.querySelectorAll('h1,h2,h3,p,table,blockquote,a,pre,code');
  const map = new Map();
  for (const el of els) {
    const s = window.getComputedStyle(el);
    for (const prop of ['color','backgroundColor','borderLeftColor','borderBottomColor']) {
      const v = s[prop];
      if (v && !v.includes('rgba(0, 0, 0, 0)')) map.set(v, (map.get(v)||0)+1);
    }
  }
  [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,20)
    .map(([c,n])=>c+' x'+n).join('\n')
"
```

---

### Step 5 — 提取字体

```bash
$B js "
  const tags = ['body','h1','h2','h3','p','table','code','blockquote'];
  const result = {};
  for (const tag of tags) {
    const el = document.querySelector(tag);
    if (!el) continue;
    const s = window.getComputedStyle(el);
    result[tag] = {
      fontFamily: s.fontFamily.split(',')[0].trim().replace(/[\"']/g,''),
      fontSize: s.fontSize,
      fontWeight: s.fontWeight,
      color: s.color,
      lineHeight: s.lineHeight
    };
  }
  JSON.stringify(result, null, 2)
"
```

---

### Step 6 — 截图关键设计元素

分别截图以下元素（存在则截，不存在跳过）：

```bash
# 标题区域
$B screenshot /tmp/scout-heading.png --selector "h1, h2, .headline, .title"

# 表格（若有）
$B screenshot /tmp/scout-table.png --selector "table"

# 引用块或 callout（若有）
$B screenshot /tmp/scout-quote.png --selector "blockquote, .callout, .highlight, .pull-quote"
```

用 Read 工具逐一展示给用户。

---

### Step 7 — 分析并输出品牌风格报告

根据收集到的数据，按以下结构输出分析报告：

```markdown
## 品牌风格分析：<公司名>

**来源页面：** <报告页 URL>

### 色彩体系

| 角色 | 色值 | 来源 |
|------|------|------|
| 主色 / 标题色 | `#XXXXXX` | h1 color |
| 强调色 1 | `#XXXXXX` | 高频 CSS 色 |
| 强调色 2 | `#XXXXXX` | 高频 CSS 色 |
| 背景色 | `#XXXXXX` | body backgroundColor |
| 正文色 | `#XXXXXX` | p color |
| 链接色 | `#XXXXXX` | a color |
| 分隔线 / 装饰线 | `#XXXXXX` | border 色 |

### 字体体系

| 元素 | 字体 | 字号 | 字重 |
|------|------|------|------|
| 正文 | ... | ...pt | 400 |
| H1 | ... | ...pt | 700 |
| H2 | ... | ...pt | 700 |
| 代码 | ... | ...pt | 400 |

### 表格风格

- 边框模式：[ grid / 水平线 / 无边框 ]
- 表头背景：有 / 无，色值 `#XXXXXX`
- 斑马纹：有 / 无

### 标题装饰

- H1：[ 下划线 / 左色条 / 背景色块 / 无装饰 ]
- H2：[ 同上 ]
- H3：[ 同上 ]

### 引用块风格

- 左色条 / 背景色块 / 斜体 / 无特殊处理

### 设计关键词

（3–5 个词概括整体气质，如：保守专业、现代简洁、大胆对比）
```

---

### Step 8 — 生成 doc-forge 样式草稿

根据 Step 7 的分析，直接生成两个配置草稿：

**`<brand>-style.json`（DOCX 用）：**

```json
{
  "_source": "<报告页 URL>",
  "page": { "top_cm": 2.54, "bottom_cm": 2.54, "left_cm": 3.17, "right_cm": 3.17 },
  "body": {
    "font": "<中文字体>", "font_en": "<英文字体>",
    "size_pt": <正文字号>, "line_spacing_pt": 22,
    "space_before_pt": 0, "space_after_pt": 6,
    "first_line_indent_chars": <0 或 2>
  },
  "headings": {
    "h1": { "font": "<字体>", "font_en": "<英文字体>", "size_pt": <字号>, "bold": true, "color": "<XXXXXX>", "align": "<left/center>", "space_before_pt": 24, "space_after_pt": 12 },
    "h2": { ... },
    "h3": { ... },
    "h4": { ... }
  },
  "code_block": { "font": "Courier New", "size_pt": 10, "bg_color": null },
  "blockquote": { "font": "<字体>", "font_en": "<英文字体>", "size_pt": 11, "color": "<XXXXXX>", "left_indent_cm": 1.0 },
  "table": {
    "font": "<字体>", "font_en": "<英文字体>", "size_pt": 11,
    "header_bold": true, "header_bg_color": <null 或 "XXXXXX">,
    "border_mode": "<grid/mckinsey/rb>",
    "rule_color": "<XXXXXX>",
    "accent_color": "<XXXXXX>",
    "row_sep_color": "<XXXXXX>",
    "cell_padding_pt": 4, "space_before_pt": 8, "space_after_pt": 8
  }
}
```

**`<brand>.css`（PDF 用）：**

基于分析结果，输出完整 CSS，结构参考 `skills/writing/doc-forge/assets/rb.css`，各选择器颜色替换为分析所得色值。

---

### Step 9 — 确认并保存

询问用户：

> 以上草稿是否需要调整？确认后我可以将两个文件保存到：
> - `skills/writing/doc-forge/assets/<brand>-style.json`
> - `skills/writing/doc-forge/assets/<brand>.css`
> - 并在 `knowledge/design/<brand>-style.md` 记录品牌分析

用户确认后保存文件并提交 commit。

---

## 注意事项

- **不要下载 PDF** — 只分析 HTML 报告页，PDF 无法提取 CSS
- **CSS bundle 色值 vs 渲染色值**：两者互补，CSS bundle 给频率，渲染 API 给实际语义
- **字体回退**：官方专有字体（如 RBDesign）无法在 doc-forge 使用，记录后自动降级到 Helvetica/PingFang SC
- **色值去噪**：忽略 `#fff`、`#000`、`rgba(0,0,0,0)` 等基础色，聚焦品牌特征色
- **表格边框模式判断**：
  - 有竖线 → `grid`
  - 仅横线（麦肯锡风格，只头尾） → `mckinsey`
  - 横线 + 行间细线 → `rb`
  - 无线 → `grid`（用浅色 border_color）
