#!/usr/bin/env python3
"""Where sync-ytchannel keeps its state: watchlist.json and digests/.

Unlike sync-xtimeline there is no user-facing config step — the location is
fixed at ~/.hskill/sync-ytchannel/. HSKILL_SYNC_YTCHANNEL_DIR overrides it,
and is read on every call so tests can redirect it in-process.
"""
import os
from pathlib import Path


def get_data_dir() -> Path:
    override = os.environ.get("HSKILL_SYNC_YTCHANNEL_DIR")
    return Path(override) if override else Path.home() / ".hskill" / "sync-ytchannel"
