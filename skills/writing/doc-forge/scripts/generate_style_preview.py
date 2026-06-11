#!/usr/bin/env python3
"""
Generate a single HTML file previewing all available doc-forge styles.

Usage:
    python3 generate_style_preview.py [output.html]
    # defaults to /tmp/doc-forge-style-preview.html
"""

import sys
from pathlib import Path

import markdown as md_lib

ASSETS_DIR = Path(__file__).parent.parent / "assets"
DEFAULT_OUTPUT = Path("/tmp/doc-forge-style-preview.html")

DISPLAY_NAMES: dict[str, str] = {
    "bain": "Bain & Company",
    "bcg": "Boston Consulting Group (BCG)",
    "thesis": "中文学术论文",
    "default": "Default（Harvey 自定义）",
    "rb": "Roland Berger",
}

SAMPLE_MD = """\
# 战略报告标题

## 一、执行摘要

### 1.1 背景与目标

#### 战略优先级

这是正文段落。报告分析了当前市场环境下的核心战略选项，结合数据驱动的洞察提出行动建议，助力企业在竞争加剧的格局中保持领先。

> 关键发现：在竞争加剧的背景下，企业需要在18个月内完成数字化转型，才能保持市场领先地位。

| 指标 | 当前值 | 目标值 | 差距 |
|------|--------|--------|------|
| 市场份额 | 23% | 30% | 7pp |
| 净推荐值 | 42 | 60 | +18 |
| 运营效率 | 68% | 85% | 17pp |

```python
def calculate_gap(current, target):
    return target - current
```

---

## 二、战略选项
"""


WRAPPER_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  background: #EBEBEB;
  color: #1A1A1A;
  padding: 32px 24px;
}
h1.page-title {
  font-size: 22px;
  font-weight: 600;
  color: #111;
  margin-bottom: 8px;
}
p.page-sub {
  font-size: 13px;
  color: #555;
  margin-bottom: 32px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(520px, 1fr));
  gap: 28px;
}
.card {
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,.10);
}
.card-label {
  padding: 10px 18px;
  background: #1A1A1A;
  color: #fff;
  font-family: monospace;
  font-size: 13px;
  letter-spacing: .02em;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-label .slug {
  color: #aaa;
  font-size: 11px;
}
iframe {
  width: 100%;
  height: 580px;
  border: none;
  display: block;
}
"""


def discover_styles() -> list[tuple[str, Path]]:
    """Return (slug, css_path) pairs sorted by slug, skipping unknown stems."""
    found = []
    for css_file in sorted(ASSETS_DIR.glob("*.css")):
        stem = css_file.stem
        found.append((stem, css_file))
    return found


def build_iframe_doc(css: str, body_html: str) -> str:
    mermaid_src = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"
    local_js = Path(__file__).parent.parent / "node_modules" / "mermaid" / "dist" / "mermaid.min.js"
    if local_js.exists():
        mermaid_src = local_js.as_uri()
    return (
        "<!DOCTYPE html><html lang='zh-CN'><head>"
        "<meta charset='UTF-8'>"
        f"<style>{css}</style>"
        "</head><body>"
        f"{body_html}"
        f'<script src="{mermaid_src}"></script>'
        "<script>if(typeof mermaid!=='undefined'){"
        "mermaid.initialize({startOnLoad:true,theme:'neutral'});}</script>"
        "</body></html>"
    )


def render_body(md_text: str) -> str:
    return md_lib.markdown(md_text, extensions=["tables", "fenced_code", "attr_list"])


def build_preview(output_path: Path) -> None:
    styles = discover_styles()
    if not styles:
        print("No CSS files found in assets directory.", file=sys.stderr)
        sys.exit(1)

    body_html = render_body(SAMPLE_MD)
    cards_html = []
    for slug, css_path in styles:
        display = DISPLAY_NAMES.get(slug, slug)
        css = css_path.read_text(encoding="utf-8")
        iframe_doc = build_iframe_doc(css, body_html)
        # escape for srcdoc attribute (only & and " need escaping in attr values)
        srcdoc = iframe_doc.replace("&", "&amp;").replace('"', "&quot;")
        card = (
            f'<div class="card">'
            f'<div class="card-label">'
            f'<span>{display}</span>'
            f'<span class="slug">{slug}.css</span>'
            f'</div>'
            f'<iframe srcdoc="{srcdoc}" loading="lazy"></iframe>'
            f'</div>'
        )
        cards_html.append(card)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Doc Forge — Style Preview</title>
<style>{WRAPPER_CSS}</style>
</head>
<body>
<h1 class="page-title">Doc Forge — Style Preview</h1>
<p class="page-sub">共 {len(styles)} 种内置样式 · 每个预览框使用相同示例内容渲染</p>
<div class="grid">
{"".join(cards_html)}
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
