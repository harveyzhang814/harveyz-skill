# site_rules 三档抽取设计：selector 默认 / +transform / 全 JS 兜底

**主线（可证伪）：** 表达力可以分档放开，但**能力**必须随档位收紧、且升档只能由人发起。只要"无人值守路径上不会执行新写的任意代码"这条守得住，全 JS 兜底就不是安全债务而是覆盖面。

若最终设计里出现任何一条自愈路径能自动写出并执行全 JS，这条主线就被证伪了。

前置设计：`2026-09-02-sync-website-design.md`（本文只改其 §3.2 规则库一节，其余不动）。

---

## 1. 定位

现在 site_rules 只有一档：一组 CSS selector，求值器写死为 `querySelectorAll(item)` → 每个条目内 `querySelector` 取 title/link/date。

它表达不了这些：字段要拼接或清洗（日期只在 URL 路径里）、条目要过滤（跳过 sponsored/置顶）、数据在 JSON-LD 或全局变量里而不在 DOM 里、需要交互（点"加载更多"）、shadow DOM。

**这个上限比设计时估的低。** 现有两个标定过的站里已经有一个逼近它：claude.com/blog 把同一批文章渲染两遍（网格版可见、列表版藏在 `hidden` tabpanel），靠"把 item 限定到某个容器内"才绕过去；要是两份渲染交错、或要按"这个条目有没有某个子元素"筛，selector 就没辙。

更硬的反证：**browser-fetch 自己已有的四个抽取器（generic / wechat / arxiv / youtube）没有一个能用 selector 表达。** YouTube 那个直接读 `ytInitialData` 全局变量，微信那个读 `window.ct` 算发布时间。全是手写 JS。

所以放开表达力是对的。问题只在于放开之后，"无人值守的 Agent 会在没人看着时写代码并执行"这条路要堵死。

---

## 2. 三档

| 档 | 存什么 | 在哪求值 | 拿得到什么 |
|---|---|---|---|
| `selector` | 一组 CSS 选择器 | 目标页面 | 受限于选择器形状；实现里用 `json.dumps` 塞成 JS 字符串字面量，带引号也逃不出去 |
| `selector+transform` | 选择器 + `transform.js` | selector 在目标页面；**transform 在空白页上下文** | transform 的输入只有 selector 抽出的 JSON 数组；**无目标站 DOM、无 cookie、无登录态** |
| `script` | `extract.js` | 目标页面 | 全部——所以要人批 |

**二档的隔离是这套分级的支点。** 如果 transform 也在目标页面里跑，它的能力跟全 JS 完全相同（能读 cookie、能带着登录态发请求），"二档可自动、三档要人批"就只是输入变干净了、能力没变，分级失去意义。

隔离方式：在 `about:blank` 上开一个页面，把 selector 抽出的数组作为参数传进 `page.evaluate`。这**不是真沙箱**——`fetch` 还在，只是拿不到目标站的凭据和 DOM。这条限度必须明写，不能当成沙箱来依赖。

---

## 3. 存储 schema

### 3.1 目录即规则

```
site_rules/
  claude.com/
    rule.json
    transform.js      ← 仅二档
    extract.js        ← 仅三档
    review.md         ← 仅三档：评估意见全文 + 批准记录
  simonwillison.net/
    rule.json         ← 一档，只有这一个文件
```

**JS 存成真正的 .js 文件，不内联进 JSON 字符串。** 内联意味着代码变成转义过的单行字符串：人读不了、`diff` 看不了、linter 跑不了，Agent 要改它也得先反转义再转回去。代码的维护成本主要花在"能不能看清它现在是什么"上，内联把这一条直接砍掉。

代价是一条规则从一个文件变成一个目录：删除要整目录删、写入不再是单文件原子操作、多文件之间要保持一致。这三条在 §3.3 处理。

### 3.2 rule.json

```json
{
  "schema_version": 2,
  "domain": "claude.com",
  "list_url": "https://claude.com/blog",
  "mode": "selector",
  "selectors": { "item": "...", "title": "...", "link": "...", "date": "..." },
  "calibrated_at": "2026-09-03T03:05:03.767366+00:00",
  "sample": [ { "title": "...", "url": "...", "date_text": "..." } ]
}
```

