"""URL → (platform, handle)，以及 creator id 用的 slug。

YouTube 的正则原样取自 sync-ytchannel/scripts/watchlist.py，行为要保持一致：
/watch?v= 这类单视频链接必须拒绝——名册收的是渠道，不是单条物料。
"""
import re

_YOUTUBE_RE = re.compile(
    r"^https?://(?:www\.|m\.)?youtube\.com/(?:(@[^/?#]+)|(?:channel|c|user)/([^/?#]+))(?:/[^/?#]*)?/?(?:[?#].*)?$"
)
_X_RE = re.compile(
    r"^https?://(?:www\.)?(?:x|twitter)\.com/@?([A-Za-z0-9_]+)/?(?:[?#].*)?$"
)


def parse_channel_url(url: str) -> tuple[str, str]:
    url = url.strip()

    match = _YOUTUBE_RE.match(url)
    if match:
        at_handle, path_id = match.groups()
        return "youtube", (at_handle[1:] if at_handle else path_id)

    match = _X_RE.match(url)
    if match:
        return "x", match.group(1)

    raise ValueError(f"不是可识别的渠道 URL：{url}")


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    if not slug:
        raise ValueError(f"无法从 {text!r} 生成 slug")
    return slug


def channel_key(platform: str, handle: str) -> str:
    return f"{platform}:{handle}"
