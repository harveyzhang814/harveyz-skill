---
migrated: false
---

# fetch_user_timeline：拟人化抓取节奏设计

## 背景

`sync-xtimeline` 通过 `browser-fetch-mcp` 的 `fetch_user_timeline` 抓取被关注账号的时间线。抓取用的是用户本人的真实登录态（从本地 Chrome 解密出的 session cookie），但翻页动作是典型的脚本特征：

- 滚动走 `page.evaluate("window.scrollBy(0, window.innerHeight * 3)")`——不产生任何输入事件，且一次跳三屏。
- 每轮固定 `wait_for_timeout(800)`，节奏机械。
- 账号之间零间隔串行轮询，抓完一个立刻关浏览器开下一个。
- 唯一的反检测措施是 `--disable-blink-features=AutomationControlled` 加一个固定 UA，时序、viewport 都不随机。

风险落点是用户的真实账号：一旦被判定为自动化，代价是限流、临时锁定或强制验证，不是某个可丢弃的测试号。

这轮设计把抓取节奏改成贴近真人浏览的行为，代价是运行时间从 15-20 秒/账号涨到最坏约 1.5 分钟/账号。

## 范围

**做：**

- 新增 `browser_fetch_mcp/pacing.py`：节奏决策的纯函数集合，全部接收调用方传入的 `random.Random`，不做 I/O、不 sleep。
- `_xcom_scrape_timeline` 的滚动编舞改为真实输入事件（`page.mouse.wheel` / `page.mouse.move`）+ 随机停顿 + 偶发回滚。
- viewport 每次调用随机取值，不再固定 `1280x900`。
- `fetch_user_timeline` 两次调用之间强制随机冷却，冷却状态落盘在 `_data_dir()/timeline_pace.json`，跨进程生效。
- `config.py` 扩两个纯 I/O 函数读写该时间戳。
- `pacing.py` 与新增 config 函数的确定性单元测试。

**不做：**

- 不改 `skills/research/sync-xtimeline/` 下任何文件。节奏是 MCP 工具自带的默认行为，任何调用方都自动享有，调用方不需要知道它存在。
- 不随机化账号遍历顺序。工具一次只看见一个 `profile_url`，结构上不知道关注列表存在；固定顺序是很弱的信号，不值得为它把机制拆回 skill 侧。
- 不把 watchlist / 已读游标内化进 MCP。那是 `sync-xtimeline` 的业务状态，不是浏览能力；且 `browser-fetch-mcp` 由 `clip-url` 共用，不应为单一消费者承担订阅语义。
- 不改成整个 run 复用一个浏览器会话。保持每账号一次独立启动，换取天然的失败隔离和逐账号落盘的游标。
- 不加任何配置项或 MCP 工具参数。所有常量硬编码在 `pacing.py` 顶部。
- 不碰 TLS 指纹、Canvas/WebGL 指纹、Playwright 自身的 CDP 痕迹。本设计只针对**行为指纹**。
- 不为浏览器交互本身写测试（沿用现有 xcom 抽取的测试策略，见"测试策略"）。

## 架构

三个模块，职责互不重叠：

| 模块 | 职责 | 可测性 |
|---|---|---|
| `pacing.py` | 纯决策：给定 `rng`，返回滚多少、停多久、要不要回滚、viewport 多大 | 固定种子即可确定性断言 |
| `config.py` | 纯 I/O：读写 `timeline_pace.json` 里的上次抓取时间戳 | tmp_path 往返测试 |
| `server.py` | 编排：把决策翻译成 Playwright 调用，执行 sleep | 不测（需要真实浏览器与登录态） |

### a) `pacing.py`

常量：

```python
INITIAL_DWELL_RANGE     = (2.0, 5.0)     # 秒；页面出现首条推文后、首次滚动前
WHEEL_TICKS_RANGE       = (8, 15)        # 每轮滚动拆成几个滚轮事件
WHEEL_DELTA_RANGE       = (100, 200)     # 每个滚轮事件的像素位移
WHEEL_TICK_GAP_RANGE    = (0.03, 0.08)   # 秒；滚轮事件之间
READ_PAUSE_RANGE        = (1.5, 4.0)     # 秒；常规"扫一眼新出现的卡片"
LONG_PAUSE_RANGE        = (8.0, 15.0)    # 秒；被某条推文吸引住
LONG_PAUSE_PROBABILITY  = 1 / 6
BACKSCROLL_PROBABILITY  = 0.2            # 滚过头往回拉
BACKSCROLL_TICKS_RANGE  = (2, 4)         # 回滚比正向滚更短
VIEWPORT_WIDTH_RANGE    = (1280, 1600)
VIEWPORT_HEIGHT_RANGE   = (800, 1000)
COOLDOWN_RANGE          = (20.0, 90.0)   # 秒；两次 fetch_user_timeline 之间
```

接口：

