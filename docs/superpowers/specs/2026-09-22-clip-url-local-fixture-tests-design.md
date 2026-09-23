# clip-url 本地化 Playwright 测试设计

## 概述

将 `skills/research/clip-url` 的端到端测试从公开网站迁移到进程内本地 HTTP fixture，消除 `https://example.com` 的 Playwright 30 秒导航超时，同时继续覆盖真实 `browser-fetch` CLI 和 Chromium 抽取路径。

## 背景

当前测试把公网访问和外部页面内容作为前提。命令行 HTTP 请求可立即取得 `example.com` 的 200 响应，但 Chromium 导航仍会超时；因此失败来自测试的外部依赖，而不是 clip-url 的包装逻辑。

## 方案

在 clip-url 测试夹具中启动仅绑定 `127.0.0.1` 的临时 HTTP 服务器，并提供稳定的 Example Domain 风格 HTML。将 `mcp_fetch_client` 和 `mcp_debug_client` 的真实网络用例改用此 URL。保留 subprocess、browser-fetch CLI、Playwright、隔离数据目录和最终 Markdown 断言。

图片位置回归已由 `tools/browser-fetch/tests/test_markdown.py` 的纯单元测试覆盖；clip-url 的回环 fixture 不伪造 loopback 图片下载，因为生产代码特意拒绝私有/回环地址以防 SSRF。

## 错误处理

fixture 在 `finally` 中关闭 HTTP server 并等待线程退出。测试仍将 browser-fetch 的非零退出变为失败，因此本地导航、抽取或写入回归不会被掩盖。

## 验证

运行 `skills/research/clip-url/tests/`，再运行 `npm test`。完整套件若有无关的外网测试失败，将如实单列报告。

## 范围边界

不改变 `browser-fetch` 的生产导航超时，也不更改线上抓取语义；本次只让 clip-url 的自动化测试可重复执行。
