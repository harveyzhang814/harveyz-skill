#!/usr/bin/env python3
"""
Render question-me internal tree text to a visual HTML card tree.
Usage: echo "<tree text>" | python3 render_tree.py OUTPUT_PATH [--open]
"""

import sys
import re
import argparse
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List

LINE_RE = re.compile(
    r'\[(?P<label>\w+):(?P<status>done|open|infer|skip)\]\s+'
    r'id=(?P<node_id>\w+)'
    r'(?:\s+dep=(?P<dep_id>\w+))?'
    r'\s+(?P<text>.+)'
)

@dataclass
class Node:
    label: str
    status: str
    node_id: str
    dep_id: Optional[str]
    text: str
    children: List['Node'] = field(default_factory=list)


def parse_nodes(tree_text: str) -> List[Node]:
    nodes = []
    for line in tree_text.splitlines():
        m = LINE_RE.match(line.strip())
        if m:
            d = m.groupdict()
            nodes.append(Node(
                label=d['label'], status=d['status'],
                node_id=d['node_id'], dep_id=d['dep_id'],
                text=d['text'].strip()
            ))
    return nodes


def build_tree(nodes: List[Node]):
    id_map = {n.node_id: n for n in nodes}
    roots = []
    for node in nodes:
        if node.dep_id and node.dep_id in id_map and node.dep_id != node.node_id:
            id_map[node.dep_id].children.append(node)
        else:
            roots.append(node)
    # Collect any nodes unreachable from roots (mutual cycles) and surface them
    reachable = set()
    stack = list(roots)
    while stack:
        n = stack.pop()
        reachable.add(n.node_id)
        stack.extend(n.children)
    for node in nodes:
        if node.node_id not in reachable:
            roots.append(node)
    return roots, id_map


def find_current(nodes: List[Node], id_map: dict) -> Optional[str]:
    """Return node_id of the highest-impact open node with satisfied dep."""
    candidates = []
    for node in nodes:
        if node.status != 'open':
            continue
        dep_ok = node.dep_id is None or (
            node.dep_id in id_map and id_map[node.dep_id].status == 'done'
        )
        if dep_ok:
            impact = sum(1 for n in nodes if n.dep_id == node.node_id)
            candidates.append((-impact, node.node_id))
    candidates.sort()
    return candidates[0][1] if candidates else None


STATUS_CFG = {
    'done':  {'border': '#22c55e', 'bg': '#f0fdf4', 'icon': '✓'},
    'open':  {'border': '#eab308', 'bg': '#fffbeb', 'icon': '?'},
    'infer': {'border': '#94a3b8', 'bg': '#f8fafc', 'icon': '~'},
    'skip':  {'border': '#e2e8f0', 'bg': '#f8fafc', 'icon': '-'},
}


def _esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _render_card(node: Node, current_id: Optional[str], id_map: dict) -> str:
    cfg = STATUS_CFG.get(node.status, STATUS_CFG['open'])
    is_current = node.node_id == current_id
    is_locked = (
        node.status == 'open' and node.dep_id and
        id_map.get(node.dep_id) is not None and
        id_map[node.dep_id].status != 'done'
    )

    opacity = '0.45' if is_locked else '1'
    highlight = 'box-shadow:0 0 0 2px #3b82f6;border-color:#3b82f6;' if is_current else ''

    if node.status == 'done':
        q_html = _esc(node.label)
        a_html = f'<span class="a done">{_esc(node.text)}</span>'
    elif is_locked:
        q_html = _esc(node.text)
        a_html = f'<span class="a locked">等待 {node.dep_id} 先回答</span>'
    elif node.status == 'infer':
        q_html = _esc(node.label)
        a_html = f'<span class="a infer">{_esc(node.text)}（推断）</span>'
    elif node.status == 'skip':
        q_html = _esc(node.text)
        a_html = '<span class="a skip">已跳过</span>'
    else:
        q_html = _esc(node.text)
        a_html = '<span class="a pending">待回答…</span>'

    dep_row = f'<div class="meta">dep: {node.dep_id}</div>' if node.dep_id else ''
    divider_dep = '<hr class="div">' + dep_row if node.dep_id else ''

    children_html = ''
    if node.children:
        cards = ''.join(_render_card(c, current_id, id_map) for c in node.children)
        children_html = f'<div class="ch">{cards}</div>'

    return f'''<div class="nw" id="n-{node.node_id}">
  <div class="card" style="border-left:4px solid {cfg['border']};background:{cfg['bg']};opacity:{opacity};{highlight}">
    <div class="ct"><span class="ic">{cfg['icon']}</span><span class="nid">{node.node_id}</span></div>
    <hr class="div">
    <div class="row"><span class="lb q">Q</span><span class="qt">{q_html}</span></div>
    <div class="row"><span class="lb a">A</span>{a_html}</div>
    {divider_dep}
  </div>
  {children_html}
</div>'''


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
     background:#f1f5f9;min-height:100vh;padding-bottom:72px}
