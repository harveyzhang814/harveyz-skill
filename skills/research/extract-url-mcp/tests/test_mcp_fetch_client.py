"""Stage 3 validation test: real network, real browser-fetch-mcp subprocess,
real MCP stdio protocol, real fetch_article (site-aware extraction with
image download) — no mocks.

Run: python3 -m pytest skills/research/extract-url-mcp/tests/ -v
(ambient system Python — matches how mcp_fetch_client.py itself runs)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from mcp_fetch_client import fetch_and_save  # noqa: E402


def test_fetch_and_save_writes_real_content(tmp_path):
    origin_path = asyncio.run(fetch_and_save("https://example.com", tmp_path))

    assert origin_path.exists()
    assert origin_path.name == "article.md"
    assert origin_path.parent.name == "Origin"
    content = origin_path.read_text(encoding="utf-8")

    assert "source_url: https://example.com" in content
    assert 'origin_title: "Example Domain"' in content
    assert "author:" in content
    assert "publish_date:" in content
    assert "# Example Domain" in content
    assert "This domain is for use in documentation examples" in content
    # title dedup: the heading should not repeat as a body block
    assert content.count("Example Domain") == 2  # frontmatter + heading only


def test_fetch_and_save_extracts_multiple_blocks_and_downloads_images(tmp_path):
    origin_path = asyncio.run(
        fetch_and_save("https://en.wikipedia.org/wiki/Model_Context_Protocol", tmp_path)
    )

    content = origin_path.read_text(encoding="utf-8")
    paragraphs = [p for p in content.split("\n\n") if p.strip() and not p.startswith("---")]
    # frontmatter block + heading + at least a few real paragraphs
    assert len(paragraphs) >= 5
    assert "Model Context Protocol" in content

    # fetch_article downloads real images for this page (7 as of writing) —
    # confirm at least one landed next to Origin/, and the body references it.
    article_dir = origin_path.parent.parent
    image_dir = article_dir / "Image"
    assert image_dir.exists()
    assert len(list(image_dir.iterdir())) > 0
    assert "![](../Image/" in content


def test_fetch_and_save_accepts_chrome_profile_without_crashing(tmp_path):
    """Doesn't assert on retry content (needs real auth cookies, out of
    scope for an automated test) — just confirms chrome_profile is
    correctly forwarded to fetch_article and the call completes."""
    empty_profile = tmp_path / "EmptyProfile"
    origin_path = asyncio.run(
        fetch_and_save("https://example.com", tmp_path, chrome_profile=str(empty_profile))
    )
    assert origin_path.exists()
