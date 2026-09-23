# clip-url 本地 fixture 测试实施计划

**目标：** 让 clip-url 的真实 Playwright/CLI 测试不再依赖公网网站。

**架构：** 测试进程提供回环 HTTP 服务器，browser-fetch 子进程通过原有路径访问固定 HTML。图片位置由 browser-fetch 已有的纯单元测试覆盖，因为下载器会有意拒绝回环图片地址。仅替换测试 URL、固定页面断言和测试夹具；生产抓取代码不变。

**技术栈：** pytest、`http.server`、线程、本地 Playwright Chromium。

---

### Task 1: 建立受控站点并迁移 clip-url 网络测试

**文件：**
- 修改: `skills/research/clip-url/tests/conftest.py`
- 修改: `skills/research/clip-url/tests/test_mcp_fetch_client.py`
- 修改: `skills/research/clip-url/tests/test_mcp_debug_client.py`

- [ ] **Step 1: 写入使用 `local_article_url` 的回归断言**

```python
def test_call_fetch_page_returns_html(local_article_url):
    payload = call_fetch_page(local_article_url)
    assert payload["status"] == 200
    assert "Example Domain" in payload["html"]
```

- [ ] **Step 2: 运行单测，记录 fixture 尚不存在导致的 RED**

运行: `python3 -m pytest skills/research/clip-url/tests/test_mcp_debug_client.py::test_call_fetch_page_returns_html -vv`

预期: FAIL，指出 `local_article_url` fixture 未定义。

- [ ] **Step 3: 添加最小本地 HTTP fixture 和固定页面资源**

```python
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
yield f"http://127.0.0.1:{server.server_port}/article.html"
server.shutdown()
thread.join()
```

- [ ] **Step 4: 将 clip-url 真实网络测试改用 fixture，并保留 CLI/Chromium 断言**

```python
origin_path = fetch_and_save(local_article_url)
assert "source_url: " + local_article_url in content
```

- [ ] **Step 5: 运行所有 clip-url 测试**

运行: `python3 -m pytest skills/research/clip-url/tests/ -q`

预期: PASS。

- [ ] **Step 6: 提交**

```bash
git add docs/superpowers/specs/2026-09-22-clip-url-local-fixture-tests-design.md docs/superpowers/plans/2026-09-22-clip-url-local-fixtures.md skills/research/clip-url/tests
git commit -m "test(clip-url): replace live pages with local fixtures"
```

### Task 2: 验证仓库测试入口

**文件：**
- 验证: `package.json`

- [ ] **Step 1: 运行完整测试入口**

运行: `npm test`

预期: 退出码 0；若其他套件仍有外网故障，记录套件与失败原因，不将其归为本修改造成。
