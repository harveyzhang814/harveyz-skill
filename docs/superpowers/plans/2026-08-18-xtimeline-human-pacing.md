# fetch_user_timeline 拟人化抓取节奏 实施计划

**目标：** 把 `fetch_user_timeline` 的翻页/冷却行为从机械脚本特征改成贴近真人浏览的节奏，机制全部落在 `browser-fetch-mcp` 工具侧。

**架构：** 三个模块职责不重叠——`pacing.py`（纯决策函数，接收 `random.Random`，不做 I/O/sleep）、`config.py`（纯 I/O，读写 `timeline_pace.json` 时间戳）、`server.py`（编排：把决策翻译成 Playwright 调用与 sleep）。

**技术栈：** Python, pytest, Playwright async API。

**权威依据：** `docs/superpowers/specs/2026-08-17-xtimeline-human-pacing-design.md`（本计划的所有常量、签名、伪代码均取自此文档，不重新设计）。

---

### Task 1: `pacing.py` 纯决策函数 + 确定性单测

**文件：**
- 创建: `tools/browser-fetch-mcp/browser_fetch_mcp/pacing.py`
- 测试: `tools/browser-fetch-mcp/tests/test_pacing.py`

- [ ] **Step 1: 编写失败的测试**

```python
"""Deterministic tests for pacing.py's pure decision functions — every
function takes a seeded random.Random, so no real sleeping happens here."""
import random

from browser_fetch_mcp import pacing


def test_plan_scroll_burst_forward_ticks_deltas_gaps_in_range():
    rng = random.Random(1)
    burst = pacing.plan_scroll_burst(rng)
    assert pacing.WHEEL_TICKS_RANGE[0] <= len(burst) <= pacing.WHEEL_TICKS_RANGE[1]
    for delta, gap in burst:
        assert pacing.WHEEL_DELTA_RANGE[0] <= delta <= pacing.WHEEL_DELTA_RANGE[1]
        assert pacing.WHEEL_TICK_GAP_RANGE[0] <= gap <= pacing.WHEEL_TICK_GAP_RANGE[1]


def test_plan_scroll_burst_backward_deltas_negative_and_shorter():
    rng = random.Random(2)
    burst = pacing.plan_scroll_burst(rng, backward=True)
    assert pacing.BACKSCROLL_TICKS_RANGE[0] <= len(burst) <= pacing.BACKSCROLL_TICKS_RANGE[1]
    for delta, gap in burst:
        assert -pacing.WHEEL_DELTA_RANGE[1] <= delta <= -pacing.WHEEL_DELTA_RANGE[0]
        assert pacing.WHEEL_TICK_GAP_RANGE[0] <= gap <= pacing.WHEEL_TICK_GAP_RANGE[1]


def test_pick_read_pause_distribution_hits_both_ranges_near_probability():
    rng = random.Random(3)
    samples = [pacing.pick_read_pause(rng) for _ in range(4000)]
    long_count = sum(1 for s in samples if s >= pacing.LONG_PAUSE_RANGE[0])
    short_count = len(samples) - long_count
    assert short_count > 0
    assert long_count > 0
    ratio = long_count / len(samples)
    assert abs(ratio - pacing.LONG_PAUSE_PROBABILITY) < 0.03
    for s in samples:
        in_short = pacing.READ_PAUSE_RANGE[0] <= s <= pacing.READ_PAUSE_RANGE[1]
        in_long = pacing.LONG_PAUSE_RANGE[0] <= s <= pacing.LONG_PAUSE_RANGE[1]
        assert in_short or in_long


def test_should_backscroll_distribution_near_probability():
    rng = random.Random(4)
    samples = [pacing.should_backscroll(rng) for _ in range(4000)]
    ratio = sum(samples) / len(samples)
    assert abs(ratio - pacing.BACKSCROLL_PROBABILITY) < 0.03


def test_pick_viewport_in_range():
    rng = random.Random(5)
    viewport = pacing.pick_viewport(rng)
    assert pacing.VIEWPORT_WIDTH_RANGE[0] <= viewport["width"] <= pacing.VIEWPORT_WIDTH_RANGE[1]
    assert pacing.VIEWPORT_HEIGHT_RANGE[0] <= viewport["height"] <= pacing.VIEWPORT_HEIGHT_RANGE[1]


def test_pick_initial_dwell_in_range():
    rng = random.Random(6)
    dwell = pacing.pick_initial_dwell(rng)
    assert pacing.INITIAL_DWELL_RANGE[0] <= dwell <= pacing.INITIAL_DWELL_RANGE[1]


def test_pick_cooldown_in_range():
    rng = random.Random(7)
    cooldown = pacing.pick_cooldown(rng)
    assert pacing.COOLDOWN_RANGE[0] <= cooldown <= pacing.COOLDOWN_RANGE[1]


def test_plan_mouse_move_coordinates_within_viewport():
    rng = random.Random(8)
    viewport = {"width": 1400, "height": 900}
    x, y, steps = pacing.plan_mouse_move(rng, viewport)
    assert 0 <= x <= viewport["width"]
    assert 0 <= y <= viewport["height"]
    assert steps > 0


def test_same_seed_produces_same_results_for_every_function():
    for fn, args, kwargs in [
        (pacing.pick_initial_dwell, (), {}),
        (pacing.plan_scroll_burst, (), {}),
        (pacing.plan_scroll_burst, (), {"backward": True}),
        (pacing.pick_read_pause, (), {}),
        (pacing.should_backscroll, (), {}),
        (pacing.pick_viewport, (), {}),
        (pacing.pick_cooldown, (), {}),
    ]:
        r1 = fn(random.Random(42), *args, **kwargs)
        r2 = fn(random.Random(42), *args, **kwargs)
        assert r1 == r2

    viewport = {"width": 1400, "height": 900}
    r1 = pacing.plan_mouse_move(random.Random(42), viewport)
    r2 = pacing.plan_mouse_move(random.Random(42), viewport)
    assert r1 == r2
```

