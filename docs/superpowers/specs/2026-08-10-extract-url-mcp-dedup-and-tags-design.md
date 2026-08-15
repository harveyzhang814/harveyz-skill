# extract-url-mcp URL 去重与固定标签词表 Design

## Motivation

`extract-url-mcp` 目前是"Stage 4 验证性构建"：调用方每次传入一个临时 `output_dir`，不写真实 Obsidian Vault，没有 URL 去重，标签由 LLM 自由生成、不参考任何受控词表。这次要补上去重和标签两项能力，并且要求"配置内容和 extract-url 相同"——即直接共用 `extract-url` 真实的 `VAULT_PATH` 和 `fixed_tags.txt`，让两个 skill 抓过的文章互相认得出"已经抓过"，标签也用同一套词表。

## Scope

**In scope：**
- 去重：抓取前查 `<hash8>/meta.json` 是否已存在且 `source_url` 匹配，命中则跳过；抓取成功后写 `meta.json`，让后续调用（不论走哪个 skill）都能查到。
- 标签：Subagent 2 改为两阶段——从正文提炼 `candidate_tags`，从共享的 `fixed_tags.txt` 词表里匹配 `tags`，规则与 extract-url 完全一致；写文件后跑一遍"命中固定词表就从 candidate_tags 挪进 tags"的兜底逻辑。
- `extract-url-mcp` 改为强制使用共享的 `VAULT_PATH`（读取 `~/.hskill/url-extract/config.json`），不再接受调用方传入的 `output_dir`。

**Out of scope：**
- 不改动 `browser-fetch-mcp`（`tools/browser-fetch-mcp/`）——这次改动完全在 `extract-url-mcp` 客户端一侧，`fetch_article`/`markdown.assemble_and_write` 的行为不变。
- 不做 `repair_frontmatter` 那套畸形 YAML 自动修复机制——`extract-url-mcp` 的 frontmatter 是服务端（`markdown.py`）统一生成的干净格式，不像 extract-url 历史上那样需要这层防御性修复。
- `CHROME_PROFILE` 保持现状，不与 extract-url 的 `CHROME_PROFILE` 配置合并——两者是不同的持久化位置（`browser-fetch-mcp` 自己的 `~/.hskill/browser-fetch-mcp/`  vs. extract-url 的 `~/.hskill/url-extract/config.json`），本次不动。
- 不修复 Origin 文件命名不一致的问题：`browser-fetch-mcp` 的 `markdown.assemble_and_write` 固定写 `article.md`，extract-url 写 `sanitize_filename(标题) + '.md'`。两边现在会共用同一套 `<hash8>/` 目录结构，所以 `extract-url-mcp` 抓的文章文件名会跟 extract-url 抓的看起来不一致。去重逻辑不受影响（`meta.json` 只比对 `source_url`，不比对文件名），这里只是记录下这个已知的观感差异，留作后续可选的清理项。
- 不做 `extract-url-mcp` 自己独立的 VAULT_PATH/fixed_tags.txt 初始化对话流程——如果共享配置不存在，提示用户先运行 `extract-url` 完成初始化，不重复造一套初始化 UI。

## Architecture

```
extract-url-mcp
  │
  ├─ scripts/vault_config.py（新增）
  │    读取 ~/.hskill/url-extract/config.json 的 VAULT_PATH（支持环境变量覆盖，供测试用）
  │    get_vault_path() / get_url_hash(url) / get_article_paths(url)
  │
  ├─ scripts/dedup_check.py（新增，照抄 extract-url 版本重写）
  │    检查 <hash8>/meta.json 是否存在且 source_url 匹配
  │    打印 ALREADY_FETCHED 或 OK
  │
  ├─ scripts/article_meta.py（新增，从 extract-url 的 article_utils.py 里挑需要的部分重写）
  │    load_fixed_tags(path)
  │    write_meta_json(url, meta_path, article_path, category='')
  │    enforce_tag_separation(article_path, fixed_tags_path)
  │
  ├─ scripts/write_meta_and_separate.py（新增，CLI 包装脚本）
  │    供 Subagent 2 以 subprocess 方式调用，内部依次调用
  │    article_meta.write_meta_json + article_meta.enforce_tag_separation
  │
  ├─ scripts/mcp_fetch_client.py（改动）
  │    fetch_and_report/fetch_and_save 不再接受 output_dir 参数
  │    改为内部调用 vault_config.get_article_paths(url) 计算 article_dir
  │
  ├─ references/subagent1-fetch-prompt.md（改动）
  │    新增步骤 0：调用 dedup_check.py，ALREADY_FETCHED 则报告跳过并结束
  │
  ├─ references/subagent2-tag-translate-prompt.md（改动）
  │    阶段 1a：从正文提炼 candidate_tags（规则照搬 extract-url）
  │    阶段 1b：从共享 fixed_tags.txt 匹配 tags（规则照搬 extract-url）
  │    新增最后一步：调用 article_meta.write_meta_json + enforce_tag_separation
  │
  └─ SKILL.md（改动）
       去掉 OUTPUT_DIR 占位符相关内容
       新增共享配置存在性检查（不存在则提示先跑 extract-url）
       更新参考文件表
```

