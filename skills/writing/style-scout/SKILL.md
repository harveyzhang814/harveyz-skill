---
name: style-scout
description: "Survey a brand's visual design style from their official website and output a structured design knowledge document. Trigger when the user wants to analyze a company's design style — e.g. 'analyze McKinsey style', 'survey BCG design', 'extract style from URL'. Outputs to knowledge/design/<brand>-style.md only. Use /design-derive to generate format-specific configs from the knowledge doc."
user_invocable: true
version: "2.1.0"
---

## 概述

给定一个公司官网 URL，调查其设计风格，输出 `knowledge/design/<brand>-style.md`。

**只做调查，不生成配置。** 配置生成由 `/design-derive` 负责。

调查分**两个阶段**：先全面调查主页（品牌色、导航、CTA 按钮、Hero 区域），再深入报告/文章正文页（排版、表格、引用块、代码块）。两阶段数据合并后写入知识文档。

输出文档遵循 `knowledge/design/TEMPLATE.md` 的完整结构，覆盖：色彩体系（三维分类）、字体体系、间距体系、组件规则、视觉层级、图像处理、数据可视化、各格式推导指南。

> **依赖：** 必须先通过 `/browse` skill 完成 browse 初始化。

---

## 执行步骤

### Step 1 — 确认目标

从对话上下文获取目标 URL 和品牌简称（用于文件命名）。若未提供，询问：

> 请提供官网 URL 和品牌简称（如 https://www.mckinsey.com，简称 mckinsey）

---

## 阶段一：主页调查（品牌色 + 全局风格）

### Step 2 — 加载主页并关闭弹窗

```bash
$B goto <URL>
$B screenshot /tmp/scout-homepage.png
```

用 Read 工具展示截图，确认页面加载正常。若有 cookie / newsletter 弹窗，先关闭：

```bash
$B snapshot -i
$B click @eN   # accept/close 按钮
```

---

### Step 3 — 主页：提取品牌动作色（CTA 按钮）

> 主页 Hero 区和导航栏是品牌动作色（CTA 按钮色）出现频率最高的地方，是装饰线颜色的首选来源。

```bash
$B js "
  const els = [...document.querySelectorAll('button,a,[class*=btn],[class*=cta],[class*=tag],[class*=badge],[class*=label],[class*=chip],[class*=hero] *,nav *')];
  const map = new Map();
  for (const el of els) {
    const bg = window.getComputedStyle(el).backgroundColor;
    if (!bg || bg==='rgba(0, 0, 0, 0)' || bg==='rgb(255, 255, 255)' || bg==='rgb(0, 0, 0)') continue;
    map.set(bg, (map.get(bg)||0)+1);
  }
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,10)
    .map(([c,n])=>toHex(c)+' x'+n+'  bg:'+c).join('\n')
"
```

同时记录导航栏背景色和 Hero 区域背景色：

```bash
$B js "
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  const nav = document.querySelector('nav,header,[class*=nav],[class*=header]');
  const hero = document.querySelector('[class*=hero],[class*=banner],[class*=jumbotron],[class*=masthead]');
  JSON.stringify({
    navBg: nav ? toHex(window.getComputedStyle(nav).backgroundColor) : 'not found',
    heroBg: hero ? toHex(window.getComputedStyle(hero).backgroundColor) : 'not found',
    navColor: nav ? toHex(window.getComputedStyle(nav).color) : 'not found',
  })
"
```

---

### Step 4 — 主页：提取背景色层级

```bash
$B js "
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  const map = new Map();
  for (const el of document.querySelectorAll('section,article,div,header,footer,nav,aside,main,pre,code,[class*=card],[class*=block],[class*=section]')) {
    const bg = window.getComputedStyle(el).backgroundColor;
    if (!bg || bg==='rgba(0, 0, 0, 0)' || bg==='rgb(255, 255, 255)' || bg==='rgb(0, 0, 0)') continue;
    map.set(toHex(bg), (map.get(toHex(bg))||0)+1);
  }
  [...map.entries()].sort((a,b)=>b[1]-a[1]).slice(0,12).map(([c,n])=>c+' x'+n).join('\n')
"
```

---

### Step 5 — 主页：CSS bundle 提取（捕捉未渲染颜色）

