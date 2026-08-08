---
migrated: false
---

# extract-url-mcp Stage 1：设计

## 背景

`browser-fetch-mcp`（Phase A，已合并进 `staging`）是一个独立的 MCP server，还没有被任何真实消费者调用过——之前所有验证都是它自己的单元/e2e 测试直接 spawn 自己。这次要写一个新的、独立命名的 skill（`extract-url-mcp`），像真实消费者一样通过 MCP 协议调用它，验证这条链路在实际使用场景里能跑通。

不修改 `extract-url` 或 `probe-session`。不注册进 `~/.claude.json` 的 `mcpServers`（那需要重启/重连才能生效，这轮先不依赖）。

## 范围

分两阶段，本设计只覆盖 **Stage 1**：验证"调用 browser-fetch-mcp 抓取一个 URL 并保存原文"这条链路。Stage 2（打标+翻译+存 Obsidian，复刻 extract-url 的 Subagent 2）在 Stage 1 跑通之后再做，不在这次范围内。

**做：**
- `scripts/mcp_fetch_client.py`：全新脚本，作为真实 MCP client，spawn `tools/browser-fetch-mcp/browser-fetch-mcp.sh` 作为 stdio server，调用 `fetch_page(url)`，从返回的原始 HTML 里提取标题和正文段落（用标准库 `html.parser`，不引入新依赖——`mcp` 包已全局可用，不需要 playwright，因为浏览器逻辑全部在 browser-fetch-mcp 那一侧），写一个 Origin markdown 文件。
- `SKILL.md` + `references/subagent1-fetch-prompt.md`：最小化的编排层，证明"以 skill 派发的方式调用这条新抓取链路"这个形状也是通的，不只是脚本本身能跑。
- 测试：用一个真实 URL 跑一遍，确认 Origin 文件被写出且内容非空。

**不做：**
- 打标、翻译、存 Obsidian（Stage 2）
- 写 `~/.hskill/extract-url-mcp/config.json` 之类的正式配置初始化流程——Stage 1 的输出目录先写死/传参，不需要完整的用户配置向导
- 登录态抓取（`use_auth`）——Stage 1 只验证匿名抓取链路
- `skills-index.json` 注册——这是验证性质的构建，不对外发布
- 多平台补丁的实际差异化实现——`scripts/mcp_fetch_client.py` 是纯 Python + subprocess，任何能跑 bash+python3 的平台都能调用，四平台补丁只是复制 extract-url 的①派发差异模式，不需要针对 MCP 做平台特化

## 输出契约（对齐 extract-url 现有模式）

`mcp_fetch_client.py <url> <output_dir>` 执行后：
- stdout 最后一行 `ORIGIN_PATH: <path>`（与 extract-url 的 Subagent 1 契约一致，方便未来 Stage 2 复用同样的编排模式）
- Origin 文件格式（frontmatter + 正文），字段对齐 `docs/reference/file-format.md` 里 extract-url 现有约定的最小子集：`source_url`、`fetch_date`、`origin_title`

## 验证方式

用真实网络请求（`https://example.com` 或类似的简单页面）跑一次完整链路，人工确认 Origin 文件内容正确。这是本轮唯一的验收标准。