## Component 1：`vault_config.py`

```python
def get_vault_path() -> str:
    """读取 ~/.hskill/url-extract/config.json 的 VAULT_PATH。
    路径支持环境变量 HSKILL_EXTRACT_URL_CONFIG 覆盖（测试用）。
    文件不存在或缺少 VAULT_PATH 时抛出清晰的错误，提示用户先运行 extract-url 完成初始化。"""

def get_url_hash(url: str) -> str:
    """md5(url)[:8]，与现有 mcp_fetch_client.py 的 _hash8 算法一致。"""

def get_article_paths(url: str) -> dict:
    """返回 {article_dir, origin_path, translation_path, meta_path}。
    article_dir = VAULT_PATH/<hash8>
    origin_path = article_dir/Origin/article.md（文件名固定，不按标题命名——与现有行为一致）
    translation_path = article_dir/Translation/article.md
    meta_path = article_dir/meta.json"""
```

## Component 2：`dedup_check.py`

行为与 extract-url 版本一致：通过环境变量 `CHECK_URL` 传参（避免 shell 注入），检查 `meta_path` 是否存在且其中 `source_url` 与传入 URL 匹配，打印 `ALREADY_FETCHED` 或 `OK`。

## Component 3：`article_meta.py`

只搬运 `article_utils.py` 里去重和标签相关的三个函数，不搬运 `repair_frontmatter`/`sanitize_filename`/`build_article_from_json` 等本次用不到的部分：

- `load_fixed_tags(path)` — 读取分组注释文本文件，跳过 `#` 开头行和空行，返回 set。
- `write_meta_json(url, meta_path, article_path, category='')` — 写入 `{source_url, title, category, fetched_at, issues}`，`title` 取 `os.path.basename(article_path)`（本次固定是 `"article.md"`，见 Out of scope 里的命名不一致说明）。不搬运原版里 `.fetch_issues.tmp` 合并逻辑——`extract-url-mcp` 没有 Subagent 1 阶段问题记录机制，这部分不适用。
- `enforce_tag_separation(article_path, fixed_tags_path)` — 读文章 frontmatter 的 `tags`/`candidate_tags`，把命中 `fixed_tags_path` 词表的 `candidate_tags` 条目挪进 `tags`，就地改写文件；`fixed_tags_path` 不存在或没有变动则不改文件。

## Component 4：`mcp_fetch_client.py` 改动

`fetch_and_report(url, chrome_profile=None) -> dict` 和 `fetch_and_save(url, chrome_profile=None) -> Path` 去掉 `output_dir` 参数，内部调用 `vault_config.get_article_paths(url)` 得到 `article_dir` 传给 `fetch_article`。`main()` 的 CLI 参数相应减少一个位置参数（`<url> [chrome_profile]`，不再需要 `<output_dir>`）。

## Component 5：Subagent 1 去重检查

`subagent1-fetch-prompt.md` 新增步骤 0（在现有抓取步骤之前）：

```python
import subprocess, os
result = subprocess.run(
    ['python3', 'SkillDir/scripts/dedup_check.py'],
    env={'CHECK_URL': url_safe, 'PATH': os.environ.get('PATH', '')},
    capture_output=True, text=True
)
```

`ALREADY_FETCHED` → 报告"已抓取，跳过"并结束，不再调用 `mcp_fetch_client.py`。`OK` → 按现有流程继续。

## Component 6：Subagent 2 两阶段打标 + meta.json 写入

`subagent2-tag-translate-prompt.md` 的打标部分改为两阶段，规则文字照搬 extract-url 现有版本（代表性与抽象粒度、并列清单合并、去重合并、术语保留原文四条规则一字不改）：

