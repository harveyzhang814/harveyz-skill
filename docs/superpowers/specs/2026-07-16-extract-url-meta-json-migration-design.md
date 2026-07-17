# extract-url 索引改为 meta.json + 合并迁移 设计文档

## 概述

把 extract-url skill 的索引存储从集中式 SQLite（`url-index.db`）改为每篇文章目录下的 `meta.json`（落实 `2026-07-16-extract-url-index-storage-decision.md` 的方案 B），并把这次迁移与上一版本尚未对真实数据执行的目录结构迁移（flat → `<hash8>/{Origin,Translation,Image}/`）合并成一次迁移，对真实 Vault 一并执行。

## 背景

- 决策文档已确认：唯一真实查询场景是精确 URL 去重，`<hash8>` 目录名本身就是索引键，继续维护集中式 SQLite 是多余的间接层，还背着 iCloud/Obsidian 同步风险和并发锁问题
- 上一版本的目录结构迁移代码已落地（`config.py`、`playwright_*.py`、subagent 提示词均已改用 `<hash8>` 路径），但迁移脚本从未在真实 Vault 数据上执行过；真实数据现状：0 个 `<hash8>` 目录，`Origin/` 365 文件、`Image/` 1937 文件、根目录译文 288 篇，全部仍是旧扁平结构；`url-index.db` 仍在 `Reading/` 根目录，150 行
- 额外发现：`Reading/` 根目录下有一批当前代码不引用的历史遗留 db 文件、8 个 `.sync-conflict-*` iCloud 冲突文件——纳入本次改造范围一并清理
- 现有 `_rebuild_db()` 是全量重建、不读旧库补充数据，与决策文档"frontmatter 为主、db 辅助补充"的要求不一致，这次一并修正
- 现有 `record_issues` 在 Subagent 1 阶段的调用是时序死代码（索引行/文件当时还不存在，UPDATE 是空操作），这次一并修正

## 架构设计

### meta.json 数据模型

位置：`VAULT_PATH/<hash8>/meta.json`。字段沿用 `url_index` 表现有语义，去掉从未被下游代码读取过的 `origin_path`/`article_path`（目录结构本身已隐含）：

```json
{
  "source_url": "https://example.com/article",
  "title": "文章标题",
  "category": "分类",
  "fetched_at": "2026-07-16",
  "issues": ""
}
```

写入时机：与当前 SQLite 写入时机一致——Subagent 2（打标+翻译）成功后创建/覆盖 meta.json。`issues` 字段合并 Subagent 1 阶段产生的问题（见"issues 时序修复"节）。

### 去重查询（dedup_check.py）

```
hash8 = get_url_hash(url)   # 复用 config.py 已有函数
meta_path = VAULT_PATH/<hash8>/meta.json
若 meta_path 不存在 → OK（未完成，可重试）
若存在 → 读取，校验 source_url 精确匹配
  匹配 → ALREADY_FETCHED
  不匹配（8位md5碰撞，概率可忽略）→ OK
```

检查 `meta.json` 是否存在而非检查目录是否存在，是因为 meta.json 只在 Subagent 2 成功后才写入——这与当前"只有原文没有译文的部分完成状态应判定为未完成、允许重试"的语义完全一致，不引入行为变化。对外接口（env var `CHECK_URL`、stdout `ALREADY_FETCHED`/`OK`）不变，`subagent1-fetch-prompt.md` 的调用方式无需改动。

### issues 时序修复

当前 bug：`playwright_web*.py` 在 Subagent 1（抓取）阶段调用 `record_issues` 时，索引行尚未创建（只有 Subagent 2 结束才 INSERT），UPDATE 是空操作，问题被静默丢弃。

修复：Subagent 1 阶段的 issues 写入 `<hash8>/.fetch_issues.tmp`（此时 `<hash8>/Origin/` 已由抓取脚本创建，目录存在）；Subagent 2 写 meta.json 时读取该临时文件内容，与自身产生的 issues 合并写入 `issues` 字段，写入后删除临时文件。

### 涉及文件改造清单

| 文件 | 改动 |
|---|---|
| `scripts/config.py` | 无需新增（`get_url_hash` 已存在，复用即可） |
| `references/article_utils.py` | `write_url_index` → `write_meta_json`；`record_issues` → 写 `.fetch_issues.tmp` / 合并进 meta.json 两个函数 |
| `scripts/dedup_check.py` | 去掉 `sqlite3`，改为 meta.json 存在性+内容校验 |
| `scripts/validate_article.py` | 调用改为 `write_meta_json` |
| `scripts/playwright_web.py`、`playwright_web_arxiv.py`、`playwright_xcom.py` | `record_issues` 调用改为写 `.fetch_issues.tmp` |
| `scripts/migrate_to_folder_structure.py` | 见下节"合并迁移脚本" |
| `SKILL.md` | 去掉"URL 去重索引（SQLite）"整节，改写为 meta.json 版本；路径变量表去掉 `DB:` 行；版本号递增 |
| `references/subagent1-fetch-prompt.md` | 新增"写临时 issues 文件"一步，调用接口文案不变 |
| `references/subagent2-tag-translate-prompt.md` | "写入 SQLite 索引"文案改为"写入 meta.json"，调用接口（`validate_article.py`）不变 |
| `tests/conftest.py` 及依赖它的 6 个测试文件 | 见"测试策略"节 |

