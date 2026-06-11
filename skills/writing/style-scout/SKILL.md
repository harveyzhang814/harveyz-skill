---
name: style-scout
description: "Survey a brand's visual design style from their official website and output a structured design knowledge document. Trigger when the user wants to analyze a company's design style — e.g. 'analyze McKinsey style', 'survey BCG design', 'extract style from URL'. Outputs to knowledge/design/<brand>-style.md only. Use /design-derive to generate format-specific configs from the knowledge doc."
user_invocable: true
version: "2.0.0"
---

## 概述

给定一个公司官网 URL，调查其设计风格，输出 `knowledge/design/<brand>-style.md`。

**只做调查，不生成配置。** 配置生成由 `/design-derive` 负责。

输出文档遵循 `knowledge/design/TEMPLATE.md` 的完整结构，覆盖：色彩体系（三维分类）、字体体系、间距体系、组件规则、视觉层级、图像处理、数据可视化、各格式推导指南。

> **依赖：** 必须先通过 `/browse` skill 完成 browse 初始化。

---

## 执行步骤

### Step 1 — 确认目标

从对话上下文获取目标 URL 和品牌简称（用于文件命名）。若未提供，询问：

> 请提供官网 URL 和品牌简称（如 https://www.mckinsey.com，简称 mckinsey）

---

### Step 2 — 浏览首页，寻找报告入口

```bash
$B goto <URL>
$B screenshot /tmp/scout-homepage.png
```

用 Read 工具展示截图，确认页面加载。寻找报告/出版物入口（关键词：Reports / Publications / Insights / Research / Thinking / 研究报告 / 白皮书）：

```bash
$B snapshot -i
$B click @eN
```

---

### Step 3 — 进入具体报告正文页

点击进入**有 HTML 正文的报告页**（非 PDF 下载）。判断标准：有标题 + 正文段落 + 至少一张图或表格。

```bash
# 关闭 cookie 弹窗（若存在）
$B snapshot -i
$B click @eN   # accept/close 按钮

$B screenshot /tmp/scout-report.png
```

用 Read 工具展示截图，记录当前 URL。

---

### Step 4 — 提取色彩（三维分类）

**4a. 品牌动作色（最重要，装饰线首选）**

```bash
$B js "
  const els = [...document.querySelectorAll('button,a,[class*=btn],[class*=cta],[class*=tag],[class*=badge],[class*=label],[class*=chip]')];
  const map = new Map();
  for (const el of els) {
    const bg = window.getComputedStyle(el).backgroundColor;
    if (!bg || bg==='rgba(0, 0, 0, 0)' || bg==='rgb(255, 255, 255)' || bg==='rgb(0, 0, 0)') continue;
    map.set(bg, (map.get(bg)||0)+1);
  }
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,8)
    .map(([c,n])=>toHex(c)+' x'+n+'  bg:'+c).join('\n')
"
```

**4b. 文字色（按元素语义）**

```bash
$B js "
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  ['h1','h2','h3','h4','p','a','small'].map(tag => {
    const el = document.querySelector(tag); if(!el) return null;
    const s = window.getComputedStyle(el);
    const hex = toHex(s.color);
    const px = parseFloat(s.fontSize);
    // 判断是否视觉近黑（R+G+B < 150）
    const m = s.color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    const nearBlack = m ? (parseInt(m[1])+parseInt(m[2])+parseInt(m[3]) < 150) : false;
    return tag.padEnd(6)+hex+'  '+(nearBlack?'[视觉近黑]':'[有色]')+'  '+s.fontWeight+'w  '+(px*0.75).toFixed(0)+'pt';
  }).filter(Boolean).join('\n')
"
```

**4c. 装饰/线条色（仅有实际宽度的 border）**

```bash
$B js "
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  const map = new Map();
  for (const el of document.querySelectorAll('*')) {
    const s = window.getComputedStyle(el);
    for (const side of ['Left','Bottom','Top','Right']) {
      const w = parseFloat(s['border'+side+'Width']||0);
      const c = s['border'+side+'Color'];
      if (w < 0.5 || !c || c==='rgba(0, 0, 0, 0)' || c==='rgb(255, 255, 255)' || c==='rgb(0, 0, 0)') continue;
      const key = toHex(c)+'|'+side.toLowerCase();
      map.set(key, (map.get(key)||0)+1);
    }
  }
  [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10)
    .map(([k,n])=>k.split('|')[0].padEnd(10)+'side:'+k.split('|')[1].padEnd(8)+'x'+n).join('\n')
"
```

**4d. 背景色层级**

```bash
$B js "
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  const map = new Map();
  for (const el of document.querySelectorAll('section,article,div,header,footer,nav,aside,main,pre,code,[class*=card],[class*=block],[class*=section]')) {
    const bg = window.getComputedStyle(el).backgroundColor;
    if (!bg || bg==='rgba(0, 0, 0, 0)' || bg==='rgb(255, 255, 255)' || bg==='rgb(0, 0, 0)') continue;
    map.set(toHex(bg), (map.get(toHex(bg))||0)+1);
  }
  [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10).map(([c,n])=>c+' x'+n).join('\n')
"
```

