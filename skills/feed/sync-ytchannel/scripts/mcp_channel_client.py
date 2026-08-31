#!/usr/bin/env python3
"""browser-fetch CLI wrapper for the `channel` subcommand. 模块名的 mcp_
前缀是历史遗留，保留是为了不波及 SKILL.md 和上游 fetch_new_videos.py。

保持 async def：fetch_new_videos.py 在 asyncio.run() 里 await 它。
"""
from typing import Optional

import browser_fetch_cli


async def fetch_channel_videos(
    channel_url: str, chrome_profile: Optional[str] = None, max_videos: int = 30
) -> list[dict]:
    args = ["channel", channel_url, "--max", str(max_videos)]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    return browser_fetch_cli.call(*args)["videos"]