- 阶段 1a：从正文提炼 `candidate_tags` + 一句话摘要 `description`。
- 阶段 1b：读取共享 `fixed_tags.txt`，匹配出 `tags`（规则同样照搬：须是核心论点或反复呈现的主题，不能是仅提及一次的例子/引用来源；不与 `candidate_tags` 语义重复）。

写文件后新增最后一步（照抄 `validate_article.py`，去掉 frontmatter 修复部分）：

```python
import subprocess, os
result = subprocess.run(
    ['python3', 'SkillDir/scripts/write_meta_and_separate.py'],
    env={
        'ARTICLE_URL': url,
        'ARTICLE_PATH': translation_path,
        'PATH': os.environ.get('PATH', ''),
    },
    capture_output=True, text=True, timeout=60
)
```

（这里 `write_meta_and_separate.py` 是一个小的 CLI 包装脚本，内部调用 `article_meta.write_meta_json` + `article_meta.enforce_tag_separation`，供 Subagent 2 以 subprocess 方式调用——保持与现有脚本调用风格一致，不在 prompt 里直接内联复杂 Python 逻辑。）

## Component 7：SKILL.md 改动

- 去掉现有"确认默认 chrome_profile"步骤之外，新增一步：检查 `~/.hskill/url-extract/config.json` 是否存在；不存在则提示"请先运行 extract-url skill 完成初始化（配置 VAULT_PATH 和固定词表）"，流程终止。
- 去掉所有 `<OUTPUT_DIR>` 占位符替换逻辑（Subagent 1 派发不再需要这个参数）。
- 更新参考文件表，加入新增的三个脚本。

## Testing

- `vault_config.py`：单测覆盖 `get_vault_path`（正常读取、文件不存在报错、缺 VAULT_PATH 报错）、`get_url_hash`、`get_article_paths`（路径拼接正确性），全部用 `HSKILL_EXTRACT_URL_CONFIG` 环境变量指向 `tmp_path` 下的假 config，不碰真实配置。
- `dedup_check.py`：单测覆盖首次调用（无 meta.json → OK）、重复调用（meta.json 存在且 source_url 匹配 → ALREADY_FETCHED）、meta.json 存在但 source_url 不匹配（→ OK，不同 URL 哈希碰撞的情况理论上不会发生，但保留这个边界行为一致）。
- `article_meta.py`：单测覆盖 `load_fixed_tags`（正常解析、跳过注释/空行、文件不存在返回空 set）、`write_meta_json`（写入正确字段）、`enforce_tag_separation`（命中词表挪动、未命中不挪动、无 candidate_tags 不改文件、fixed_tags_path 不存在不改文件）。
- `write_meta_and_separate.py`：作为薄 CLI 包装脚本，测试覆盖正常调用（写出 meta.json、按需挪动 candidate_tags）和参数缺失时的报错退出码，不重复测试 `article_meta.py` 已覆盖的内部逻辑。
- `mcp_fetch_client.py`：现有真实网络测试（`test_fetch_and_save_writes_real_content` 等）改为通过 `HSKILL_EXTRACT_URL_CONFIG` 指向 `tmp_path` 下的假 VAULT_PATH，不再传 `output_dir` 参数，验证文章确实写到 `<假VAULT_PATH>/<hash8>/Origin/article.md`。
- 所有测试全程不得写入真实的 `~/.hskill/url-extract/` 或真实 Obsidian Vault。

## Global Constraints

- `VAULT_PATH` 只读，来自 `~/.hskill/url-extract/config.json`（与 extract-url 完全同一份配置文件），不新增独立的 extract-url-mcp 专属配置。
- `fixed_tags.txt` 只读，路径固定 `~/.hskill/url-extract/fixed_tags.txt`，与 extract-url 完全同一份词表文件。
- 所有新脚本/改动脚本的测试必须通过环境变量覆盖配置路径，不得读写真实的 `~/.hskill/url-extract/` 目录。
- 不搬运 `repair_frontmatter`，不新增 extract-url-mcp 自己的初始化对话流程。
- Design spec 讨论过程中明确的决定：直接共用 extract-url 真实 VAULT_PATH；强制使用共享 VAULT_PATH（不保留调用方自定义 output_dir 的选项）；去重/标签逻辑在 extract-url-mcp 内独立重写，不跨 skill import extract-url 的代码。
