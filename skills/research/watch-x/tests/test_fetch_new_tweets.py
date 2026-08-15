"""Only the deterministic, network-free path is covered here (empty
watchlist) — per-handle fetch/diff behavior is covered by
test_watchlist.py's compute_update tests (pure, no network) and
test_mcp_timeline_client.py's validation tests (real MCP call, no live
X login needed). A full live run needs a real logged-in Chrome profile,
same out-of-scope boundary as the rest of the xcom test suite.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_new_tweets.py"


def test_empty_watchlist_produces_empty_report(tmp_path):
    data_dir = tmp_path / "data"
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={**os.environ, "HSKILL_WATCH_X_DATA_DIR": str(data_dir),
             "BROWSER_FETCH_MCP_DATA_DIR": str(tmp_path / "bfm-data")},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["new"] == {}
    assert report["baselines"] == {}
    assert report["failures"] == {}
    assert "run_time" in report