**4e. CSS bundle 补充（捕捉未渲染颜色）**

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
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  const tags = ['h1','h2','h3','h4','p','a','code','pre','small','blockquote'];
  tags.map(tag => {
    const el = document.querySelector(tag); if(!el) return null;
    const s = window.getComputedStyle(el);
    const px = parseFloat(s.fontSize);
    const lh = parseFloat(s.lineHeight);
    return [
      tag.padEnd(12),
      s.fontFamily.split(',')[0].replace(/[\"']/g,'').trim().padEnd(28),
      (px*0.75).toFixed(1)+'pt'.padEnd(8),
      'w:'+s.fontWeight.padEnd(6),
      'lh:'+(lh/px).toFixed(2),
      toHex(s.color)
    ].join('  ');
  }).filter(Boolean).join('\n')
"
```

---

### Step 6 — 提取间距与版面参数

```bash
$B js "
  const body = document.body;
  const s = window.getComputedStyle(body);
  const main = document.querySelector('main, article, [class*=content], [class*=body]');
  const ms = main ? window.getComputedStyle(main) : null;
  JSON.stringify({
    bodyMaxWidth: s.maxWidth,
    bodyPadding: s.padding,
    mainMaxWidth: ms?.maxWidth,
    mainPadding: ms?.padding,
    h1MarginBottom: window.getComputedStyle(document.querySelector('h1')||body).marginBottom,
    h2MarginTop: window.getComputedStyle(document.querySelector('h2')||body).marginTop,
    pMarginBottom: window.getComputedStyle(document.querySelector('p')||body).marginBottom,
    lineHeight: s.lineHeight,
  }, null, 2)
"
```

---

### Step 7 — 提取组件样式

**表格（若有）：**

```bash
$B js "
  const t = document.querySelector('table');
  if (!t) { 'no table found'; } else {
    const th = t.querySelector('th');
    const td = t.querySelector('td');
    const s = window.getComputedStyle(th||t);
    const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
    JSON.stringify({
      thBg: toHex(s.backgroundColor), thColor: toHex(s.color), thFontWeight: s.fontWeight,
      thBorderBottom: window.getComputedStyle(th||t).borderBottom,
      tdBorder: td ? window.getComputedStyle(td).border : 'N/A',
    })
  }
"
```

**引用块（若有）：**

```bash
$B js "
  const bq = document.querySelector('blockquote,[class*=quote],[class*=callout],[class*=pullquote]');
  if (!bq) { 'no blockquote found'; } else {
    const s = window.getComputedStyle(bq);
    const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
    JSON.stringify({ bg: toHex(s.backgroundColor), borderLeft: s.borderLeft, color: toHex(s.color), fontStyle: s.fontStyle })
  }
"
```

---

### Step 8 — 截图关键元素

```bash
$B viewport 1280x900
$B js "window.scrollTo(0,0)"
$B screenshot /tmp/scout-top.png --clip 0,0,1280,600    # 标题区

$B js "window.scrollTo(0,800)"
$B screenshot /tmp/scout-body.png --clip 0,0,1280,600   # 正文段落

# 表格（若有）
$B screenshot /tmp/scout-table.png --selector "table"

# 引用块（若有）
$B screenshot /tmp/scout-quote.png --selector "blockquote,[class*=callout],[class*=pull-quote]"
```

用 Read 工具逐一展示截图，**目测验证**：
- 标题文字色是否视觉近黑？
- 品牌动作色（按钮色）是否清晰可识别？
- 装饰线颜色？
- 表格边框模式？

---

### Step 9 — 整理并写入知识文档

读取 `knowledge/design/TEMPLATE.md` 的结构，将调查数据填入，写到 `knowledge/design/<brand>-style.md`。

**填写规则：**
- 第 2.2 节"品牌动作色"：填 Step 4a 的结果
- 第 2.3 节"文字色"：填 Step 4b，并标注"[视觉近黑]"
- 第 9 节"推导指南"的 PDF 装饰线颜色：**必须来自 2.2 动作色，不能用 2.3 近黑文字色**
- 未能从页面提取到的字段：填 `待补充` 而非空着

写入后，**展示给用户确认**：

> `knowledge/design/<brand>-style.md` 已生成，请重点核查：
> 1. **2.2 品牌动作色** — 这是文档装饰线的颜色，是否为最具识别性的品牌颜色？
> 2. **2.3 文字色** — 标注为 [视觉近黑] 的颜色在截图中是否确实接近黑色？
> 3. **9. 推导指南** — 各格式的装饰线颜色是否都来自动作色而非文字色？
>
> 确认后可运行 `/design-derive` 生成具体格式配置。

---

## 注意事项

- **不下载 PDF** — 只分析 HTML 页面
- **先关弹窗再截图** — cookie/newsletter 弹窗会遮挡内容
- **CSS 变量站点** — bundle 色值稀少时，说明该站用 CSS 变量，用渲染层 API 补充
- **深色 ≠ 有色** — `[视觉近黑]` 颜色不适合做装饰线；选用动作色
- **未找到的组件** — 表格/引用块在报告页没有时，可另找一篇或标记"待补充"