- [ ] **Step 2: 运行测试确认失败（模块不存在）**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_pacing.py -q`
预期: FAIL（`ModuleNotFoundError: No module named 'browser_fetch_mcp.pacing'`）

- [ ] **Step 3: 编写最小实现**

```python
"""Pure decision functions for human-like scroll pacing on x.com timeline
scraping. No I/O, no sleeping — callers (server.py) translate the returned
plans into Playwright calls and page.wait_for_timeout()/asyncio.sleep().
Every function takes a caller-owned random.Random so tests can seed for
determinism; production passes an unseeded module-level instance that
self-seeds from OS entropy at process start."""
import random

INITIAL_DWELL_RANGE = (2.0, 5.0)
WHEEL_TICKS_RANGE = (8, 15)
WHEEL_DELTA_RANGE = (100, 200)
WHEEL_TICK_GAP_RANGE = (0.03, 0.08)
READ_PAUSE_RANGE = (1.5, 4.0)
LONG_PAUSE_RANGE = (8.0, 15.0)
LONG_PAUSE_PROBABILITY = 1 / 6
BACKSCROLL_PROBABILITY = 0.2
BACKSCROLL_TICKS_RANGE = (2, 4)
VIEWPORT_WIDTH_RANGE = (1280, 1600)
VIEWPORT_HEIGHT_RANGE = (800, 1000)
COOLDOWN_RANGE = (20.0, 90.0)
MOUSE_MOVE_STEPS_RANGE = (5, 15)


def pick_initial_dwell(rng: random.Random) -> float:
    return rng.uniform(*INITIAL_DWELL_RANGE)


def plan_scroll_burst(rng: random.Random, *, backward: bool = False) -> list[tuple[int, float]]:
    tick_range = BACKSCROLL_TICKS_RANGE if backward else WHEEL_TICKS_RANGE
    ticks = rng.randint(*tick_range)
    burst = []
    for _ in range(ticks):
        delta = rng.randint(*WHEEL_DELTA_RANGE)
        if backward:
            delta = -delta
        gap = rng.uniform(*WHEEL_TICK_GAP_RANGE)
        burst.append((delta, gap))
    return burst


def pick_read_pause(rng: random.Random) -> float:
    if rng.random() < LONG_PAUSE_PROBABILITY:
        return rng.uniform(*LONG_PAUSE_RANGE)
    return rng.uniform(*READ_PAUSE_RANGE)


def should_backscroll(rng: random.Random) -> bool:
    return rng.random() < BACKSCROLL_PROBABILITY


