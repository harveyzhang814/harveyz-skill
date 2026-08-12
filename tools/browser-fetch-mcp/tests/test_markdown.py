"""Unit tests for markdown.py's article assembly — pure string/file
logic, no MCP protocol, no browser, no network."""
from pathlib import Path

from browser_fetch_mcp.markdown import assemble_and_write, sanitize_filename, _format_block


def test_writes_frontmatter_and_heading(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="Example Domain",
        author="",
        publish_date="",
        blocks=[{"tag": "p", "content": "Some body text."}],
        image_blocks=[],
    )
    assert origin_path == tmp_path / "Origin" / "Example Domain.md"
    content = origin_path.read_text(encoding="utf-8")
    assert "source_url: https://example.com" in content
    assert 'origin_title: "Example Domain"' in content
    assert "# Example Domain" in content
    assert "Some body text." in content


def test_leading_h1_matching_title_is_deduped(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="My Title",
        author="",
        publish_date="",
        blocks=[
            {"tag": "h1", "content": "My Title"},
            {"tag": "p", "content": "Body paragraph."},
        ],
        image_blocks=[],
    )
    content = origin_path.read_text(encoding="utf-8")
    # frontmatter's origin_title + the "# My Title" heading only —
    # the h1 block must not ALSO appear a third time as a body block.
    assert content.count("My Title") == 2


def test_image_before_first_block_is_prepended(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="Untitled",
        author="",
        publish_date="",
        blocks=[{"tag": "p", "content": "Body paragraph."}],
        image_blocks=[{"filename": "img_1.jpg", "alt": "", "after_block": -1}],
    )
    content = origin_path.read_text(encoding="utf-8")
    body = content.split("# Untitled\n\n", 1)[1]
    assert body.startswith("![](../Image/img_1.jpg)")


def test_image_after_block_zero_moves_to_pre_imgs_when_h1_deduped(tmp_path):
    """Regression: after_block indices are computed against the ORIGINAL
    (undeduped) blocks list. When blocks[0] is a dropped h1, an image with
    after_block == 0 meant 'right after the h1' — that h1 is gone, so the
    image belongs at the very start of the body (pre_imgs), not glued to
    the next real paragraph."""
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="My Title",
        author="",
        publish_date="",
        blocks=[
            {"tag": "h1", "content": "My Title"},
            {"tag": "p", "content": "Intro paragraph."},
        ],
        image_blocks=[{"filename": "img_1.jpg", "alt": "", "after_block": 0}],
    )
    content = origin_path.read_text(encoding="utf-8")
    body_units = content.split("\n\n")
    intro_unit = next(u for u in body_units if "Intro paragraph." in u)
    assert "![](../Image/img_1.jpg)" not in intro_unit
    assert any("![](../Image/img_1.jpg)" in u for u in body_units if u != intro_unit)


def test_image_placed_after_matching_block_index(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="Untitled",
        author="",
        publish_date="",
        blocks=[
            {"tag": "p", "content": "First paragraph."},
            {"tag": "p", "content": "Second paragraph."},
        ],
        image_blocks=[{"filename": "img_1.jpg", "alt": "", "after_block": 0}],
    )
    content = origin_path.read_text(encoding="utf-8")
    body_units = content.split("\n\n")
    first_unit = next(u for u in body_units if "First paragraph." in u)
    assert "![](../Image/img_1.jpg)" in first_unit


def test_sanitize_filename_strips_unsafe_characters():
    assert sanitize_filename('Title: "A/B" <Test>?*|\\') == "Title AB Test"
    assert sanitize_filename("...leading dots") == "leading dots"


def test_block_tag_formatting():
    assert _format_block({"tag": "h2", "content": "Heading"}) == "## Heading"
    assert _format_block({"tag": "li", "content": "Item"}) == "- Item"
    assert _format_block({"tag": "blockquote", "content": "Quoted"}) == "> Quoted"
    assert _format_block({"tag": "table", "content": "| a | b |"}) == "| a | b |"
    assert _format_block({"tag": "pre", "content": "code()"}) == "```\ncode()\n```"
    assert _format_block({"tag": "code", "content": "x"}) == "`x`"
    assert _format_block({"tag": "p", "content": "Plain text."}) == "Plain text."


def test_creates_origin_dir_and_returns_its_path(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="Untitled",
        author="",
        publish_date="",
        blocks=[],
        image_blocks=[],
    )
    assert origin_path.parent == tmp_path / "Origin"
    assert origin_path.parent.is_dir()
