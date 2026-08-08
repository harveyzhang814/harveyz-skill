---
migrated: false
---

# browser-fetch-mcp：X.com/Twitter 抽取能力设计

## 背景

[上一轮设计](2026-08-08-browser-fetch-mcp-article-extraction-design.md)把 `extract-url` 的通用/微信/arXiv 三站点抽取逻辑迁移进了 `browser-fetch-mcp` 的 `fetch_article` 工具，X.com/Twitter（`playwright_xcom.py`）当时被明确排除：它需要 headed 模式优先、失败降级 headless（且降级后用完全不同的一份 JS），每次调用独立开关浏览器而不是复用 warm persistent context，跟其他三站点共享的架构模型不兼容。

本设计把这条路径补上，作为独立一轮：给 `fetch_article` 新增对 x.com/twitter.com 的支持，架构上与其他三站点并存但不同。

## 范围

**做：**
- `dispatch_site()` 不再对 x.com/twitter.com 报错，改为路由到 `"xcom"`。
- 新增 xcom 专属的浏览器生命周期：不用 `_get_context()` 的 warm persistent context，每次调用独立 `browser.launch()` → 用 → `browser.close()`。
- headed 优先、失败降级 headless，两套场景各自逐字迁移一份抽取 JS（`_EXTRACT_JS_HEADED` / `_EXTRACT_JS_HEADLESS`）。
- `chrome_profile` 对 xcom 是必需参数，缺失直接 `ValueError`。
- 复用 `images.py::download_images()` 做图片下载，不重新迁移。
- 两套 JS 均返回 `{error: ...}` 时，`fetch_article` 抛 `RuntimeError`（携带 JS 返回的错误信息）——这是上一轮设计里提到但当时不适用的分支，这轮真正用得上。

**不做：**
- 不写自动化测试——headed 模式需要真实显示环境，自动化测试环境（CI、这个开发环境本身）大概率没有，写了也测不到主路径。实现完成后由人工在有真实 GUI 的机器上手动验证一次真实、需要登录态的抓取。
- 不修改 `fetch_page`、其他三站点（generic/wechat/arxiv）的现有代码路径、`extract-url` 本身。
- 不新增返回字段——沿用上一轮定下的 8 个字段（`title`/`author`/`publish_date`/`blocks`/`image_blocks`/`site`/`cookies_injected`/`thin_retry_used`），xcom 的 JS 额外返回的 `totalTextBlocks`/`totalImages` 字段直接丢弃（可从 `len(blocks)`/`len(image_blocks)` 推出，不需要单独暴露）。
- 不做"薄内容自动重试"——xcom 从一开始就要求登录态，没有"先匿名试一次，薄了再重试"的场景，`thin_retry_used` 对 xcom 恒为 `False`。

## 架构

```
fetch_article(url, output_dir, chrome_profile)
  │
  ├─ URL scheme 校验（沿用现有逻辑，http/https only）
  ├─ site = dispatch_site(url)  →  "xcom"（x.com / www.x.com / twitter.com / www.twitter.com）
  │
  └─ site == "xcom" 分支：
       ├─ chrome_profile 为空 → ValueError（不像通用三站点是"可选，缺了就不重试"，这里是硬性必需）
       ├─ 从 chrome_profile 提取 cookie（复用现有 extract_cookies()）
       ├─ 尝试 headed：browser.launch(headless=False, args=[...AutomationControlled]) → new_context(viewport=1280x900) → add_cookies → goto → 滚动编舞 → page.evaluate(_EXTRACT_JS_HEADED) → browser.close()
       ├─ 若异常 → 降级 headless：browser.launch(headless=True) → new_context() → add_cookies → goto → wait_for_selector → page.evaluate(_EXTRACT_JS_HEADLESS) → browser.close()
       ├─ 两次都失败或 JS 返回 {error: ...} → RuntimeError
       ├─ download_images(result["imageBlocks"], output_dir)   ← 复用 images.py，不重新迁移
       └─ 返回统一 8 字段结构，site="xcom", thin_retry_used=False
```

其他三站点（generic/wechat/arxiv）的分支完全不变，仍然走 `_get_context()` 的 warm context 模型。两套生命周期模型在同一个 `fetch_article` 函数里以 `if site == "xcom": ... else: ...` 的形式并存，互不干扰。

## JS 迁移

`_EXTRACT_JS_HEADED` 和 `_EXTRACT_JS_HEADLESS` 从 `playwright_xcom.py` 逐字迁移（含所有注释——上一轮曾因为手动誊抄漏掉注释被 review 打回，这轮直接在实现阶段用 diff 校验字节级一致，不再手抄）。两者的关键差异：

| | headed | headless |
|---|---|---|
| SPAN 噪音阈值 | 3 字符 | 30 字符 |
| CODE 标签处理 | 有专属处理器 | 无（headless 渲染不出代码块，处理了也没意义） |
| PRE 空白 | 保留原始空白 | 同样保留（两者一致） |
| `querySelectorAll('code.language-text, pre')` 兜底扫描 | 有 | 无 |

浏览器启动参数、滚动编舞（`window.scrollTo` 循环 25 次配合 `wait_for_timeout`）、X Notes 富文本检测（`wait_for_selector('[data-testid="twitterArticleRichTextView"]')`）均从 `_do_scrape()` 逐字迁移。

**一处刻意不跟原脚本一致的地方**：原脚本的 `_do_scrape()` 在 `browser.launch()` 和 `browser.close()` 之间没有 try/finally——因为它是一次性 CLI 进程，中途抛异常浏览器进程没关也无所谓，反正整个 Python 进程马上退出。`browser-fetch-mcp` 是长期运行的 server 进程，同样的代码不加保护会导致每次失败的抓取都残留一个僵尸 Chrome 进程，跑得越久积累越多。这里必须用 `try/finally` 包裹，确保不管是否抛异常都调用 `browser.close()`。

## 图片下载

直接调用 `browser_fetch_mcp.images.download_images(image_blocks, output_dir)`，不新增代码——xcom 的图片下载逻辑（SSRF 防护 + 扩展名推断 + 下载）与其他三站点完全一样，`images.py` 已经是通用实现。

## 错误处理

- URL scheme 非 http/https → `ValueError`（沿用 `fetch_article` 现有校验）。
- `chrome_profile` 为空 → `ValueError`（xcom 专属，比通用三站点更严格——那三站点 `chrome_profile` 是可选的重试触发条件，这里是硬性前提）。
- headed 和 headless 都抛异常，或最终拿到的抽取结果里有 `error` 字段（例如页面上找不到 `article[data-testid="tweet"]`）→ `RuntimeError`，带上错误信息。
- 单张图片下载失败 → 沿用 `download_images()` 现有行为（记录、跳过，不中断整体流程）。

## 测试策略

不写自动化测试。实现完成后，人工在有真实 GUI 的机器上，用一个真实需要登录态的 X 文章或推文 URL，手动跑一次 `fetch_article`，确认：
- headed 路径能正常启动（不因为没有显示环境而报错）
- 抽取到的 title/author/blocks 内容合理
- 图片能正常下载
- 如果手动把 headed 强制失败（比如临时改代码模拟异常），headless 降级路径也能跑通并拿到内容（哪怕质量更差）