`mode` 取 `selector` / `selector+transform` / `script`。`selectors` 在 `script` 档缺席。`script` 档另有：

```json
  "approval": {
    "approved_at": "2026-09-03T04:00:00+00:00",
    "reviewer": "<评审 subagent 标识>",
    "review_file": "review.md"
  }
```

**`mode` 是显式字段，不靠"有没有那个 .js 文件"隐式判定。** 加载时校验 mode 与文件存在性一致，不一致就报规则损坏并拒绝使用——**不静默降级**。静默降级意味着删掉一个 `extract.js` 就能让三档规则悄悄退成一档继续跑，而摘要上看不出任何异常。

### 3.3 一致性与原子性

- **写**：先写进同目录下的临时目录 `<domain>.tmp/`，全部文件落盘后 `os.replace` 整目录换过去。中断只会留下一个 `.tmp` 目录，不会产生半条规则。
- **删**：`shutil.rmtree` 整目录。
- **加载校验**：`mode` 与文件存在性不符 → 抛错，不返回半条规则。
- **孤儿清理**：加载 `list_rules` 时跳过 `.tmp` 目录，不报错也不自动删——留着给人看是怎么断的。

### 3.4 迁移

现有两条规则是扁平的 `<domain>.json`（`simonwillison.net`、`claude.com`）。

- **读**：扁平文件仍然认，视为 `mode: "selector"`、`schema_version: 1`。
- **写**：一律写新目录格式；若同名扁平文件存在，写成功后删掉它。
- 结果是两条现有规则在下次标定或下次写入时自动迁移，不需要单独跑迁移脚本，也不会在迁移前失效。

---

## 4. 谁能写到哪一档

| 路径 | 上限 |
|---|---|
| 自愈（`run` 内，无人值守） | `selector+transform` |
| `/sync-website calibrate <handle>` | `selector+transform` |
| `/sync-website calibrate <handle> --allow-script` | `script`，且强制走 §5 评审 |

`articles-rule set` 在 CLI 层同样分开：写 `script` 档需要显式 `--mode script` 且必须同时给 `--review-file`，没有评审文件就拒绝落盘。这样"绕过评审"不是一个需要靠纪律避免的事，而是命令行层面做不到。

---

## 5. 三档的评审

```
1. 主会话 Agent 写 extract.js
2. articles-probe 跑通，过机械门槛（calibration_gate.py，阈值不变）
3. 机械静态扫描 → 产出材料，不做门禁
4. 派独立 subagent 评审 → 结构化评估意见
5. 意见摆给用户 → 用户批准意见（不是批准代码）
6. articles-rule set --mode script --review-file <f> → 落盘
```

### 5.1 评审必须由独立 subagent 做

**写 JS 的 Agent 不能给自己签字。** 理由跟 handoff skill 里"`已验收` 只能由第二方写"完全一样：写的人一旦能自己签字，签字这个动作的信息量就退化成"写的人说没问题"——而这个信息在"我写完了"里已经有了，两者变成同义词。风险还会反向放大，一份自我认证的评估通常附着一套看起来很可信的理由，比没有评估更难被怀疑。

### 5.2 评估意见必须回答的四件事

1. **这段代码读了什么** —— DOM 选择器、全局变量、`window.*`
2. **有没有网络请求 / cookie / storage 访问** —— 有就点名，写清在哪一行、做什么
3. **抽取逻辑一句话概括**
4. **为什么 selector 做不到** —— 答不上来就说明不该升三档，评审应给"不建议"

结论三选一：`可批准` / `有条件可批准（附条件）` / `不建议（附理由）`。

第 2 条之所以有信息量，是因为 §7 确认过：登录态在 JS 之外注入，一个正当的抽取器**没有任何理由碰 cookie**。碰了就是异常信号。

### 5.3 静态扫描只作材料，不作门禁

