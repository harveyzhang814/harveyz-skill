---
name: article-fetcher
description: "Use for the fetch-URL → translate → save-to-Obsidian workflow. Trigger whenever a user has a web URL (article, blog post, tweet, newsletter) and wants it fetched, translated into Chinese, and saved locally — even if they say it obliquely (e.g. \"存到 obsidian\", \"抓取\", \"save this\", \"translate and archive\"). Handles single URLs and batch lists, and X.com / Twitter (Playwright + Chrome Profile). Skip only if: no URL is present (user pasting raw text to translate), user wants a summary without archiving, or user is asking about a site's tech stack without wanting to save anything."
---

# Article Fetcher

## 核心设计：两步分离

**第一步（Subagent 1）**：抓取文章 + 下载图片 → 保存原文到 Origin
**第二步（Subagent 2）**：读取 Origin → 翻译 → 保存译文到 Article

两步由主 session 串联：Subagent 1 完成后，再派发 Subagent 2。

> 分离原因：翻译是 LLM 密集型任务，容易超时；抓取是 I/O 密集型任务，速度稳定。分开后各自超时独立，互不影响。

---

## 路径变量

```
Base:     {{VAULT_PATH}}
Origin:   {{VAULT_PATH}}/Origin
Article:  {{VAULT_PATH}}
Image:    {{VAULT_PATH}}/Image
SkillDir: {{SKILL_DIR}}
```

---

## URL 去重索引（SQLite）

**数据库路径：** `{{SKILL_DIR}}/scripts/url-index.db`

**表结构：**

```sql
CREATE TABLE url_index (
    url          TEXT PRIMARY KEY,
    title        TEXT,
    fetched_at   TEXT,
    issues       TEXT,
    category     TEXT,
    origin_path  TEXT,
    article_path TEXT
);
```

---

## 单篇抓取流程（主 session 执行）

当收到 1 个 URL 抓取任务时，主 session 执行以下流程：

### 步骤 1：派发 Subagent 1（抓取 + 保存原文）

```bash
sessions_spawn \
  --task "【Subagent 1 - 抓取】抓取文章并保存原文。

URL: <URL>

执行步骤：
1. 查 SQLite 去重（{{SKILL_DIR}}/scripts/url-index.db），如果 URL 已存在则报告「已抓取，跳过」。
2. 判断 URL 类型：
   - X.com / Twitter：用 Playwright（Chrome Profile 2）抓取 + 下载图片到 Image/ 目录
   - 其他网站：用 web_fetch + Playwright 抓取
3. 将原文保存到 Origin/ 目录（含完整 frontmatter：publish_date、fetch_date、author、source_url、origin_title）
4. 校验 frontmatter（repair_frontmatter）
5. 完成后报告：文章标题、block 数、图片数、origin_path

【Playwright 脚本】：（见下方完整代码块）

【校验代码】：（见下方校验代码块）

完成后报告格式（用换行分隔，避免标题含 `|` 时解析出错）：
```
ORIGIN_PATH: {origin_path}
抓取完成：{标题} ({block数} blocks, {图片数} images)
```
" \
  --runtime "subagent" \
  --mode "run"
```

### 步骤 2：等待 Subagent 1 完成

收到 Subagent 1 的完成通知后，从报告中提取 `ORIGIN_PATH:` 开头的那行，取其值作为 origin_path。检查文件是否存在。

### 步骤 3：派发 Subagent 2（翻译）

