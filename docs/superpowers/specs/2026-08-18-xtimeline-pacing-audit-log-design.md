---
migrated: false
---

# fetch_user_timeline：拟人节奏审计日志设计

## 概述

给 `fetch_user_timeline` 已实现的拟人化抓取节奏（冷却、viewport、滚动编舞）加一份落盘的行为日志，用于两件事：事后复盘某次抓取的节奏是否够拟人，以及排查抓取失败/提前 break 时当时的节奏参数。

## 背景

`docs/superpowers/specs/2026-08-17-xtimeline-human-pacing-design.md` 已经把 `fetch_user_timeline` 的翻页/冷却行为改成了拟人化节奏（`pacing.py` 纯决策函数 + `server.py` 编排），但整个过程没有留痕——出问题时只能靠 stderr 的 headed→headless 回退提示，看不到当时的 viewport、每轮滚了几个 tick、停了多久、有没有 backscroll。这轮补一份结构化的审计日志。

## 用户故事

- 用户手动跑一次 `/sync-xtimeline run` 后，想确认这次抓取"看起来像不像真人在刷"——翻开当天的日志文件，逐行看滚动/停顿序列。
- 某次抓取提前触发 stall break 或 headed 回退失败，用户想知道当时卡在哪一轮、参数是什么，而不是只看到一行 stderr 报错。

## 架构设计

新增 `browser_fetch_mcp/pacing_log.py`，与 `config.py` 同级、职责相似（纯 I/O，无业务逻辑），但读写模型不同：`config.py` 是"整份覆写的单值状态"，`pacing_log.py` 是"按日期分文件的追加事件流"。`pacing.py` 保持不变，不参与任何 I/O。

`server.py` 在 `fetch_user_timeline` 和 `_xcom_scrape_timeline` 的编排点调用 `pacing_log.append_event(...)`，同步写（不用 `asyncio.create_task`/`asyncio.to_thread`）——本地 append 一行 JSON 是亚毫秒级操作，相对于节奏本身秒级的停顿可忽略不计；同步写还能保证进程中途退出时已经执行到的事件不会丢，这对审计"失败现场"这条用户故事更重要。

一次 `fetch_user_timeline` 调用生成一个 `run_id`（`uuid.uuid4().hex[:12]`），贯穿该次调用产生的所有事件（包括 headed 失败后 headless 重试产生的另一批事件），审计时按 `run_id` 过滤就能拼出一次调用的完整节奏序列。

### `pacing_log.py`

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

`now` 是可选的显式参数（而不是函数内部悄悄取 `datetime.now()`），测试用固定时间戳注入，生产调用不传、走真实时钟——跟 `pacing.py` 的 `rng` 传入模式是同一个思路：调用方（测试或 `server.py`）决定不确定性从哪来。

### `server.py`：`fetch_user_timeline` 里的事件

在冷却判断处（现有代码 `now = time.time()` / `last = config.get_last_timeline_fetch_at(...)` 之后）：

```python
run_id = uuid.uuid4().hex[:12]

last = config.get_last_timeline_fetch_at(_data_dir())
if last is not None:
    planned_cooldown = pacing.pick_cooldown(_rng)
    remaining = planned_cooldown - (now - last)
    waited = max(remaining, 0.0)
    pacing_log.append_event(
        _data_dir(), "cooldown",
        run_id=run_id, profile_url=profile_url, last_fetch_at=last,
        planned_cooldown_s=round(planned_cooldown, 2), waited_s=round(waited, 2),
    )
    if remaining > 0:
        await asyncio.sleep(remaining)
else:
    pacing_log.append_event(
        _data_dir(), "cooldown_skipped",
        run_id=run_id, profile_url=profile_url, reason="no_previous_fetch",
    )
```

（`pick_cooldown` 只在 `last is not None` 时调用，跟现有逻辑一致——第一次抓取不消耗一次随机数、也不产生一条误导性的"计划冷却"日志。）

在抓取阶段，包一层记录耗时/结果，`result` 初始为 `None` 以便 `finally` 里安全判断：

```python
scrape_start = time.time()
result = None
error_msg = None
headless_fallback = False
try:
    try:
        result = await _xcom_scrape_timeline(profile_url, pw_cookies, headless=False, max_tweets=max_tweets, run_id=run_id)
    except Exception as e:
        headless_fallback = True
        print(
            f"[browser-fetch-mcp] headed timeline scrape failed ({e}); "
            f"falling back to headless (lower fidelity)",
            file=sys.stderr,
        )
        try:
            result = await _xcom_scrape_timeline(profile_url, pw_cookies, headless=True, max_tweets=max_tweets, run_id=run_id)
        except Exception as e2:
            error_msg = str(e2)
            raise RuntimeError(
                f"fetch_user_timeline failed for {profile_url} (headed and headless both failed): {e2}"
            ) from e2
finally:
    config.set_last_timeline_fetch_at(_data_dir(), now)
    pacing_log.append_event(
        _data_dir(), "fetch_end",
        run_id=run_id, profile_url=profile_url,
        total_tweets=len(result["tweets"]) if result is not None else 0,
        headless_fallback=headless_fallback,
        duration_s=round(time.time() - scrape_start, 2),
        error=error_msg,
    )
```

### `server.py`：`_xcom_scrape_timeline` 里的事件

函数签名加一个 `run_id: str` 参数。`attempt = "headless" if headless else "headed"`，所有事件带上它，因为 headed 失败重试 headless 时两批事件用同一个 `run_id` 但要能区分是哪次尝试。

