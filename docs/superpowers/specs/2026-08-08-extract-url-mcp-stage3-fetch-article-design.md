---
migrated: false
---

# extract-url-mcp Stage 3：改用 fetch_article

## 背景

`extract-url-mcp`（[Stage 1](2026-08-08-extract-url-mcp-stage1-design.md)/[Stage 2](2026-08-08-extract-url-mcp-stage2-design.md) 已合并进 `staging`）目前的抓取脚本 `scripts/mcp_fetch_client.py` 调用 `browser-fetch-mcp` 的 `fetch_page`（只返回原始 HTML），自己用一个从零写的 `_ArticleExtractor(HTMLParser)` 做文字抽取——不认站点、不处理图片、不认证。

`browser-fetch-mcp` 现在已经有了 `fetch_article`：站点感知（generic/wechat/arxiv/xcom）、结构化返回（title/author/publish_date/blocks/image_blocks）、内置图片下载、xcom 需要的认证态抓取。本轮把 `mcp_fetch_client.py` 改成直接调用 `fetch_article`，去掉自写的 HTML 解析层。

依然是验证性构建：不注册进 `skills-index.json`，不碰 `extract-url`/`probe-session`。

## 范围

**做：**
- `fetch_and_save()` 改为调用 `fetch_article`，去掉 `_ArticleExtractor`/`extract_article()`。
- 输出目录结构对齐真实 `extract-url`：`<output_dir>/<hash8>/Origin/article.md` 旁边多一个 `<hash8>/Image/`，`fetch_article` 自己把图片下载到这里（把 `<hash8>` 目录作为 `output_dir` 参数传给 `fetch_article`）。
- Origin markdown 正文按 `image_blocks[].after_block` 位置插入 `![](../Image/{filename})`。
- `_format_block` 扩展支持 `fetch_article` 可能返回的新 tag：`table`（arXiv，内容已经是现成的 markdown 表格，原样输出）、`pre`/`code`/`span`（xcom）。
- Origin frontmatter 新增 `author`、`publish_date`（`fetch_article` 直接给这两个字段，之前只有 `source_url`/`fetch_date`/`origin_title`）。
- `fetch_and_save(url, output_dir, chrome_profile=None)` 新增 `chrome_profile` 参数，透传给 `fetch_article`。
- 新写 `scripts/detect_xcom_chrome_profile.py`（从零写，不导入 `extract-url` 的 `detect_chrome_profile.py`）：只检查 Chrome profile 的 Cookies 库里是否存在 `auth_token`/`ct0`/`twid`（存在性检查，不解密），推荐一个 profile。
- `SKILL.md` 新增一步：URL host 匹配 x.com/twitter.com 时，运行探测脚本、把结果展示给用户、**明确询问确认**后才把确认的 `chrome_profile`（或 `None`）传给 Subagent 1——不允许探测完不确认直接用。
- `subagent1-fetch-prompt.md` 新增 `<CHROME_PROFILE>` 占位符，脚本调用改成 3 个位置参数。
- `SKILL.md` frontmatter 版本号/描述更新为 "Stage 3"。
- 更新 `test_mcp_fetch_client.py` 的真实网络测试断言，适配新的抽取路径和输出结构（`Image/` 目录、新增 frontmatter 字段）。

**不做：**
- 不做 URL 去重（meta.json）——沿用 Stage 1/2 已确认跳过的范围。
- `chrome_profile` 不接入微信/arXiv 的自动确认流程——只有 x.com/twitter.com 触发探测+确认这一步；微信/arXiv 需要认证态时，`chrome_profile` 仍然只能手动传（不新增自动探测逻辑，那两个站点没有固定的 auth cookie 集合可以像 x.com 一样简单判断"是否登录"）。
- `subagent2-tag-translate-prompt.md` 不变——打标/翻译逻辑跟抓取方式无关，且它目前不读 `author`/`publish_date`，这轮也不改它去读这两个新字段（Translation frontmatter 字段集合保持不变）。
- 不写真实 Obsidian Vault——继续用调用方指定的测试目录（沿用 Stage 1/2 的约定）。
- 不做"自动选 profile 就直接用"——探测脚本的输出必须先给用户看、等确认，这是本轮明确要保留的边界（源自 `extract-url` 自己 `detect_chrome_profile.py` 文档字符串里"Agent 不得主动调用/不得自动探测后直接使用"的约束精神）。

## 架构

```
fetch_and_save(url, output_dir, chrome_profile=None)
  │
  ├─ hash8 = md5(url)[:8]
  ├─ article_dir = output_dir / hash8
  ├─ 调用 fetch_article(url, output_dir=str(article_dir), chrome_profile=chrome_profile)
  │    （站点判断、内容抽取、图片下载、xcom 认证全部交给 fetch_article 内部处理）
  ├─ 拿到 {title, author, publish_date, blocks, image_blocks, site, cookies_injected, thin_retry_used}
  ├─ 丢弃跟 title 重复的开头 h1 block（沿用 Stage 1 的去重逻辑）
  ├─ 按 tag 类型格式化每个 block（新增 table/pre/code/span 处理）
  ├─ 按 after_block 位置插入图片引用 ![](../Image/{filename})
  └─ 写 article_dir/Origin/article.md，frontmatter 含 source_url/fetch_date/origin_title/author/publish_date
```

