---
migrated: false
---

# browser-fetch-mcp：文章抽取能力（fetch_article）设计

## 背景

`extract-url`（真实生产 skill）的 Subagent 1 抓取阶段目前依赖 4 个各自独立的 Playwright 脚本，按 URL 分发：

- `playwright_web.py`（通用站点）
- `playwright_web_wechat.py`（微信公众号）
- `playwright_web_arxiv.py`（arXiv HTML 论文）
- `playwright_xcom.py`（X.com / Twitter）

每个脚本内嵌一份 in-browser JS（`_EXTRACT_JS`），从 DOM 里抽取 `title`/`author`/`publishDate`/`blocks`/`imageBlocks`，外加图片下载、frontmatter 校验等落盘逻辑。这些抽取逻辑目前只服务于 `extract-url` 自己，无法被其他消费者复用；`browser-fetch-mcp`（[Phase A 设计](2026-08-08-browser-fetch-mcp-phase-a-design.md)）目前只提供 `fetch_page`（返回原始 HTML），不做任何内容抽取。

本设计把**通用 / 微信 / arXiv 三个站点**的抽取逻辑迁移进 `browser-fetch-mcp`，作为新工具 `fetch_article`。**X.com 单独排除**，留待后续一轮：它需要 headed 模式优先 + 失败降级 headless（两套不同 JS）、`--disable-blink-features=AutomationControlled`、Draft.js 专属滚动等待编舞，与现有的 headless-only warm persistent context 模型架构冲突，porting 成本和设计复杂度都明显更高，值得单独讨论。

## 范围

**做：**
- `browser-fetch-mcp` 新增工具 `fetch_article(url, output_dir, use_auth=False, chrome_profile=None)`，返回结构化抽取内容（非原始 HTML）。
- 逐字迁移 `playwright_web.py` / `playwright_web_wechat.py` / `playwright_web_arxiv.py` 三份 `_EXTRACT_JS`，改为在 `fetch_page` 现有 warm context 导航过的**活页面**上执行（不复刻原脚本"存 HTML 文件→`set_content()`重建 DOM"的两段式做法——这是一处刻意的简化，已与用户确认接受相应的行为差异）。
- 按 URL 做站点分发（Python 侧模式匹配，不是 subagent prompt 里的 LLM 判断）。
- 迁移"内容偏薄自动用 cookie 重抓"的兜底机制。
- 迁移图片下载（含 SSRF 防护、扩展名推断）。
- 真实测试验证（HTML fixture + 真实网络冒烟测试）。

**不做：**
- 不支持 X.com（遇到直接报错，留待后续一轮单独设计）。
- 不修改 `extract-url` 任何代码（`SKILL.md`、脚本、`subagent1-fetch-prompt.md` 都不动）——只建能力，不做消费者迁移，延续 Phase A 已确立的模式。
- 不做 `dedup_check.py`（meta.json 去重）、`repair_frontmatter`、`candidate_tags` 固定词表——这些是"如何组织 Markdown 文件"的产品层规则，不属于"如何抽取网页内容"的抓取层能力。
- 不复用 `extract-url` 的 `config.py`（`VAULT_PATH`/`CHROME_PROFILE` 全局配置）——`fetch_article` 的所有路径都由调用方通过参数显式传入。

## 架构

`fetch_article` 与现有 `fetch_page` 并列，共享同一套 warm persistent context 机制（`_get_context()`）：

```
调用方 → fetch_article(url, output_dir, use_auth, chrome_profile)
           │
           ├─ 站点分发：按 URL 判断 generic / wechat / arxiv / (xcom → 报错)
           ├─ 复用 fetch_page 的抓取路径：_get_context() → page.goto(url)
           ├─ page.evaluate(对应站点的 EXTRACT_JS) → 结构化结果
           ├─ 若 chrome_profile 有值且内容偏薄 → cookie 注入重新导航一次，取更优结果
           ├─ 下载 image_blocks 里的图片到 output_dir/Image/
           └─ 返回结构化 dict
```

## `fetch_article` 签名与返回

```python
@mcp.tool()
async def fetch_article(
    url: str,
    output_dir: str,
    chrome_profile: Optional[str] = None,
) -> dict
```

（没有 `use_auth` 参数——薄内容重试完全由 `chrome_profile` 是否有值决定，`use_auth` 在这个工具里不对应任何实际行为分支，加了反而混淆语义，故不设。）

返回：

