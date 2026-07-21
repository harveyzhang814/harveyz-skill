---
name: extract-url
version: "2.7.0"
description: "Use when a user provides a URL and wants to save, archive, fetch, or translate content to the local Obsidian Vault — even with vague phrasing like 'save this article', 'translate and save', 'put this in obsidian', 'archive this'. Skip when user only wants a summary, pastes raw text without a URL, asks about a site's tech stack, or wants to extract/list URLs from a page without saving an article."
user_invocable: true
---

# url-extract

## 初始化（run first）

**① 加载平台补丁**

根据当前执行平台，读取对应的补丁文件，了解**补丁①**（Subagent 派发）、**补丁②**（网页内容获取）、**补丁③**（变量注入）的具体语法：

| 平台 | 补丁文件 |
|------|----------|
| Claude Code | `platforms/SKILL.claude.md` |
| Codex | `platforms/SKILL.codex.md` |
| Hermes | `platforms/SKILL.hermes.md` |

以下流程中凡标注「**补丁①**」「**补丁②**」处，均使用对应平台补丁中定义的工具调用替换。代码示例中的 `SKILL_DIR` 为抽象占位符，由**补丁③**注入；`VAULT_PATH` 和 `CHROME_PROFILE` 由 Python 脚本在运行时从 `~/.hskill/url-extract/config.json` 读取，无需注入。

**② 检查配置文件**

