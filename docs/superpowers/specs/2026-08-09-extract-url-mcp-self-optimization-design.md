# extract-url-mcp 自优化机制 Design

## Motivation

`browser-fetch-mcp` 的 `fetch_article` 目前用固定逻辑抓取内容：`dispatch_site()` 按 hostname 路由到四套写死的抽取脚本之一（generic/wechat/arxiv/xcom），未知网站一律走 generic。遇到 generic 抽取不出内容的新网站时，今天唯一的补救路径是人工介入：手动改 `extractors.py`、重启 MCP、重新测试。

目标是把这条"发现新网站抓不好 → 找到能用的方法 → 固化成最小代码改动"的流程变成 agent 可以自主执行的标准动作，而不是每次都要人工介入。

## Scope

**In scope：**
- `browser-fetch-mcp` 新增一个调试用 MCP 工具，供自优化流程对真实页面迭代试验抽取逻辑。
- `extract-url-mcp` skill 新增一个"自优化 subagent"及其派发流程，在检测到抓取异常时自动触发。
- 自优化 subagent 遵循的诊断 + 固化 playbook（标准动作序列 + 最小变动/归纳原则）。

**Out of scope：**
- 不改动 `fetch_page`、`fetch_article` 现有的四套抽取脚本本身的行为（自优化流程产出的改动是新增分支，不是重写现有分支）。
- 不实现自动合并/自动发布——固化后的代码改动停在一个新分支上，走仓库既有的 `finishing-a-development-branch` 收尾流程，由人决定是否合并。
- 不在这次设计里预先构建一套"选择器覆盖配置系统"——归纳成标准机制这件事，只在第二次真的遇到同类小差异时才由自优化 subagent 现场做（YAGNI），而不是这次预先搭好框架。
- 不改动真正生产用的 `extract-url` skill（非 MCP 版本）。

## Architecture

```
extract-url-mcp SKILL.md 主流程
  │
  ├─ Subagent 1（抓取）— 不变，只是失败/内容过薄时把诊断信息带回主流程
  │
  ├─ 主流程判断：fetch_article 报错，或返回结果 is_thin（即使 thin_retry_used 已经为 true）
  │     │
  │     ├─ 否 → 正常进入 Subagent 2（打标 + 翻译）
  │     └─ 是 → 派发 Subagent 3（自优化，新增）
  │              │
  │              ├─ 固化成功 → 主流程重新派发 Subagent 1 重试同一 URL → 继续正常流程
  │              └─ 放弃 → 把诊断结果汇报给用户，流程终止（不重试、不强行固化）
```

## Component 1: `evaluate_js` MCP 工具

**文件**：`tools/browser-fetch-mcp/browser_fetch_mcp/server.py`

**签名**：
```python
@mcp.tool()
async def evaluate_js(
    url: str,
    js_code: str,
    chrome_profile: Optional[str] = None,
) -> dict:
```

**行为**：
- 校验 `url` scheme 必须是 http/https（复用 `fetch_article` 已有的校验逻辑/错误信息风格）。
- 若提供 `chrome_profile`：走认证 context（复用 `_get_context`/`_profile_key`/`extract_cookies` 现有机制，与 `fetch_page(use_auth=True, chrome_profile=...)` 同一套路径），否则走匿名 context。
- `page.goto(url, wait_until="domcontentloaded", timeout=30000)`，然后 `page.evaluate(js_code)`，返回 `{"result": <evaluate 的返回值>}`。
- **不下载图片、不写任何文件、不做 thin 检测、不做重试**——纯粹是"对真实页面跑一段 JS 看结果"的调试通道，语义上类似 `fetch_page` 但返回结构化的 JS 执行结果而不是整页 HTML。
- 用完关闭 page（不关闭 context，context 复用现有的持久化+缓存机制）。
- `js_code` 由调用方（自优化 subagent）完全掌控，不做沙箱限制——权限模型与"谁能调用这个 MCP server"一致，不新增额外风险面（`page.evaluate` 本身无法访问宿主文件系统）。

**测试**：`tools/browser-fetch-mcp/tests/test_evaluate_js.py`，参照 `test_fetch_page` 现有的测试风格（真实网络请求，覆盖：基本返回值、`chrome_profile` 认证路径、非法 URL scheme 报错）。

## Component 2: 自优化 Subagent（Subagent 3）

**新增文件**：`skills/research/extract-url-mcp/references/subagent-self-optimize-prompt.md`（与现有 `subagent1-fetch-prompt.md`、`subagent2-tag-translate-prompt.md` 同级）。

