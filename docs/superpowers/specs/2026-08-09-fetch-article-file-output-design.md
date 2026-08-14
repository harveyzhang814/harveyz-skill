---
title: fetch_article server-side markdown assembly + file output
migrated: false
---

# fetch_article Server-Side Markdown Assembly + File Output — Design

## Problem

`fetch_article` (browser-fetch-mcp) returns structured JSON (`title`,
`author`, `publish_date`, `blocks`, `image_blocks`, `site`,
`cookies_injected`, `thin_retry_used`). The only real caller,
`extract-url-mcp/scripts/mcp_fetch_client.py`, takes that JSON, assembles
it into a Markdown file (`Origin/article.md`) with YAML frontmatter, and
returns only the file path to its own caller — so the extract-url-mcp
pipeline never puts article content into an agent's context.

That "assemble + write + return path" logic lives entirely in
`mcp_fetch_client.py`. Any other MCP client that calls `fetch_article`
directly gets the raw `blocks` JSON back in its own context, with no way
to opt into the cheaper file-based contract. The goal is to move that
capability into `fetch_article` itself, as the default, while still
supporting the raw-JSON contract for callers that explicitly want it.

## Architecture

`fetch_article` gains one new parameter: `output_format: str = "path"`,
with two allowed values:

- **`"path"` (default)** — `fetch_article` assembles the Markdown body
  itself (title/author/publish_date frontmatter, heading/list/table/code
  block formatting, image placement by `after_block` index, leading-h1
  dedup against the title), writes it to
  `<output_dir>/Origin/article.md`, and returns
  `{"origin_path", "title", "author", "publish_date", "site",
  "cookies_injected", "thin_retry_used"}` — no `blocks`/`image_blocks`.
- **`"json"`** — behavior and return shape are unchanged from today:
  `{"title", "author", "publish_date", "blocks", "image_blocks", "site",
  "cookies_injected", "thin_retry_used"}`, no `article.md` written.

Image downloading (`<output_dir>/Image/img_N.ext`) is unaffected by
`output_format` — it already happens unconditionally today and continues
to.

An invalid `output_format` value raises `ValueError`.

`fetch_page` is out of scope — it isn't mentioned in this request and
already has exactly one behavior (return raw HTML); there's no existing
"other format" for it to default away from.

## Components

**`tools/browser-fetch-mcp/browser_fetch_mcp/server.py`**
- `fetch_article` signature: add `output_format: str = "path"`.
- After the existing `image_blocks = await asyncio.to_thread(download_images, ...)` line, branch on
  `output_format`:
  - `"json"`: return the dict exactly as built today.
  - `"path"`: call a new markdown-assembly helper (new module, see
    below), write `Origin/article.md` under `output_dir`, and return the
    slimmed dict with `origin_path`.
  - anything else: `raise ValueError(f"Invalid output_format: {output_format!r} (expected 'path' or 'json')")`.

**`tools/browser-fetch-mcp/browser_fetch_mcp/markdown.py`** (new)
- Port `_format_block`, the leading-h1 dedup, the image-placement loop,
  and the YAML-frontmatter template verbatim from
  `mcp_fetch_client.py:_format_block`/`fetch_and_save` (lines 39-54,
  87-136 of the current file). Same UTC+8 (`timezone(timedelta(hours=8))`)
  hardcoded fetch-date — no new config, matches existing behavior exactly.
- Public function: `assemble_and_write(output_dir: Path, url: str, title: str, author: str, publish_date: str, blocks: list[dict], image_blocks: list[dict]) -> Path` — creates `output_dir/Origin/`, writes `article.md`, returns its path.

**`skills/research/extract-url-mcp/scripts/mcp_fetch_client.py`**
- `fetch_and_save()` no longer sets `tool_args["output_format"]` (relies
  on the server default `"path"`), and no longer formats anything itself
  — it takes `payload["origin_path"]` from the MCP result and returns
  `Path(payload["origin_path"])`.
- Delete `_format_block` and all Markdown-assembly code from this file —
  it now moves entirely into `browser_fetch_mcp/markdown.py`.
- `_hash8(url)` and the per-URL `article_dir = output_dir / _hash8(url)`
  computation stay in this file unchanged — that's extract-url-mcp's own
  multi-article workspace convention, not something `fetch_article`
  should own.
- `main()` is unchanged (`print(f"ORIGIN_PATH: {origin_path}")`).

## Data Flow

```
extract-url-mcp SKILL.md (subagent1-fetch-prompt.md)
  → subprocess.run(mcp_fetch_client.py, timeout=120)
    → fetch_and_save(url, output_dir, chrome_profile)
      → stdio_client → fetch_article(url, article_dir, chrome_profile)
                        [output_format defaults to "path"]
        → browser_fetch_mcp.markdown.assemble_and_write(...)
          writes article_dir/Origin/article.md
          writes article_dir/Image/img_N.ext (unchanged, via images.py)
        ← {"origin_path": "<article_dir>/Origin/article.md", ...}
      ← Path(payload["origin_path"])
    prints "ORIGIN_PATH: <path>"
```

A hypothetical direct MCP caller wanting raw blocks passes
`output_format="json"` and gets today's exact JSON shape back, with no
file written.

## Error Handling

No new error paths beyond the existing ones (`ValueError` for x.com
without a Chrome profile, `RuntimeError` for scrape failures) plus the
one new `ValueError` for an invalid `output_format`. Markdown assembly
and file writing are the same operations `mcp_fetch_client.py` already
performs today (`Path.mkdir(parents=True, exist_ok=True)`,
`Path.write_text`) — no new failure modes are introduced by moving them
server-side.

## Testing

- `tools/browser-fetch-mcp/tests/test_fetch_article.py`: add coverage for
  `output_format="path"` (default) — asserts `Origin/article.md` is
  written with correct frontmatter, heading/list/table/code formatting,
  leading-h1 dedup, and image placement (porting the equivalent
  assertions currently in extract-url-mcp's tests). Add one
  `output_format="json"` regression test asserting the return shape and
  absence of `Origin/article.md` are identical to pre-change behavior.
  Add one test for the invalid-`output_format` `ValueError`.
- `tools/browser-fetch-mcp/tests/` gains `test_markdown.py` for the new
  `markdown.assemble_and_write` module in isolation (no MCP protocol, no
  browser).
- `skills/research/extract-url-mcp/tests/test_mcp_fetch_client.py`:
  remove assertions that duplicate the assembly logic now covered in
  browser-fetch-mcp's own tests; keep the tests that cover
  `_hash8`/`article_dir` computation and the `ORIGIN_PATH:` stdout
  contract, updated to mock the new (path-shaped) `fetch_article`
  response instead of the old blocks-shaped one.

## Global Constraints

- `output_format` default is `"path"`; `"json"` must remain byte-for-byte
  compatible with today's `fetch_article` return shape.
- Frontmatter fields and format (`source_url`, `fetch_date` in UTC+8,
  `origin_title`, `author`, `publish_date`) stay exactly as today —
  no new configuration.
- `fetch_page` is unchanged; out of scope for this work.
- Image download behavior (`<output_dir>/Image/img_N.ext`, filename-only
  metadata) is unchanged and unaffected by `output_format`.