```bash
sessions_spawn \
  --task "【Subagent 2 - 翻译】读取原文并翻译为简体中文。

URL: <URL>
origin_path: <上一步获取的 origin_path>
category: <category 可选，来源列表页抓取的分类标签>
fetch_type: <fetch_type 可选，默认 manual；传入时用传入值（cron/ manual），未传入时默认 manual 并写入 frontmatter>

执行步骤：
1. 读取 origin_path 文件
2. 调用 LLM 将正文翻译为简体中文（图片标记和代码块原样保留）
3. 保存译文到 Article/ 目录
   - 文件名与 Origin 文件名相同（不含路径前缀）
   - frontmatter 包含：publish_date、fetch_date、author、source_url、origin_title、category（如有）、fetch_type、tags、description
   - 正文上方插入双向链接 [[Origin/<文件名>]]
4. 写 SQLite 索引（url_index 表），含 category
5. 校验（repair_frontmatter + record_issues）
6. 完成后报告：文章标题、article_path

【翻译要求】：
- 保留原义和逻辑，专有名词保留英文
- 图片标记 ![](Image/...) 原样保留
- 代码块内容原样保留
- tags 建议：AI, Agent, Engineering 等（根据内容调整）
- category：若传入则写入 frontmatter
- fetch_type：若传入则写入 frontmatter；若未传入则默认 "manual" 并写入 frontmatter
- description：一句话摘要

【校验代码】：
```python
import sys, os, sqlite3, re
sys.path.insert(0, '{{SKILL_DIR}}/references')
from article_utils import repair_frontmatter, record_issues
from datetime import datetime, timezone, timedelta

origin_path = '<origin_path>'
article_path = '{{VAULT_PATH}}/' + os.path.basename(origin_path)
url = '<URL>'

fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
fm_art, fixed_art, rem_art = repair_frontmatter(article_path, url, {'fetch_date': fetch_date})

if rem_art:
    record_issues(url, "; ".join(rem_art))
    raise Exception(f"校验未通过：{rem_art}")
else:
    record_issues(url, "")

# 写 SQLite（用 yaml.safe_load 解析 frontmatter，避免含冒号的值被截断）
import yaml
db_path = os.path.expanduser("{{SKILL_DIR}}/scripts/url-index.db")
conn = sqlite3.connect(db_path)
with open(article_path, encoding='utf-8') as f:
    content = f.read()
fm = {}
if content.startswith('---'):
    parts = content.split('---', 2)
    if len(parts) >= 3:
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except Exception:
            pass
conn.execute("""INSERT OR REPLACE INTO url_index (url, title, fetched_at, issues, category, origin_path, article_path) VALUES (?,?,?,?,?,?,?)""",
    (url, os.path.basename(article_path), fetch_date, '', fm.get('category',''), origin_path, article_path))
conn.commit()
print(f"翻译完成：{article_path}")
```

完成后报告格式：
翻译完成：{标题} | {article_path}
" \
  --runtime "subagent" \
  --runTimeoutSeconds 1200 \
  --mode "run"
```

### 步骤 4：向 Harvey 报告最终结果

---

## 批量抓取流程（2 篇或以上）

### 核心原则

1. **随机间隔**：每次只启动 1 个抓取 Subagent 1，等待完成后随机等 60~180 秒再派发下一个
2. **同时活跃不超过 5 个**（抓取 + 翻译各算一个）
3. **任务清单先确认**

### 执行流程

**步骤 1**：批量查 SQLite，整理任务清单（已抓取的标记跳过）

**步骤 2**：逐一派发 Subagent 1（抓取），每完成一个立即派发对应的 Subagent 2（翻译）

```
Subagent 1 (抓取) → Subagent 2 (翻译) → [等待] → Subagent 1 (抓取) → Subagent 2 (翻译) → ...
```

每篇 Subagent 2 完成后，**在主 session 中用以下代码随机等待**再发下一篇：

```python
import time, random
wait = random.randint(60, 180)
print(f"等待 {wait} 秒后继续下一篇...")
time.sleep(wait)
```

---

## Playwright 抓取代码（X.com）