**输入**（由主流程填充到 prompt 模板里）：
- 失败的 URL
- Subagent 1 的诊断信息：dispatch 到的 site、block 数、总字符数、是否报错（及错误信息）、`thin_retry_used` 是否已经为 true
- `chrome_profile`（如果配置过默认值）

**权限**：读写 `tools/browser-fetch-mcp/` 源码、在该目录下跑 `.venv/bin/pytest`、执行 git 分支创建与提交。**不允许 merge/push**——固化完成后走仓库既有的 `finishing-a-development-branch` 流程，由人决定后续。分支命名遵循仓库现有规范（`feature/`/`fix/`/`chore/`/`doc/`/`release/` 前缀）。

**输出报告**：
- `RESULT: SOLIDIFIED` + 分支名 + 改了哪些文件 + 新增测试跑绿的证据（全量 suite 通过）
- 或 `RESULT: GAVE_UP` + 试过哪些候选方案 + 每个方案失败的具体原因 + 原始 HTML 里内容大致所在位置（供人工排查）

## Playbook：自优化 Subagent 必须遵循的动作序列

### Step 0 — 排除假阳性

先确认这确实是"抽取逻辑有问题"，而不是"文章本来就短"：用 `fetch_page` 拿原始 HTML，粗略估算正文文本量（例如 body 内可见文本总字符数），跟 Subagent 1 报告的已抽取字符数对比。差距明显（原始内容量远大于已抽取量）才继续往下走；如果原始内容本身就很短，判定为假阳性，直接汇报 `RESULT: GAVE_UP`，原因写清楚是"内容本身就短，非抽取缺陷"。

### Step 1 — 静态分析

用 `fetch_page` 拿到的原始 HTML，定位真实正文/标题/作者所在的 DOM 结构和候选选择器。

### Step 2 — 用 `evaluate_js` 按"最小变动优先"顺序逐个试

按以下顺序尝试，一旦某个候选方案返回的 blocks 明显覆盖了 Step 1 定位到的正文内容就停止，进入 Step 3：

1. **直接套用现有的一套抽取脚本**：把 `browser_fetch_mcp.extractors.EXTRACT_JS` 里的 generic/wechat/arxiv 三套脚本原样通过 `evaluate_js` 跑一遍，看是否已经有一套碰巧能用。
2. **只换 main 选择器**：以 generic 脚本为基础，只替换"定位正文根节点"那一行的选择器，候选池给足够常见的一批（`article`、`main`、`.post-content`、`.entry-content`、`[role=main]`、`#content` 等），其余逻辑不动。
3. **innerText 换 textContent**：怀疑正文节点被 CSS 隐藏（参考 wechat 当初 `#js_content` 的 `visibility:hidden` 坑），把 generic 脚本里的 `innerText` 读取换成 `textContent`，其余不动。
4. **认证重试**：若怀疑是登录墙/内容分级，且有 `chrome_profile` 可用，带上 cookie 重新跑（`evaluate_js(url, js_code, chrome_profile=...)`）。
5. **最后手段——全新专属脚本**：以上都不行，才允许参照 wechat/arxiv 当初的做法，为这个网站手写一段完整的定制抽取 JS。这是成本最高的选项，只有前四种都验证失败才能用。

单个 URL 上，Step 2 总共最多调用 `evaluate_js` **5 次**（每次调用测试一个候选方案，5 次分配给上面 5 种分支自行决定，例如全部用于分支 2 的不同候选选择器也可以）；5 次用完仍未找到能用方案，直接汇报 `RESULT: GAVE_UP`。

### Step 3 — 固化：最小变动 + 同类归纳

找到能用的候选方案后，按命中的分支类型决定固化方式：

- **命中 2/3 类（选择器级别的小差异）**：先检查这类"小差异"是不是已经在别的网站上出现过一次（即另一个网站当初也是靠类似的选择器/`textContent` tweak 解决的，现存代码里能找到痕迹）。
  - 若是**第一次**出现：只在 `dispatch_site()` / `EXTRACT_JS` 里为这个网站新增一个最小分支，不动其他网站现有逻辑。
  - 若这是**第二次**出现同类小差异：把这两处（新网站 + 之前那个用类似 tweak 解决的网站）一起归纳成一个标准化机制（例如一个可参数化的选择器覆盖表），而不是继续各自散落成独立分支。归纳时只动这两处相关代码，不touch其他网站的抽取逻辑。
