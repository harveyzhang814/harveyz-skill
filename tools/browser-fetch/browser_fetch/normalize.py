"""page.evaluate 返回之后的共享归一化 —— spec §7.3。

跑在 Python 侧、在 JS 边界之外，所以三档（selector / selector+transform /
script）都绕不过去。一档模板已经用 linkEl.href 解析成绝对 URL，而 urljoin
对绝对 URL 幂等，所以无条件跑它不改变一档行为，同时兜住一个返回原始相对
href 的三档脚本 —— 相对 URL 会静默破坏游标与归档去重（两者都拿 URL 当主键）。

已知上限：三档 JS 返回原始相对属性、且页面带 <base href> 时，浏览器的
.href 是对的而 urljoin(list_url, ...) 会算错。三档写作约定要求返回 .href，
评审 subagent 检查这一条。
"""
import re
from urllib.parse import urljoin

_WHITESPACE = re.compile(r"\s+")


def _clean(value) -> str:
    """非字符串一律归零 —— 抽取 JS 是不可信输出，不假设它给的是字符串。"""
    if not isinstance(value, str):
        return ""
    return _WHITESPACE.sub(" ", value).strip()


def normalize_articles(raw_items, list_url: str) -> list[dict]:
    """把抽取 JS 的原始输出收敛成契约形状：恰好 title/url/date_text 三个
    字符串键。无法解析出 url 的条目丢弃 —— 一个没有可解析链接的条目永远
    不是一篇可用的文章。"""
    out = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        raw_url = item.get("url")
        url = urljoin(list_url, raw_url.strip()) if isinstance(raw_url, str) and raw_url.strip() else ""
        if not url:
            continue
        out.append({
            "title": _clean(item.get("title")),
            "url": url,
            "date_text": _clean(item.get("date_text")),
        })
    return out
