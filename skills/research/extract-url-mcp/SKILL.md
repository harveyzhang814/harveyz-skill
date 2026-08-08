---
name: extract-url-mcp
version: "0.1.0"
description: "Stage 1 validation build — NOT for real use. Fetches a URL through the browser-fetch-mcp MCP server (instead of extract-url's direct Playwright subprocess) and saves the origin content. Proves the MCP-based fetch path works end to end."
user_invocable: true
---

# extract-url-mcp（Stage 1，验证性构建）

这是 [browser-fetch-mcp](../../../tools/browser-fetch-mcp/) 的验证性消费者，不是给 extract-url 用的真实替代品。只做"抓取 + 存原文"（Stage 1），不做打标/翻译/存 Obsidian（Stage 2 未实现）。不接受真实产品使用，只用于验证 MCP 抓取链路。

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

### 步骤 2：派发 Subagent 1（MCP 抓取）

读取 `references/subagent1-fetch-prompt.md`，将其中 `<URL>` 替换为 url_safe，`<OUTPUT_DIR>` 替换为一个输出目录（Stage 1 没有正式的 VAULT_PATH 配置流程，调用方直接指定一个目录，例如临时目录），按当前平台的 subagent 派发机制派发。

### 步骤 3：向用户报告

收到 Subagent 1 完成通知后，从报告中提取 `ORIGIN_PATH:`，向用户报告文件路径。Stage 1 到此结束——不做打标、翻译、存 Obsidian。

## 参考文件

| 文件 | 用途 |
|------|------|
| `references/subagent1-fetch-prompt.md` | Subagent 1（MCP 抓取）派发 prompt 模板 |
| `scripts/mcp_fetch_client.py` | 核心脚本：真实 MCP client，调用 browser-fetch-mcp 的 `fetch_page` |