.hdr{background:#fff;border-bottom:1px solid #e2e8f0;
     padding:12px 24px;display:flex;align-items:center;gap:12px}
.htitle{font-weight:600;font-size:15px;color:#0f172a}
.pw{display:flex;align-items:center;gap:8px;margin-left:auto}
.pb{width:120px;height:6px;background:#e2e8f0;border-radius:3px}
.pf{height:100%;background:#22c55e;border-radius:3px}
.pl{font-size:12px;color:#64748b}
.tree{padding:32px 24px;overflow-x:auto}
.roots{display:flex;gap:24px;align-items:flex-start}
.nw{display:flex;flex-direction:column;align-items:center}
.card{width:220px;border-radius:8px;padding:12px;border:1px solid #e2e8f0;
      border-left-width:4px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.ct{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.ic{font-size:13px;font-weight:700;color:#475569}
.nid{font-size:11px;font-weight:600;color:#94a3b8;font-family:monospace}
.div{border:none;border-top:1px solid #e2e8f0;margin:6px 0}
.row{display:flex;gap:6px;align-items:flex-start;margin:3px 0}
.lb{font-size:10px;font-weight:700;min-width:14px;margin-top:1px}
.lb.q{color:#3b82f6}.lb.a{color:#10b981}
.qt{font-size:12px;color:#1e293b;line-height:1.4}
.a{font-size:12px;line-height:1.4}
.a.done{color:#166534}
.a.pending{color:#94a3b8;font-style:italic;border-bottom:1px dashed #cbd5e1}
.a.locked{color:#94a3b8;font-style:italic}
.a.infer{color:#64748b;font-style:italic}
.a.skip{color:#94a3b8;text-decoration:line-through}
.meta{font-size:10px;color:#94a3b8;font-family:monospace;margin-top:2px}
.ch{display:flex;gap:16px;padding-top:20px;position:relative}
.ch::before{content:'';position:absolute;top:0;left:calc(50% - 1px);
            width:2px;height:20px;background:#cbd5e1}
.nw{position:relative}
.nw::after{content:'';position:absolute;bottom:-20px;left:calc(50% - 1px);
           width:2px;height:20px;background:#cbd5e1}
.nw:last-child::after,.nw:only-child::after{display:none}
.bar{position:fixed;bottom:0;left:0;right:0;background:#fff;
     border-top:1px solid #e2e8f0;padding:12px 24px;
     box-shadow:0 -2px 8px rgba(0,0,0,.06)}
.bq{font-size:13px;color:#1e293b;font-weight:500}
"""


def render_html(tree_text: str) -> str:
    nodes = parse_nodes(tree_text)
    roots, id_map = build_tree(nodes)
    current_id = find_current(nodes, id_map)

    done_count = sum(1 for n in nodes if n.status == 'done')
    total = len(nodes)
    pct = int(done_count / total * 100) if total else 0

    tree_html = ''.join(_render_card(r, current_id, id_map) for r in roots)

    bar_html = ''
    if current_id and current_id in id_map:
        cur = id_map[current_id]
        bar_html = f'<div class="bar"><div class="bq">当前问题：{_esc(cur.text)}</div></div>'

    return f'''<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="3">
<title>question-me</title>
<style>{CSS}</style>
</head><body>
<div class="hdr">
  <span class="htitle">question-me</span>
  <div class="pw">
    <div class="pb"><div class="pf" style="width:{pct}%"></div></div>
    <span class="pl">{done_count} / {total}</span>
  </div>
</div>
<div class="tree"><div class="roots">{tree_html}</div></div>
{bar_html}
</body></html>'''


def main():
    ap = argparse.ArgumentParser(description='Render question-me tree to HTML')
    ap.add_argument('output', help='Output HTML file path')
    ap.add_argument('--open', action='store_true', help='Open in browser after writing')
    args = ap.parse_args()

    tree_text = sys.stdin.read()
    html = render_html(tree_text)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)

    if args.open:
        subprocess.run(['open', args.output], check=False)


if __name__ == '__main__':
    main()
