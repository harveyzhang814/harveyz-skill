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
