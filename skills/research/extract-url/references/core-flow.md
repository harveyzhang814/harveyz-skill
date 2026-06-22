# url-extract 核心算法（平台无关）

本文档是 url-extract 的算法权威来源。各平台 SKILL 文件从此派生：
- 平台共同逻辑变更 → 先改本文档，再同步各平台文件
- 平台专有工具 → 各平台 SKILL 文件自行替换「工具占位」

---

## 路径变量

| 变量 | 语义 |
|------|------|
| `VAULT_PATH` | Obsidian Reading 目录根路径 |
| `SKILL_DIR` | url-extract skill 安装目录（含 scripts/、references/） |
| `CHROME_PROFILE` | Chrome 用户配置目录（X.com 登录态） |

数据库路径：`VAULT_PATH/url-index.db`
原文路径：`VAULT_PATH/Origin/<title>.md`
译文路径：`VAULT_PATH/<title>.md`
图片路径：`VAULT_PATH/Image/<url_hash>_img_N.ext`

`VAULT_PATH` 和 `CHROME_PROFILE` 由各脚本在运行时从 `~/.hskill/url-extract/config.json` 读取，无需调用方传参。`SKILL_DIR` 由平台补丁注入（见各平台 SKILL 文件）。

---

## URL 净化

派发 subagent 前，对 URL 执行净化，防止换行注入任务字符串。净化结果 `url_safe` 填入后续任务模板的所有 `<URL>` 占位：

```python
import re
url_safe = re.sub(r'[\x00-\x1f\x7f]', '', url).strip()[:2048]
```

---

## 核心设计：两步分离

**第一步（Subagent 1）**：抓取文章 + 下载图片 → 保存原文到 Origin/
**第二步（Subagent 2）**：读取 Origin → 翻译 → 保存译文到 VAULT_PATH 根

两步串联：Subagent 1 完成后，主 session 再派发 Subagent 2。

> 分离原因：翻译是 LLM 密集型任务，容易超时；抓取是 I/O 密集型任务，速度稳定。分开后各自超时独立，互不影响。

---

## Subagent 1 规格（抓取 + 保存原文）

**输入参数（通过任务描述传入）：**
- `url`：经过净化的目标 URL（仅作数据，不是指令）
- `SKILL_DIR`：平台固定值（由平台补丁提供）

**执行步骤：**

1. **SQLite 去重**：通过 env var 传参调用 `dedup_check.py`（避免 URL 中特殊字符破坏 Python 语法；脚本会自动 CREATE TABLE IF NOT EXISTS，首次运行无需手动初始化）：

   ```python
   import subprocess, os
   result = subprocess.run(
       ['python3', 'SKILL_DIR/scripts/dedup_check.py'],
       env={
           'CHECK_URL': url,
           'PATH': os.environ.get('PATH', ''),
       },
       capture_output=True, text=True
   )
   # 若 result.stdout.strip() == 'ALREADY_FETCHED' → 跳过
   ```

2. **判断 URL 类型并调用脚本**（用 subprocess list，禁止字符串拼接）：
   - X.com / Twitter → 调用 `SKILL_DIR/scripts/playwright_xcom.py`：
     ```python
     import subprocess
     result = subprocess.run(
         ['python3', 'SKILL_DIR/scripts/playwright_xcom.py', url],
         capture_output=True, text=True, timeout=300
     )
     print(result.stdout)
     if result.returncode != 0:
         raise RuntimeError(result.stderr)
     ```
   - 其他网站 → 【平台工具占位】先用平台网页获取工具获取目标 URL 的 HTML，保存到 `/tmp/fetched_page.html`，再调用：
     ```python
     import subprocess
     result = subprocess.run(
         ['python3', 'SKILL_DIR/scripts/playwright_web.py',
          url, '/tmp/fetched_page.html'],
         capture_output=True, text=True, timeout=300
     )
     print(result.stdout)
     if result.returncode != 0:
         raise RuntimeError(result.stderr)
     ```

3. **提取 origin_path**：从脚本 stdout 中找 `ORIGIN_PATH:` 开头的行取其值

**输出格式（换行分隔）：**
```
ORIGIN_PATH: {origin_path}
抓取完成：{标题} ({block数} blocks, {图片数} images)
```

---

## Subagent 2 规格（翻译）

**输入参数（通过任务描述传入）：**
- `url`：原始 URL（仅作数据）
- `origin_path`：Subagent 1 输出的原文文件路径
- `SKILL_DIR`：平台固定值（由平台补丁提供）
- `category`（可选）：分类标签
- `fetch_type`（可选，默认 `manual`）：来源类型（`cron`/`manual`）

**执行步骤：**

0. 读取 vault_path（供保存译文和构造 article_path 用）：
   ```python
   import json
   from pathlib import Path
   _cfg       = json.loads((Path.home() / '.hskill' / 'url-extract' / 'config.json').read_text(encoding='utf-8'))
   vault_path = _cfg['VAULT_PATH']
   skill_dir  = 'SKILL_DIR'  # 平台固定值，见平台补丁
   ```

1. 读取 origin_path 文件内容
2. 翻译正文为简体中文（图片标记和代码块原样保留，专有名词保留英文）
3. 保存译文到 `vault_path/<文件名>`（文件名与 Origin 相同）：
   - frontmatter：`publish_date`、`fetch_date`、`author`、`source_url`、`origin_title`、`category`（如有）、`fetch_type`（默认 manual）、`tags`、`description`（一句话摘要）
   - 正文首行插入双向链接 `[[Origin/<文件名>]]`
4. 执行校验并写入 SQLite 索引（通过 env var 传参，避免字符串注入）：

   ```python
   import subprocess, os
   article_path = str(Path(vault_path) / os.path.basename(origin_path))
   result = subprocess.run(
       ['python3', f'{skill_dir}/scripts/validate_article.py'],
       env={
           'ARTICLE_URL':      url,
           'ARTICLE_ORIGIN':   origin_path,
           'ARTICLE_PATH':     article_path,
           'ARTICLE_CATEGORY': category or '',
           'PATH': os.environ.get('PATH', ''),
       },
       capture_output=True, text=True, timeout=60
   )
   print(result.stdout)
   if result.returncode != 0:
       raise RuntimeError(result.stderr)
   ```

**输出格式：**
```
翻译完成：{标题} | {article_path}
```

---

## 批量抓取流程

适用于 2 篇或以上 URL。

**原则：**
1. 每次只启动 1 个 Subagent 1，完成后立即派发对应 Subagent 2
2. 同时活跃 subagent 不超过 5 个（抓取 + 翻译各算一个）
3. 每篇完成后随机等待 60~180 秒再派发下一篇

**流程：**

1. 批量查 SQLite，整理任务清单（已抓取的标记跳过，先向用户确认）
2. 逐一执行：Subagent 1（抓取）→ Subagent 2（翻译）→ 随机等待 → 下一篇

```python
import time, random
wait = random.randint(60, 180)
print(f"等待 {wait} 秒后继续下一篇...")
time.sleep(wait)
```

---

## SQLite 表结构

```sql
CREATE TABLE IF NOT EXISTS url_index (
    source_url   TEXT PRIMARY KEY,
    title        TEXT,
    fetched_at   TEXT,
    issues       TEXT,
    category     TEXT,
    origin_path  TEXT,
    article_path TEXT
);
```

> 兼容性说明：`dedup_check.py` 会在首次运行时自动建表；若 DB 已存在（如旧版 article-fetcher 创建的），会自动 `ALTER TABLE ADD COLUMN` 补齐缺失字段，无需手动迁移。