## 合并迁移脚本设计（`migrate_to_folder_structure.py`）

沿用现有 `plan`/`apply [--no-backup]`/`find-merges`/`apply-merge` CLI 接口和"先 plan 预览、再 apply 执行"的人工确认节奏，不新建脚本。

- **`build_plan()`/`apply_plan()`**：配对逻辑（按译文双链找原文、URL 校验）、文件移动（Origin/Translation/Image 迁入 `<hash8>/`）、双链与图片引用改写，全部保持不变——这部分就是上一版本尚未执行的目录迁移，直接复用
- **`_rebuild_db()` → `_write_meta_jsons(vault_path, plan, old_db_path)`**：对每条成功迁移的条目，在新的 `<hash8>/` 目录下写 meta.json。数据源优先级：迁移后的 frontmatter 为主，`old_db_path`（原 `url-index.db`）里同 `source_url` 的行作为 frontmatter 缺失字段时的兜底补充——修正现有 `_rebuild_db` 完全不读旧库的问题
- **新增 `_cleanup_legacy_files(vault_path)`**：迁移成功后执行，删除 `url-index.db`（含其 2 张未用遗留表 `urls`/`articles`）、当前代码不引用的历史孤儿 db 文件（`url_index.db` 下划线版、`reading.db`、`reading_index.db`、`.fetch_history.db`、`articles.db`、`cursor-articles.db`、`article_fetch_log.sqlite` 等）、以及 8 个 `.sync-conflict-*` 冲突文件（db 冲突副本 2 个、`.DS_Store` 冲突 4 个、`Origin/`md 冲突 1 个、`Image/`图片冲突 1 个）
- **`apply-merge` 收尾补充**：合并后若目标目录同时具备 Origin+Translation，生成 meta.json（此前该场景完全没有索引产出）
- **执行顺序（`apply` 子命令内部）**：`build_plan` → 打印摘要 → 备份 tar.gz → `apply_plan`（移动文件+改写链接）→ `_write_meta_jsons` → `_cleanup_legacy_files` → 打印最终结果（迁移数/失败数/清理文件数）

## 测试策略

`tests/conftest.py` 的 `url_index_db` fixture 改为等价的 meta.json 读写 helper（例如 `meta_json_dir` fixture，负责创建/读取指定 `<hash8>/meta.json`）。依赖它的测试文件（`test_dedup_check.py`、`test_validate_article.py`、`test_playwright_web.py`、`test_playwright_web_arxiv.py`、`test_migrate_to_folder_structure.py`，以及 conftest 自身）断言从 SQL 查询改为读 meta.json 文件内容，覆盖面不变（去重命中/未命中、写入后可读、issues 合并、迁移后 meta.json 路径正确、幂等性、`_cleanup_legacy_files` 删除的文件确实消失且不误删无关文件）。

## 真实数据执行流程

沿用上次已验证过的安全流程：

1. 用户在场，关闭 Obsidian、暂停 iCloud 同步
2. `python3 migrate_to_folder_structure.py plan` 预览，人工确认
3. `python3 migrate_to_folder_structure.py apply`（自动 tar.gz 备份到 `Reading/` 同级目录）
4. 校验迁移结果（抽查 `<hash8>/meta.json` 内容、去重脚本行为、Obsidian 双链是否可跳转）
5. 恢复 iCloud 同步

## 风险与缓解

- **meta.json 生成时数据源优先级出错**（用了不完整的旧库数据覆盖了完整的 frontmatter 数据）：明确"frontmatter 为主，旧库仅补缺失字段"的优先级规则，并在测试中覆盖两者冲突时的取值断言
- **`_cleanup_legacy_files` 误删有效文件**：清理清单基于本次调研的具体文件名硬编码列出，不使用通配符批量匹配，避免误删真实用户数据
- **issues 临时文件遗留**：Subagent 2 写入 meta.json 后必须删除 `.fetch_issues.tmp`；若 Subagent 2 失败，临时文件残留不影响下次重试（下次 Subagent 1 会覆盖同名临时文件）
- **真实数据迁移**：延用已验证过的备份+plan预览+人工确认流程，不引入新风险