```bash
$B js "[...document.styleSheets].map(s=>s.href).filter(Boolean)"
$B download "<主CSS_URL>" /tmp/scout-bundle.css
grep -oE '#[0-9a-fA-F]{6}\b' /tmp/scout-bundle.css | tr '[:lower:]' '[:upper:]' | \
  sort | uniq -c | sort -rn | grep -vE '#(FFFFFF|000000)' | head -25
```

---

### Step 6 — 主页：截图存档

```bash
$B viewport 1280x900
$B js "window.scrollTo(0,0)"
$B screenshot /tmp/scout-home-top.png --clip 0,0,1280,700     # Hero + 导航区

$B js "window.scrollTo(0,700)"
$B screenshot /tmp/scout-home-mid.png --clip 0,0,1280,700     # 卡片 / CTA 区域
```

用 Read 工具展示两张截图，目测记录：
- 导航栏颜色和文字色
- Hero 区域主色调
- CTA 按钮颜色（这是动作色）
- 卡片样式（有无阴影、圆角、边框）

---

## 阶段二：报告正文页调查（排版 + 组件细节）

### Step 7 — 找到并进入报告正文页

从当前页面寻找报告/出版物入口（关键词：Reports / Publications / Insights / Research / Thinking / 研究报告 / 白皮书）：

```bash
$B snapshot -i
$B click @eN   # 报告入口链接
```

点击进入**有 HTML 正文的报告页**（非 PDF 下载）。判断标准：有标题 + 正文段落 + 至少一个复杂元素（图表、表格、引用块）。

```bash
# 关闭可能的弹窗
$B snapshot -i
$B click @eN   # 若有弹窗则关闭

$B screenshot /tmp/scout-report.png
```

用 Read 工具展示截图，记录当前报告页 URL。

---

### Step 8 — 报告页：提取完整色彩（三维分类）

**8a. 动作色（在报告页再次确认，补充文章内 CTA）**

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

**8b. 文字色（按元素语义，标注视觉近黑）**

```bash
$B js "
  const toHex = c => { const m=c.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/); return m?'#'+[m[1],m[2],m[3]].map(x=>parseInt(x).toString(16).padStart(2,'0')).join('').toUpperCase():c; };
  ['h1','h2','h3','h4','p','a','small'].map(tag => {
    const el = document.querySelector(tag); if(!el) return null;
    const s = window.getComputedStyle(el);
    const hex = toHex(s.color);
    const px = parseFloat(s.fontSize);
    const m = s.color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    const nearBlack = m ? (parseInt(m[1])+parseInt(m[2])+parseInt(m[3]) < 150) : false;
    return tag.padEnd(6)+hex+'  '+(nearBlack?'[视觉近黑]':'[有色]')+'  '+s.fontWeight+'w  '+(px*0.75).toFixed(0)+'pt';
  }).filter(Boolean).join('\n')
"
```

**8c. 装饰/线条色（仅有实际宽度的 border）**

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

---

### Step 9 — 报告页：提取字体体系

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

### Step 10 — 报告页：提取间距与版面参数

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

### Step 11 — 报告页：提取组件样式

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
      thBorderTop: window.getComputedStyle(th||t).borderTop,
      thBorderBottom: window.getComputedStyle(th||t).borderBottom,
      tdBorder: td ? window.getComputedStyle(td).border : 'N/A',
      tdBorderBottom: td ? window.getComputedStyle(td).borderBottom : 'N/A',
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
    JSON.stringify({ bg: toHex(s.backgroundColor), borderLeft: s.borderLeft, color: toHex(s.color), fontStyle: s.fontStyle, fontFamily: s.fontFamily.split(',')[0] })
  }
"
```

---

### Step 12 — 截图关键元素（报告页）

```bash
$B viewport 1280x900
$B js "window.scrollTo(0,0)"
$B screenshot /tmp/scout-report-top.png --clip 0,0,1280,600    # 报告标题区

$B js "window.scrollTo(0,800)"
$B screenshot /tmp/scout-report-body.png --clip 0,0,1280,600   # 正文段落区

# 表格（若有）
$B screenshot /tmp/scout-table.png --selector "table"

