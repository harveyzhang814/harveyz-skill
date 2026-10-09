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
iframe.diagram{width:100%;border:1px solid var(--line);border-radius:10px;margin:12px 0;display:block}
code{background:var(--soft);padding:1px 5px;border-radius:4px;font-size:.9em}
@media (max-width:900px){.wrap{grid-template-columns:1fr}nav{display:none}}
"""

RESIZE = """
for (const f of document.querySelectorAll('iframe.diagram')) {
  const box = () => { const d = f.contentDocument; return d.querySelector('.container') || d.body; };
  const fit = () => { try { f.style.height = Math.ceil(box().getBoundingClientRect().height) + 'px'; } catch (_) {} };
  const setup = () => { fit(); try { new f.contentWindow.ResizeObserver(fit).observe(box()); } catch (_) {} };
  // 早于本脚本加载完的 iframe 不会再触发 load
  if (f.contentDocument && f.contentDocument.readyState === 'complete' && f.contentDocument.body) setup();
  else f.addEventListener('load', setup);
}
"""


def embed(diagram_html: str) -> str:
    tagged = re.sub(r"<html\b", '<html data-embed="true"', diagram_html, count=1)
    return f'<iframe class="diagram" height="600" srcdoc="{html.escape(tagged, quote=True)}"></iframe>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("out")
    ap.add_argument("--title", required=True)
    a = ap.parse_args()

    content_path = Path(a.content)
    body = content_path.read_text(encoding="utf-8")
    ddir = content_path.parent / "diagrams"

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
    print(f"ok: {a.out} ({len(page) // 1024} KB, {n} sections)")


if __name__ == "__main__":
    main()
