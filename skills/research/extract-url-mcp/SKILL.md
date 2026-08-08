---
name: extract-url-mcp
version: "0.3.0"
description: "Stage 3 validation build — NOT for real use. Fetches a URL through browser-fetch-mcp's fetch_article (site-aware extraction: generic/wechat/arxiv/xcom, with image download), tags, translates, and saves origin + translation. Proves the MCP-based fetch path works end to end inside a two-subagent flow shaped like extract-url."
user_invocable: true
---

# extract-url-mcp（Stage 3，验证性构建）

这是 [browser-fetch-mcp](../../../tools/browser-fetch-mcp/) 的验证性消费者，不是给 extract-url 用的真实替代品。做"抓取（MCP，经 fetch_article 做站点感知抽取）→ 打标 + 翻译 → 存文件"两阶段流程，跟 extract-url 的 Subagent 1/2 结构对齐，但做了简化（无固定词表、无 URL 去重、不写真实 Obsidian Vault）。不接受真实产品使用，只用于验证 MCP 抓取链路能否支撑一个完整的两阶段 skill 流程。

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

### 步骤 2：判断是否需要询问 chrome_profile（仅 x.com/twitter.com）

```python
from urllib.parse import urlparse
hostname = urlparse(url_safe).hostname or ""
needs_xcom_auth = hostname in ("x.com", "www.x.com", "twitter.com", "www.twitter.com")
```

若 `needs_xcom_auth` 为真：

1. 运行 `python3 SkillDir/scripts/detect_xcom_chrome_profile.py`，把完整输出（对比表 + `RECOMMENDED_PROFILE:` 那行）原样展示给用户。
2. 向用户提问：使用推荐的 profile？或输入一个替代的 profile 路径？注意：x.com 抓取需要登录态，没有匿名抓取选项——必须提供有效的 Chrome profile 路径。
3. 等用户明确回答后：
   - 若用户提供了有效的 profile 路径（推荐的或自己输入的），记为 `chrome_profile`，继续派发 Subagent 1。
   - 若用户选择不提供 profile（例如没有找到合适的账户），报告给用户"x.com 抓取需要登录态，无法继续"，然后停止流程——不派发 Subagent 1。

**不允许**：探测完不询问用户、直接把探测到的 profile 传给 Subagent 1——这一步必须有用户明确确认，且只有确认了有效的 profile 才能派发。

若 `needs_xcom_auth` 为假，`chrome_profile` 直接设为空（不留任何字符），不运行探测脚本、不询问用户。

### 步骤 3：派发 Subagent 1（MCP 抓取）

读取 `references/subagent1-fetch-prompt.md`，将其中 `<URL>` 替换为 url_safe，`<OUTPUT_DIR>` 替换为一个输出目录（没有正式的 VAULT_PATH 配置流程，调用方直接指定一个测试目录，不写真实 Obsidian Vault），`<CHROME_PROFILE>` 替换为上一步确定的 chrome_profile，按当前平台的 subagent 派发机制派发。

### 步骤 4：等待 Subagent 1 完成

从报告中提取 `ORIGIN_PATH:` 开头的那行，取其值作为 origin_path。

### 步骤 5：派发 Subagent 2（打标 + 翻译）

读取 `references/subagent2-tag-translate-prompt.md`，将其中 `<ORIGIN_PATH>` 替换为上一步的 origin_path，按当前平台的 subagent 派发机制派发。

### 步骤 6：向用户报告

从 Subagent 2 报告中提取 `TRANSLATION_PATH:`，向用户报告 origin_path 和 translation_path。

## 参考文件

| 文件 | 用途 |
|------|------|
| `references/subagent1-fetch-prompt.md` | Subagent 1（MCP 抓取）派发 prompt 模板 |
| `references/subagent2-tag-translate-prompt.md` | Subagent 2（打标 + 翻译）派发 prompt 模板 |
| `scripts/mcp_fetch_client.py` | 核心脚本：真实 MCP client，调用 browser-fetch-mcp 的 `fetch_article` |
| `scripts/detect_xcom_chrome_profile.py` | 检测哪个 Chrome profile 登录了 x.com（只查 cookie 存在性，不解密），仅供用户确认用，不自动使用检测结果 |
