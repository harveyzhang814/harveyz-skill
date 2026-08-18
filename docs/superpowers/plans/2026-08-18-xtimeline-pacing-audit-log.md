# fetch_user_timeline 拟人节奏审计日志 实施计划

**目标：** 给 `fetch_user_timeline` 已有的拟人化节奏（冷却/viewport/滚动编舞）加一份按日期分文件的落盘审计日志，覆盖每次冷却判断、每轮滚动的每个 wheel tick、以及最终停止原因。

**架构：** 新增 `pacing_log.py`（纯 I/O，追加事件流，`config.py` 同级但读写模型不同）；`pacing.py` 不变；`server.py` 在编排点同步调用 `pacing_log.append_event`。

**技术栈：** Python, pytest。

**权威依据：** `docs/superpowers/specs/2026-08-18-xtimeline-pacing-audit-log-design.md`（本计划的模块划分、事件 schema、函数签名均取自此文档）。

---

### Task 1: `pacing_log.py` 纯 I/O 事件追加 + 往返测试

**文件：**
- 创建: `tools/browser-fetch-mcp/browser_fetch_mcp/pacing_log.py`
- 测试: `tools/browser-fetch-mcp/tests/test_pacing_log.py`

- [ ] **Step 1: 编写失败的测试**

```python
"""Round-trip tests for pacing_log.py's append-only JSONL audit log —
pure I/O, no timers, same tmp_path style as test_config.py."""
import json
from datetime import datetime

from browser_fetch_mcp import pacing_log


def test_append_event_writes_jsonl_line_with_event_and_fields(tmp_path):
    when = datetime(2026, 8, 18, 10, 30, 0)
    pacing_log.append_event(
        tmp_path, "cooldown", now=when, run_id="abc123", profile_url="https://x.com/someuser", waited_s=42.5
    )
    log_file = tmp_path / "timeline_pace_log-2026-08-18.jsonl"
    assert log_file.exists()
    line = log_file.read_text(encoding="utf-8").strip()
    entry = json.loads(line)
    assert entry["event"] == "cooldown"
    assert entry["run_id"] == "abc123"
    assert entry["profile_url"] == "https://x.com/someuser"
    assert entry["waited_s"] == 42.5
    assert entry["ts"] == when.isoformat(timespec="seconds")


def test_append_multiple_events_appends_lines_not_overwrite(tmp_path):
    when = datetime(2026, 8, 18, 10, 30, 0)
    pacing_log.append_event(tmp_path, "viewport", now=when, run_id="abc123", width=1400, height=900)
    pacing_log.append_event(tmp_path, "initial_dwell", now=when, run_id="abc123", dwell_s=3.2)
    log_file = tmp_path / "timeline_pace_log-2026-08-18.jsonl"
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "viewport"
    assert json.loads(lines[1])["event"] == "initial_dwell"


def test_events_on_different_dates_go_to_different_files(tmp_path):
    pacing_log.append_event(tmp_path, "cooldown", now=datetime(2026, 8, 17, 23, 0, 0), run_id="a")
    pacing_log.append_event(tmp_path, "cooldown", now=datetime(2026, 8, 18, 0, 5, 0), run_id="b")
    assert (tmp_path / "timeline_pace_log-2026-08-17.jsonl").exists()
    assert (tmp_path / "timeline_pace_log-2026-08-18.jsonl").exists()
    day1 = (tmp_path / "timeline_pace_log-2026-08-17.jsonl").read_text(encoding="utf-8").strip().splitlines()
    day2 = (tmp_path / "timeline_pace_log-2026-08-18.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(day1) == 1
    assert len(day2) == 1


def test_append_event_swallows_write_failure_and_warns(tmp_path, capsys):
    when = datetime(2026, 8, 18, 10, 30, 0)
    # Make the target log path a directory instead of a file, so open(path, "a") raises IsADirectoryError.
    (tmp_path / "timeline_pace_log-2026-08-18.jsonl").mkdir()
    pacing_log.append_event(tmp_path, "cooldown", now=when, run_id="abc123")  # must not raise
    captured = capsys.readouterr()
    assert "pacing log write failed" in captured.err
```