# 引用块（若有）
$B screenshot /tmp/scout-quote.png --selector "blockquote,[class*=callout],[class*=pull-quote]"
```

用 Read 工具逐一展示截图，**目测验证**：
- 标题文字色是否视觉近黑？
- 与主页截图对比，动作色是否一致？
- H3 是否有左色条装饰？
- 表格边框模式（全框 / 仅横线 / 带行分隔线）？

---

## 阶段三：整理与输出

### Step 13 — 合并两阶段数据，按三层 Token 模型写入知识文档

综合主页调查（Step 3–6）和报告页调查（Step 8–12）的结果，按 `knowledge/design/TEMPLATE.md` 的三层 Token 结构填写，写到 `knowledge/design/<brand>-style.md`。

**数据来源优先级：**

| Token 层 | 字段 | 优先来源 | 补充来源 |
|---------|------|---------|---------|
| 2.1 Primitive | 所有原始色值 | 主页 CSS bundle（Step 5）频率最高 | 报告页渲染层补充 |
| 2.2 Semantic：Interactive | 主 CTA 按钮色 | **主页 Hero/CTA 按钮**（Step 3） | 报告页（Step 8a）交叉确认 |
| 2.2 Semantic：Text | 文字色层级 | 报告页（Step 8b）语义最清晰 | — |
| 2.2 Semantic：Surface | 背景色层级 | 主页（Step 4）更丰富 | 报告页补充 |
| 2.2 Semantic：Border | 装饰/线条色 | 报告页（Step 8c） | — |
| 2.3 Component | 组件映射 | 参照 TEMPLATE.md 默认值 | 报告页截图目测覆盖 |
| 3 字体体系 | — | 报告页（Step 9） | 主页 CSS bundle 确认字体名 |
| 4 间距 | — | 报告页（Step 10） | — |
| 5 组件规则 | — | 报告页（Step 11） | — |

**填写规则（按层次）：**

**2.1 Primitive Tokens：**
- 将所有发现的原始色值整理为 `色相-明度` 命名格式
- 只写"是什么"，不写用途

**2.2 Semantic Tokens：**
- `color.interactive.primary`：**必须是主页 CTA 按钮色**，不能是文字色
- `color.text.*` 中标注 `[视觉近黑]`（RGB 三通道和 < 150）
- `color.border.accent` 指向 `{color.interactive.primary}`，无需填原始值

**2.3 Component Tokens：**
- 大多数保持 TEMPLATE.md 默认映射（指向 Interactive/Text/Border）
- 若目测截图与默认映射不符（如 H3 实际无左色条、blockquote 用背景块而非左色条），修改对应行
- 表格模式（grid/mckinsey/rb）在此层的 `comp.table.*` 中注明

**通用规则：**
- 未能从页面提取到的字段：填 `待补充` 而非空着
- 不在 2.3 Component 层以外重复写颜色规则（"装饰线用动作色"已硬编码在 Component Tokens）

写入后，**展示给用户确认**：

> `knowledge/design/<brand>-style.md` 已生成，请重点核查：
> 1. **2.1 Primitives** — 品牌调色盘是否完整？有无遗漏的特征色？
> 2. **2.2 Interactive** — `color.interactive.primary` 是否为主页最显眼的 CTA 按钮色？
> 3. **2.2 Text** — `[视觉近黑]` 标注是否准确？这些颜色是否确实在截图中接近黑色？
> 4. **2.3 Component** — 若有非默认映射（如 blockquote 颜色），是否已修改对应行？
>
> 确认后可运行 `/design-derive` 生成具体格式配置。

---

## 注意事项

- **不下载 PDF** — 只分析 HTML 页面
- **先关弹窗再截图** — cookie/newsletter 弹窗会遮挡内容，每次跳转后都要检查
- **CSS 变量站点** — bundle 色值稀少时，说明该站用 CSS 变量，用渲染层 API 补充
- **深色 ≠ 有色** — `[视觉近黑]` 颜色不适合做装饰线；选用动作色
- **主页 vs 报告页冲突** — 若两页的动作色不一致，以主页 Hero CTA 为准并在文档中注明
- **未找到的组件** — 表格/引用块在报告页没有时，可另找一篇或标记"待补充"
