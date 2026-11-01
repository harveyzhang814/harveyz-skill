#!/usr/bin/env python3
"""把 content.html 片段与 archify 图组装成单个离线 HTML。

用法: assemble.py <content.html> <out.html> --title <标题>
占位 <!--diagram:ID--> 替换为 diagrams/ID.html 的内联 iframe（嵌入模式）。
"""
import argparse, html, re, sys
from pathlib import Path

CSS = """
:root{--fg:#0f172a;--muted:#64748b;--bg:#fff;--line:#e2e8f0;--soft:#f8fafc;--accent:#0891b2}
@media (prefers-color-scheme:dark){:root{--fg:#e2e8f0;--muted:#94a3b8;--bg:#0b1120;--line:#1e293b;--soft:#111827}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{display:grid;grid-template-columns:220px minmax(0,1fr);gap:40px;max-width:1280px;margin:0 auto;padding:32px}
nav{position:sticky;top:24px;align-self:start;font-size:14px}
nav a{display:block;color:var(--muted);text-decoration:none;padding:3px 0}nav a:hover{color:var(--accent)}
h1{font-size:30px;margin:0 0 8px}h2{font-size:22px;margin:48px 0 12px;padding-top:8px;border-top:1px solid var(--line)}
h3{font-size:17px;margin:28px 0 8px}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}th{background:var(--soft)}
.thesis{border-left:4px solid var(--accent);background:var(--soft);padding:12px 16px;margin:16px 0}
.c-read,.c-infer,.c-unknown{font-size:12px;padding:0 6px;border-radius:4px;margin-left:4px;white-space:nowrap}
.c-read{background:#dcfce7;color:#166534}.c-infer{background:#fef9c3;color:#854d0e}.c-unknown{background:#fee2e2;color:#991b1b}
.diagram-scroll{overflow-x:auto;margin:12px 0}
iframe.diagram{box-sizing:border-box;width:100%;border:1px solid var(--line);border-radius:10px;margin:0 auto;display:block}
code{background:var(--soft);padding:1px 5px;border-radius:4px;font-size:.9em}
.anchors{font-size:13px;color:var(--muted);overflow-wrap:anywhere}
@media (max-width:900px){.wrap{grid-template-columns:minmax(0,1fr)}nav{display:none}}
"""

RESIZE = """
// 宽度默认占满正文栏；图高超过视口 MAX_VH 时收窄居中；但缩放不低于 MIN_SCALE，
// 栏宽不够时外层横向滚动——字小到读不清比滚动更糟。高度始终跟随图的实际高度。
const MIN_SCALE = 0.75, MAX_VH = 0.85;
const frames = [...document.querySelectorAll('iframe.diagram')];
for (const f of frames) {
  const box = () => { const d = f.contentDocument; return d.querySelector('.container') || d.body; };
  const fit = () => { try {
    f.style.height = Math.ceil(box().getBoundingClientRect().height) + f.offsetHeight - f.clientHeight + 'px';
  } catch (_) {} };
  f.size = () => { try {
    const svg = f.contentDocument.querySelector('.diagram-container svg'), { width: vw, height: vh } = svg.viewBox.baseVal;
    const b = box().getBoundingClientRect(), s = svg.getBoundingClientRect();
    const px = f.offsetWidth - s.width, py = b.height - s.height;
    const cap = (innerHeight * MAX_VH - py) * vw / vh + px;
    f.style.width = Math.round(Math.max(vw * MIN_SCALE + px, Math.min(f.parentElement.clientWidth, cap))) + 'px';
  } catch (_) {} };
  const setup = () => {
    if (f.dataset.fitted) return;
    f.dataset.fitted = '1';
    f.size(); fit(); try { new f.contentWindow.ResizeObserver(fit).observe(box()); } catch (_) {}
  };
  f.addEventListener('load', setup);
  // 早于本脚本加载完的 iframe 不会再触发 load。srcdoc 载入前的占位文档是
  // about:blank，它的 readyState 也是 complete，只认 about:srcdoc
  const d = f.contentDocument;
  if (d && d.URL === 'about:srcdoc' && d.readyState === 'complete') setup();
}
addEventListener('resize', () => frames.forEach(f => f.dataset.fitted && f.size()));
"""


def embed(diagram_html: str) -> str:
    tagged = re.sub(r"<html\b", '<html data-embed="true"', diagram_html, count=1)
    return (f'<div class="diagram-scroll"><iframe class="diagram" height="600" '
            f'srcdoc="{html.escape(tagged, quote=True)}"></iframe></div>')


NOISE = [
    ("路径:行号", r"[\w./-]+\.\w{1,5}:\d+"),
    ("文件名", r"\b[\w./-]+\.(?:tsx?|jsx?|mjs|py|go|rs|java|kt|rb|sh|json|ya?ml|toml|md|css|html)\b"),
    ("条款编号", r"§\s*\d+(?:\.\d+)*|裁决\s*R\d+|\bR\d{1,3}\b"),
    ("代码片段", r"<code>.*?</code>"),
    ("读到标签", r'class="c-read"'),
]


def lint(body: str):
    """锚点区之外的噪音：返回 (正文字数, [(类型, 上下文)])。"""
    text = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    text = re.sub(r'<section class="anchors">.*?</section>', "", text, flags=re.S)
    chars = len(re.findall(r"[一-鿿]", re.sub(r"<[^>]+>", "", text)))
    hits, seen = [], set()
    for kind, pat in NOISE:
        for m in re.finditer(pat, text):
            if m.start() in seen:
                continue
            seen.add(m.start())
            ctx = re.sub(r"<[^>]+>|\s+", " ", text[max(0, m.start() - 30):m.end() + 30]).strip()
            hits.append((kind, ctx))
    return chars, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("out")
    ap.add_argument("--title", required=True)
    a = ap.parse_args()

    content_path = Path(a.content)
    body = content_path.read_text(encoding="utf-8")
    ddir = content_path.parent / "diagrams"
    chars, hits = lint(body)

    missing = []

    def sub(m):
        p = ddir / f"{m.group(1)}.html"
        if not p.is_file():
            missing.append(m.group(1))
            return ""
        return embed(p.read_text(encoding="utf-8"))

    body = re.sub(r"<!--\s*diagram:([A-Za-z0-9_-]+)\s*-->", sub, body)
    if missing:
        sys.exit(f"missing diagrams: {', '.join(missing)}")

    toc, n = [], 0

    def anchor(m):
        nonlocal n
        n += 1
        text = re.sub(r"<[^>]+>", "", m.group(2))
        toc.append(f'<a href="#s{n}">{text}</a>')
        return f'<h2{m.group(1)} id="s{n}">{m.group(2)}</h2>'

    body = re.sub(r"<h2([^>]*)>(.*?)</h2>", anchor, body, flags=re.S)

    t = html.escape(a.title)
    page = (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{t}</title>'
            f'<style>{CSS}</style></head><body><div class="wrap"><nav>{"".join(toc)}</nav>'
            f'<main><h1>{t}</h1>{body}</main></div><script>{RESIZE}</script></body></html>')
    Path(a.out).write_text(page, encoding="utf-8")
    print(f"ok: {a.out} ({len(page) // 1024} KB, {n} sections, 正文 {chars} 字)")
    if not hits:
        print("噪音检查：✓ 无")
    for kind, ctx in hits:
        print(f"⚠️ {kind}: …{ctx}…")
    if hits:
        print(f"噪音检查：⚠️ {len(hits)} 处")


if __name__ == "__main__":
    main()