扫 `fetch` / `XMLHttpRequest` / `document.cookie` / `localStorage` / `eval` / `Function(`，结果作为评审 subagent 的输入。

**不作为门禁**：黑名单靠字符串拼接就能绕（`window["fe"+"tch"]`），当门禁只会给假安全感——一段"通过了安全扫描"的代码比一段没扫过的更难被怀疑。

### 5.4 review.md

评估意见全文 + 用户批准时间，随规则一起落盘。没有它，三个月后没人知道当初批的是什么、基于什么理由批的。

---

## 6. 失效与维护

| 情况 | 行为 |
|---|---|
| 一档 / 二档抽出 0 条 | 走自愈：就地重标定，上限二档 |
| 二档 `transform.js` 抛错 | 当作抽取失败，同上走自愈（自愈可以重写 transform） |
| **三档抽出 0 条或抛错** | **记 `failures`，不自愈、不自动降级** |
| 规则目录 `mode` 与文件不符 | 记 `failures`，报规则损坏 |

**三档不自愈是刻意的。** 自愈会绕过评审那道门——那是这套设计唯一的人工关卡。代价是：三档站改版后必然漏报，直到人来处理。这是设计意图，不是缺陷。

**可见性**：`digest.py` 在摘要里标注哪些渠道跑的是三档规则，跟已有的"本轮重新标定过"标注并列。没有它，"这个站正在跑一段人工批准过的代码"这件事批完就沉底了。

---

## 7. 复用边界：什么是本来就有的，什么要补

这一节回答"抽取 JS 要不要自己处理登录态"，以及更一般的"复用原则是写进去的还是本身具备的"。

### 7.1 登录态：本身就具备，JS 不需要碰

调用顺序是：解析 Chrome profile → 解密 cookie → 注入 browser context → `page.goto` → **最后才** `page.evaluate(js)`。JS 跑起来时页面已经是登录态视角渲染完的，它从头到尾碰不到也不需要碰凭据。

证据：现有四个抽取器的 JS 里，`document.cookie` / `localStorage` / credentials 一次都没出现过（`grep` 确认）。抽取 JS 与凭据处理从来不在一层。

**所以三档 JS 无需重写任何登录逻辑，它免费继承。**

### 7.2 归一化：不是本来就有的，一档靠模板兜着，三档会漏

一档的求值模板做了两件 JS 侧的事：

```js
title: titleEl.textContent.replace(/\s+/g, ' ').trim()   // 空白归一
url:   linkEl.href                                        // 相对转绝对（浏览器原生）
```

三档没有模板，这两件事就落到每个站的 JS 作者头上。第二条是**会静默破坏增量语义的正确性陷阱**：忘了用 `.href` 而写成 `getAttribute('href')`，产出的是相对 URL——而游标（`seen_urls`）和归档去重都拿 URL 当主键，一批相对 URL 会被当成全新条目、永远去不了重，而且摘要上看起来完全正常。

### 7.3 做法：把复用挪到 JS 边界之外，不写成劝告

一句"尽可能复用 browser-fetch 已有能力"的原则，对一个正在写第 5 个站的 Agent 约束力约等于零。改成结构上绕不过去的：

**`page.evaluate` 返回之后，Python 侧统一过一遍归一化管线**，三档二档一档共用：

1. `title` / `date_text`：`re.sub(r"\s+", " ", s).strip()`
2. `url`：`urljoin(list_url, url)`
3. 丢弃 `url` 为空的条目（这条现在已经有了）

一档模板里的 `.href` 保留不动——`urljoin` 对已经绝对的 URL 是幂等的，所以一档行为完全不变。

**已知上限**：三档 JS 若返回原始相对属性、且页面带 `<base href>`，浏览器的 `.href` 会是对的而 `urljoin(list_url, ...)` 会算错。正确做法是三档 JS 也返回 `.href`，这一点写进三档写作约定，并列入评审 subagent 的检查项。这是残留缺口，不是被消除的。

---

## 8. 边界

