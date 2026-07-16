---
title: extract-url 产物存储结构改造 design
date: 2026-07-16
status: approved
---

# extract-url 产物存储结构改造 — 设计文档

## 概览

`extract-url`（skills/research/extract-url/）目前把一篇文章的产物拆散存放：译文放 Vault 根目录、原文放 `Origin/`、图片放共享的 `Image/`，靠文件名/哈希前缀避免碰撞。本次改造把**同一篇文章的原文、译文、图片收进一个专属文件夹**，并把散落在多个脚本里的路径拼接逻辑收敛成一处，同时提供一次性迁移脚本把存量数据（288 篇译文 / 365 篇原文 / 1887 张图片）搬进新结构。

**改动原则：最小改动。** 只动路径生成、链接生成、以及新增迁移脚本；不改 `dedup_check.py`、`count_article_stats.py`、`validate_article.py`（它们只透传路径参数，与路径格式无关，已核实）；不改 `url-index.db` 的表结构（只改写入其中的路径内容）；发现的 `urls`/`articles` 两张未使用遗留表本次不清理。

---

## 新目录结构

```
Reading/
└── <hash8>/                                 # url_hash = md5(source_url).hexdigest()[:8]
    ├── Origin/
    │   └── <origin_title_sanitized>.md
    ├── Translation/
    │   └── <origin_title_sanitized>.md      # 译文文件名沿用原文文件名（与现状一致）
    └── Image/
        └── img_1.jpg, img_2.png, ...        # 去掉哈希前缀（文件夹已按 hash 分区，前缀冗余）
```

`<origin_title_sanitized>` 沿用现有清洗规则（去除 `\ / : * ? < > | " .`）。

---

## 路径集中化

`scripts/config.py` 新增共享函数：

```python
def get_article_paths(source_url: str, origin_title: str) -> dict:
    """返回 article_dir / origin_dir / translation_dir / image_dir / origin_path / translation_path"""
```

内部用 `md5(source_url.encode()).hexdigest()[:8]` 算 hash，拼出 `VAULT_PATH/<hash>/...`。

**改动方消费该函数：**

| 文件 | 现状 | 改动 |
|------|------|------|
| `scripts/playwright_web.py` | 自己拼 `Origin/`/`Image/` 路径，自己算 hash | 改用 `get_article_paths` |
| `scripts/playwright_web_arxiv.py` | 同上 | 同上 |
| `scripts/playwright_xcom.py` | 同上 | 同上 |
| `references/article_utils.py` | `build_article_from_json` 里硬编码 `Image/`、`[[Origin/{}]]` | 改用新路径 + 新链接格式（见下） |
| `references/subagent2-tag-translate-prompt.md` | 绕开 `config.py` 自己 `json.loads` 读 config，自己拼 `article_path = vault/basename(origin_path)` | 改成调用 `get_article_paths(source_url, origin_title)`，`origin_title` 从 `origin_path` 的文件名解出 |

三个 `playwright_*.py` 里各自重复的 md5 哈希算法和图片链接拼接字符串一并收敛（不新增文件，直接在各自文件里改调用点）。

---

## 双链与图片引用格式

**已核实 Vault 实际根目录是 `/Users/harveyzhang96/Vault/Product`**（`.obsidian/` 所在处），`Reading` 是其下子目录；`app.json` 未覆盖 `newLinkFormat`，用 Obsidian 默认的"最短路径匹配"（按路径后缀唯一性解析）。抽查真实文件确认现有约定是带 `.md` 后缀的相对路径链接，例如：

```
[[Origin/A Framework for Frontier AI and the Dawning of a New Age.md]]
```

新格式在此基础上加上 hash 前缀保证后缀在全 vault 唯一：

```
[[<hash>/Origin/<origin_title>.md]]
```

图片嵌入因为正文文件现在多嵌套一层（`Origin/` 或 `Translation/`），从 `![](Image/xxx)` 改为：

```
![](../Image/xxx)
```

只有译文链接原文，原文不反向链接译文（与现状一致）。

---

## 迁移脚本（`scripts/migrate_to_folder_structure.py`，新增）

### 分组 key

每个文件按**自己 frontmatter 里的 `source_url`** 算 hash 决定归属文件夹——不依赖文件名匹配或双链，天然兼容"译文文件名与原文不同"的情况。

