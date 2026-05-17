---
name: article-fetcher
version: "1.1.0"
description: "抓取指定 URL 的文章，翻译为简体中文，保存原文到 Origin/、译文到 Vault 根目录，图片下载到 Image/，并写入 SQLite 去重索引。支持 X.com/Twitter（Playwright + Chrome Profile 2）和普通网站（web_fetch + Playwright 提取）。支持批量 URL（随机间隔 60–180 秒、最多 5 个并发 Subagent）。

只要用户提供了 URL 且想要保存、存档、抓取、翻译到本地 Vault，就应触发本 skill——即使用词模糊（如"存一下这篇"、"帮我翻译保存"、"把这个存到 obsidian"、"抓一下"、"archive 这篇"、"save this"、"存到我的库"）。

跳过条件：用户只要摘要不需要存档；用户粘贴原文要求翻译但无 URL；用户询问网站技术栈而非保存内容。"
---

# Article Fetcher

## 核心设计：两步分离

**第一步（Subagent 1）**：抓取文章 + 下载图片 → 保存原文到 Origin/
**第二步（Subagent 2）**：读取 Origin → 翻译 → 保存译文到 Article/

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
DB:       {{VAULT_PATH}}/url-index.db
```

---

## URL 去重索引（SQLite）

**数据库路径：** `{{VAULT_PATH}}/url-index.db`

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

### 步骤 1：派发 Subagent 1（抓取 + 保存原文）

```bash
sessions_spawn \
  --task "【Subagent 1 - 抓取】抓取文章并保存原文。

URL: <URL>

执行步骤：
1. 查 SQLite 去重：
   python3 -c \"
   import sqlite3
   conn = sqlite3.connect('{{VAULT_PATH}}/url-index.db')
   row = conn.execute('SELECT url FROM url_index WHERE url=?', ('<URL>',)).fetchone()
   conn.close()
   print('ALREADY_FETCHED') if row else print('OK')
   \"
   如果输出 ALREADY_FETCHED，报告「已抓取，跳过」并结束。

2. 判断 URL 类型并用 subprocess list 调用脚本（禁止 bash 字符串拼接，避免 shell 注入）：
   - X.com / Twitter：
     ```python
     import subprocess, sys
     result = subprocess.run(
         ['python3', '{{SKILL_DIR}}/scripts/playwright_xcom.py',
          url, '{{VAULT_PATH}}', '{{SKILL_DIR}}'],
         capture_output=True, text=True, timeout=300
     )
     print(result.stdout)
     if result.returncode != 0:
         raise RuntimeError(result.stderr)
     ```
   - 其他网站：先用 web_fetch 工具获取 HTML 保存到 /tmp/fetched_page.html，再：
     ```python
     import subprocess, sys
     result = subprocess.run(
         ['python3', '{{SKILL_DIR}}/scripts/playwright_web.py',
          url, '/tmp/fetched_page.html', '{{VAULT_PATH}}', '{{SKILL_DIR}}'],
         capture_output=True, text=True, timeout=300
     )
     print(result.stdout)
     if result.returncode != 0:
         raise RuntimeError(result.stderr)
     ```

3. 从脚本标准输出中提取 ORIGIN_PATH: 开头的行，取其值作为 origin_path。

完成后报告格式（换行分隔，避免标题含 | 时解析出错）：
ORIGIN_PATH: {origin_path}
抓取完成：{标题} ({block数} blocks, {图片数} images)
" \
  --runtime "subagent" \
  --mode "run"
```

### 步骤 2：等待 Subagent 1 完成

收到完成通知后，从报告中提取 `ORIGIN_PATH:` 开头的那行，取其值作为 origin_path。检查文件是否存在。

### 步骤 3：派发 Subagent 2（翻译）

```bash
sessions_spawn \
  --task "【Subagent 2 - 翻译】读取原文并翻译为简体中文。

URL: <URL>
origin_path: <上一步获取的 origin_path>
category: <category 可选，来源列表页抓取的分类标签>
fetch_type: <fetch_type 可选，默认 manual；传入时用传入值（cron/manual），未传入时默认 manual>

执行步骤：
1. 读取 origin_path 文件
2. 翻译正文为简体中文（图片标记和代码块原样保留，专有名词保留英文）
3. 保存译文到 {{VAULT_PATH}}/<文件名>：
   - 文件名与 Origin 文件名相同
   - frontmatter：publish_date、fetch_date、author、source_url、origin_title、
     category（如有）、fetch_type（默认 manual）、tags、description（一句话摘要）
   - 正文首行插入双向链接 [[Origin/<文件名>]]
4. 执行校验并写入 SQLite 索引（用 subprocess list + env var 传参，避免字符串注入）：

   ```python
   import subprocess, os
   article_path = '{{VAULT_PATH}}/' + os.path.basename(origin_path)
   result = subprocess.run(
       ['python3', '{{SKILL_DIR}}/scripts/validate_article.py'],
       env={
           'ARTICLE_URL':       url,
           'ARTICLE_ORIGIN':    origin_path,
           'ARTICLE_PATH':      article_path,
           'ARTICLE_DB':        '{{VAULT_PATH}}/url-index.db',
           'ARTICLE_SKILL_DIR': '{{SKILL_DIR}}',
           'ARTICLE_CATEGORY':  category or '',
           'PATH': os.environ.get('PATH', ''),
       },
       capture_output=True, text=True, timeout=60
   )
   print(result.stdout)
   if result.returncode != 0:
       raise RuntimeError(result.stderr)
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

1. **随机间隔**：每次只启动 1 个 Subagent 1，等待完成后随机等 60~180 秒再派发下一个
2. **同时活跃不超过 5 个**（抓取 + 翻译各算一个）
3. **任务清单先确认**

### 执行流程

**步骤 1**：批量查 SQLite，整理任务清单（已抓取的标记跳过）

**步骤 2**：逐一派发 Subagent 1（抓取），每完成一个立即派发对应的 Subagent 2（翻译）

```
Subagent 1 (抓取) → Subagent 2 (翻译) → [等待] → Subagent 1 (抓取) → ...
```

每篇 Subagent 2 完成后，**在主 session 中随机等待**再发下一篇：

```python
import time, random
wait = random.randint(60, 180)
print(f"等待 {wait} 秒后继续下一篇...")
time.sleep(wait)
```

---

## 附录

- 抓取脚本：[scripts/playwright_xcom.py](scripts/playwright_xcom.py)（X.com）、[scripts/playwright_web.py](scripts/playwright_web.py)（普通网站）
- 校验脚本：[scripts/validate_article.py](scripts/validate_article.py)（Subagent 2 校验 + SQLite 写入，通过 env var 接收参数）
- 工具函数：[references/article_utils.py](references/article_utils.py)（format_block、sanitize_filename、repair_frontmatter、write_url_index 等）
- 文件格式模板：[references/file-format.md](references/file-format.md)
