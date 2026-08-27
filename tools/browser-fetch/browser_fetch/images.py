"""Image download for fetch_article: SSRF-safe URL check, extension
inference, and the download loop. Ported from extract-url's
playwright_web.py / playwright_web_wechat.py / playwright_web_arxiv.py,
which all carry an identical copy of this logic.
"""
import ipaddress
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def is_safe_image_url(src: str) -> bool:
    """Block file://, non-HTTP schemes, and private/loopback/link-local
    IPs (SSRF prevention)."""
    parsed = urlparse(src)
    if parsed.scheme not in ("http", "https"):
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except (ValueError, TypeError):
        pass  # hostname, not a bare IP — allow
    return True


_EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def infer_ext(url: str, content_type: str = "") -> str:
    """Guess a file extension from the URL or an explicit Content-Type."""
    if content_type:
        return _EXT_MAP.get(content_type, ".jpg")
    url_lower = url.lower()
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        if ext in url_lower:
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def download_images(image_blocks: list[dict], output_dir: Path) -> list[dict]:
    """Download each safe image in image_blocks to <output_dir>/Image/.

    Unsafe URLs are skipped entirely (not present in the result). A
    download failure still produces an entry with the intended filename —
    the caller can tell it failed by the file not existing on disk — so
    one bad image never aborts extraction of the rest of the article.
    """
    image_dir = Path(output_dir) / "Image"
    image_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for i, img in enumerate(image_blocks):
        if not is_safe_image_url(img["src"]):
            continue
        ext = infer_ext(img["src"])
        filename = f"img_{i + 1}{ext}"
        fpath = image_dir / filename
        try:
            req = urllib.request.Request(img["src"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            fpath.write_bytes(data)
        except Exception:
            pass
        downloaded.append(
            {"filename": filename, "alt": img.get("alt", ""), "after_block": img["afterBlock"]}
        )
    return downloaded
