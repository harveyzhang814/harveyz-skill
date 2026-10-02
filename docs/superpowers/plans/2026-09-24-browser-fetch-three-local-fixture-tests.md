# Browser-fetch 三个公网失败用例本地化实施计划

**目标：** 让一个 arXiv 文章测试和两个 `example.com` 页面导航测试在默认套件中不依赖公网，同时保留对应的 CLI、Chromium、路由和提取覆盖。

**架构：** `tools/browser-fetch/tests/conftest.py` 提供生命周期受控的本地静态页面 URL。页面 CLI 测试继续经 `run_cli` 运行真实 CLI/Playwright；arXiv 测试将 URL 路由断言与现有固定 HTML 的真实 Chromium 提取断言组合。生产代码不改。

**技术栈：** pytest、Python `ThreadingHTTPServer`、Playwright Chromium、browser-fetch CLI。

---

### Task 1: 为页面 CLI 用例提供本地 fixture

**文件：**

- 修改: `tools/browser-fetch/tests/conftest.py:1-63`
- 测试: `tools/browser-fetch/tests/test_cli_page_eval.py:4-25`

- [ ] **Step 1: 编写失败的页面导航测试改动**

让 `test_page_anonymous_fetch` 和 `test_page_auth_with_empty_profile_injects_nothing` 接收 `local_page_url`，并用该 URL 调用 `run_cli`；先把标题断言改为固定 fixture 标题。

- [ ] **Step 2: 运行目标测试确认 fixture 缺失**

运行: `cd tools/browser-fetch && python3 -m pytest tests/test_cli_page_eval.py::test_page_anonymous_fetch tests/test_cli_page_eval.py::test_page_auth_with_empty_profile_injects_nothing -q`

预期: FAIL，提示 `local_page_url` fixture 不存在。

- [ ] **Step 3: 编写最小 fixture**

在 `conftest.py` 定义固定 HTML（标题为 `Local Browser Fetch Fixture`）和 `local_page_url` fixture。使用 `ThreadingHTTPServer(("127.0.0.1", 0), handler)`、后台线程、`try/finally`、`shutdown()` 与 `join()`；fixture 只提供 HTML，不提供图片资源。

- [ ] **Step 4: 运行目标测试确认通过**

运行: `cd tools/browser-fetch && python3 -m pytest tests/test_cli_page_eval.py::test_page_anonymous_fetch tests/test_cli_page_eval.py::test_page_auth_with_empty_profile_injects_nothing -q`

预期: 2 passed；仍断言匿名请求、认证空 profile、状态和 cookies 注入行为。

### Task 2: 使 arXiv 用例不依赖真实 arXiv

**文件：**

- 修改: `tools/browser-fetch/tests/test_fetch_article.py:1-43,158-186`
- 测试: `tools/browser-fetch/tests/test_fetch_article.py:32-43`

- [ ] **Step 1: 编写确定性 arXiv 用例**

将 `test_fetch_article_arxiv_uses_arxiv_route_and_fixture` 设为无需 `run_cli` 的异步测试：导入 `dispatch_site`，断言 `dispatch_site("https://arxiv.org/html/2608.06020") == "arxiv"`；再调用 `_evaluate_extraction("arxiv", _ARXIV_FIXTURE_HTML, tmp_path)` 并断言标题及内容块数。

- [ ] **Step 2: 运行 arXiv 测试确认覆盖目标行为**

运行: `cd tools/browser-fetch && python3 -m pytest tests/test_fetch_article.py::test_fetch_article_arxiv_uses_arxiv_route_and_fixture -q`

预期: PASS；若 fixture 块数与预期不符，只调整断言到固定 fixture 的真实、非空输出，不改生产提取器。

- [ ] **Step 3: 运行相邻 arXiv fixture 回归**

运行: `cd tools/browser-fetch && python3 -m pytest tests/test_fetch_article.py::test_fetch_article_arxiv_uses_arxiv_route_and_fixture tests/test_fetch_article.py::test_extract_js_arxiv_converts_data_table_but_skips_equation_table -q`

预期: 2 passed，分别覆盖路由加提取与表格行为。

### Task 3: 回归验证与提交

**文件：**

- 修改: `tools/browser-fetch/tests/conftest.py`
- 修改: `tools/browser-fetch/tests/test_cli_page_eval.py`
- 修改: `tools/browser-fetch/tests/test_fetch_article.py`
- 创建: `docs/superpowers/specs/2026-09-24-browser-fetch-three-local-fixture-tests-design.md`
- 创建: `docs/superpowers/plans/2026-09-24-browser-fetch-three-local-fixture-tests.md`

- [ ] **Step 1: 运行 browser-fetch 全套测试**

运行: `cd tools/browser-fetch && python3 -m pytest tests/ -q`

预期: 通过，且输出不含这三个公网导航超时。

- [ ] **Step 2: 运行仓库全量测试**

运行: `npm test`

预期: 不再出现本规格所列 arXiv / `example.com` 超时；若其他外网测试失败，保留其精确输出并停止，不作豁免推断。

- [ ] **Step 3: 静态检查与提交**

运行: `git diff --check`

预期: 无输出且退出码 0。

- [ ] **Step 4: 提交**

运行: `git add tools/browser-fetch/tests/conftest.py tools/browser-fetch/tests/test_cli_page_eval.py tools/browser-fetch/tests/test_fetch_article.py docs/superpowers/specs/2026-09-24-browser-fetch-three-local-fixture-tests-design.md docs/superpowers/plans/2026-09-24-browser-fetch-three-local-fixture-tests.md && git commit -m "test(browser-fetch): localize flaky navigation tests"`
