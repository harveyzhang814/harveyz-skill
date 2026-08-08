---
name: extract-url-mcp
version: "0.2.0"
description: "Stage 2 validation build — NOT for real use. Fetches a URL through the browser-fetch-mcp MCP server (instead of extract-url's direct Playwright subprocess), tags, translates, and saves origin + translation. Proves the MCP-based fetch path works end to end inside a two-subagent flow shaped like extract-url."
user_invocable: true
---

# extract-url-mcp（Stage 2，验证性构建）

这是 [browser-fetch-mcp](../../../tools/browser-fetch-mcp/) 的验证性消费者，不是给 extract-url 用的真实替代品。做"抓取（MCP）→ 打标 + 翻译 → 存文件"两阶段流程，跟 extract-url 的 Subagent 1/2 结构对齐，但做了简化（无固定词表、无 URL 去重、不写真实 Obsidian Vault）。不接受真实产品使用，只用于验证 MCP 抓取链路能否支撑一个完整的两阶段 skill 流程。

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

读取 `references/subagent1-fetch-prompt.md`，将其中 `<URL>` 替换为 url_safe，`<OUTPUT_DIR>` 替换为一个输出目录（Stage 2 没有正式的 VAULT_PATH 配置流程，调用方直接指定一个测试目录，不写真实 Obsidian Vault），按当前平台的 subagent 派发机制派发。

### 步骤 3：等待 Subagent 1 完成

从报告中提取 `ORIGIN_PATH:` 开头的那行，取其值作为 origin_path。

### 步骤 4：派发 Subagent 2（打标 + 翻译）

读取 `references/subagent2-tag-translate-prompt.md`，将其中 `<ORIGIN_PATH>` 替换为上一步的 origin_path，按当前平台的 subagent 派发机制派发。

### 步骤 5：向用户报告

从 Subagent 2 报告中提取 `TRANSLATION_PATH:`，向用户报告 origin_path 和 translation_path。

## 参考文件

| 文件 | 用途 |
|------|------|
| `references/subagent1-fetch-prompt.md` | Subagent 1（MCP 抓取）派发 prompt 模板 |
| `references/subagent2-tag-translate-prompt.md` | Subagent 2（打标 + 翻译）派发 prompt 模板 |
| `scripts/mcp_fetch_client.py` | 核心脚本：真实 MCP client，调用 browser-fetch-mcp 的 `fetch_page` |
