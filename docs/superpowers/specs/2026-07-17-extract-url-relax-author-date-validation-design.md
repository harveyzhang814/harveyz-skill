# extract-url 译文校验放宽 author/publish_date 设计文档

## 概述

`validate_article.py` 对译文做校验时，`author`/`publish_date` 字段缺失会导致整篇文章无法完成索引。这两个字段是源网站的元数据，很多网站本身就不提供，不应该卡死整篇文章的索引流程。放宽这两个字段的强制校验，其余字段（`source_url`/`origin_title`/`description`）校验不变。

## 背景

真实测试（Wikipedia 页面）发现：源网站没有 `author`/`publish_date` 元标签时，Subagent 1 抓取阶段已经能正确处理（`skip_remaining_fields={'description'}` 让原文校验只警告不阻塞）；但 Subagent 2 阶段的 `validate_article.py` 调用 `repair_frontmatter(article_path, url)` 时没有排除任何字段，`author`/`publish_date` 缺失会被判定为 `remaining` 非空，触发 `exit(1)`，`write_meta_json` 永远不会执行——这类文章永远停留在"部分完成"状态，无法被去重索引记录，也无法在 Obsidian 里正常呈现为已完成文章。

这个行为在旧 SQLite 版本里完全一样严格（`record_issues` 面对同样的空 `remaining` 判断也会 `exit(1)`），不是这次 meta.json 迁移引入的新问题，但既然发现了就顺手修。

## 架构设计

`references/article_utils.py` 的 `repair_frontmatter` 已经在这次迁移里加了 `skip_remaining_fields` 参数（用于 Subagent 1 阶段排除 `description`），本次改动直接复用这个已有机制，不新增任何函数或参数。

`scripts/validate_article.py` 里唯一一处 `repair_frontmatter(article_path, url)` 调用，改为：

```python
fm, fixed_fields, remaining = repair_frontmatter(article_path, url, skip_remaining_fields={'author', 'publish_date'})
```

`source_url`/`origin_title`/`description` 三个字段的强制校验保持不变——这三者要么是去重索引的主键（`source_url`），要么是 Subagent 2 自身应该产出的内容（`description`），要么在正常流程下几乎不可能为空（`origin_title`，抓取阶段已有 `'Untitled'` 兜底），缺失代表 skill 自身流程出了问题，应该继续阻塞。

## 数据流

无变化。`author`/`publish_date` 缺失时，`remaining` 里不再包含这两项，`validate_article.py` 正常走到 `write_meta_json`，`meta.json` 正常写入。这两个字段缺失的信息本身不会被记录到任何地方（未来若想追踪"哪些文章缺作者信息"，需要另外设计，不在本次范围内）。

## 测试策略

在 `tests/test_validate_article.py` 新增：
- 译文缺 `author`/`publish_date` 但其余字段齐全 → `validate_article.py` 应 exit 0，`meta.json` 正常写入
- 译文缺 `description`（阻塞字段）→ 应仍然 `exit 1`，确认阻塞字段没有被误放宽

## 风险和缓解

- **误放宽范围**：`skip_remaining_fields` 精确传入 `{'author', 'publish_date'}`，不影响其余三个字段的校验逻辑，用测试覆盖两侧行为
- **历史数据**：真实 Vault 尚未迁移（Task 9 待执行），这次改动不影响已有数据，只影响后续新抓取的文章
