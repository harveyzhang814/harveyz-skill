# extract-url 索引存储方案调研决策文档

## 概述

调研 extract-url skill 当前用集中式 SQLite（`url-index.db`）维护 URL 去重索引是否合理，对比改为每篇文章目录下独立 `meta.json` 的可行性，产出结论供后续决定是否实施。**本文档只做决策，不涉及任何代码改动。**

## 背景

`extract-url` 最近完成了一次存储结构重构（见 `2026-07-16-extract-url-storage-restructure-design.md`），把文章从扁平结构迁移为按 `<hash8> = md5(source_url)[:8]` 分目录的结构（`VAULT_PATH/<hash8>/{Origin,Translation,Image}/`）。这次重构没有触及索引层：`url-index.db` 的表结构和用途保持不变，只是表内 `origin_path`/`article_path` 两列存储的路径值跟着更新。

现状调研（详见附录）确认：

- `url-index.db` 是集中式 SQLite，唯一表 `url_index` 含 7 个标准列（`source_url` PK, `title`, `fetched_at`, `issues`, `category`, `origin_path`, `article_path`），磁盘上实际还残留若干历史列和 2 张未使用的遗留表（`urls`, `articles`）
- **唯一真实消费者**是 `dedup_check.py`，做精确 `source_url` 匹配去重；没有列表查询、tag 检索等其他用例
- 数据库文件位于 `VAULT_PATH/url-index.db`，在 Obsidian Vault 内，会被 Obsidian/iCloud 同步机制一并同步——SQLite 文件被云同步工具同步是已知的高风险模式（同步期间的半写状态可能导致库损坏或产生无法合并的 `.sync-conflict-*` 副本）
- 代码层面没有并发写入保护（无 WAL、无 busy_timeout、无重试逻辑），多会话并发抓取时可能触发 `database is locked`
- `issues` 字段在 Subagent 1（抓取）阶段的回填调用实际是死代码：此时该 URL 对应的行还不存在，`UPDATE ... WHERE source_url=?` 是空操作

## 评估维度对比

| 维度 | A. SQLite 搬出 Vault | B. per-article meta.json（推荐） | C. meta.json + 派生缓存 |
|---|---|---|---|
| 查询（去重） | 不变，仍需打开 db 文件查询 | 直接 `<hash8>` 目录存在性检查，命中后读 1 个 meta.json 确认 URL；无需数据库 | 同 B，另加缓存加速未来的批量/tag 查询（当前无此需求） |
| 并发写入安全 | 未解决：仍是共享文件，多会话写入会锁竞争 | 天然安全：不同文章写入互不触碰同一文件 | 同 B，但缓存重建/增量更新引入新的一致性问题 |
| 迁移成本 | 低：只挪文件位置，无需改数据格式 | 中：需为现有文章生成 meta.json（可复用 `migrate_to_folder_structure.py` 已有的 frontmatter 解析工具） | 中高：在 B 基础上再实现缓存构建/失效逻辑 |
| Obsidian 生态兼容性 | 一般：二进制文件留在纯文本 Vault 里始终是异类 | 好：JSON 是纯文本，符合 Obsidian 生态惯例，不参与 Markdown 索引 | 好（同 B），缓存本身在 Vault 外不影响 Obsidian |
| 数据完整性/同步风险 | 未解决 | 解决：无共享文件，单篇 meta.json 损坏不影响其他文章 | 解决（同 B） |
| 扩展性（列表/tag 检索等） | 有（SQL 查询能力） | 弱：需要时得扫描全部 meta.json | 有：缓存层可支撑，但目前无真实需求，属预留 |

## 结论

**采用方案 B：per-article meta.json，不设中心索引。**

理由：调研确认唯一真实查询场景是精确 URL 去重，而 hash8 目录命名已经把这个需求解决了大半——`<hash8>` 本身就是从 `source_url` 派生的索引键。继续维护集中式 SQLite 索引是多余的间接层，还背着 iCloud/Obsidian 同步风险和并发锁问题。方案 C 的扩展查询能力当前没有真实用例支撑，属于过度设计（YAGNI）。

## 方案 B 设计草图

> 以下为供未来实施参考的设计草图，本次调研不实施。

- **文件位置**：`VAULT_PATH/<hash8>/meta.json`
- **字段**：沿用 `url_index` 现有语义 —— `source_url`, `title`, `fetched_at`, `issues`, `category`；`origin_path`/`article_path` 可省略（目录结构已隐含，可按需推导）
- **去重查询**：`Path(VAULT_PATH, hash8).exists()` → 若存在，读 meta.json 校验 `source_url` 精确匹配（防 8 位 md5 碰撞；当前规模下碰撞概率可忽略，约 1.5e-5）
- **写入时机**：与当前 SQLite 写入时机一致——Subagent 2（打标+翻译）成功后创建/覆盖 meta.json；`issues` 回填需要修正现有的时序问题（不应照搬 Subagent 1 阶段的死代码调用）

## 迁移与遗留处理

- **数据源优先级**：以现存文章目录下的 frontmatter 为主要数据源；`url-index.db` 现有的 150 行作为辅助补充，仅在 frontmatter 缺失对应字段时用 db 数据兜底
- **遗留 SQLite**：迁移完成后 `url-index.db`（含 2 张未使用历史表 `urls`/`articles`）整体废弃删除，不保留兼容层（无消费者需要它）

## 风险与缓解

- **Hash 碰撞**：8 位 md5，当前规模（几百篇文章）碰撞概率约 1.5e-5，通过读 meta.json 二次校验 URL 兜底，风险可接受
- **迁移期间数据丢失**：延用已验证过的迁移脚本模式（构建计划 → 人工确认 → 执行 → 备份），不新增风险
- **本决策文档不涉及代码改动**：实施仍需走一次单独的 brainstorming → plan → subagent 实施流程

## 附录：现状调研摘要

调研范围：`skills/research/extract-url/` 全部脚本、references、SKILL.md，以及 `/Users/harveyzhang96/Vault/Product/Reading/url-index.db` 的实际 schema。

- Schema 权威定义：`scripts/dedup_check.py:22-32`、`scripts/migrate_to_folder_structure.py:216-228`、`SKILL.md:92-102`
- 唯一 INSERT 点：`references/article_utils.py:264-287`（`write_url_index`），由 `scripts/validate_article.py` 在 Subagent 2 结束时调用
- UPDATE 点（issues 回填）：`playwright_web.py:223,226`、`playwright_web_arxiv.py:280,283`、`playwright_xcom.py:465,468`、`validate_article.py:35,46`
- 唯一 SELECT 点：`scripts/dedup_check.py:43`，精确 `source_url` 匹配
- DB 路径：`VAULT_PATH/url-index.db`（`scripts/config.py`、各 `playwright_*.py`），VAULT_PATH 来自 `~/.hskill/url-extract/config.json`
- 最近的存储结构迁移文档（`docs/superpowers/specs/2026-07-16-extract-url-storage-restructure-design.md:128-130`）明确「表结构不变，只改写入其中的路径内容」，未讨论索引存储方案本身
