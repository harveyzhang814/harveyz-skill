---
name: extract-url-mcp
version: "0.5.0"
description: "Fetches a URL through browser-fetch-mcp's fetch_article (site-aware extraction: generic/wechat/arxiv/xcom, with image download and a persisted default chrome_profile), tags against extract-url's shared fixed-tag vocabulary, translates, and saves origin + translation into extract-url's real shared Obsidian Vault (VAULT_PATH) with cross-skill URL dedup. Not extract-url's full equivalent yet (no frontmatter auto-repair), but writes real vault content, not a validation-only test directory."
user_invocable: true
---

# extract-url-mcp（Stage 4，验证性构建）

这是 [browser-fetch-mcp](../../../tools/browser-fetch-mcp/) 的验证性消费者，跟 extract-url 的 Subagent 1/2 结构对齐，做"抓取（MCP，经 fetch_article 做站点感知抽取）→ 打标 + 翻译 → 存文件"两阶段流程。URL 去重和固定标签词表与 extract-url 共用同一份 `~/.hskill/url-extract/config.json`（`VAULT_PATH`）和 `fixed_tags.txt`，两边抓过的文章互相认得出"已抓取"。仍不是 extract-url 的完全等价替代（例如没有 `validate_article.py` 那样的 frontmatter 自动修复），只用于验证 MCP 抓取链路能否支撑一个完整的两阶段 skill 流程并逐步对齐生产行为。抓取产出的原文文件名固定为 `Origin/article.md`（与 extract-url 按标题命名的 `Origin/<标题>.md` 不同），两者共存于同一个 `<hash8>/` 目录下，去重判定只看 `meta.json` 的 `source_url`，不受文件名差异影响。

## 路径变量

```
SkillDir: skills/research/extract-url-mcp
```

## 执行流程

### 步骤 1：净化 URL

```python
import re
url_safe = re.sub(r'[\x00-\x1f\x7f]', '', url).strip()[:2048]
```

### 步骤 2：确认默认 chrome_profile（首次使用时设置一次，之后不再询问）

运行 `python3 SkillDir/scripts/chrome_profile_config.py get`。

- 若输出 `CONFIGURED: <path>`：已经配置过默认 profile，跳过下面的检测和提问，直接进入步骤 3。
- 若输出 `NOT_CONFIGURED`（不论当前 URL 是什么网站，只要还没配置过就会命中这一分支）：
  1. 运行 `python3 SkillDir/scripts/detect_xcom_chrome_profile.py`，把完整输出（对比表 + `RECOMMENDED_PROFILE:` 那行）原样展示给用户。
  2. 向用户提问：把推荐的 profile 设为以后的默认值？或输入一个替代路径？也可以选择这次先不设置。
  3. 若用户提供了 profile 路径（推荐的或自己输入的）：运行 `python3 SkillDir/scripts/chrome_profile_config.py set <path>` 持久化。此后所有网站的抓取都不会再触发这个设置流程。
  4. 若用户选择不设置：不持久化任何值，本次继续（x.com 的 URL 会在 Subagent 1 里因为 browser-fetch-mcp 的 `fetch_article` 报错而失败——x.com 没有匿名抓取选项；非 x.com 的 URL 正常匿名抓取，不受影响）。

**不允许**：跳过展示直接把探测到的 profile 设为默认值——必须等用户明确回答，且只有用户确认后才能调用 `chrome_profile_config.py set`。

### 步骤 2.5：确认共享配置存在（VAULT_PATH / 固定词表）

```python
import subprocess
result = subprocess.run(
    ['python3', '-c',
     'import sys; sys.path.insert(0, "SkillDir/scripts"); import vault_config; print(vault_config.get_vault_path())'],
    capture_output=True, text=True
)
```

- 若 `result.returncode != 0`（`config.json` 不存在，或存在但缺 `VAULT_PATH` 字段）：向用户报告"请先运行 extract-url skill 完成初始化（配置 Obsidian Vault 路径和固定标签词表），再回来使用本 skill"，流程终止。
- 若 `result.returncode == 0`：再检查 `~/.hskill/url-extract/fixed_tags.txt` 是否存在：
  ```bash
  ls ~/.hskill/url-extract/fixed_tags.txt 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
  ```
  不存在也不阻断流程——固定标签匹配会自动跳过（`tags` 恒为空列表，只有 `candidate_tags` 生效），但要提示用户一句"固定词表文件不存在，本次抓取只会生成候选标签，不会匹配固定标签"。继续步骤 3。

### 步骤 3：派发 Subagent 1（MCP 抓取）

读取 `references/subagent1-fetch-prompt.md`，将其中 `<URL>` 替换为 url_safe，`<CHROME_PROFILE>` 替换为空（不留任何字符）——browser-fetch-mcp 的 `fetch_article` 会自己解析已持久化的默认 chrome_profile，不需要这里显式传值，按当前平台的 subagent 派发机制派发。文章存储目录由 Subagent 1 内部通过共享的 VAULT_PATH 自动计算，不再需要这里传参。

### 步骤 4：等待 Subagent 1 完成，判断是否需要自优化

从报告中读取 `RESULT:` 那行。