def plan_mouse_move(rng: random.Random, viewport: dict) -> tuple[int, int, int]:
    x = rng.randint(0, viewport["width"])
    y = rng.randint(0, viewport["height"])
    steps = rng.randint(*MOUSE_MOVE_STEPS_RANGE)
    return (x, y, steps)


def pick_viewport(rng: random.Random) -> dict:
    return {
        "width": rng.randint(*VIEWPORT_WIDTH_RANGE),
        "height": rng.randint(*VIEWPORT_HEIGHT_RANGE),
    }


def pick_cooldown(rng: random.Random) -> float:
    return rng.uniform(*COOLDOWN_RANGE)
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_pacing.py -q`
预期: PASS，9 passed，总用时 < 2s

- [ ] **Step 5: 提交**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/pacing.py tools/browser-fetch-mcp/tests/test_pacing.py
git commit -m "feat(browser-fetch-mcp): add pacing.py human-scroll decision functions"
```

---

### Task 2: `config.py` 扩两个函数读写 `timeline_pace.json`

**文件：**
- 修改: `tools/browser-fetch-mcp/browser_fetch_mcp/config.py`
- 修改: `tools/browser-fetch-mcp/tests/test_config.py`

- [ ] **Step 1: 编写失败的测试（追加到 test_config.py 末尾）**

```python
def test_get_last_timeline_fetch_at_returns_none_when_unconfigured(tmp_path):
    assert config.get_last_timeline_fetch_at(tmp_path) is None


def test_set_then_get_last_timeline_fetch_at_round_trips(tmp_path):
    config.set_last_timeline_fetch_at(tmp_path, 1755500000.0)
    assert config.get_last_timeline_fetch_at(tmp_path) == 1755500000.0


def test_timeline_pace_file_written_at_expected_location(tmp_path):
    config.set_last_timeline_fetch_at(tmp_path, 1.0)
    assert (tmp_path / "timeline_pace.json").exists()


def test_last_timeline_fetch_at_survives_set_default_chrome_profile(tmp_path):
    """set_default_chrome_profile fully overwrites config.json — the
    timeline timestamp must live in a separate file so it isn't wiped."""
    config.set_last_timeline_fetch_at(tmp_path, 1755500000.0)
    config.set_default_chrome_profile(tmp_path, "/some/chrome/profile")
    assert config.get_last_timeline_fetch_at(tmp_path) == 1755500000.0
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_config.py -q`
预期: FAIL（`AttributeError: module 'browser_fetch_mcp.config' has no attribute 'get_last_timeline_fetch_at'`）

- [ ] **Step 3: 编写最小实现（追加到 config.py 末尾）**

```python
def _pace_file(data_dir: Path) -> Path:
    return data_dir / "timeline_pace.json"


def get_last_timeline_fetch_at(data_dir: Path) -> Optional[float]:
    path = _pace_file(data_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("last_timeline_fetch_at")


def set_last_timeline_fetch_at(data_dir: Path, ts: float) -> None:
    path = _pace_file(data_dir)
    path.write_text(json.dumps({"last_timeline_fetch_at": ts}), encoding="utf-8")
```

（模块顶部已有 `import json`, `from pathlib import Path`, `from typing import Optional`，无需新增 import。）

- [ ] **Step 4: 运行测试确认通过**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_config.py -q`
预期: PASS，8 passed（原 4 + 新增 4）

- [ ] **Step 5: 提交**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/config.py tools/browser-fetch-mcp/tests/test_config.py
git commit -m "feat(browser-fetch-mcp): persist last timeline fetch timestamp"
```

---

### Task 3: `server.py` — `_xcom_scrape_timeline` 滚动编舞改为真实输入事件

