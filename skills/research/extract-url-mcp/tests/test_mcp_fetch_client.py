"""Stage 3 validation test: real network, real browser-fetch-mcp subprocess,
real MCP stdio protocol, real fetch_article (site-aware extraction with
image download) — no mocks.

Run: python3 -m pytest skills/research/extract-url-mcp/tests/ -v
(ambient system Python — matches how mcp_fetch_client.py itself runs)
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from mcp_fetch_client import fetch_and_save  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """fetch_and_save spawns browser-fetch-mcp with env=dict(os.environ), so the
    server subprocess inherits this. Point it at a per-test data dir so tests
    never read or write the real ~/.hskill/browser-fetch-mcp/ state (fetch_article
    consults the persisted default chrome_profile)."""
    monkeypatch.setenv("BROWSER_FETCH_MCP_DATA_DIR", str(tmp_path / "data"))


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


def test_fetch_and_save_image_placement_after_h1_dedup(tmp_path):
    """Regression test: verify images placed after the h1 block (after_block==0)
    are moved to pre_imgs when h1 dedup fires, not wrongly appended to the
    intro paragraph. Under the bug, dedup_offset was missing, so after_block
    indices were off by one — images meant for pre_imgs got glued onto the
    real article content instead, appearing in the same body unit.

    This test specifically checks that the intro paragraph body unit contains
    NO image references (images should be in earlier pre_imgs units instead)."""
    origin_path = asyncio.run(
        fetch_and_save("https://en.wikipedia.org/wiki/Model_Context_Protocol", tmp_path)
    )

    content = origin_path.read_text(encoding="utf-8")
    body_units = content.split("\n\n")

    # Find the body unit containing the real intro paragraph.
    # Exact phrase: "The Model Context Protocol (MCP) is an open standard..."
    # unique to the main article content, not nav lists.
    intro_idx = None
    for i, unit in enumerate(body_units):
        if (
            "The Model Context Protocol" in unit
            and "Anthropic" in unit
            and "open standard" in unit
        ):
            intro_idx = i
            break

    assert intro_idx is not None, "Intro paragraph not found in output"

    # Critical assertion: the intro paragraph itself must NOT contain images.
    # Under the bug, images with after_block==0 would be wrongly placed INTO
    # this very unit (concatenated with paragraph text), breaking the boundary
    # between pre-images and real content. Correct behavior: images stay in
    # earlier units (the pre_imgs section), not in this unit.
    assert (
        "![](../Image/" not in body_units[intro_idx]
    ), "Images wrongly placed in intro paragraph unit — dedup_offset bug detected"

    # Sanity check: images should exist somewhere in earlier units
    # (i.e., correctly attached to nav/heading content before article body).
    assert any(
        "![](../Image/" in unit for unit in body_units[:intro_idx]
    ), "No images found in pre-content units (unexpected)"