```python
from playwright.sync_api import sync_playwright
import os, json, urllib.request, hashlib
from datetime import datetime, timezone, timedelta

chrome_profile = os.path.expanduser('~/Library/Application Support/Google/Chrome/Profile 2')
url = "<URL>"
url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

import sys
sys.path.insert(0, '{{SKILL_DIR}}/references')
from article_utils import infer_ext

save_dir = "{{VAULT_PATH}}/Image"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=chrome_profile, headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url, timeout=30000)
    page.wait_for_timeout(8000)

    result = page.evaluate(r"""() => {
        const article = document.querySelector('article[data-testid="tweet"]');
        if (!article) return {error: 'No article found'};

        const titleEl = article.querySelector('[data-testid="twitter-article-title"]');
        const title = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

        const timeEl = article.querySelector('article time');
        const publishDate = timeEl ? timeEl.getAttribute('datetime') : '';

        const authorEl = article.querySelector('[data-testid="User-Name"]');
        let author = '';
        if (authorEl) {
            const authorText = authorEl.innerText.replace(/\s+/g, ' ').trim();
            author = authorText.split('@')[0].trim();
        }

        const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE']);
        const contentUnits = [];
        let lastText = '';

        const walker = document.createTreeWalker(article, NodeFilter.SHOW_ELEMENT);
        let node;
        while (node = walker.nextNode()) {
            if (skipTags.has(node.tagName.toUpperCase())) continue;
            const tag = node.tagName.toUpperCase();
            const tid = node.getAttribute('data-testid') || '';

            if (tag === 'DIV' && tid === 'tweetPhoto') {
                const img = node.querySelector('img');
                if (img && img.src && !img.src.includes('data:') && !img.src.includes('/profile_images/')) {
                    contentUnits.push({type: 'image', src: img.src, alt: img.alt || ''});
                }
            } else if (tag === 'SPAN' && tid === '') {
                let directText = '';
                for (const cn of node.childNodes) {
                    if (cn.nodeType === Node.TEXT_NODE) {
                        directText += (cn.textContent || '').replace(/\s+/g, ' ').trim() + ' ';
                    }
                }
                directText = directText.trim();
                let hasLiAncestor = false;
                let ancestor = node.parentElement;
                while (ancestor && ancestor.tagName) {
                    if (['LI','OL','UL'].includes(ancestor.tagName.toUpperCase())) {
                        hasLiAncestor = true;
                        break;
                    }
                    ancestor = ancestor.parentElement;
                }
                if (hasLiAncestor) continue;
                const isNoise = (
                    directText.length < 30 ||
                    /^[@#]?[\d.]+[KMB]?$/i.test(directText) ||
                    directText.startsWith('@')
                );
                const isSubset = lastText.length > 10 && (lastText.includes(directText) || directText.includes(lastText));
                if (!isNoise && !isSubset && directText.length >= 30) {
                    contentUnits.push({type: 'text', tag: 'span', content: directText});
                    lastText = directText;
                }
            } else if (['H2','H3','P','LI','BLOCKQUOTE','PRE'].includes(tag)) {
                const t = node.innerText.replace(/\s+/g, ' ').trim();
                if (t && t.length > 5) {
                    contentUnits.push({type: 'text', tag: tag.toLowerCase(), content: t});
                    lastText = t;
                }
            }
        }

        const blocks = [];
        const imageBlocks = [];
        for (let i = 0; i < contentUnits.length; i++) {
            const unit = contentUnits[i];
            if (unit.type === 'text') {
                blocks.push({
                    type: ['H2','H3'].includes(unit.tag.toUpperCase()) ? 'heading' : 'block',
                    tag: unit.tag,
                    content: unit.content,
                    blockIndex: blocks.length
                });
            } else if (unit.type === 'image') {
                imageBlocks.push({
                    src: unit.src,
                    alt: unit.alt,
                    afterBlock: blocks.length - 1
                });
            }
        }

        return {title, author, publishDate, blocks, imageBlocks, totalTextBlocks: blocks.length, totalImages: imageBlocks.length};
    }""")

    result['publishDate'] = result.get('publishDate', '')

with open('/tmp/x_article_combined.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

downloaded = []
for i, img in enumerate(result.get('imageBlocks', [])):
    ext = infer_ext(img['src'])
    fname = f"{url_hash}_img_{i+1}{ext}"
    fpath = os.path.join(save_dir, fname)
    try:
        req = urllib.request.Request(img['src'], headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'image/*'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(fpath, 'wb') as f:
            f.write(data)
        print(f"  [{i+1}] Downloaded {fname} ({len(data)} bytes)")
        downloaded.append({**img, 'filename': fname})
    except Exception as e:
        print(f"  [{i+1}] Failed {fname}: {e}")
        downloaded.append({**img, 'filename': fname})

with open('/tmp/x_article_combined.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
data['images'] = downloaded
with open('/tmp/x_article_combined.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

ctx.close()

print(f"Title: {result['title']}")
print(f"Text blocks: {result['totalTextBlocks']}, Images: {result['totalImages']}")
```