**文件：**
- 修改: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py:1-16`（imports）、`:35`（`_rng` 模块级变量）、`:135-189`（`_xcom_scrape_timeline`）

无新增自动化测试（浏览器交互不测，沿用现有策略）。用 `uv run pytest -q` 全量回归确认没有破坏别的东西。

- [ ] **Step 1: 加 import 与模块级 `_rng`**

在 `server.py` 顶部 import 区（第 6-9 行 `import asyncio/hashlib/os/sys` 之后插入）：

```python
import random
import time
```

第 29 行 `from browser_fetch_mcp import config, markdown` 改为：

```python
from browser_fetch_mcp import config, markdown, pacing
```

第 35 行 `_state = {"playwright": None, "contexts": {}}` 之后插入：

```python
_rng = random.Random()
```

- [ ] **Step 2: 改写 `_xcom_scrape_timeline` 的 viewport 与滚动循环**

原文件 135-189 行整段替换为：

```python
async def _xcom_scrape_timeline(
    profile_url: str, pw_cookies: list[dict], headless: bool, max_tweets: int
) -> dict:
    """One-off browser launch for an x.com/twitter.com profile timeline —
    same lifecycle model as _xcom_scrape (never reuses the warm persistent
    context, always closes in finally), but scrolls repeatedly and merges
    each pass's visible cards into an accumulator (keyed by tweet_id, so a
    card re-seen after scrolling doesn't duplicate) instead of extracting
    once. Stops early once max_tweets are collected, or after
    _TIMELINE_STALL_LIMIT consecutive scroll passes yield no new tweets
    (the account has fewer than max_tweets total, or the feed stopped
    loading more).

    Scroll choreography uses page.mouse.wheel (a trusted, CDP-dispatched
    input event) broken into several small ticks with randomized gaps,
    occasional backscroll, and randomized read pauses — see
    docs/superpowers/specs/2026-08-17-xtimeline-human-pacing-design.md.
    A backscroll pass is expected to yield zero new tweets (the viewport
    moves back over already-collected cards) and must not count toward
    stalls, or it gets misread as "reached the end of the feed"."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            viewport = pacing.pick_viewport(_rng)
            ctx_kwargs = {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                "viewport": viewport,
            }

            ctx = await browser.new_context(**ctx_kwargs)
            await ctx.add_cookies(pw_cookies)
            page = await ctx.new_page()
            await page.goto(profile_url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=60000)
            await page.wait_for_timeout(pacing.pick_initial_dwell(_rng) * 1000)

            collected: dict[str, dict] = {}
            stalls = 0
            backscrolled = False
            for _ in range(_TIMELINE_MAX_SCROLL_ITERATIONS):
                result = await page.evaluate(EXTRACT_JS_XCOM_TIMELINE)
                before = len(collected)
                for tweet in result["tweets"]:
                    collected[tweet["tweetId"]] = tweet

                if len(collected) >= max_tweets:
                    break
                if len(collected) == before:
                    if backscrolled:
                        pass
                    else:
                        stalls += 1
                        if stalls >= _TIMELINE_STALL_LIMIT:
                            break
                else:
                    stalls = 0

                x, y, steps = pacing.plan_mouse_move(_rng, viewport)
                await page.mouse.move(x, y, steps=steps)

                backscrolled = pacing.should_backscroll(_rng)
                for delta, gap in pacing.plan_scroll_burst(_rng, backward=backscrolled):
                    await page.mouse.wheel(0, delta)
                    await page.wait_for_timeout(gap * 1000)

                await page.wait_for_timeout(pacing.pick_read_pause(_rng) * 1000)

            tweets = sorted(collected.values(), key=lambda t: int(t["tweetId"]), reverse=True)
            return {"tweets": tweets[:max_tweets]}
        finally:
            await browser.close()
```

- [ ] **Step 3: 全量回归 + 参数校验四用例计时**

运行: `cd tools/browser-fetch-mcp && uv run pytest -q`
预期: PASS，全部通过（86 + Task 1/2 新增用例数）

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_fetch_user_timeline.py -q`
预期: PASS，4 passed，< 5s（此时冷却还没接入 `fetch_user_timeline`，这一步只是确认改动没有意外影响这四个用例）

- [ ] **Step 4: 提交**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py
git commit -m "feat(browser-fetch-mcp): humanize timeline scroll choreography"
```

---

### Task 4: `server.py` — `fetch_user_timeline` 接入冷却

**文件：**
- 修改: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`（`fetch_user_timeline` 函数体，冷却校验之后、浏览器启动之前）

无新增自动化测试；用现有 `test_fetch_user_timeline.py` 的四个用例验证冷却没有泄漏到校验之前（这是本任务最大的坑）。

- [ ] **Step 1: 运行现有四个用例记录当前耗时基线**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_fetch_user_timeline.py -q`
预期: PASS，4 passed，< 5s（改动前基线）

- [ ] **Step 2: 在 cookie 校验之后、`_xcom_scrape_timeline` 调用之前插入冷却**

找到 `fetch_user_timeline` 函数体里这一段（cookie 校验结束处）：

```python
    pw_cookies = [
        {"name": k, "value": v, "domain": ".x.com", "path": "/", "secure": True}
        for k, v in cookies_dict.items()
    ]

    try:
        result = await _xcom_scrape_timeline(profile_url, pw_cookies, headless=False, max_tweets=max_tweets)
```

改为：

```python
    pw_cookies = [
        {"name": k, "value": v, "domain": ".x.com", "path": "/", "secure": True}
        for k, v in cookies_dict.items()
    ]

    now = time.time()
    last = config.get_last_timeline_fetch_at(_data_dir())
    if last is not None:
        remaining = pacing.pick_cooldown(_rng) - (now - last)
        if remaining > 0:
            await asyncio.sleep(remaining)

    try:
        result = await _xcom_scrape_timeline(profile_url, pw_cookies, headless=False, max_tweets=max_tweets)
```

- [ ] **Step 3: 在函数末尾加 `finally` 落盘时间戳**

找到 `fetch_user_timeline` 里现有的 headed→headless 回退逻辑：

```python
    try:
        result = await _xcom_scrape_timeline(profile_url, pw_cookies, headless=False, max_tweets=max_tweets)
    except Exception as e:
        print(
            f"[browser-fetch-mcp] headed timeline scrape failed ({e}); "
            f"falling back to headless (lower fidelity)",
            file=sys.stderr,
        )
        try:
            result = await _xcom_scrape_timeline(profile_url, pw_cookies, headless=True, max_tweets=max_tweets)
        except Exception as e:
            raise RuntimeError(
                f"fetch_user_timeline failed for {profile_url} (headed and headless both failed): {e}"
            ) from e
```

改为（外层包一个 `try/finally`，成功失败都写时间戳）：

```python
    try:
        try:
            result = await _xcom_scrape_timeline(profile_url, pw_cookies, headless=False, max_tweets=max_tweets)
        except Exception as e:
            print(
                f"[browser-fetch-mcp] headed timeline scrape failed ({e}); "
                f"falling back to headless (lower fidelity)",
                file=sys.stderr,
            )
            try:
                result = await _xcom_scrape_timeline(profile_url, pw_cookies, headless=True, max_tweets=max_tweets)
            except Exception as e:
                raise RuntimeError(
                    f"fetch_user_timeline failed for {profile_url} (headed and headless both failed): {e}"
                ) from e
    finally:
        config.set_last_timeline_fetch_at(_data_dir(), now)
```

- [ ] **Step 4: 运行四个用例确认冷却没有泄漏到校验之前**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_fetch_user_timeline.py -q`
预期: PASS，4 passed，< 5s（与 Step 1 基线相当——四个用例全部在 `now = time.time()` 之前的校验阶段就 raise ValueError，从未到达冷却逻辑）

- [ ] **Step 5: 全量回归**

运行: `cd tools/browser-fetch-mcp && uv run pytest -q`
预期: PASS，全部通过

- [ ] **Step 6: 确认 skill 侧零改动**

运行: `git diff staging --stat -- skills/`
预期: 空输出

- [ ] **Step 7: 提交**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py
git commit -m "feat(browser-fetch-mcp): add randomized cooldown between timeline fetches"
```

---

## 自检清单（写计划时已过一遍）

- **规格覆盖**：spec 的「架构」a/b/c/d 四节分别对应 Task 1（a）、Task 2（b）、Task 4（c）、Task 3（d）；「测试策略」的 pacing/config 断言点全部进了 Task 1/2 的测试代码。
- **占位符扫描**：无 TBD/TODO/"参考 Task N"/"添加适当的错误处理"。
- **类型一致性**：`pacing.py` 各函数签名与 spec 接口表一致；`plan_mouse_move` 的 `steps` 取值范围 spec 未给出具体数值，新增本地常量 `MOUSE_MOVE_STEPS_RANGE = (5, 15)`（仅供 Playwright `mouse.move(steps=...)` 使用，不影响任何测试断言的可证伪性——测试只断言 `steps > 0`）。