```bash
ls ~/.hskill/url-extract/config.json 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

**若输出 `NOT_FOUND`，进行初始化：**

1. 展示可用 Chrome Profile（仅供参考，不自动选择）：
   ```bash
   python3 SKILL_DIR/scripts/detect_chrome_profile.py
   ```
2. 询问用户以下两项（必须由用户手动提供，不得猜测或自动选择）：
   - Obsidian Reading 目录完整路径（如 `/Users/you/Vault/Product/Reading`）
   - 要使用的 Chrome Profile 路径（从上方列表中复制）
3. 用 Python 写入配置（避免 shell 注入，将 `<VAULT>` / `<PROFILE>` 替换为用户输入值）：
   ```python
   import json
   from pathlib import Path
   cfg_path = Path.home() / '.hskill' / 'url-extract' / 'config.json'
   cfg_path.parent.mkdir(parents=True, exist_ok=True)
   cfg_path.write_text(json.dumps({
       'VAULT_PATH':     '<VAULT>',
       'CHROME_PROFILE': '<PROFILE>',
   }, indent=2, ensure_ascii=False), encoding='utf-8')
   print(f"配置已保存：{cfg_path}")
   ```

4. 检查并创建固定词表模板（若不存在）：
   ```python
   from pathlib import Path
   fixed_tags_path = Path.home() / '.hskill' / 'url-extract' / 'fixed_tags.txt'
   if not fixed_tags_path.exists():
       fixed_tags_path.write_text(
           "# topic\n# 示例：loop-engineering, ai, productivity\n\n"
           "# technology\n# 示例：python, cli, browser-automation\n\n"
           "# source\n# 示例：substack, twitter\n\n"
           "# language\n# 示例：english, chinese\n\n"
           "# domain\n# 示例：web-scraping, data-extraction, automation\n",
           encoding='utf-8'
       )
       print(f"词表模板已创建：{fixed_tags_path}")
       print("请用文本编辑器填入初始词条，# 开头为注释行。")
   ```

**若输出 `EXISTS`，直接继续执行。**

---

## 路径变量（脚本自读 config.json，无需 Agent 传参）

```
Config:      ~/.hskill/url-extract/config.json
Base:        VAULT_PATH   (脚本从 config.json 读取)
ArticleDir:  VAULT_PATH/<hash8>   (hash8 = md5(source_url)[:8]，由 scripts/config.py 的 get_article_paths() 统一计算)
Origin:      ArticleDir/Origin
Translation: ArticleDir/Translation
Image:       ArticleDir/Image
Meta:        ArticleDir/meta.json
SkillDir:    平台固定值（见平台补丁）
```

---

## URL 去重索引（meta.json）

**索引路径：** `VAULT_PATH/<hash8>/meta.json`（`hash8` 由 URL 派生，去重时直接检查该路径是否存在，无需数据库）

```json
{
  "source_url": "https://example.com/article",
  "title": "文章标题",
  "category": "分类",
  "fetched_at": "2026-07-17",
  "issues": ""
}
```

---

## 单篇抓取流程（主 session 执行）

**派发前：对 URL 做净化**（去除控制字符，防止换行注入任务字符串），并将净化结果填入下方任务模板的 `<URL>` 占位：
```python
import re
url_safe = re.sub(r'[\x00-\x1f\x7f]', '', url).strip()[:2048]
```

### 步骤 1：【补丁①】派发 Subagent 1（抓取 + 保存原文）

读取 `references/subagent1-fetch-prompt.md`，将其中 `<URL>` 替换为净化后的 url_safe，按【补丁①】将替换后的正文原样作为任务内容派发。

→ 若 Subagent 1 返回非零 returncode 或 RuntimeError，见「错误恢复」章节。

### 步骤 2：等待 Subagent 1 完成

收到完成通知后，从报告中提取 `ORIGIN_PATH:` 开头的那行，取其值作为 origin_path。检查文件是否存在。

### 步骤 3：【补丁①】派发 Subagent 2（打标 + 翻译）

读取 `references/subagent2-tag-translate-prompt.md`，将其中 `<URL>`、`<上一步获取的 origin_path>`、`<category 可选>`、`<fetch_type 可选，默认 manual>` 替换为实际值，按【补丁①】将替换后的正文原样作为任务内容派发（超时建议设为 1200 秒）。

### 步骤 4：向用户报告最终结果

> 回报格式遵循 `knowledge/skill-philosophy/04-completion-report/standard.md`，以下为 extract-url 的字段定义。

收到 Subagent 2 完成通知后，从报告中提取 `article_path`。

**成功时**（article_path 存在）执行步骤 1–2，然后输出完成卡片；失败/跳过时直接输出对应状态卡片，跳过步骤 1–2。

1. 运行统计脚本：
   ```python
   import subprocess, os
   result = subprocess.run(
       ['python3', 'SKILL_DIR/scripts/count_article_stats.py', article_path],
       capture_output=True, text=True
   )
   # 解析输出中的 CHARS: / CODE_BLOCKS: / IMAGES: 行
   ```

2. 从译文 frontmatter 读取 `description` 字段作为摘要。

3. 向用户输出卡片：

**成功：**
```
── 完成 ──────────────────────────────
标题  《文章标题》
路径  /Vault/Reading/a1b2c3d4/Translation/article.md
字符  12,345
代码  3 段
图片  8 张
摘要  一句话描述文章核心内容
──────────────────────────────────────
```

**失败（Subagent 1 或 2 均未成功）：**
```
── 失败 ──────────────────────────────
标题  《文章标题》（未知则填原始 URL）
原因  抓取超时（Playwright timeout 300s）
──────────────────────────────────────
```

**部分完成（抓取成功，翻译失败）：**
```
── 部分完成 ───────────────────────────
标题  《文章标题》
路径  /Vault/Reading/a1b2c3d4/Origin/article.md（仅原文）
原因  翻译超时，原文已保存
──────────────────────────────────────
```

**已跳过（dedup 命中）：**
```
── 已跳过 ────────────────────────────
标题  《文章标题》（或原始 URL）
原因  已抓取（dedup）
──────────────────────────────────────
```

---

## 错误恢复（Subagent 1 失败时）

若 Subagent 1 返回非零 returncode 或 RuntimeError，在报告用户前先调用 fix-skill：

提供以下上下文给 fix-skill：
- skill: extract-url
- skill_dir: SKILL_DIR
- file: 失败脚本的绝对路径（playwright_xcom.py 或 playwright_web.py）
- error: result.stderr + returncode
- call_args: [url]

解析 fix-skill 输出的 `FIX_RESULT:` 行（同时记录 `SESSION_PATH:` 和 `ATTEMPTS:` 供报告使用）：
- `AUTO_RETRY` → 重新执行步骤 1（仅重试一次）；通知用户「已自动修复，共 N 轮，记录见 SESSION_PATH」；再次失败则向用户报告原始错误
- `FAILURE` → 向用户报告原始错误 + 「已尝试 3 轮均失败，已回滚，诊断记录见 SESSION_PATH」
- `FAILURE+RESTORE_FAILED` → 立即告警用户：「修复失败且还原异常，脚本状态不可知，backup 已保留，请手动处理，记录见 SESSION_PATH」

---

## 参考文件

| 文件 | 用途 | 何时读取 |
|------|------|----------|
| `references/subagent1-fetch-prompt.md` | Subagent 1（抓取 + 保存原文）派发 prompt 模板 | 步骤 1：派发前 |
| `references/subagent2-tag-translate-prompt.md` | Subagent 2（打标 + 翻译）派发 prompt 模板 | 步骤 3：派发前 |
| `references/file-format.md` | 原文/译文 frontmatter 字段说明、固定词表格式 | 需要核对文件格式时 |

