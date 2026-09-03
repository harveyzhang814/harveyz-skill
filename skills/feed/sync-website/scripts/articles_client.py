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


ALLOWED_MODES = ("selector", "selector+transform")


async def probe_articles(
    list_url: str,
    selectors: dict,
    transform_file: Optional[str] = None,
    chrome_profile: Optional[str] = None,
) -> list[dict]:
    """标定试跑，不落盘。"""
    import json as _json
    args = ["articles-probe", list_url, "--selectors", _json.dumps(selectors, ensure_ascii=False)]
    if transform_file:
        args += ["--transform-file", transform_file]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    return browser_fetch_cli.call(*args)["articles"]


async def set_rule(
    domain: str,
    list_url: str,
    selectors: dict,
    sample: list,
    mode: str = "selector",
    transform_file: Optional[str] = None,
) -> dict:
    """固化规则。

    mode 白名单在这里再挡一道 —— 自愈路径上限是二档（spec §4），而 skill
    这一层是自愈唯一的调用入口。CLI 侧也有 choices 限制，但那道限制随时
    可能因为加三档支持而放开；这一道是给自愈路径专用的，不随之放开。
    """
    import json as _json
    if mode not in ALLOWED_MODES:
        raise ValueError(f"sync-website 不能写 mode={mode!r}：自愈与常规标定上限是二档")
    args = [
        "articles-rule", "set", domain,
        "--selectors", _json.dumps(selectors, ensure_ascii=False),
        "--list-url", list_url,
        "--sample", _json.dumps(sample, ensure_ascii=False),
        "--mode", mode,
    ]
    if transform_file:
        args += ["--transform-file", transform_file]
    return browser_fetch_cli.call(*args)