- [ ] **Step 2: 运行测试确认失败（模块不存在）**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_pacing_log.py -q`
预期: FAIL（`ModuleNotFoundError: No module named 'browser_fetch_mcp.pacing_log'`）

- [ ] **Step 3: 编写最小实现**

```python
"""Append-only JSONL audit log for fetch_user_timeline's pacing decisions —
pure I/O, no business logic. One file per calendar day
(timeline_pace_log-YYYY-MM-DD.jsonl) so the log doesn't grow unbounded
across /loop's long-running scheduled runs. Write failures are swallowed
(a stderr warning, no exception) — this is an auxiliary audit trail, not
a hard dependency of the scrape itself."""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def _log_file(data_dir: Path, when: datetime) -> Path:
    return data_dir / f"timeline_pace_log-{when:%Y-%m-%d}.jsonl"


def append_event(data_dir: Path, event: str, *, now: Optional[datetime] = None, **fields) -> None:
    ts = now or datetime.now()
    entry = {"ts": ts.isoformat(timespec="seconds"), "event": event, **fields}
    try:
        with open(_log_file(data_dir, ts), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        print(
            f"[browser-fetch-mcp] pacing log write failed ({e}); continuing without logging this event",
            file=sys.stderr,
        )
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_pacing_log.py -q`
预期: PASS，4 passed

- [ ] **Step 5: 提交**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/pacing_log.py tools/browser-fetch-mcp/tests/test_pacing_log.py
git commit -m "feat(browser-fetch-mcp): add pacing_log.py JSONL audit event log"
```

---

### Task 2: `server.py` — `_xcom_scrape_timeline` 接入节奏事件 + `stopped_reason`

**文件：**
- 修改: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`（import、`_xcom_scrape_timeline` 签名与函数体）

无新增自动化测试（浏览器交互不测）。本任务用全量回归 + 现有四个 timeline 校验用例计时来验证没有破坏既有行为。

- [ ] **Step 1: 加 import**

第 31 行：

```python
from browser_fetch_mcp import config, markdown, pacing
```

改为：

```python
from browser_fetch_mcp import config, markdown, pacing, pacing_log
```

第 6-11 行 import 区加一行 `import uuid`（放在 `import time` 之后按字母序）：

```python
import asyncio
import hashlib
import os
import random
import sys
import time
import uuid
```

- [ ] **Step 2: 改 `_xcom_scrape_timeline` 签名，加 `run_id` 参数**

原：

```python
async def _xcom_scrape_timeline(
    profile_url: str, pw_cookies: list[dict], headless: bool, max_tweets: int
) -> dict:
```

改为：

```python
async def _xcom_scrape_timeline(
    profile_url: str, pw_cookies: list[dict], headless: bool, max_tweets: int, run_id: str
) -> dict:
```

- [ ] **Step 3: 挑 viewport 后记 `"viewport"`，dwell 后记 `"initial_dwell"`**

原（158-176 行内）：

```python
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
```

改为：

```python
        attempt = "headless" if headless else "headed"
        try:
            viewport = pacing.pick_viewport(_rng)
            pacing_log.append_event(
                _data_dir(), "viewport", run_id=run_id, attempt=attempt,
                width=viewport["width"], height=viewport["height"],
            )
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
            initial_dwell = pacing.pick_initial_dwell(_rng)
            pacing_log.append_event(
                _data_dir(), "initial_dwell", run_id=run_id, attempt=attempt,
                dwell_s=round(initial_dwell, 2),
            )
            await page.wait_for_timeout(initial_dwell * 1000)
```

- [ ] **Step 4: 改滚动循环——加 `i`、`stopped_reason`、每轮 `scroll_pass_start`/`wheel_tick`/`scroll_pass_end`**

原（177-207 行）：

```python
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
```

改为：

```python
            collected: dict[str, dict] = {}
            stalls = 0
            backscrolled = False
            stopped_reason = "iteration_limit"
            iterations_run = 0
            for i in range(_TIMELINE_MAX_SCROLL_ITERATIONS):
                iterations_run = i + 1
                result = await page.evaluate(EXTRACT_JS_XCOM_TIMELINE)
                before = len(collected)
                for tweet in result["tweets"]:
                    collected[tweet["tweetId"]] = tweet

                if len(collected) >= max_tweets:
                    stopped_reason = "max_tweets"
                    break
                if len(collected) == before:
                    if backscrolled:
                        pass
                    else:
                        stalls += 1
                        if stalls >= _TIMELINE_STALL_LIMIT:
                            stopped_reason = "stall_limit"
                            break
                else:
                    stalls = 0

                pacing_log.append_event(
                    _data_dir(), "scroll_pass_start", run_id=run_id, attempt=attempt,
                    iteration=i, tweets_before=before, stalls=stalls,
                )

                x, y, steps = pacing.plan_mouse_move(_rng, viewport)
                await page.mouse.move(x, y, steps=steps)

                backscrolled = pacing.should_backscroll(_rng)
                for tick_index, (delta, gap) in enumerate(pacing.plan_scroll_burst(_rng, backward=backscrolled)):
                    await page.mouse.wheel(0, delta)
                    await page.wait_for_timeout(gap * 1000)
                    pacing_log.append_event(
                        _data_dir(), "wheel_tick", run_id=run_id, attempt=attempt,
                        iteration=i, tick_index=tick_index, delta=delta, gap_s=round(gap, 3),
                    )

                read_pause = pacing.pick_read_pause(_rng)
                await page.wait_for_timeout(read_pause * 1000)

                pacing_log.append_event(
                    _data_dir(), "scroll_pass_end", run_id=run_id, attempt=attempt,
                    iteration=i, tweets_after=len(collected), backscroll=backscrolled,
                    mouse_move={"x": x, "y": y, "steps": steps}, read_pause_s=round(read_pause, 2),
                )

            tweets = sorted(collected.values(), key=lambda t: int(t["tweetId"]), reverse=True)
            tweets = tweets[:max_tweets]
            pacing_log.append_event(
                _data_dir(), "scrape_attempt_end", run_id=run_id, attempt=attempt,
                total_tweets=len(tweets), iterations_run=iterations_run, stopped_reason=stopped_reason,
            )
            return {"tweets": tweets}
```

（`stopped_reason` 默认值 `"iteration_limit"`：循环跑满 `_TIMELINE_MAX_SCROLL_ITERATIONS` 次都没触发 `max_tweets` 或 `stall_limit` 的 break 时，就是自然跑到循环结束，对应这个默认值，不需要在循环尾部再显式赋值。)

- [ ] **Step 5: 全量回归**

运行: `cd tools/browser-fetch-mcp && uv run pytest -q`
预期: PASS，全部通过（99 + Task 1 新增 4 = 103）

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_fetch_user_timeline.py -q`
预期: PASS，4 passed，< 5s（此时 `fetch_user_timeline` 还没传 `run_id` 给 `_xcom_scrape_timeline`，这一步会在 Task 3 完成后才真正调得通；这里先确认 Task 2 的改动本身没有语法错误、没有意外影响这四个用例——它们在参数校验阶段就返回，根本不会进入 `_xcom_scrape_timeline`）

- [ ] **Step 6: 提交**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py
git commit -m "feat(browser-fetch-mcp): log wheel-tick-level pacing events during timeline scroll"
```

---

### Task 3: `server.py` — `fetch_user_timeline` 接入 `run_id`/冷却事件/`fetch_end`

**文件：**
- 修改: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`（`fetch_user_timeline` 函数体）

无新增自动化测试；用现有 `test_fetch_user_timeline.py` 的四个用例验证 `run_id` 生成和日志调用没有泄漏到校验之前。

- [ ] **Step 1: 运行现有四个用例记录当前耗时基线**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_fetch_user_timeline.py -q`
预期: PASS，4 passed，< 5s（Task 2 结束时的基线）

- [ ] **Step 2: 冷却判断处生成 `run_id`，记 `"cooldown"`/`"cooldown_skipped"`**

原（534-539 行）：

```python
    now = time.time()
    last = config.get_last_timeline_fetch_at(_data_dir())
    if last is not None:
        remaining = pacing.pick_cooldown(_rng) - (now - last)
        if remaining > 0:
            await asyncio.sleep(remaining)
```

改为：

```python
    run_id = uuid.uuid4().hex[:12]

    now = time.time()
    last = config.get_last_timeline_fetch_at(_data_dir())
    if last is not None:
        planned_cooldown = pacing.pick_cooldown(_rng)
        remaining = planned_cooldown - (now - last)
        waited = max(remaining, 0.0)
        pacing_log.append_event(
            _data_dir(), "cooldown", run_id=run_id, profile_url=profile_url, last_fetch_at=last,
            planned_cooldown_s=round(planned_cooldown, 2), waited_s=round(waited, 2),
        )
        if remaining > 0:
            await asyncio.sleep(remaining)
    else:
        pacing_log.append_event(
            _data_dir(), "cooldown_skipped", run_id=run_id, profile_url=profile_url, reason="no_previous_fetch",
        )
```

- [ ] **Step 3: 抓取阶段传 `run_id`，包一层记 `"fetch_end"`**

原（541-557 行）：

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

改为：

```python
    scrape_start = time.time()
    result = None
    error_msg = None
    headless_fallback = False
    try:
        try:
            result = await _xcom_scrape_timeline(
                profile_url, pw_cookies, headless=False, max_tweets=max_tweets, run_id=run_id
            )
        except Exception as e:
            headless_fallback = True
            print(
                f"[browser-fetch-mcp] headed timeline scrape failed ({e}); "
                f"falling back to headless (lower fidelity)",
                file=sys.stderr,
            )
            try:
                result = await _xcom_scrape_timeline(
                    profile_url, pw_cookies, headless=True, max_tweets=max_tweets, run_id=run_id
                )
            except Exception as e2:
                error_msg = str(e2)
                raise RuntimeError(
                    f"fetch_user_timeline failed for {profile_url} (headed and headless both failed): {e2}"
                ) from e2
    finally:
        config.set_last_timeline_fetch_at(_data_dir(), now)
        pacing_log.append_event(
            _data_dir(), "fetch_end", run_id=run_id, profile_url=profile_url,
            total_tweets=len(result["tweets"]) if result is not None else 0,
            headless_fallback=headless_fallback,
            duration_s=round(time.time() - scrape_start, 2),
            error=error_msg,
        )
```

- [ ] **Step 4: 运行四个用例确认没有泄漏到校验之前**

运行: `cd tools/browser-fetch-mcp && uv run pytest tests/test_fetch_user_timeline.py -q`
预期: PASS，4 passed，< 5s（与 Step 1 基线相当——这四个用例全部在 `run_id = uuid.uuid4()...` 之前的校验阶段就 raise ValueError）

- [ ] **Step 5: 全量回归**

运行: `cd tools/browser-fetch-mcp && uv run pytest -q`
预期: PASS，全部通过（103 passed）

- [ ] **Step 6: 确认 skill 侧零改动**

运行: `git diff staging --stat -- skills/`
预期: 空输出

- [ ] **Step 7: 提交**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py
git commit -m "feat(browser-fetch-mcp): log cooldown decision and fetch summary with run_id"
```

---

## 自检清单（写计划时已过一遍）

- **规格覆盖**：spec 的「架构设计」`pacing_log.py`/`fetch_user_timeline` 事件/`_xcom_scrape_timeline` 事件三节分别对应 Task 1/Task 3/Task 2；「数据流」的完整事件序列（cooldown → viewport → initial_dwell → scroll_pass\* → scrape_attempt_end → fetch_end）在 Task 2+3 的代码里全部出现。
- **占位符扫描**：无 TBD/TODO/"参考 Task N"。
- **类型一致性**：`pacing_log.append_event` 签名、`_xcom_scrape_timeline` 新增的 `run_id` 参数、`stopped_reason` 三个取值，在 Task 2/3 的代码块里保持一致；`attempt` 变量在 Task 2 Step 3 定义，Task 2 Step 4 沿用同一个局部变量，不重复计算。
- **测试覆盖边界**：Task 2/3 的 server.py 改动本身不写自动化测试（浏览器交互，沿用既有策略），靠全量回归 + 四个校验用例计时判断没有引入回归——这与 spec「测试策略」一节的边界一致。