- **命中 1 类（现有脚本原样能用）**：只需要在 `dispatch_site()` 里给这个 hostname 加一条路由到已有脚本的规则，不新增任何 JS。
- **命中 4 类（认证重试解决）**：确认是否现有的 `thin_retry` 自动重试机制本该覆盖这个场景但没生效——如果是配置/触发条件的 bug，修 bug；如果是这个网站需要认证但被判定成了别的 site 类型导致没走到 retry 分支，按 2/3 类同样的"是否第一次出现"逻辑处理。
- **命中 5 类（全新专属脚本）**：参照 wechat/arxiv 当初的模式新增一套完整脚本 + `dispatch_site()` 路由，不动其他网站。

### Step 4 — 补测试 + 回归验证

为固化的改动补测试，测试风格和位置参照 `tests/test_extractors.py`（dispatch/抽取逻辑单测）、`tests/test_fetch_article.py`（端到端）现有模式。跑该工具目录下**全量** `.venv/bin/pytest`（不是只跑新增测试），必须全绿才能进入 Step 5。

### Step 5 — 提交并停下

在符合命名规范的新分支上提交改动（commit message 说明是自优化流程针对哪个网站固化的哪种方案）。**不 merge、不 push**——提交完就停，把分支名和改动摘要写进报告，交还给主流程。主流程按 `finishing-a-development-branch` 的标准菜单交给人工决定合并/PR/保留。

## 主流程编排改动

**文件**：`skills/research/extract-url-mcp/SKILL.md`

在现有"步骤 4：等待 Subagent 1 完成"之后插入判断：

- Subagent 1 报告 `fetch_article` 成功且非 thin → 走原有步骤 5（Subagent 2）。
- Subagent 1 报告失败，或成功但 `thin_retry_used=true` 之后仍然 thin → 派发 Subagent 3（自优化），把失败 URL + 诊断信息传入 `references/subagent-self-optimize-prompt.md` 模板。
  - Subagent 3 报告 `RESULT: SOLIDIFIED` → 重新走一遍步骤 3-4（用同一个 URL 重新派发 Subagent 1），预期这次能正常抓到内容，再继续步骤 5-6。
  - Subagent 3 报告 `RESULT: GAVE_UP` → 直接向用户汇报失败原因（Subagent 3 报告里的诊断内容），流程终止，不再重试、不再派发 Subagent 2。

## Error Handling / Guardrails

- `evaluate_js` 是纯调试通道，不做任何持久化副作用（不写文件、不下载图片），即使被其他调用方误用也不会破坏 `fetch_article` 的现有行为或产生垃圾文件。
- 自优化 subagent 对单个 URL 的 `evaluate_js` 调用次数硬上限 5 次，防止无限试错。
- 固化改动前必须先在 Step 0 排除"内容本来就短"的假阳性，避免为了凑合过 is_thin 阈值而引入错误的抽取逻辑。
- 固化改动必须全量测试套件通过才能提交，防止破坏已有四个网站的抽取逻辑。
- 固化改动只提交到新分支，不自动合并——大改动（新增/归纳抽取逻辑）影响面是所有调用 `browser-fetch-mcp` 的 skill，必须留给人工审查。

## Testing Plan

- `evaluate_js` 新增单测：基本返回值、`chrome_profile` 认证路径、非法 scheme 报错（真实网络测试，风格参照现有 `test_fetch_page` 测试）。
- 自优化流程本身不写单元测试（它是一个 prompt 驱动的 subagent 行为，不是可单测的纯函数），靠 Step 4 里"每次固化必须自带测试 + 全量回归"来保证质量。
- Playbook 文档（`references/subagent-self-optimize-prompt.md`）本身不需要额外测试基础设施。

## Global Constraints

- 自优化 subagent 不允许 merge/push，只能提交到新分支——遵循仓库既有的分支收尾约定（`finishing-a-development-branch`）。
- 分支命名遵循仓库现有规范（`feature/`/`fix/`/`chore/`/`doc/`/`release/` 前缀，无 `refactor/`）。
- 固化改动前必须跑全量 `.venv/bin/pytest`（`tools/browser-fetch-mcp/`），全绿才能提交。
- 单个 URL 上 `evaluate_js` 调用次数上限 5 次。
- 不预先构建选择器覆盖配置系统——归纳成标准机制只在真的第二次遇到同类小差异时才现场做。
