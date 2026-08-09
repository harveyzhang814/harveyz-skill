"""Article Markdown assembly for fetch_article's output_format="path"
mode: block formatting, leading-h1 dedup against the title, image
placement by after_block index, and YAML frontmatter — ported verbatim
from extract-url-mcp/scripts/mcp_fetch_client.py's original
_format_block/fetch_and_save assembly logic.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _format_block(block: dict) -> str:
    tag = block["tag"]
    content = block["content"]
    if tag in ("h1", "h2", "h3"):
        return f"{'#' * int(tag[1])} {content}"
    if tag == "li":
        return f"- {content}"
    if tag == "blockquote":
        return f"> {content}"
    if tag == "table":
        return content
    if tag == "pre":
        return f"```\n{content}\n```"
    if tag == "code":
        return f"`{content}`"
    return content


def assemble_and_write(
    output_dir: Path,
    url: str,
    title: str,
    author: str,
    publish_date: str,
    blocks: list[dict],
    image_blocks: list[dict],
) -> Path:
    """Assemble blocks/image_blocks into Markdown with YAML frontmatter
    and write it to <output_dir>/Origin/article.md. Returns that path."""
    dedup_offset = 0
    if blocks and blocks[0]["tag"] == "h1" and blocks[0]["content"] == title:
        blocks = blocks[1:]
        dedup_offset = 1

    pre_imgs = [f'![](../Image/{img["filename"]})' for img in image_blocks if img["after_block"] == -1]
    if dedup_offset:
        # after_block == 0 meant "right after the h1" — that h1 is gone
        # now, so those images belong at the very start of the body instead.
        pre_imgs += [f'![](../Image/{img["filename"]})' for img in image_blocks if img["after_block"] == 0]

    body_units = []
    if pre_imgs:
        body_units.append("\n".join(pre_imgs))

    for i, block in enumerate(blocks):
        parts = [_format_block(block)]
        for img in image_blocks:
            if img["after_block"] == i + dedup_offset:
                parts.append(f'![](../Image/{img["filename"]})')
        body_units.append("\n".join(parts))

    body = "\n\n".join(body_units)

    origin_dir = Path(output_dir) / "Origin"
    origin_dir.mkdir(parents=True, exist_ok=True)
    origin_path = origin_dir / "article.md"

    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    content = f"""---
source_url: {url}
fetch_date: {fetch_date}
origin_title: "{title}"
author: "{author}"
publish_date: "{publish_date}"
---

# {title}

{body}
"""
    origin_path.write_text(content, encoding="utf-8")
    return origin_path
