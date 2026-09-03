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

    mode 白名单在这里再挡一道，但目前没有任何生产代码会经过这个函数 ——
    SKILL.md 的 calibrate 流程（含 run 的自愈复用的那一份）是让模型直接
    shell 出去调 browser-fetch CLI，不经过这层 Python 封装。今天"自愈上限
    二档"这条性质，实际是靠 CLI 自己的 `--mode` choices 撑住的（见
    cli.py）。这道白名单是为将来预留的第二道防线：CLI 的 choices 随时可能
    因为加三档支持而放开，届时若有调用方真的路由到这个函数，这里仍然会
    把关。是否要把自愈路径真正接到这个函数上、让这道防线生效，是阶段二
    （Task 13）待决定的问题。
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