- 挑完 viewport 后：`append_event(_data_dir(), "viewport", run_id=run_id, attempt=attempt, width=viewport["width"], height=viewport["height"])`
- 算出 initial dwell 后（`sleep` 之前）：`append_event(_data_dir(), "initial_dwell", run_id=run_id, attempt=attempt, dwell_s=round(dwell, 2))`
- 每轮循环开始（决定要不要继续滚之后、真正滚之前）：`append_event(_data_dir(), "scroll_pass_start", run_id=run_id, attempt=attempt, iteration=i, tweets_before=before, stalls=stalls)`
- 滚动 burst 里每个 tick 都记（这是本次澄清里用户明确要的粒度）：`append_event(_data_dir(), "wheel_tick", run_id=run_id, attempt=attempt, iteration=i, tick_index=tick_index, delta=delta, gap_s=round(gap, 3))`
- 本轮结束（read pause 之后）：`append_event(_data_dir(), "scroll_pass_end", run_id=run_id, attempt=attempt, iteration=i, tweets_after=len(collected), backscroll=backscrolled, mouse_move={"x": x, "y": y, "steps": steps}, read_pause_s=round(read_pause, 2))`
- 循环结束后：`append_event(_data_dir(), "scrape_attempt_end", run_id=run_id, attempt=attempt, total_tweets=len(tweets), iterations_run=i+1, stopped_reason=stopped_reason)`，其中 `stopped_reason` 取 `"max_tweets"` / `"stall_limit"` / `"iteration_limit"` 三者之一——需要在循环里新增一个局部变量跟踪触发了哪个 break 条件（现有代码只 `break`，不记原因）。

## 数据流

```
fetch_user_timeline 调用
  → 生成 run_id
  → 冷却判断 → 写 "cooldown" 或 "cooldown_skipped"
  → （可能 asyncio.sleep）
  → _xcom_scrape_timeline(headless=False, run_id) 编排一次抓取
      → 写 "viewport" → "initial_dwell"
      → 每轮循环：写 "scroll_pass_start" → N 条 "wheel_tick" → "scroll_pass_end"
      → 循环结束：写 "scrape_attempt_end"（attempt="headed"）
  → 若失败 → 同上再跑一遍 headless（attempt="headless"，同一个 run_id）
  → finally：写 "fetch_end"（不管成功失败都写，跟 set_last_timeline_fetch_at 同一个 finally）
```

所有事件落到 `_data_dir()/timeline_pace_log-<今天日期>.jsonl`，同一个 `run_id` 的事件按写入顺序自然是时间顺序（单进程内 `sync-xtimeline` 严格串行调用，不存在并发交错写乱序的问题——这跟冷却机制本身的并发假设一致）。

## 错误处理

- `append_event` 内部捕获 `OSError`（写盘失败：磁盘满、权限问题等），打印 stderr 提示后直接返回，不抛出、不重试——审计日志是辅助手段，不能成为抓推文这个主流程的单点故障。
- `_xcom_scrape_timeline` 或 `fetch_user_timeline` 本身抛出的异常不受影响：`pacing_log.append_event` 调用点都在 `finally` 或正常流程里，不会吞掉/掩盖原有的 `ValueError`/`RuntimeError`。
- `fetch_end` 事件的 `error` 字段只在 headed+headless 都失败时非空；单纯 headed 失败但 headless 成功的场景，`error=null` 但 `headless_fallback=true`，两者结合就能看出"重试过但最终成功"。

## 测试策略

`pacing_log.py` 是纯 I/O，跟 `config.py` 一样用 `tmp_path` 做往返测试（新增 `tests/test_pacing_log.py`）：

- 写一条事件后，文件按 `now` 参数对应的日期命名，文件内容是一行合法 JSON，字段与传入的 `event`/`**fields` 一致。
- 连续写两条事件，文件里是两行（追加而非覆盖）。
- 传入不同日期的 `now`，落到两个不同文件，互不干扰。
- 写盘失败时（构造一个目标路径实际是目录而非文件，触发 `IsADirectoryError`）不抛异常，`capsys` 断言 stderr 有提示。

`server.py` 里的调用点不新增自动化测试——浏览器交互本身不测，沿用 `2026-08-17` 设计的既有策略。但要跑一遍现有 `tests/test_fetch_user_timeline.py` 的四个用例，确认新增的 `pacing_log.append_event` 调用没有被安排进参数校验阶段（那四个用例应该连 `run_id` 都不会生成，因为它们在 `run_id = uuid.uuid4()...` 之前就已经 raise ValueError 返回了）。

## 风险和缓解

- **日志文件按日期切分但没有自动清理**：交给用户自己管（本次澄清已确认），长期看 `_data_dir()` 会积累多个 `timeline_pace_log-*.jsonl`，但审计日志本身也是数据，不做自动删除更安全。
- **`wheel_tick` 粒度下单次抓取可能产生几十上百行日志**（15 轮 × 8-15 tick ≈ 120-225 行/attempt，headed 失败回退时翻倍）：符合用户本次明确选择的粒度要求，不做精简。
- **日志字段里包含 `profile_url`**：这是用户自己关注列表里的公开账号 URL，不是敏感信息，落盘到用户本地 `_data_dir()`（`~/.hskill/browser-fetch-mcp/contexts` 或测试期间的 `BROWSER_FETCH_MCP_DATA_DIR` 覆盖路径）跟其他配置文件同等敏感级别。
