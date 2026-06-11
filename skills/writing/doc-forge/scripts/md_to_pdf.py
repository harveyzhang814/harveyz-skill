#!/usr/bin/env python3
"""
Convert Markdown to PDF via Playwright Chromium.

Usage:
    python3 md_to_pdf.py input.md [output.pdf] [--style style.css]
    python3 md_to_pdf.py --dump-style
"""

import argparse
import re
import sys
from pathlib import Path

import markdown as md_lib

ASSETS_DIR = Path(__file__).parent.parent / "assets"
MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def _mermaid_js_src() -> str:
    local = Path(__file__).parent.parent / "node_modules" / "mermaid" / "dist" / "mermaid.min.js"
    if local.exists():
        return local.as_uri()
    return "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"


def _extract_mermaid(md_text: str) -> tuple[str, dict[str, str]]:
    """Replace ```mermaid blocks with unique placeholders. Returns modified text and mapping."""
    blocks: dict[str, str] = {}

    def replacer(m: re.Match) -> str:
        key = f"XMERMAIDX{len(blocks)}X"
        blocks[key] = f'<pre class="mermaid">{m.group(1).strip()}</pre>'
        return key

    return MERMAID_RE.sub(replacer, md_text), blocks


def build_html(md_text: str, css_path: Path) -> tuple[str, int]:
    """Return complete HTML string and count of Mermaid blocks."""
    _css_file = css_path
    if not _css_file.exists():
        print(f"Error: {_css_file} not found", file=sys.stderr)
        sys.exit(1)

    processed, mermaid_blocks = _extract_mermaid(md_text)

    body = md_lib.markdown(
        processed,
        extensions=["tables", "fenced_code", "attr_list"],
    )

    for key, block in mermaid_blocks.items():
        body = body.replace(f"<p>{key}</p>", block)
        body = body.replace(key, block)

    _template_file = ASSETS_DIR / "template.html"
    if not _template_file.exists():
        print(f"Error: {_template_file} not found — reinstall the skill", file=sys.stderr)
        sys.exit(1)

    template = _template_file.read_text(encoding="utf-8")
    css = _css_file.read_text(encoding="utf-8")

    html = (
        template
        .replace("{{CSS_CONTENT}}", css)
        .replace("{{BODY_CONTENT}}", body)
        .replace("{{MERMAID_JS_PATH}}", _mermaid_js_src())
    )
    return html, len(mermaid_blocks)


def render_pdf(html: str, output_path: Path, base_url: str, mermaid_count: int) -> None:
    from playwright.sync_api import sync_playwright

    # Write temp HTML into the same directory as the source MD so that
    # relative image paths (e.g. ./diagram.png) resolve correctly.
    base_dir = Path(base_url.removeprefix("file://").rstrip("/"))
    tmp_html = base_dir / f"_md_to_pdf_tmp_{output_path.stem}.html"
    try:
        tmp_html.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(tmp_html.as_uri())
            if mermaid_count > 0:
                page.wait_for_function(
                    f"document.querySelectorAll('pre.mermaid svg').length >= {mermaid_count}",
                    timeout=10000,
                )
            page.pdf(path=str(output_path), format="A4", print_background=True)
            browser.close()
    finally:
        if tmp_html.exists():
            tmp_html.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Markdown to PDF.")
    parser.add_argument("input", nargs="?", help="Input .md file")
    parser.add_argument("output", nargs="?", help="Output .pdf file (default: same name)")
    parser.add_argument("--style", help="CSS style file")
    parser.add_argument("--dump-style", action="store_true",
                        help="Print default CSS and exit")
    args = parser.parse_args()

    if args.dump_style:
        _css_file = ASSETS_DIR / "default.css"
        if not _css_file.exists():
            print(f"Error: {_css_file} not found — reinstall the skill", file=sys.stderr)
            sys.exit(1)
        print(_css_file.read_text(encoding="utf-8"))
        return

    if not args.input:
        parser.error("input is required unless --dump-style is used")

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".pdf")
    css_path = Path(args.style) if args.style else ASSETS_DIR / "default.css"
    base_url = input_path.resolve().parent.as_uri() + "/"

    md_text = input_path.read_text(encoding="utf-8")
    html, mermaid_count = build_html(md_text, css_path)
    render_pdf(html, output_path, base_url, mermaid_count)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
