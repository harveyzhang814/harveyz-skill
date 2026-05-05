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

[[Origin/文章原标题.md]]

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
| `tags` | — | ✅ 必须 | YAML 列表格式，非逗号分隔 |
| `description` | — | ✅ 必须 | 一两句话摘要，供快速阅读，基于译文内容提取 |

## 文件命名规则

| 特殊字符 | 处理 |
|----------|------|
| `\` `/` `:` | 移除 |
| `.` 开头 | 移除 |
| `*` `?` `<` `>` `|` `"` | 移除 |

## 保存路径

| 类型 | 路径 |
|------|------|
| 原文 | `Origin/<origin_title>.md` |
| 译文 | `<title>.md`（无 Origin 子文件夹） |
| 图片 | `Image/<url_hash>_img_N.ext` |
