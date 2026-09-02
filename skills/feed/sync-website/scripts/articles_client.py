#!/usr/bin/env python3
"""browser-fetch CLI wrapper for the `articles` subcommand — the
sync-website counterpart of sync-ytchannel's mcp_channel_client.py. Wraps
the NO_RULE signal (browser-fetch exits 2 with "NO_RULE: <domain>" on
stderr, surfaced by browser_fetch_cli.call as a generic RuntimeError) into
a typed exception, so fetch_new_articles.py can route it to
report["needs_calibration"] without string-matching a generic error.

Keeps async def: fetch_new_articles.py awaits it inside asyncio.run().
"""
from typing import Optional

import browser_fetch_cli


class NoRuleError(Exception):
    """No calibrated selector rule exists yet for this URL's domain."""


async def fetch_articles(list_url: str, chrome_profile: Optional[str] = None) -> list[dict]:
    args = ["articles", list_url]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    try:
        return browser_fetch_cli.call(*args)["articles"]
    except RuntimeError as e:
        if str(e).startswith("NO_RULE:"):
            raise NoRuleError(str(e)) from e
        raise