`fetch_article` 已经把 `<hash8>/Image/` 建好并把图片下载进去了（`fetch_article` 内部 `download_images()` 逻辑），`mcp_fetch_client.py` 只需要在正文里正确引用这些文件名，不需要自己再下载一次。

## Block 格式化

`_format_block(tag, content)` 扩展：

| tag | 处理 |
|-----|------|
| h1/h2/h3 | `#`/`##`/`###` 前缀（不变） |
| li | `- ` 前缀（不变） |
| blockquote | `> ` 前缀（不变） |
| table | 原样输出（`fetch_article` 的 arXiv 抽取 JS 已经把表格转成 markdown 管道表格字符串） |
| pre | ` ```content``` ` 代码块围栏（xcom 会出现） |
| code | `` `content` `` 行内代码（xcom 会出现） |
| span / 其他 | 原样当正文段落输出（xcom 的 span block 就是普通段落文本） |

## 图片插入

```python
image_blocks = payload["image_blocks"]  # [{filename, alt, after_block}]
pre_imgs = [f'![](../Image/{img["filename"]})' for img in image_blocks if img["after_block"] == -1]
# pre_imgs 插在正文最前面

for i, block in enumerate(blocks):
    parts = [format_block(block)]
    for img in image_blocks:
        if img["after_block"] == i:
            parts.append(f'![](../Image/{img["filename"]})')
    body_units.append('\n'.join(parts))
```

`alt` 文本不写进 markdown（跟真实 `extract-url` 的 `![](path)` 格式一致，不带 alt）。

## Frontmatter

```yaml
---
source_url: {url}
fetch_date: {今天日期}
origin_title: "{title}"
author: {payload["author"]}
publish_date: {payload["publish_date"]}
---
```

`author`/`publish_date` 为空字符串时原样写空值，不做"缺失就报错"之类的校验（这是验证性构建，不是 `extract-url` 那套带 `repair_frontmatter` 校验的生产流程）。

## chrome_profile 检测流程

新脚本 `scripts/detect_xcom_chrome_profile.py`：

```
扫描 CHROME_BASE 下的 Default / Profile* 目录
对每个 profile：复制 Cookies 数据库到临时文件，查询 host_key IN ('.twitter.com', '.x.com') 的 cookie name 集合（只查存在性，不用 pycookiecheat 解密）
判断 {'auth_token', 'ct0', 'twid'} 是否有交集 → 有交集 = "可能登录了"
打印人类可读对比表 + 一行 RECOMMENDED_PROFILE: <path>（或 RECOMMENDED_PROFILE: (none found)）
```

`SKILL.md` 新增步骤（净化 URL 之后，派发 Subagent 1 之前）：

```
若 url_safe 的 host 匹配 x.com / www.x.com / twitter.com / www.twitter.com：
    运行 detect_xcom_chrome_profile.py
    把结果（含 RECOMMENDED_PROFILE 那行）展示给用户
    询问：用推荐的 profile？换一个路径？还是不用登录态匿名抓？
    等用户明确回答后，把确认的路径（或 None）作为 chrome_profile
否则：
    chrome_profile = None
```

`subagent1-fetch-prompt.md` 里的脚本调用从：
```python
subprocess.run(['python3', 'SCRIPT', url, output_dir], ...)
```
改成：
```python
subprocess.run(['python3', 'SCRIPT', url, output_dir, chrome_profile or ''], ...)
```
`mcp_fetch_client.py` 的 `main()` 把空字符串当作 `None` 处理。

## 测试

`test_mcp_fetch_client.py` 现有两个真实网络测试（example.com、Wikipedia MCP 条目）需要重写：
- 输出路径断言从 `<output_dir>/<hash8>/Origin/article.md` 不变，但新增对 `<hash8>/Image/` 存在性的检查（如果目标页面有图片的话——example.com 没有图片，Wikipedia 条目大概率有）。
- frontmatter 断言新增 `author:`/`publish_date:` 字段存在（值可以是空，只要字段在）。
- 正文内容断言可能需要根据 `fetch_article` 通用抽取 JS 的实际输出调整（不是简单照搬旧 HTMLParser 抽取的断言，需要实际跑一次确认）。
- `detect_xcom_chrome_profile.py` 的测试：不依赖真实 X.com 登录态，测"没有任何 profile 匹配时打印 RECOMMENDED_PROFILE: (none found)"这类可控场景；真实检测到已登录 profile 的路径留给人工验证（跟 `browser-fetch-mcp` 那轮 xcom 能力一样，认证态相关的真实验证无法自动化）。