```python
{
    "title": str,
    "author": str,
    "publish_date": str,
    "blocks": [{"tag": str, "content": str}],
    "image_blocks": [{"filename": str, "alt": str, "after_block": int}],
    "site": "generic" | "wechat" | "arxiv",
    "cookies_injected": int,
    "thin_retry_used": bool,
}
```

`output_dir` 必填，图片下载到 `<output_dir>/Image/img_N.ext`；`image_blocks[].filename` 回填实际下载后的文件名（相对 `Image/` 的文件名，不含目录前缀）。

## 站点分发规则

按 `urlparse(url).hostname`（精确匹配或指定后缀，避免子串匹配被 `notmp.weixin.qq.com.evil.com` 这类域名绕过）+ path 判断（Python 代码，不经过 LLM）：

| 条件 | 站点 |
|------|------|
| hostname == `mp.weixin.qq.com` | `wechat` |
| hostname == `arxiv.org` 且 path 含 `/html/` | `arxiv` |
| hostname in (`x.com`, `www.x.com`, `twitter.com`, `www.twitter.com`) | 报错 `ValueError("X.com not supported yet")` |
| 其余 | `generic` |

## 抽取执行

三份 `_EXTRACT_JS`（逐字迁移，仅去掉脚本外层的 CLI/文件读写代码）分别对应三个站点分支，通过 `page.evaluate(js)` 在 `fetch_page` 同款的活页面上执行。**不做**原脚本"预抓 HTML 存文件 → 另开浏览器 `set_content()` 重建 DOM"的两段式流程——直接在 `page.goto()` 导航完成后的页面上跑抽取，行为上更接近"页面加载完之后看到的最终 DOM"（包括懒加载图片、JS 渲染后显示的隐藏内容），与原脚本调试时假设的"静态快照 DOM"存在预期内的差异，通过下方测试策略验证。

## 薄内容自动重试

沿用现有阈值（`<20 blocks` 或 `<3000` 字符）：

```python
def _is_thin(result: dict) -> bool:
    blocks = result.get("blocks", [])
    total_chars = sum(len(b["content"]) for b in blocks)
    return len(blocks) < 20 or total_chars < 3000
```

`chrome_profile` 有值且首次结果偏薄时，用现有 cookie 注入机制（`cookies.py` 的 `extract_cookies`）重新导航一次并重新抽取，取 blocks 更多的一次结果；`thin_retry_used` 标记本次调用是否触发过重试。`chrome_profile` 为空则不重试，直接返回薄内容。

## 图片下载

沿用三个脚本现有逻辑：
- SSRF 防护：拒绝非 http/https、私有/回环/链路本地 IP。
- 扩展名推断：从 URL 或 Content-Type 猜测（`.jpg`/`.png`/`.gif`/`.webp`，默认 `.jpg`）。
- 下载失败的图片仍保留在 `image_blocks` 里（`filename` 字段仍填充，便于调用方感知哪些图片下载失败），不中断整体抽取流程。

## 错误处理

- URL scheme 非 http/https → 抛 `ValueError`（复用 `fetch_page` 现有校验风格）。
- `use_auth=True` 但 `chrome_profile` 为空 → 抛 `ValueError`（复用 `fetch_page` 现有约束）。
- 命中 x.com/twitter.com → 抛 `ValueError`，明确提示暂不支持。
- 站点抽取 JS 返回 `{error: ...}`（例如通用站点找不到 `<article>`/`<main>`）→ 原样抛出为 `RuntimeError`。
- 单张图片下载失败 → 记录、跳过，不影响整体调用成功。

## 测试策略

对齐 `extract-url` 现有测试思路和 `extract-url-mcp` Stage 1 的真实网络验证思路：

- **微信 / arXiv**：本地 HTML fixture（复刻真实页面结构，参考 `extract-url/tests/` 里已有的 fixture 写法），测抽取 JS 本身的正确性，不依赖真实网络。
- **通用站点 + 至少一个真实 arXiv HTML 论文页**：真实网络端到端冒烟测试，验证"活页面抽取"相对原脚本"`set_content()`重建"的行为差异在真实页面上是可接受的。
- 站点分发规则、薄内容重试触发条件、图片 SSRF 防护：单元测试覆盖边界条件（沿用 `extract-url` 现有测试里已验证过的用例，如 invalid scheme、缺 chrome_profile 等）。

## 后续（本轮不做）

- X.com 抽取能力：需要单独设计 headed-mode 优先 + headless 降级（两套不同 JS）的一次性浏览器生命周期，不复用 warm persistent context。
- 是否/何时把 `extract-url` 迁移为消费 `fetch_article`：本轮不涉及，延续 Phase A 已确立的"先建能力，迁移留待后续"模式。