```python
def pick_initial_dwell(rng) -> float
def plan_scroll_burst(rng, *, backward: bool = False) -> list[tuple[int, float]]
    # [(delta_y_px, gap_seconds), ...]
    # backward=True → delta_y 取负、tick 数用 BACKSCROLL_TICKS_RANGE
def pick_read_pause(rng) -> float          # 按 LONG_PAUSE_PROBABILITY 落到长停顿区间
def should_backscroll(rng) -> bool
def plan_mouse_move(rng, viewport) -> tuple[int, int, int]   # (x, y, steps)
def pick_viewport(rng) -> dict             # {"width": w, "height": h}
def pick_cooldown(rng) -> float
```

滚轮拆成 8-15 个 100-200px 的小 tick 而不是一次跳三屏，是因为真人滚轮输出的就是一串小增量；`page.mouse.wheel` 经 CDP 派发的是 trusted 事件，`window.scrollBy` 不是。

`rng` 由 `server.py` 持有一个模块级 `_rng = random.Random()`（无种子，每次进程启动自播种）传入；`pacing.py` 自己不持有任何随机状态，测试传 `random.Random(seed)`。

下文伪代码里的 `sleep(秒)` 一律实现为 `await page.wait_for_timeout(秒 * 1000)`（与现有 `_xcom_scrape_timeline` 一致），只有冷却发生在浏览器存在之前，用 `await asyncio.sleep(秒)`。

### b) `config.py` 扩两个函数

```python
def get_last_timeline_fetch_at(data_dir: Path) -> Optional[float]   # epoch 秒
def set_last_timeline_fetch_at(data_dir: Path, ts: float) -> None
```

写在**独立文件** `timeline_pace.json`，不能塞进 `config.json`——`set_default_chrome_profile` 是整份覆写的，会把时间戳冲掉。

### c) `server.py`：`fetch_user_timeline` 的冷却

```
fetch_user_timeline(profile_url, chrome_profile, max_tweets)
  │
  ├─ URL scheme 校验 / 非 x.com 拒绝 / chrome_profile 缺失 → ValueError   ← 冷却之前，保持快速失败
  ├─ 提取 cookie；无 session cookie → ValueError                          ← 同上
  │
  ├─ 冷却：last = config.get_last_timeline_fetch_at(_data_dir())
  │        if last is not None:
  │            remaining = pacing.pick_cooldown(_rng) - (now - last)
  │            if remaining > 0: await asyncio.sleep(remaining)
  │
  ├─ try: headed 抓取 → 失败则 headless 抓取
  └─ finally: config.set_last_timeline_fetch_at(_data_dir(), now)         ← 成功失败都写
```

冷却必须放在全部校验之后、浏览器启动之前。放前面会让现有的参数校验测试（`test_fetch_user_timeline.py` 里四个 ValueError 用例，均不启动浏览器）每个都真睡几十秒。

时间戳在 `finally` 里更新，所以抓取失败同样计入冷却——出错之后更不该立刻重试。

单独手工调一次 `fetch_user_timeline` 不会白等：距上次抓取已经几小时的话，`remaining` 算出来是负数，不 sleep。

### d) `server.py`：`_xcom_scrape_timeline` 的滚动编舞

```
viewport = pacing.pick_viewport(_rng)        # headed 与 headless 都设置
goto(profile_url) → wait_for_selector('article[data-testid="tweet"]')
sleep(pacing.pick_initial_dwell(_rng))       # 真人先看头部，不会选择器一返回就滚

backscrolled = False
for _ in range(_TIMELINE_MAX_SCROLL_ITERATIONS):
    result = page.evaluate(EXTRACT_JS_XCOM_TIMELINE)
    before = len(collected)
    merge result into collected

    if len(collected) >= max_tweets: break

    if len(collected) == before:
        if backscrolled:
            pass                              # 回滚那一轮抓不到新推文是必然的，不算 stall
        else:
            stalls += 1
            if stalls >= _TIMELINE_STALL_LIMIT: break
    else:
        stalls = 0

    x, y, steps = pacing.plan_mouse_move(_rng, viewport)
    page.mouse.move(x, y, steps=steps)

    backscrolled = pacing.should_backscroll(_rng)
    for delta, gap in pacing.plan_scroll_burst(_rng, backward=backscrolled):
        page.mouse.wheel(0, delta)
        sleep(gap)

    sleep(pacing.pick_read_pause(_rng))
```

`backscrolled` 这个标志是必需的：回滚之后视口回到已抓过的区域，该轮必然抓不到新推文，现有的 `stalls` 计数器会把它误判成"feed 到底了"而提前 break。

viewport 现在只在 headed 分支设置（headless 走 Playwright 默认 1280x720）。改成两个分支都用 `pick_viewport`，消除固定尺寸这个指纹。

## 时间预算

单轮成本：滚轮 burst（8-15 tick × 0.03-0.08s ≈ 0.24-1.2s）+ 阅读停顿（1.5-4s，1/6 概率 8-15s），平均约 3.5s。

