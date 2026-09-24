# Browser-fetch 三个公网失败用例本地化设计

## 概述

将当前全量 `npm test` 中已记录的三个浏览器公网导航失败替换为确定性测试，消除它们对公网 DNS、TLS、CDN 和 Chromium 出站路径的依赖。范围严格限于这三项：一个 arXiv 文章抓取用例与两个 `example.com` 页面导航用例。

## 背景

此前全量测试记录了一个 arXiv `Page.goto` 超时和两个 `example.com` `Page.goto` 超时。这些错误发生在测试环境的外部网络路径，不能说明生产抓取逻辑失效。仓库已经有以本地 HTTP server、真实 CLI 进程和真实 Chromium 组合测试的先例；先前 `clip-url` 已采用同一原则。

## 目标与非目标

目标：

- 默认 `npm test` 不再因这三个已记录用例访问公网而失败。
- 保留两个页面用例对真实 `browser-fetch` CLI、真实 Chromium、`page.goto`、JSON 输出和认证参数处理的覆盖。
- 保留 arXiv URL 路由与 arXiv 提取 JavaScript 的覆盖，不改变提取器行为。

非目标：

- 不修改 `tools/browser-fetch/browser_fetch/` 的任何生产代码。
- 不增加 `page.goto` 超时，不弱化 SSRF 检查，也不使用 loopback 图片下载。
- 不清理其他目前仍通过的真实站点测试；它们不属于本次最小修复范围。
- 不把真实网络测试标记为跳过或用 mock 替代 CLI/Chromium 页面测试。

## 设计

### 页面 CLI 用例

在 `tools/browser-fetch/tests/conftest.py` 增加一个会在 `127.0.0.1` 随机端口启动、并在测试结束时关闭的静态 HTML fixture。它返回一个固定标题与正文，供两个失败的 `page` CLI 用例使用。

两个用例仍经由 `run_cli` 启动独立 CLI 进程，仍会让 Playwright 执行一次实际的 `page.goto`。断言改为 fixture 标题和成功状态；认证参数、空 profile 与 `cookies_injected == 0` 的断言保持不变。

### arXiv 用例

`test_fetch_article_arxiv_uses_arxiv_route_and_fixture` 不再导航真实 arXiv 页面。该用例的语义拆成两个已可离线证明的边界：

1. `dispatch_site("https://arxiv.org/html/<id>")` 必须返回 `arxiv`，覆盖 URL 路由规则。
2. 现有 `_ARXIV_FIXTURE_HTML` 经真实 Chromium `page.set_content()` 和 `EXTRACT_JS["arxiv"]` 提取，必须产生结构化内容，覆盖 arXiv 专用提取器。

本次会让该测试显式组合并断言这两项，避免声称本地回环地址是 arXiv 主机。这样不需要篡改 DNS、TLS 或生产路由规则。

## 错误处理与隔离

fixture server 必须用 `try/finally` 关闭 server 并 join 线程。`run_cli` 继续仅设置 `BROWSER_FETCH_DATA_DIR`，不覆盖 `HOME`，使 Playwright 浏览器缓存保持可用。没有任何测试向本地 server 请求图片，避免绕过生产对 loopback 图片的 SSRF 拒绝。

## 验收标准

- 两个改动后的页面 CLI 用例在无公网访问情况下通过，且仍断言 CLI 返回码、状态、标题和认证行为。
- arXiv 用例在无公网访问情况下断言路由选择和 fixture 提取到的内容块。
- `python3 -m pytest tools/browser-fetch/tests/ -q` 在工具私有 `.venv` 不存在的工作树中使用仓库 runner 的系统解释器回退路径。
- `npm test` 不再出现这三项已记录的 arXiv / `example.com` 浏览器导航超时；本轮不对其他外部测试的稳定性作承诺。
- `git diff --check` 通过。

## 风险与缓解

本地 server 只能验证通用 HTTP 导航，不能证明 arXiv 域名的在线可达性；在线可达性不是默认单元/集成测试的稳定责任。arXiv 特有逻辑通过真实 Chromium 对固定 HTML 执行提取，并独立断言 URL 路由，覆盖原测试的代码行为而不依赖外部服务。
