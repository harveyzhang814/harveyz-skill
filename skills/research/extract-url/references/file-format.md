# 文件格式模板

## 原文文件格式

```markdown
---
publish_date: YYYY-MM-DD
fetch_date: YYYY-MM-DD
author: 作者名
source_url: https://xxx.com/article
origin_title: Original Title
category: Category（可选，来源列表页抓取的分类标签）
tags:
  - tag1
  - tag2
description: 一两句话摘要
---

文章正文...
```

## 译文文件格式

```markdown
---
publish_date: YYYY-MM-DD
fetch_date: YYYY-MM-DD
author: 作者名
source_url: https://xxx.com/article
origin_title: Original Title
category: Category（可选，来源列表页抓取的分类标签）
tags:
  - tag1
  - tag2
description: 一两句话摘要，概括文章核心内容，供快速阅读。
---

[[<hash8>/Origin/文章原标题.md]]

---

翻译后的正文...
```

## frontmatter 字段说明

| 字段 | 原文文件 | 译文文件 | 来源 |
|------|----------|----------|------|
| `publish_date` | ✅ 必须 | ✅ 必须 | 页面显示日期，ISO 8601 格式取前 10 位（YYYY-MM-DD） |
| `fetch_date` | ✅ 必须 | ✅ 必须 | 抓取时间，格式 YYYY-MM-DD（北京时间） |
| `author` | ✅ 必须 | ✅ 必须 | 页面显示作者，若无则留空 |
| `source_url` | ✅ 必须 | ✅ 必须 | 当前抓取的 URL |
| `origin_title` | — | ✅ 必须 | 原文标题，用于 obsidian 双向链接 |
| `category` | 可选 | 可选 | 来源列表页抓取的分类标签，由 cron 任务注入，article-fetcher skill 只做透传 |
| `tags` | 可选 | ✅ 必须 | YAML 列表格式；来自 `~/.hskill/url-extract/fixed_tags.txt` 词表，由 Subagent 2 从词表中选取适用条目；可为空列表 |
| `candidate_tags` | — | 可选 | YAML 列表格式；由 LLM 从文章内容自由提取的候选标签，定期 review 决定是否升入固定词表；可为空列表或缺失 |
| `description` | — | ✅ 必须 | 一两句话摘要，供快速阅读，基于译文内容提取 |

## 文件命名规则

```python
import re
origin_filename = re.sub(r'[\\/:*?<>|".]', '', title) + '.md'
```

移除字符：`\ / : * ? < > | " .`（与 SKILL.md 保持一致）。

## 保存路径

文章专属文件夹：`<hash8>/`，其中 `hash8 = md5(source_url).hexdigest()[:8]`，统一由 `scripts/config.py` 的 `get_article_paths()` 计算（图片、原文/译文文件名共用同一算法）。

| 类型 | 路径 |
|------|------|
| 原文 | `<hash8>/Origin/<origin_title>.md` |
| 译文 | `<hash8>/Translation/<origin_title>.md`（与原文同名） |
| 图片 | `<hash8>/Image/img_N.ext` |

双链示例（译文首行）：`[[<hash8>/Origin/<origin_title>.md]]`
图片引用示例（原文/译文正文内）：`![](../Image/img_1.jpg)`

## 固定词表（fixed_tags.txt）

路径：`~/.hskill/url-extract/fixed_tags.txt`

格式：分组注释平铺文本，`#` 开头行为注释，脚本读取时跳过。

```
# topic
loop-engineering
ai

# language
english
chinese

# source
substack
twitter
```

**维护规则：**
- 直接用文本编辑器编辑，修改立即生效（无需重新安装 skill）
- `candidate_tags` 中反复出现的词条，可手动升入词表
- validate_article.py 会自动将 `candidate_tags` 中命中词表的条目移入 `tags`（兜底移位）
