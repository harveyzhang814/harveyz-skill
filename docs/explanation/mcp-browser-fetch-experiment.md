# 浏览器抓取 MCP 化实验：常驻 Playwright Context 能否替代 Cookie 复制

对 [chrome-profile-cookie-injection.md](chrome-profile-cookie-injection.md) 描述的方案做的一次小规模可行性实验：能不能用一个**常驻的、跑在 MCP server 里的 Playwright 上下文**，替代"每次调用都复制解密 Chrome cookie 数据库"这套 pycookiecheat 方案。

结论先行：核心机制成立，但目前只验证到"机制可行"这一层，**是否值得做成跨 skill 共享的 MCP 基础设施还没有设计**——这篇文档只记录实验发现，不代表决策。

---

## 起因：现有方案的两个成本

[chrome-profile-cookie-injection.md](chrome-profile-cookie-injection.md) 记录的机制本身没问题，但有两个跟"每次调用"绑定的成本：

- **每次都要复制+解密**：从 Chrome Profile 复制 `Cookies` 文件到 `/tmp`，触发 Keychain 解密，每次调用都重新做一遍。
- **每次都冷启动浏览器**：`extract-url` 的 `scripts/playwright_*.py` 是逐次 `subprocess.run` 起一个新的无头 Chromium，用完即弃。

如果登录态可以被一个常驻进程持有，这两个成本理论上都能摊掉。MCP server 天然是个可以常驻的进程，所以拿它做了这次实验。

---

## 实验设计

三个独立脚本，互不导入 extract-url 现有代码：

1. **基线**：每次调用 `chromium.launch()` 新起一个浏览器，测冷启动耗时。
2. **登录态跨进程存活测试**：进程 A 用 `launch_persistent_context(profile_dir)` 种一个 cookie，进程 B（全新进程，同一个 profile_dir）读回这个 cookie，验证 profile 目录能不能把登录态带过进程重启。
3. **真实 MCP server**：用 `mcp` Python SDK 的 FastMCP 写一个 `fetch_page(url)` 工具，内部持有一个模块级单例的常驻 `persistent_context`，通过一个真实的 stdio MCP client 连续调用 3 次。

---

## 发现

### 1. 常驻上下文确实能省掉冷启动

| | 耗时 |
|---|---|
| 基线（每次新开浏览器） | 平均 0.998s |
| MCP server 第 1 次调用（冷启动） | 0.995s |
| MCP server 第 2、3 次调用（复用常驻 context） | 0.038s / 0.036s |

热复用比冷启动快约 **26 倍**。这个数字只在 `https://example.com` 这种简单页面上测的，重网页会被网络/渲染耗时摊薄，但"浏览器进程本身的启动开销被消除"这件事是确定的。

### 2. 登录态能跨进程重启存活——但有一个前提

第一次测试失败了，原因值得记下来：测试 cookie 没设 `expires`，Chromium 把它当 **session cookie**，这类 cookie 设计上就不会写盘——不是 Playwright 或 persistent context 的限制，是浏览器的正常行为。补上一个未来过期时间后：

```python
ctx.add_cookies([{
    "name": "x", "value": "y", "domain": "example.com", "path": "/",
    "expires": time.time() + 3600 * 24 * 30,   # 必须有 expires，否则不落盘
}])
```

进程 A 种下的 cookie，在全新启动的进程 B 里读回来完全一致。真实网站的登录 cookie（如 X.com 的 `auth_token`）几乎都是带过期时间的持久 cookie，所以这条路径对实际场景是适用的。

### 3. FastMCP 的 tool 函数跑在 event loop 里，Playwright 必须用 async API

用 `playwright.sync_api` 直接报错：

```
It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead.
```

原因：FastMCP 的工具函数在 server 自己的 asyncio event loop 里执行，Playwright 的同步 API 会检测到自己身处已有事件循环并拒绝运行（这是 Playwright 的保护性限制，不是 bug）。换成 `playwright.async_api` 后正常工作。这是当前 `extract-url` 的 `playwright_*.py`（全部用 sync API，跑在独立 subprocess 里）完全不会遇到的坑——如果未来真的把这套逻辑搬进 MCP server，是一次不小的 API 改写量，不是纯粹的"照抄一遍"。

---

## 跨平台约束：还没解决

`extract-url` 是四平台 skill（Claude Code / Codex / Hermes / Pi），当前"浏览器自动化"部分之所以能覆盖全部四个平台，靠的是 `subprocess.run(['python3', 'SKILL_DIR/scripts/playwright_*.py', ...])`——任何能跑 bash + python3 的平台都能用，完全不依赖 MCP client 支持。

MCP 化必然要求每个平台的 agent 运行时都配置了 MCP client 并注册了对应 server。Codex 有 MCP 支持；Hermes、Pi 目前的补丁文件（`platforms/SKILL.hermes.md`、`platforms/SKILL.pi.md`）显示它们更精简（Pi 甚至没有原生网页抓取工具，靠 `curl`），没有证据表明这两个平台有 MCP client 能力。这次实验没有验证这一点，只是复述此前的评估结论——如果要往下推进，这是第一个需要落实的前提。

---

## 定位：跨 skill 基础设施候选，未设计

这次实验证明的是"常驻 MCP browser server 这个模式本身可行"，但没有涉及一个更大的问题：**能不能有一个所有 skill 都能调用的共享 MCP browser-fetch server，而不是每个 skill 各自实现一遍 Playwright 逻辑？**

这个更大范畴的问题还没讨论过，至少包括：

- 多 skill 复用时的 server 生命周期管理（谁启动、谁关闭、崩溃后怎么重启）
- 每个 skill 需要的抓取/提取逻辑差异很大（extract-url 的内容块提取 vs 未来其他 skill 可能需要的截图/表单交互），共享 server 的接口要设计成多通用
- 配置注入（profile 目录、超时、per-skill 的 JS 提取脚本）怎么在多 skill 场景下不互相污染
- 上一节的跨平台约束会不会让"共享基础设施"这个前提本身就不成立

这些都需要单独一轮 brainstorming 才能落地，这次实验只是给了一个"技术上可行"的最小证据，不是设计。

---

## 这次实验没有验证的部分

- 没有对接真实登录态网站（X.com/微信等），只用不需要登录的 `example.com` 测了 cookie 机制本身
- 没有测试官方 `@playwright/mcp` 或已配置的 `claude-in-chrome` MCP 作为替代路径（brainstorming 阶段讨论过，这次范围内明确排除了）
- 没有验证 Codex/Hermes/Pi 是否真的有 MCP client 支持，只是从现有补丁文件的证据做了推断
- 实验脚本本身是临时性的，写在 scratchpad 里跑完即弃，没有进 repo——这篇文档记录的是发现，不是可复用代码

---

## 相关文件

| 文件 | 用途 |
|------|------|
| [chrome-profile-cookie-injection.md](chrome-profile-cookie-injection.md) | 当前生产环境实际使用的方案：pycookiecheat 复制解密 cookie |
| [xcom-playwright-auth.md](xcom-playwright-auth.md) | extract-url 对 cookie 注入机制的具体应用（X.com） |
| `skills/research/extract-url/scripts/playwright_web.py` | 当前每次调用冷启动浏览器的实际实现 |
