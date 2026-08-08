---
migrated: false
---

# browser-fetch-mcp Phase A：设计

> **实现后更新：** 本文原按 `mcp` 1.x 的 `FastMCP` 类撰写。最终评审发现 `pyproject.toml` 未设上限的 `mcp>=1.28.0` 在洁净安装下实际解析到 `mcp==2.0.0`，而该版本已将 `FastMCP` 更名为 `MCPServer`（API 形状不变：`.tool()` 装饰器、`.run(transport="stdio")`）。已实现代码以 `mcp>=2.0.0` + `MCPServer` 为准，下文提及 FastMCP 之处均指同一机制。

## 背景

`skills/research/extract-url` 的 `playwright_web.py` / `playwright_xcom.py` 和 `skills/research/probe-session` 的 `probe.py`，各自独立实现了同一套逻辑：从 Chrome Profile 复制解密 cookie（`pycookiecheat`），注入 Playwright headless context，抓取需要登录态才能访问的页面。两个 skill 是这个问题域下真实存在、当前就重复的两个消费者——不是预测性需求。

一次可行性实验（见 [docs/explanation/mcp-browser-fetch-experiment.md](../../explanation/mcp-browser-fetch-experiment.md)）验证了：

- 常驻 Playwright `persistent_context` 相比每次调用冷启动浏览器，热复用调用快约 26 倍（0.995s → 0.038s）
- 登录态 cookie（带 `expires` 的持久 cookie）能跨进程重启在 persistent context 的 profile 目录里存活，可以替代"每次调用都复制解密 Chrome cookie 数据库"的现有方案
- FastMCP 的工具函数跑在 server 自己的 asyncio event loop 里，必须用 `playwright.async_api`，不能用 `sync_api`（会直接报错拒绝执行）
- 跨平台约束仍未解决：`extract-url` 现有的 subprocess 调用模型对 Claude Code / Codex / Hermes / Pi 四个平台统一有效，MCP 化只能覆盖有 MCP client 支持的平台（至少 Claude Code、大概率 Codex；Hermes、Pi 未验证）

## 定位

仓库级共享基础设施，从设计上支持多消费者（当前已知：extract-url、probe-session），不是 extract-url 专属。

分阶段推进：

- **Phase A（本设计范围）**：只建 MCP server 本身，含自测。不迁移任何现有 skill，不接入任何平台的 MCP client 配置。
- **Phase B（后续）**：把 extract-url 和 probe-session 迁移到实际调用这个 server，替掉各自重复的 `pycookiecheat` 逻辑。
- **Phase C（后续，视 Phase B 结果决定是否需要）**：在 MCP 之外加一层常驻 daemon + 薄 subprocess CLI，让 Hermes/Pi 等没有 MCP client 的平台也能拿到"常驻上下文 + 免 cookie 复制"的收益，MCP 变成其中一种可选传输层而非唯一入口。

## Phase A 范围

**做**：

- 新建 `tools/browser-fetch-mcp/` 包，遵循 `tools/hub`、`tools/sync-agent` 的既有打包惯例
- 实现一个 MCP 工具 `fetch_page(url, use_auth, chrome_profile)`，内部用常驻 `persistent_context` 抓取页面
- 自带测试：起 server 用真实 MCP client（stdio）连续调用，验证功能正确性和热复用效果

**不做**：

- 不修改 `extract-url` 或 `probe-session` 现有代码
- 不在任何平台的 MCP client 配置（`~/.claude.json` 的 `mcpServers` 等）里注册这个 server
- 不做任意 JS eval、内容块提取、cookie 跨 profile 共享缓存等消费者特定逻辑——这些要么应该留在各 skill 里，要么没有第二个真实需求支撑当前实现

## 架构

### 包结构

```
tools/browser-fetch-mcp/
  pyproject.toml         # hatchling, [project.scripts] 入口
  tool.json              # name/version/description/uninstallPaths（hskill tool 注册格式）
  browser-fetch-mcp.sh   # dev-mode 检测 + venv 惯例，照抄 tools/hub/hub.sh
  browser_fetch_mcp/
    __init__.py
    server.py            # FastMCP server + fetch_page 工具
  tests/
    test_server.py
```

复用 hskill 现有的 tool 安装/卸载机制（`~/.hskill/tools/browser-fetch-mcp/venv`），不发明新的分发方式。

### 工具面

```python
@mcp.tool()
async def fetch_page(
    url: str,
    use_auth: bool = False,
    chrome_profile: str | None = None,
) -> dict:
    """返回 {html: str, title: str, status: int, cookies_injected: int}"""
```

- `use_auth=False`：走常驻的匿名 persistent context，忽略 `chrome_profile`
- `use_auth=True` + `chrome_profile` 给定：从该 profile 提取解密 cookie，注入该 profile 对应的常驻认证态 context
- `use_auth=True` 但 `chrome_profile=None`：视为调用方参数错误，直接抛异常（MCP 工具调用失败），不静默退化成匿名抓取——避免调用方以为拿到了认证态结果、实际却是匿名内容
- `chrome_profile` 是参数，不是 server 启动时固定的 env var——因为不同消费者（extract-url、probe-session）各自 `config.json` 里配置的 Chrome Profile 可能不同，server 不能假设只有一个消费者

### 生命周期与并发

- 单进程持有多个 module-level 的 warm context，以 `chrome_profile`（`use_auth=False` 时用固定 key）为键懒加载、按需创建，避免不同消费者的登录态互相污染
- 必须用 `playwright.async_api`（实验已验证 sync API 在 FastMCP 的 event loop 里会直接报错）
- 不做进程崩溃自动重启——MCP client（Claude Code/Codex 的 MCP 管理机制）本身有进程生命周期管理，不重复造轮子

## 测试策略

`tests/test_server.py`，用 `mcp` SDK 的 client（stdio transport）连接真实 server 进程：

1. `use_auth=False` 基本抓取：返回的 `title`/`html` 符合预期
2. 连续两次调用同一 URL，验证第二次明显快于第一次（热复用生效，对照实验数据）
3. `use_auth=True` 但指定的 `chrome_profile` 下没有对应站点的 cookie：应返回 `cookies_injected: 0`，不抛异常——调用方（如 probe-session）需要能拿这个值做判断，这是 probe-session 现有逻辑里已经依赖的行为模式

## 风险 / 未解决问题（留给 Phase B/C）

- 跨平台约束：Hermes/Pi 是否有 MCP client 支持，这轮不验证
- 多消费者并发访问同一个 `chrome_profile` 的 context 时是否需要加锁——Phase A 只有自测，没有真实并发场景，留到 Phase B 迁移后观察
- 是否需要 server 侧的 cookie 有效期检测/失效提醒——当前 probe-session 已经有自己的诊断逻辑，Phase B 迁移时再决定这部分职责归属