- 不改一档现有行为（除 §7.3 的幂等归一化）
- 不改 `dispatch_site()`，不改 browser-fetch 已有的四个抽取器
- 不给 `articles` 加 pacing（沿用前一份设计的判断）
- 不做三档规则的自动降级、不做规则的自动过期
- 评审 subagent 只评审、不改代码、不落盘

---

## 9. 代价汇总

| 决策 | 代价 |
|---|---|
| 目录即规则 | 一条规则从一个文件变成一个目录——删除、原子写、一致性都变复杂。用 `.tmp` + `os.replace` 消化，但多了一类需要人看的孤儿目录 |
| JS 存成独立文件 | 规则库不再是"一堆可以随便解析的 JSON"，任何读它的外部工具都要理解目录约定 |
| 二档隔离上下文 | **不是真沙箱**——`fetch` 还在，只是没有目标站凭据 |
| 三档需人工批准 | 需要全 JS 的站改版后必然漏报，直到人处理 |
| 用户批的是意见不是代码 | 信任链比"逐行审"弱、比"全自动"强。**评审 subagent 会看漏**，这条无法通过流程消除 |
| 静态扫描不作门禁 | 会漏掉刻意规避的越界；但作门禁会给假安全感，两害相权 |
| 归一化挪到 Python 侧 | 三档 JS 返回相对属性 + 页面带 `<base href>` 时 `urljoin` 会算错（§7.3） |
| `mode` 不一致即报错 | 手工编辑规则目录更容易把它弄成"损坏"状态，而不是宽容地跑起来 |

---

## 10. 判断

**技术判断**：这套设计的全部安全性压在两个点上——二档的执行上下文真的被降权了，以及 `--allow-script` 真的只能由人发起。第一点是可测的（写一条 transform 试图读 `document.cookie`，断言拿不到目标站的值）。第二点是**不可测的**，它靠的是"自愈代码路径里没有那个参数"，一次疏忽的重构就能破坏，且不会有测试失败。所以第二点应该在实现时写成显式断言而不只是"没传参数"——例如自愈路径调用标定函数时传一个 `allow_script=False` 并在函数入口 assert。

**产品判断（依据只到代码为止）**：三档是否值得做，取决于你实际想追的站里有多少是 selector 抽不了的。目前样本是 2 个站、0 个需要三档（claude.com 逼近上限但没越过）。**这个样本量支撑不了"需要三档"这个结论。** 稳妥的做法是先做一档到二档（transform 覆盖了字段清洗和条目过滤，那是最常见的两类缺口），三档留到真的撞上第一个 selector + transform 都救不了的站再做——那时也会有一个真实用例来验证评审流程，而不是对着假想场景设计。这条与"现在就把三档做完"是两条路，我倾向前者，但没有替你选。

---

## 11. 把握度

**读过代码确认的：**

- cookie 注入全部在 Python 侧、`page.goto` 之前完成（`core.py` 的 14 处 `add_cookies`/`extract_cookies`）
- 现有四个抽取器的 JS 不含 `document.cookie` / `localStorage` / credentials
- `_scrape_articles` 在 `evaluate` 之后只做了"丢弃无 url 条目"，没有其他归一化
- 一档求值模板的两行归一化在 JS 侧（`extractors.py` 的 `_EXTRACT_JS_ARTICLES_TEMPLATE`）
- selector 通过 `json.dumps` 成为 JS 字符串字面量，无法逃逸
- 现有规则库是扁平 `<domain>.json`，当前有 2 条
- claude.com/blog 的双份渲染是实测遇到的，不是假想

**推出来的（未实测）：**

- `about:blank` 上的 `page.evaluate` 拿不到目标站 cookie —— 按 playwright 的 origin 隔离推的，没写测试验证过
- `urljoin` 对绝对 URL 幂等 —— 标准库语义，但没在本项目的真实数据上跑过
- `os.replace` 对目录在 macOS + APFS 上的原子性 —— 对空目标目录成立，目标已存在时的行为需要实现时确认

**没查的：**

- 评审 subagent 用哪个模型、成本多少
- `.tmp` 孤儿目录在长期运行下的累积速度
- 你实际想追的站里有多少真的需要三档（§10 的产品判断就卡在这里）
