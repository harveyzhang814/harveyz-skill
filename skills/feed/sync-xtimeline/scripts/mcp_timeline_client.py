#!/usr/bin/env python3
"""browser-fetch CLI wrapper for the `timeline` subcommand. 模块名的 mcp_
前缀是历史遗留（本 skill 早期通过 MCP 调用），保留是为了不波及 SKILL.md
和上游 fetch_new_tweets.py。

保持 async def：fetch_new_tweets.py 在 asyncio.run() 里 await 它，
签名不变，上游零改动。
"""
from typing import Optional

import browser_fetch_cli


async def fetch_timeline(
    profile_url: str, chrome_profile: Optional[str] = None, max_tweets: int = 20
) -> list[dict]:
    args = ["timeline", profile_url, "--max", str(max_tweets)]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    return browser_fetch_cli.call(*args)["tweets"]
