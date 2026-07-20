# ADR: extract-url 的 meta.json 不做独立完整性校验

**状态：** 已采纳
**日期：** 2026-07-20

## 背景

`meta.json`（路径 `VAULT_PATH/<hash8>/meta.json`）是 extract-url skill 用于 URL 去重的索引文件，由 `skills/research/extract-url/references/article_utils.py` 中的 `write_meta_json()` 写入，调用方是 `skills/research/extract-url/scripts/validate_article.py`（Subagent 2 打标翻译流程的最后一步）。

`write_meta_json()` 只有在 `repair_frontmatter()` 成功校验译文文件的 frontmatter（`source_url`、`origin_title`、`description` 等字段）之后才会被调用；若该校验失败，脚本会在写入 meta.json 之前 `sys.exit(1)` 退出，跳过 meta.json 的写入。

meta.json 自身的字段（`source_url`、`title`、`category`、`fetched_at`、`issues`）全部来自函数内部推导，而非自由文本或用户输入：

- `source_url`：函数入参（已通过上一步校验的 URL）
- `title`：`os.path.basename(article_path)`，文件已存在故必然非空
- `fetched_at`：系统当前时间，自动生成
- `category` / `issues`：合法地可以为空字符串（可选字段）

这些字段结构上就不可能出现"缺失"的情况。

## 决策

**不为 meta.json 增加独立的完整性/schema 校验脚本。**

## 考虑过的替代方案

1. **新增 meta.json 字段完整性校验器**：单独校验 `source_url` / `title` / `fetched_at` 非空。
2. **改为原子写入**（先写临时文件再 rename），防止写入过程中崩溃导致文件损坏。

两者均被否决。

## 理由

1. meta.json 的必填字段在代码结构上已经被保证非空，完整性校验只是在验证一个已经成立的事实，属于防御性过度设计。
2. 真正的残余风险是**写入过程中崩溃导致 JSON 文件半截/损坏**，而事后完整性校验测不出这种问题（校验发生在写入完成之后）——要防这个得靠原子写入，不是完整性校验。
3. meta.json 只是个人使用场景下的去重索引文件，影响范围小；即使损坏，直接删除该文件重新抓取即可恢复，不值得为此增加复杂度。

## 后果

- 若未来 meta.json 的写入逻辑发生变化（例如字段来源从"内部推导"变成"自由文本/外部输入"），需要重新评估本决策。
- 若发现 meta.json 频繁损坏（例如进程被杀导致半截写入），应优先考虑原子写入方案，而非完整性校验。
