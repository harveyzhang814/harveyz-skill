#!/usr/bin/env python3
"""
Generate a comparison grid HTML: columns = styles, rows = element types.

Usage:
    python3 generate_style_preview.py [output.html]
    # defaults to skills/writing/doc-forge/preview/style-preview.html
"""

import re
import sys
from pathlib import Path
from typing import Callable, Union

ASSETS_DIR = Path(__file__).parent.parent / "assets"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "preview" / "style-preview.html"

DISPLAY_NAMES: dict[str, str] = {
    "bain":    "Bain & Company",
    "bcg":     "BCG",
    "thesis":  "中文学术论文",
    "default": "Default",
    "rb":      "Roland Berger",
}

RowContent = Union[str, Callable[[str, str], str]]  # (slug, css) -> html

ROWS: list[tuple[str, RowContent]] = [
    ("配色",  lambda slug, css: _palette_html(css)),
    ("H1",   "<h1>战略报告标题</h1>"),
    ("H2",   "<h2>一、执行摘要</h2>"),
    ("H3",   "<h3>1.1 背景与目标</h3>"),
    ("H4",   "<h4>战略优先级</h4>"),
    ("正文",  "<p>这是正文段落。报告分析了当前市场环境下的核心战略选项，结合数据驱动的洞察提出行动建议，助力企业保持领先地位。</p>"),
    ("引用块", "<blockquote><p>关键发现：在竞争加剧的背景下，企业需要在18个月内完成数字化转型。</p></blockquote>"),
    ("表格",  (
        "<table><thead><tr><th>指标</th><th>当前值</th><th>目标值</th><th>差距</th></tr></thead>"
        "<tbody>"
        "<tr><td>市场份额</td><td>23%</td><td>30%</td><td>7pp</td></tr>"
        "<tr><td>净推荐值</td><td>42</td><td>60</td><td>+18</td></tr>"
        "</tbody></table>"
    )),
    ("代码块", "<pre><code>def calculate_gap(current, target):\n    return target - current</code></pre>"),
    ("分隔线", "<hr>"),
]