### 从 JSON 构建原文文件

```python
import json, re, os
from datetime import datetime, timezone, timedelta

HEADING_PREFIX = {'h1': '# ', 'h2': '## ', 'h3': '### ', 'h4': '#### '}

def format_block(block):
    tag = block.get('tag', 'p')
    content = block.get('content', '')
    if tag in HEADING_PREFIX:
        return HEADING_PREFIX[tag] + content
    if tag == 'pre':
        return f'```\n{content}\n```'
    if tag == 'li':
        return f'- {content}'
    return content

with open('/tmp/x_article_combined.json', encoding='utf-8') as f:
    data = json.load(f)

blocks = data['blocks']
images = data.get('images') or []
title = data.get('title', 'Untitled')
author = data.get('author', '')
publish_date = data.get('publishDate', '')[:10]
source_url = "<URL>"

# 构建文件名
origin_filename = re.sub(r'[\\/:]', '', title) + '.md'
if origin_filename.startswith('.'):
    origin_filename = origin_filename[1:]
origin_path = f'{{VAULT_PATH}}/Origin/{origin_filename}'

body_units = []
for i, block in enumerate(blocks):
    unit_parts = [format_block(block)]
    for img in images:
        if img.get('afterBlock') == i:
            unit_parts.append(f'![](Image/{img["filename"]})')
    body_units.append('\n'.join(unit_parts))

body = '\n\n'.join(body_units)
fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

origin_content = f"""---
publish_date: {publish_date}
fetch_date: {fetch_date}
author: {author}
source_url: {source_url}
origin_title: "{title}"
---

# {title}

{body}
"""

with open(origin_path, 'w', encoding='utf-8') as f:
    f.write(origin_content)

print(f"Origin saved: {origin_path}")
print(f"Blocks: {len(blocks)}, Images: {len(images)}")
```

---

## 其他网站抓取流程

### Step 1：web_fetch 提取原始 HTML

```python
# Subagent 1 内执行
import subprocess, os
result = subprocess.run(
    ['python3', '-c',
     f"import urllib.request; req=urllib.request.Request('{url}', headers={{'User-Agent':'Mozilla/5.0'}}); resp=urllib.request.urlopen(req,timeout=30); open('/tmp/fetched_page.html','wb').write(resp.read())"],
    capture_output=True, text=True
)
# 若 web_fetch 工具可用，直接用工具调用更佳
```

也可直接调用 `web_fetch` 工具获取 HTML，保存到 `/tmp/fetched_page.html`。

### Step 2：Playwright DOM 提取 + 图片下载