### 双链作为交叉校验（不是分组依据）

对每篇译文，解析其 `[[Origin/xxx.md]]` 双链，找到对应原文文件，比较该原文的 `source_url` 与译文自己的 `source_url`：

- 一致 → 正常（两者本就会因为 url 相同落进同一 hash 文件夹）
- 不一致，或链接缺失/悬空 → 记入"链接异常"清单，**不阻塞迁移**，两个文件仍各自按自己的 `source_url` 正常归位

### frontmatter 冲突取译文

重建 `url-index.db` 时，title/category/tags/description 等字段两边都有就取译文的值（译文是打标签、写摘要后的最终版本）。

### 单边缺失

原文或译文只存在一侧时，正常迁移（对应"部分完成"状态），把已有的一侧放进对应 hash 文件夹，标记"部分完成"，并把该条记录（url、hash、缺失侧）汇总进"待补全清单"。

### 第二轮归一化 URL 比对

全部迁移完成后，对"待补全清单"做一次 URL 归一化比对（去协议头、去末尾斜杠、去 `utm_*` 等追踪参数），找出实际是同一篇文章但因 URL 字符串不完全一致被分到两个不同 hash 文件夹的 origin-only / translation-only 记录。

**只输出合并候选清单，不自动合并。** 用户人工确认后再执行合并（避免模糊匹配把不相干的两篇文章误合并）。

### 顺带修复的已知 bug

Reading 根目录下有 11 篇译文的图片链接错误写成 `![](../Image/xxx)`（本该是 `![](Image/xxx)`，是另一个 cron 流程 article-fetcher 写入的历史遗留问题）。迁移脚本反正要重写所有图片链接，顺带把这 11 篇也修正成新结构下的正确路径。

### 执行安全性

- 默认 dry-run，只打印迁移计划和统计（配对数/部分完成数/链接异常数/孤儿图片数），加 `--apply` 才真正执行
- 执行前自动对 Reading 目录打 tar 备份（带时间戳）
- 执行前提示用户关闭 Obsidian、暂停 iCloud 同步（Vault 目录里存在 `.sync-conflict-*` 文件，说明是同步中的目录）
- 用 `rename` 做移动（同文件系统内原子操作），单篇失败不中断整体，最后输出失败清单
- 幂等：目标文件夹已存在且内容符合预期则跳过，支持中断后重跑
- 迁移过程中重建 `url-index.db`（现有 150 行是不完整的旧索引，用扫描到的全量文章重新 upsert，覆盖旧值）
- 跳过 `.sync-conflict-*.md` 文件，不参与迁移

孤儿图片（未被任何文章正文引用到的图片）不移动，单独列清单供人工查看，不猜测归属。

---

## url-index.db

表结构不变。`origin_path`/`article_path` 两列存储的内容从旧的扁平绝对路径改为新的嵌套绝对路径。已确认 `dedup_check.py`（只读 `source_url`）、`count_article_stats.py`/`validate_article.py`（路径作为参数直接透传，不自行拼接）都不关心路径格式，无需改动。

---

## 落地顺序

1. 先改共享路径逻辑（`config.py` + 三个 playwright 脚本 + `article_utils.py` + subagent2 prompt），对**新抓取的文章**生效
2. 验证新流程跑通（抓取一篇真实文章，检查目录结构、双链、图片链接、DB 写入）
3. 跑迁移脚本 dry-run，人工检查计划和"链接异常/待补全/合并候选"清单
4. 关闭 Obsidian、暂停同步，跑 `--apply` 执行迁移
5. 人工确认第二轮合并候选清单，执行确认过的合并

---

## 测试范围

- `get_article_paths` 单测：不同 URL/标题组合的路径生成是否正确
- 迁移脚本的分组/异常分类逻辑：用小样本 fixture（不跑真实 Vault），覆盖完整配对、单边缺失、链接不一致、URL 归一化命中四种场景
- 迁移脚本本身：`--apply` 前必须能看到 dry-run 输出

---

## 不在范围内

- `url-index.db` 里 `urls`/`articles` 两张未使用遗留表的清理
- article-fetcher（cron 抓取流程）自身的路径约定改造——只在迁移脚本里顺带修掉它写出的 11 篇错误图片链接，不改它的抓取逻辑
- 孤儿图片的自动归属或清理