def _palette_html(css: str) -> str:
    """Extract unique brand colors from CSS and render as labeled swatches."""
    raw = re.findall(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', css)
    seen: dict[str, int] = {}
    for h in raw:
        if len(h) == 3:
            h = h[0] * 2 + h[1] * 2 + h[2] * 2
        h = h.upper()
        seen[h] = seen.get(h, 0) + 1

    entries: list[tuple[float, int, str]] = []
    for h, count in seen.items():
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        if lum > 0.96:  # skip near-whites
            continue
        entries.append((lum, count, h))

    # sort dark → light, break ties by frequency
    entries.sort(key=lambda x: (x[0], -x[1]))

    swatches = []
    for lum, _, h in entries:
        text_color = "#fff" if lum < 0.45 else "#333"
        swatches.append(
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px">'
            f'<div title="#{h}" style="width:32px;height:32px;border-radius:7px;'
            f'background:#{h};box-shadow:0 1px 4px rgba(0,0,0,.18);'
            f'border:1px solid rgba(0,0,0,.08)"></div>'
            f'<span style="font-family:monospace;font-size:7.5px;color:#555;letter-spacing:-.01em">#{h}</span>'
            f'</div>'
        )

    return (
        '<div style="display:flex;flex-wrap:wrap;gap:8px;padding:2px 0">'
        + "".join(swatches)
        + "</div>"
    )

GRID_CSS = """
*, *::before, *::after { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  background: #CACACA;
  color: #111;
}

/* ── Page chrome ── */
.page-header {
  padding: 20px 24px 14px;
  background: rgba(20, 20, 20, 0.88);
  backdrop-filter: blur(8px);
  color: #fff;
  position: sticky;
  top: 0;
  z-index: 10;
}
.page-header h1 { font-size: 15px; font-weight: 600; margin: 0 0 3px; }
.page-header p  { font-size: 11px; color: #999; margin: 0; }

/* ── Grid shell ── */
.grid-wrap { overflow-x: auto; padding: 20px; }

.grid {
  display: grid;
  grid-template-columns: 64px repeat(var(--n-styles), minmax(280px, 1fr));
  gap: 10px;
  width: max-content;
  min-width: 100%;
}

/* ── Base card ── */
.cell {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 16px 18px;
  min-height: 52px;
  overflow: hidden;
}

/* ── Row label card ── */
.cell-label {
  background: rgba(0, 0, 0, 0.12);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.20);
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-family: monospace;
  color: rgba(255, 255, 255, 0.75);
  font-weight: 600;
  letter-spacing: .05em;
  text-transform: uppercase;
  padding: 8px 4px;
}

/* ── Column header card ── */
.cell-header {
  background: rgba(20, 20, 20, 0.80);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
  color: #fff;
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  padding: 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.cell-header .slug { color: #888; font-size: 10px; font-weight: 400; }

/* corner — invisible spacer */
.cell-corner {
  background: transparent;
  border: none;
  box-shadow: none;
  backdrop-filter: none;
}
"""


def discover_styles() -> list[tuple[str, Path]]:
    return [(p.stem, p) for p in sorted(ASSETS_DIR.glob("*.css"))]


def scope_css(css: str, prefix: str) -> str:
    """Prefix all CSS selectors with .{prefix} for in-page isolation."""
    out: list[str] = []
    i = 0
    n = len(css)

    def find_block_end(start: int) -> int:
        depth = 0
        j = start
        while j < n:
            if css[j] == '{':
                depth += 1
            elif css[j] == '}':
                depth -= 1
                if depth == 0:
                    return j
            j += 1
        return n - 1

    while i < n:
        # skip whitespace
        while i < n and css[i] in ' \t\n\r':
            i += 1
        if i >= n:
            break

        # @page — drop entirely (controls print margins, irrelevant for preview)
        if css[i:i+5] == '@page':
            end = find_block_end(i)
            i = end + 1
            continue

        # @media — keep wrapper, recurse into body
        if css[i:i+6] == '@media':
            brace = css.find('{', i)
            rule_head = css[i:brace].strip()
            end = find_block_end(brace)
            inner = css[brace + 1:end]
            out.append(f"{rule_head} {{\n{scope_css(inner, prefix)}\n}}")
            i = end + 1
            continue

        # other @rules without block (e.g. @import, @charset)
        if css[i] == '@':
            semi = css.find(';', i)
            brace = css.find('{', i)
            if semi != -1 and (brace == -1 or semi < brace):
                out.append(css[i:semi + 1])
                i = semi + 1
                continue

        # regular rule: selector { ... }
        brace = css.find('{', i)
        if brace == -1:
            break
        selector_raw = css[i:brace]
        end = find_block_end(brace)
        body = css[brace:end + 1]  # includes { }

        selectors = [s.strip() for s in selector_raw.split(',') if s.strip()]
        scoped: list[str] = []
        for sel in selectors:
            if sel in ('body', ':root'):
                scoped.append(f'.{prefix}')
            elif re.match(r'^body[\s>+~[]', sel):
                scoped.append(f'.{prefix} {sel[4:].lstrip()}')
            else:
                scoped.append(f'.{prefix} {sel}')
        out.append(f"{', '.join(scoped)} {body}")
        i = end + 1

    return '\n'.join(out)


def is_up_to_date(output_path: Path, css_paths: list[Path]) -> bool:
    if not output_path.exists():
        return False
    out_mtime = output_path.stat().st_mtime
    sources = css_paths + [Path(__file__)]
    return all(src.stat().st_mtime <= out_mtime for src in sources)


def build_preview(output_path: Path) -> None:
    styles = discover_styles()
    if not styles:
        print("No CSS files found in assets directory.", file=sys.stderr)
        sys.exit(1)

    css_paths = [p for _, p in styles]
    if is_up_to_date(output_path, css_paths):
        print(f"Up to date: {output_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    n = len(styles)

    # Read CSS content (needed for both scoping and palette extraction)
    css_contents: dict[str, str] = {
        slug: css_path.read_text(encoding="utf-8") for slug, css_path in styles
    }

    # Build scoped CSS for each brand
    all_brand_css = "\n\n".join(
        f"/* ── {slug} ── */\n{scope_css(raw, slug)}"
        for slug, raw in css_contents.items()
    )

    # Build grid rows
    cells: list[str] = []

    # Header row
    cells.append('<div class="cell cell-corner"></div>')
    for slug, _ in styles:
        display = DISPLAY_NAMES.get(slug, slug)
        cells.append(
            f'<div class="cell cell-header">'
            f'<span>{display}</span>'
            f'<span class="slug">{slug}.css</span>'
            f'</div>'
        )

    # Content rows
    for row_label, row_content in ROWS:
        cells.append(f'<div class="cell cell-label">{row_label}</div>')
        for slug, _ in styles:
            html = row_content(slug, css_contents[slug]) if callable(row_content) else row_content
            cells.append(f'<div class="cell {slug}">{html}</div>')

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Doc Forge — Style Preview</title>
<style>
{GRID_CSS}
{all_brand_css}
</style>
</head>
<body>
<div class="page-header">
  <h1>Doc Forge — Style Preview</h1>
  <p>列 = 样式风格　行 = 元素类型　共 {n} 种样式</p>
</div>
<div class="grid-wrap">
  <div class="grid" style="--n-styles: {n}">
{"".join(f'    {c}' for c in cells)}
  </div>
</div>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"Preview written to: {output_path}")


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    build_preview(output)


if __name__ == "__main__":
    main()