- 若 `RESULT: SKIPPED`：该 URL 已经抓取过（去重命中），向用户报告"已抓取，跳过"并附上 `META_PATH:` 所在的文章目录，流程终止，不再派发 Subagent 2 或 Subagent 3。
- 若 `RESULT: OK` 且（`CONTENT_THIN: False`，或 `CONTENT_THIN: True` 但 `THIN_RETRY_USED: False`）：提取 `ORIGIN_PATH:` 那行的值作为 origin_path，跳到步骤 5。`CONTENT_THIN: True` 且 `THIN_RETRY_USED: False` 的情况（例如文章本来就短、或没有配置 chrome_profile 因而从未触发过认证重试）不算需要自优化——没有更多现有手段可以尝试，按正常内容处理。
- 若 `RESULT: OK` 且 `CONTENT_THIN: True` 且 `THIN_RETRY_USED: True`，或 `RESULT: FAILED`：进入步骤 4.5（自优化）。本次 URL 最多只走一次步骤 4.5——若步骤 4.5 重试后仍然满足这个条件，直接终止流程向用户报告，不再第二次派发自优化 subagent。

### 步骤 4.5：派发 Subagent 3（自优化，仅在步骤 4 判定需要时执行）

读取 `references/subagent-self-optimize-prompt.md`，把 `<URL>` 替换为 url_safe，`<CHROME_PROFILE>` 替换为已持久化的默认 chrome_profile（没有则留空，不留任何字符），其余占位符（`<SITE>`/`<BLOCK_COUNT>`/`<CHAR_COUNT>`/`<CONTENT_THIN>`/`<THIN_RETRY_USED>`/`<ERROR>`）替换为 Subagent 1 报告里对应字段的值（`RESULT: FAILED` 时 `<SITE>`/`<BLOCK_COUNT>`/`<CHAR_COUNT>`/`<CONTENT_THIN>`/`<THIN_RETRY_USED>` 全部替换为 `N/A`，`<ERROR>` 替换为 Subagent 1 报告里 `ERROR:` 那行的实际内容；`RESULT: OK` 时 `<ERROR>` 替换为空），按平台的 subagent 派发机制派发。

- Subagent 3 报告 `RESULT: SOLIDIFIED`：记下 `BRANCH:` 的值（步骤 6 汇报要用），重新派发 Subagent 1（同一个 url_safe），回到步骤 4 重新判断一次——若此次判断仍然需要自优化，直接终止并向用户报告，不再进入步骤 4.5。
- Subagent 3 报告 `RESULT: GAVE_UP`，或重试后 Subagent 1 仍然满足步骤 4 的自优化触发条件：向用户报告失败（带上 Subagent 1 最新的诊断信息，以及 Subagent 3 报告里的 `ATTEMPTS`/`DIAGNOSIS`，如果有），流程终止，不再派发 Subagent 2。

### 步骤 5：派发 Subagent 2（打标 + 翻译）

读取 `references/subagent2-tag-translate-prompt.md`，将其中 `<URL>` 替换为 url_safe，`<ORIGIN_PATH>` 替换为上一步的 origin_path，按当前平台的 subagent 派发机制派发。

### 步骤 6：向用户报告

从 Subagent 2 报告中提取 `TRANSLATION_PATH:`，向用户报告 origin_path 和 translation_path。若本次运行中步骤 4.5 曾经出现过 `RESULT: SOLIDIFIED`，额外报告一行：本次抓取新增了未合并分支 `<BRANCH>`，需要用户决定后续（合并/PR/保留）。

## 参考文件

| 文件 | 用途 |
|------|------|
| `references/subagent1-fetch-prompt.md` | Subagent 1（MCP 抓取）派发 prompt 模板，含去重检查 |
| `references/subagent2-tag-translate-prompt.md` | Subagent 2（两阶段打标 + 翻译）派发 prompt 模板 |
| `references/subagent-self-optimize-prompt.md` | Subagent 3（自优化，抓取失败/过薄时触发）派发 prompt 模板 |
| `scripts/vault_config.py` | 读共享 `VAULT_PATH`（`~/.hskill/url-extract/config.json`），计算文章路径 |
| `scripts/dedup_check.py` | URL 去重检查（读 `<hash8>/meta.json`） |
| `scripts/article_meta.py` | 去重索引写入 + 固定词表兜底移位（纯函数库） |
| `scripts/write_meta_and_separate.py` | Subagent 2 用的 CLI 包装，调用 `article_meta` 写 meta.json + 移位 |
| `scripts/mcp_fetch_client.py` | 核心脚本：真实 MCP client，调用 browser-fetch-mcp 的 `fetch_article`，`fetch_and_report` 额外返回诊断字段 |
| `scripts/mcp_debug_client.py` | 自优化 subagent 用的调试客户端，包装 browser-fetch-mcp 的 `fetch_page`/`evaluate_js` |
| `scripts/detect_xcom_chrome_profile.py` | 通过 browser-fetch-mcp 的 `list_chrome_profiles` MCP 工具检测哪些 Chrome profile 登录了 x.com，仅供用户确认用，不自动使用检测结果 |
| `scripts/chrome_profile_config.py` | 读写 browser-fetch-mcp 持久化的默认 chrome_profile（`get`/`set` 子命令） |
