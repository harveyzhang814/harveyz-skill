#!/usr/bin/env python3
"""
Render question-me internal tree text to a visual HTML card tree.
Usage: echo "<tree text>" | python3 render_tree.py OUTPUT_PATH [--open]

Optional: include "# task description" as the first comment line to label the root node.
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
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        m = LINE_RE.match(stripped)
        if m:
            d = m.groupdict()
            nodes.append(Node(
                label=d['label'], status=d['status'],
                node_id=d['node_id'], dep_id=d['dep_id'],
                text=d['text'].strip()
            ))
    return nodes


def _parse_task_title(tree_text: str) -> str:
    for line in tree_text.splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            return stripped[2:].strip()
    return ''


def build_tree(nodes: List[Node]):
    id_map = {n.node_id: n for n in nodes}
    roots = []
    for node in nodes:
        if node.dep_id and node.dep_id in id_map and node.dep_id != node.node_id:
            id_map[node.dep_id].children.append(node)
        else:
            roots.append(node)
    reachable = set()
    stack = list(roots)
    while stack:
        n = stack.pop()
        if n.node_id in reachable:
            continue
        reachable.add(n.node_id)
        stack.extend(n.children)
    for node in nodes:
        if node.node_id not in reachable:
            roots.append(node)
    return roots, id_map


def find_current(nodes: List[Node], id_map: dict) -> Optional[str]:
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
    'done':  {'border': '#22c55e', 'bg': 'var(--bg-done)', 'icon': '✓'},
    'open':  {'border': '#eab308', 'bg': 'var(--bg-open)', 'icon': '?'},
    'infer': {'border': '#94a3b8', 'bg': 'var(--bg-infer)', 'icon': '~'},
    'skip':  {'border': 'var(--line)', 'bg': 'var(--bg-infer)', 'icon': '-'},
}

TERM_COLOR = {
    'done':  '#22c55e',
    'infer': '#94a3b8',
    'skip':  'var(--line)',
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

    card_html = (
        f'<div class="card" style="border-left:4px solid {cfg["border"]};'
        f'background:{cfg["bg"]};opacity:{opacity};{highlight}">'
        f'<div class="ct"><span class="ic">{cfg["icon"]}</span>'
        f'<span class="nid">{node.node_id}</span></div>'
        f'<hr class="div">'
        f'<div class="row"><span class="lb q">Q</span><span class="qt">{q_html}</span></div>'
        f'<div class="row"><span class="lb a">A</span>{a_html}</div>'
        f'{divider_dep}</div>'
    )

    has_children = bool(node.children)
    is_closed_leaf = not has_children and node.status in TERM_COLOR

    if has_children:
        inner = ''.join(_render_card(c, current_id, id_map) for c in node.children)
        tail = f'<div class="stem"></div><div class="ch">{inner}</div>'
    elif is_closed_leaf:
        color = TERM_COLOR[node.status]
        tail = f'<div class="stem"></div><div class="term-dot" style="background:{color}"></div>'
    else:
        tail = ''

    return f'<div class="nw" id="n-{node.node_id}">{card_html}{tail}</div>'


CSS = """
:root[data-theme="dark"]{--page:#0f172a;--surface:#1e293b;--border:#334155;
  --line:#475569;--text:#e2e8f0;--strong:#f8fafc;--muted:#94a3b8;--faint:#64748b;
  --icon:#cbd5e1;--ans:#86efac;--shadow:rgba(0,0,0,.4);
  --bg-done:#132a22;--bg-open:#2a2414;--bg-infer:#1e293b}
:root[data-theme="light"]{--page:#f1f5f9;--surface:#fff;--border:#e2e8f0;
  --line:#cbd5e1;--text:#1e293b;--strong:#0f172a;--muted:#64748b;--faint:#94a3b8;
  --icon:#475569;--ans:#166534;--shadow:rgba(0,0,0,.06);
  --bg-done:#f0fdf4;--bg-open:#fffbeb;--bg-infer:#f8fafc}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
     background:var(--page);min-height:100vh;padding-bottom:72px}
.hdr{background:var(--surface);border-bottom:1px solid var(--border);
     padding:12px 24px;display:flex;align-items:center;gap:12px}
.htitle{font-weight:600;font-size:15px;color:var(--strong)}
.pw{display:flex;align-items:center;gap:8px;margin-left:auto}
.pb{width:120px;height:6px;background:var(--border);border-radius:3px}
.pf{height:100%;background:#22c55e;border-radius:3px}
.pl{font-size:12px;color:var(--muted)}
.tt{font-size:12px;color:var(--muted);background:none;cursor:pointer;
    border:1px solid var(--border);border-radius:6px;padding:3px 8px}
.tree{padding:32px 24px;overflow-x:auto;display:flex;justify-content:center}
.nw{display:flex;flex-direction:column;align-items:center}
.ch{display:flex;align-items:flex-start}
.ch>.nw{padding:20px 16px 0;position:relative}
.ch>.nw::before{content:'';position:absolute;top:0;left:0;right:0;
                border-top:2px solid var(--line)}
.ch>.nw:first-child::before{left:50%}
.ch>.nw:last-child::before{right:50%}
.ch>.nw:only-child::before{display:none}
.ch>.nw::after{content:'';position:absolute;top:0;left:50%;
               transform:translateX(-1px);width:2px;height:20px;background:var(--line)}
.stem{width:2px;height:20px;background:var(--line);flex-shrink:0}
.term-dot{width:10px;height:10px;border-radius:50%;margin:2px 0}
.task-card{border:2px solid var(--icon);background:var(--surface);border-radius:8px;
           padding:10px 20px;font-size:13px;font-weight:600;color:var(--text);
           max-width:300px;text-align:center;
           box-shadow:0 1px 3px var(--shadow)}
.card{width:220px;border-radius:8px;padding:12px;border:1px solid var(--border);
      border-left-width:4px;box-shadow:0 1px 3px var(--shadow)}
.ct{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.ic{font-size:13px;font-weight:700;color:var(--icon)}
.nid{font-size:11px;font-weight:600;color:var(--faint);font-family:monospace}
.div{border:none;border-top:1px solid var(--border);margin:6px 0}
.row{display:flex;gap:6px;align-items:flex-start;margin:3px 0}
.lb{font-size:10px;font-weight:700;min-width:14px;margin-top:1px}
.lb.q{color:#3b82f6}.lb.a{color:#10b981}
.qt{font-size:12px;color:var(--text);line-height:1.4}
.a{font-size:12px;line-height:1.4}
.a.done{color:var(--ans)}
.a.pending{color:var(--faint);font-style:italic;border-bottom:1px dashed var(--line)}
.a.locked{color:var(--faint);font-style:italic}
.a.infer{color:var(--muted);font-style:italic}
.a.skip{color:var(--faint);text-decoration:line-through}
.meta{font-size:10px;color:var(--faint);font-family:monospace;margin-top:2px}
.bar{position:fixed;bottom:0;left:0;right:0;background:var(--surface);
     border-top:1px solid var(--border);padding:12px 24px;
     box-shadow:0 -2px 8px var(--shadow)}
.bq{font-size:13px;color:var(--text);font-weight:500}
"""


def render_html(tree_text: str) -> str:
    nodes = parse_nodes(tree_text)
    task_title = _parse_task_title(tree_text)
    roots, id_map = build_tree(nodes)
    current_id = find_current(nodes, id_map)

    done_count = sum(1 for n in nodes if n.status == 'done')
    total = len(nodes)
    pct = int(done_count / total * 100) if total else 0

    label = _esc(task_title) if task_title else '任务'

    if roots:
        roots_html = ''.join(_render_card(r, current_id, id_map) for r in roots)
        tree_html = (
            f'<div class="nw">'
            f'<div class="task-card">{label}</div>'
            f'<div class="stem"></div>'
            f'<div class="ch">{roots_html}</div>'
            f'</div>'
        )
    else:
        tree_html = f'<div class="task-card">{label}</div>'

    bar_html = ''
    if current_id and current_id in id_map:
        cur = id_map[current_id]
        bar_html = f'<div class="bar"><div class="bq">当前问题：{_esc(cur.text)}</div></div>'

    return f'''<!DOCTYPE html>
<html lang="zh" data-theme="dark"><head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="3">
<title>question-me</title>
<style>{CSS}</style>
<script>
// 默认暗黑；用户切换后记在 localStorage，3 秒自动刷新后仍保持
if (localStorage.getItem('question-me-theme') === 'light')
  document.documentElement.dataset.theme = 'light';
function toggleTheme() {{
  var t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = t;
  localStorage.setItem('question-me-theme', t);
}}
</script>
</head><body>
<div class="hdr">
  <span class="htitle">question-me</span>
  <div class="pw">
    <div class="pb"><div class="pf" style="width:{pct}%"></div></div>
    <span class="pl">{done_count} / {total}</span>
    <button id="theme-toggle" class="tt" onclick="toggleTheme()">明 / 暗</button>
  </div>
</div>
<div class="tree">{tree_html}</div>
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