跑满 15 轮 ≈ 初始停留 3.5s + 15 × 3.5s ≈ 56s，加上期望 2.5 次长停顿约 +27s，**约 80 秒封顶**。落在 1-3 分钟/账号的预算内，不需要调 `_TIMELINE_MAX_SCROLL_ITERATIONS`。

**这是上限不是目标。** 抓够 `max_tweets`（默认 20）就 break——活跃账号可能 2-3 轮、20 秒就结束。打开主页扫两下就走本身就是真人行为，不为凑时长强行多滚。

headed 尝试若在编舞中途失败，headless 重试会把整套编舞重跑一遍，最坏翻倍到约 3 分钟。

## 错误处理

- 冷却期间的 `asyncio.sleep` 不捕获异常；调用方取消（MCP 客户端断开）时正常向上传播。
- `pacing.py` 的函数对非法 `rng` 或非法 viewport 不做防御性校验——调用方只有 `server.py`，参数由代码而非用户提供。
- `set_last_timeline_fetch_at` 写盘失败不吞：数据目录不可写是真问题，应当暴露。
- `_xcom_scrape_timeline` 的 `finally: browser.close()` 不变，编舞中途抛异常仍然关浏览器。

## 测试策略

`pacing.py` 全是纯函数，用固定种子做确定性测试（`tests/test_pacing.py`，新增）：

- `plan_scroll_burst`：tick 数落在 `WHEEL_TICKS_RANGE`；每个 delta 落在 `WHEEL_DELTA_RANGE`；每个 gap 落在 `WHEEL_TICK_GAP_RANGE`；`backward=True` 时 delta 全为负且 tick 数落在 `BACKSCROLL_TICKS_RANGE`。
- `pick_read_pause`：大量采样后既出现常规区间也出现长停顿区间，且长停顿占比接近 `LONG_PAUSE_PROBABILITY`。
- `should_backscroll`：大量采样后 True 占比接近 `BACKSCROLL_PROBABILITY`。
- `pick_viewport` / `pick_initial_dwell` / `pick_cooldown`：取值落在各自区间。
- `plan_mouse_move`：坐标落在传入 viewport 内。
- 同一种子两次调用结果相同（确定性本身）。

**测试不得真 sleep**——只断言返回的计划和时长数值。

`config.py` 新增两个函数做 `tmp_path` 往返测试，并断言 `set_default_chrome_profile` 之后时间戳仍在（验证两个文件互不干扰）。

`_xcom_scrape_timeline` 的浏览器交互不测：需要真实 x.com 登录态和真实页面结构，跟现有 xcom 抽取逻辑的测试策略一致。现有 `test_fetch_user_timeline.py` 只覆盖参数校验，本设计不扩大它的覆盖面，但必须保证那四个用例仍然不触发冷却 sleep（见架构 c）。

## 代价与已知局限

- **运行时长**：单账号 15-20s → 最坏约 1.5 分钟（headless 回退时约 3 分钟）。关注列表增长时线性放大：10 个账号含冷却最坏约 25 分钟。`/loop`、`schedule` 无人值守跑没问题，手动 `/sync-xtimeline run` 会明显变慢。
- **headed 模式更打扰**：真实滚轮事件会让可见的浏览器窗口真的滚动。
- **时长不可预测**：随机停顿让"卡住了"和"在停顿"难以区分。缓解手段是往 stderr 打一行进度（沿用现有 headed→headless 回退的 stderr 提示风格）。
- **冷却有并发竞态**：两个 `fetch_user_timeline` 并发时时间戳会互相覆盖。`sync-xtimeline` 严格串行，不加锁。
- **只覆盖行为指纹**：TLS 指纹、Canvas/WebGL 指纹、Playwright 的 CDP 痕迹一律不动。
- **冷却是全局的**：`timeline_pace.json` 不区分账号，任何两次时间线抓取之间都要冷却。这正是想要的（真人不会零间隔连刷十几个主页），但意味着抓一个全新账号也会被上一次抓取拖住。

## 未验证项

- `page.mouse.wheel` 经 CDP 派发 trusted 事件、比 `window.scrollBy` 更接近真实输入——这是 Playwright 的文档行为，**未在 x.com 上实测**。
- X 实际用哪些信号判定自动化、本设计能把风险降低多少——**无法验证**。本设计只能说方向对：消除的是可观测的机械特征，不是某个已知的检测规则。
- 时间预算里的"平均 3.5s/轮"是按区间中值推算的，**未实测**。

## 已验证项

- MCP 层无调用超时：`ClientSession.__init__` 与 `call_tool` 的 `read_timeout_seconds` 默认均为 `None`，3 分钟的工具调用不会被掐断（`mcp_timeline_client.py` 也没有传这个参数）。
- `fetch_user_timeline` 的唯一消费者是 `sync-xtimeline`；仓库内除 `server.py`/`extractors.py`/`test_fetch_user_timeline.py` 外无其他引用。
- `set_default_chrome_profile` 整份覆写 `config.json`，因此时间戳必须另放一个文件。
- 现有 `test_fetch_user_timeline.py` 的四个用例全部在参数校验阶段返回，从不启动浏览器。