```python
from playwright.sync_api import sync_playwright
import os, json, urllib.request, hashlib, re
from datetime import datetime, timezone, timedelta

import sys
sys.path.insert(0, '{{SKILL_DIR}}/references')
from article_utils import infer_ext

url = "<URL>"
url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
save_dir = "{{VAULT_PATH}}/Image"
html_path = "/tmp/fetched_page.html"

with open(html_path, encoding='utf-8', errors='replace') as f:
    html = f.read()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_content(html, wait_until="domcontentloaded")

    result = page.evaluate(r"""() => {
        const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE','BUTTON','FORM']);
        const contentUnits = [];
        const imageBlocks = [];

        // Extract title
        const titleEl = document.querySelector('h1') || document.querySelector('title');
        const title = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

        // Extract publish date from common meta tags
        const dateMeta = document.querySelector('meta[property="article:published_time"]')
            || document.querySelector('meta[name="date"]')
            || document.querySelector('time');
        const publishDate = dateMeta
            ? (dateMeta.getAttribute('content') || dateMeta.getAttribute('datetime') || '')
            : '';

        // Extract author
        const authorMeta = document.querySelector('meta[name="author"]')
            || document.querySelector('[rel="author"]');
        const author = authorMeta
            ? (authorMeta.getAttribute('content') || authorMeta.innerText || '').trim()
            : '';

        // Walk main content area
        const main = document.querySelector('main') || document.querySelector('article') || document.body;
        const walker = document.createTreeWalker(main, NodeFilter.SHOW_ELEMENT);
        let node;
        while (node = walker.nextNode()) {
            if (skipTags.has(node.tagName.toUpperCase())) continue;
            const tag = node.tagName.toUpperCase();

            if (tag === 'IMG') {
                const src = node.src || node.getAttribute('data-src') || '';
                if (src && !src.startsWith('data:') && src.startsWith('http')) {
                    imageBlocks.push({ src, alt: node.alt || '', afterBlock: contentUnits.length - 1 });
                }
            } else if (['H1','H2','H3','P','LI','BLOCKQUOTE','PRE','CODE'].includes(tag)) {
                const t = node.innerText.replace(/\s+/g, ' ').trim();
                if (t && t.length > 10) {
                    contentUnits.push({ tag: tag.toLowerCase(), content: t });
                }
            }
        }

        return { title, author, publishDate, blocks: contentUnits, imageBlocks };
    }""")
    browser.close()

# Download images
downloaded = []
for i, img in enumerate(result.get('imageBlocks', [])):
    ext = infer_ext(img['src'])
    fname = f"{url_hash}_img_{i+1}{ext}"
    fpath = os.path.join(save_dir, fname)
    try:
        req = urllib.request.Request(img['src'], headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(fpath, 'wb') as f:
            f.write(data)
        downloaded.append({**img, 'filename': fname})
    except Exception as e:
        print(f"  Image {i+1} failed: {e}")
        downloaded.append({**img, 'filename': fname})

# Build origin file
HEADING_PREFIX = {'h1': '# ', 'h2': '## ', 'h3': '### '}

def fmt(block):
    tag, content = block['tag'], block['content']
    if tag in HEADING_PREFIX:
        return HEADING_PREFIX[tag] + content
    if tag == 'pre':
        return f'```\n{content}\n```'
    if tag == 'li':
        return f'- {content}'
    return content

blocks = result['blocks']
title = result.get('title', 'Untitled')
author = result.get('author', '')
publish_date = (result.get('publishDate') or '')[:10]
fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

# 文件名：移除特殊字符
origin_filename = re.sub(r'[\\/:*?<>|".]', '', title) + '.md'
origin_path = f'{{VAULT_PATH}}/Origin/{origin_filename}'

body_units = []
for i, block in enumerate(blocks):
    parts = [fmt(block)]
    for img in downloaded:
        if img.get('afterBlock') == i:
            parts.append(f'![](Image/{img["filename"]})')
    body_units.append('\n'.join(parts))

body = '\n\n'.join(body_units)

origin_content = f"""---
publish_date: {publish_date}
fetch_date: {fetch_date}
author: {author}
source_url: {url}
origin_title: "{title}"
---

# {title}

{body}
"""

with open(origin_path, 'w', encoding='utf-8') as f:
    f.write(origin_content)

print(f"Origin saved: {origin_path}")
print(f"Blocks: {len(blocks)}, Images: {len(downloaded)}")
```

---

## 保存后校验代码（Subagent 1 用）

```python
import sys, os, sqlite3, re
sys.path.insert(0, '{{SKILL_DIR}}/references')
from article_utils import repair_frontmatter, record_issues
from datetime import datetime, timezone, timedelta

origin_path = '<origin_path>'
url = '<URL>'

if not os.path.exists(origin_path):
    raise Exception(f"原文文件未生成：{origin_path}")

fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
fm_orig, fixed_orig, rem_orig = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date})

if rem_orig:
    record_issues(url, "; ".join(rem_orig))
    raise Exception(f"校验未通过：{rem_orig}")
else:
    record_issues(url, "")

print(f"校验通过：{origin_path}")
```

---

## 文件命名规则

```python
import re
origin_filename = re.sub(r'[\\/:*?<>|".]', '', title) + '.md'
```

移除字符：`\ / : * ? < > | " .`（与 file-format.md 保持一致）。

---

## 附录

### 文件格式模板

详见 [references/file-format.md](references/file-format.md)
