#!/usr/bin/env python3
"""sync-design 设计稿 HTML 工具（仅标准库）。

  outline <html> [状态名]    打印区段目录：样式段、图标定义区、页头区、状态块、脚本段的行号范围与大小；
                             给出状态名时只列名称或覆盖里有它的块
  migrate <manifest.json>    原地迁移 manifest 登记的所有稿子：删 base64 内嵌字体、重复图标收进
                             图标定义区、按 id / data-ui-state / data-state 属性补状态标记；
                             最后列出仍需人工（模型）补标记的状态
  check <manifest.json>      只检查不修改；有待迁移项时退出码为 1
  verify <改前> <改后>        补标记后校验：去掉状态标记与标签间空白后两份必须一致，否则退出码为 1
"""
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ANCHOR = re.compile(r'^\s*─{2,}\s*(.+?)\s*─{2,}(.*)$', re.S)
SVG = re.compile(r'<svg\b([^>]*)>(.*?)</svg>', re.S)
FONT_FACE = re.compile(
    r'@font-face\s*\{[^}]*?url\(\s*["\']?data:(?:font|application/(?:x-)?font)[^}]*\}\s*', re.S)
SPRITE_OPEN = re.compile(r'<svg class="sd-sprite"[^>]*>')
SVG_CHILD = re.compile(r'(?:^|[\s>+~,(])(?:path|circle|rect|polyline|polygon|ellipse|line|g)(?=$|[\s>+~,.:\[)])')
PARTIAL_MIN = 40_000  # 少于 4 万字符的稿子直接全量读，不要求状态标记
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


# ── 标记解析 ──

def parse_anchor(comment):
    """返回 (名称, 覆盖的状态列表)；不是标记返回 None。"""
    m = ANCHOR.match(comment)
    if not m:
        return None
    covers = []
    c = re.search(r'覆盖[:：]\s*([^\n]+)', m.group(2))
    if c:
        covers = [s.strip() for s in c.group(1).split('|') if s.strip()]
    return m.group(1).strip(), covers


def mentions(text, state):
    """标记名称里以完整词出现该状态名（前后不是 ASCII 字母数字、- 或 _）。"""
    return re.search(r'(?<![A-Za-z0-9_-])' + re.escape(state) + r'(?![A-Za-z0-9_-])', text) is not None


class Scanner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth = 0
        self.ranges = {'style': [], 'script': []}
        self.open_at = {}
        self.markers = []  # (行号, 深度, 名称, 覆盖)
        self.sprite = None
        self.body_start = None
        self.body_end = None

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        if tag in ('style', 'script'):
            self.open_at[tag] = line
        if tag == 'body':
            self.body_start = line
        if tag == 'svg' and ('class', 'sd-sprite') in attrs:
            self.sprite = [line, None, self.depth]
        if tag not in VOID:
            self.depth += 1

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        if tag in ('style', 'script') and tag in self.open_at:
            self.ranges[tag].append((self.open_at.pop(tag), line))
        if tag not in VOID:
            self.depth -= 1
        if tag == 'svg' and self.sprite and self.sprite[1] is None and self.depth == self.sprite[2]:
            self.sprite[1] = line
        if tag == 'body':
            self.body_end = line

    def handle_comment(self, data):
        a = parse_anchor(data)
        if a:
            self.markers.append((self.getpos()[0], self.depth, a[0], a[1]))


def scan(text):
    """返回 (Scanner, 顶层状态块列表[(起行, 止行, 名称, 覆盖)])。"""
    s = Scanner()
    s.feed(text)
    s.close()
    total = text.count('\n') + 1
    # 顶层标记：深度不超过上一个顶层标记；更深的算嵌在上一块里
    top, cur = [], None
    for m in s.markers:
        if cur is None or m[1] <= cur:
            top.append(m)
            cur = m[1]
    marks = {m[0] for m in top}
    stops = sorted(marks | {a for a, _ in s.ranges['script']} | {s.body_end or total})
    blocks = []
    for line, _, name, covers in top:
        stop = next((x for x in stops if x > line), total)
        # 停在脚本段或 </body> 时含该行：正文末尾常和它们挤在同一行
        blocks.append((line, stop - 1 if stop in marks else stop, name, covers))
    return s, blocks


def unmarked_states(text, states):
    s, _ = scan(text)
    names = []
    for _, _, name, covers in s.markers:
        names.append(name)
        names.extend(covers)
    return [st for st in states if not any(mentions(n, st) for n in names)]


# ── 资源 ──

def child_selectors(css):
    """样式里指向图标内部元素的选择器：<use> 引用的图标内部不吃这类选择器。"""
    out = []
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    for chunk in css.split('{')[:-1]:
        sel = chunk.rsplit('}', 1)[-1].rsplit(';', 1)[-1].strip()
        if sel and not sel.startswith('@') and SVG_CHILD.search(sel):
            out.append(sel)
    return out


def dedupable(inner):
    return len(inner) >= 80 and not any(x in inner for x in ('class=', 'id=', '${', '<use', '<svg'))


def plan_icons(text):
    """返回 (可收进图标定义区的图标 -> 出现次数, 判定函数, 指向图标内部的选择器)。"""
    css = ''.join(re.findall(r'<style[^>]*>(.*?)</style>', text, re.S))
    risky = child_selectors(css)
    risky_classes = set(re.findall(r'\.([\w-]+)', ' '.join(risky)))
    sprite = SPRITE_OPEN.search(text)
    sprite_span = (sprite.start(), text.find('</svg>', sprite.end())) if sprite else (-1, -1)

    def eligible(m):
        if sprite_span[0] <= m.start() <= sprite_span[1] or not dedupable(m.group(2)):
            return False
        cls = re.search(r'class="([^"]*)"', m.group(1))
        return not (cls and set(cls.group(1).split()) & risky_classes)

    counts = Counter(m.group(2).strip() for m in SVG.finditer(text) if eligible(m))
    # 省下的字符不够抵引用开销就不收
    groups = {inner: n for inner, n in counts.items() if (n - 1) * len(inner) - n * 40 > 200}
    return groups, eligible, risky


def strip_fonts(text, report):
    faces = FONT_FACE.findall(text)
    if faces:
        fams = re.findall(r'font-family\s*:\s*["\']?([^;"\']+)', ''.join(faces))
        report.append(f'删除内嵌字体 {len(faces)} 个：{", ".join(fams)}（字体名保留，确认 font-family 带系统回退）')
    return FONT_FACE.sub('', text)


def body_start(text):
    """正文起点：<body> 之后；省略 <body> 的稿子取 </head> 或最后一个 </style> 之后。"""
    for pat in (r'<body\b[^>]*>', r'</head>'):
        m = re.search(pat, text)
        if m:
            return m.end()
    ends = [m.end() for m in re.finditer(r'</style>', text)]
    return ends[-1] if ends else 0


def dedupe_icons(text, report):
    groups, eligible, risky = plan_icons(text)
    next_id = max((int(x) for x in re.findall(r'id="sd-icon-(\d+)"', text)), default=0) + 1
    ids = {inner: f'sd-icon-{next_id + i}' for i, inner in enumerate(groups)}
    if risky:
        report.append(f'{len(risky)} 条样式选择器指向图标内部，带相关 class 的图标已跳过：' + ' ; '.join(risky[:4]))
    if not ids:
        return text
    before = len(text)
    body = SVG.sub(lambda m: f'<svg{m.group(1)}><use href="#{ids[m.group(2).strip()]}"/></svg>'
                   if eligible(m) and m.group(2).strip() in ids else m.group(0), text)
    symbols = ''.join(f'\n<symbol id="{i}">{inner}</symbol>' for inner, i in ids.items())
    if SPRITE_OPEN.search(body):
        pos = body.find('</svg>', SPRITE_OPEN.search(body).end())
        text = body[:pos] + symbols + '\n' + body[pos:]
    else:
        at = body_start(body)
        text = (body[:at] + '\n<!-- 图标定义区：重复图标只定义一次，正文用 <use> 引用 -->\n'
                '<svg class="sd-sprite" aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden">'
                + symbols + '\n</svg>\n' + body[at:])
    report.append(f'重复图标 {len(ids)} 种收进图标定义区，减少 {(before - len(text)) // 1000}K 字符')
    return text


# ── 状态标记 ──

def infer_anchors(text, states, report):
    """状态名恰好是某个正文元素的 id / data-ui-state / data-state，且全文唯一时，在该元素前补标记。"""
    at = body_start(text)
    scripts = [m.span() for m in re.finditer(r'<script\b.*?</script>', text, re.S)]
    inserts = []
    for st in unmarked_states(text, states):
        pat = r'<\w+\b[^>]*?\s(?:id|data-ui-state|data-state)="' + re.escape(st) + r'"'
        hits = [m.start() for m in re.finditer(pat, text)
                if m.start() > at and not any(a <= m.start() < b for a, b in scripts)]
        if len(hits) == 1:
            inserts.append((hits[0], st))
    for pos, st in sorted(inserts, reverse=True):
        text = text[:pos] + f'\n<!-- ── {st} ── -->\n' + text[pos:]
    if inserts:
        report.append(f'按属性补状态标记 {len(inserts)} 个')
    return text


# ── 命令 ──

def entries(manifest_path):
    manifest = Path(manifest_path).resolve()
    root = manifest.parents[2]  # <项目>/.hskill/sync-design/manifest.json
    data = json.loads(manifest.read_text(encoding='utf-8'))
    for kind, items in (('完成稿', data.get('entries', [])), ('设计稿', data.get('drafts', []))):
        for e in items:
            yield kind, e, root / e['htmlFile']


def problems(text, states):
    out = []
    if FONT_FACE.search(text):
        out.append('有 base64 内嵌字体')
    dups = len(plan_icons(text)[0])
    if dups:
        out.append(f'{dups} 种图标重复内联')
    missing = unmarked_states(text, states) if len(text) >= PARTIAL_MIN else []
    if missing:
        out.append(f'{len(missing)} 个状态没有标记：{" | ".join(missing)}')
    return out


def cmd_outline(path, state=None):
    text = Path(path).read_text(encoding='utf-8')
    lines = text.split('\n')
    s, blocks = scan(text)

    def size(a, b):
        return f'{sum(len(x) for x in lines[a - 1:b]) // 1000}K'

    print(f'{path}  共 {len(lines)} 行，{len(text) // 1000}K 字符')
    for a, b in s.ranges['style']:
        print(f'  样式段      {a}-{b}  {size(a, b)}')
    if s.sprite:
        print(f'  图标定义区  {s.sprite[0]}-{s.sprite[1]}  {size(s.sprite[0], s.sprite[1])}')
    head_from = max([s.body_start or 0, s.sprite[1] if s.sprite else 0] + [b for _, b in s.ranges['style']]) + 1
    if blocks and blocks[0][0] > head_from:
        print(f'  页头区      {head_from}-{blocks[0][0] - 1}  {size(head_from, blocks[0][0] - 1)}')
    top = {b[0] for b in blocks}
    by_line = {b[0]: b for b in blocks}
    for line, _, name, covers in s.markers:
        if state and not any(mentions(n, state) for n in [name] + covers):
            continue
        extra = f'  覆盖：{" | ".join(covers)}' if covers else ''
        if line in top:
            a, b = by_line[line][:2]
            print(f'  状态块      {a}-{b}  {size(a, b)}  {name}{extra}')
        else:
            print(f'    └ 嵌套    {line}  {name}{extra}')
    for a, b in s.ranges['script']:
        print(f'  脚本段      {a}-{b}  {size(a, b)}')
    if not s.ranges['script']:
        print('  脚本段      无')
    if not blocks:
        print('  （没有状态标记：只能全量读）')


def cmd_migrate(manifest_path):
    todo = 0
    for kind, e, f in entries(manifest_path):
        if not f.exists():
            print(f'[缺文件] {kind} {e["id"]}: {e["htmlFile"]}')
            continue
        old = f.read_text(encoding='utf-8')
        report = []
        new = strip_fonts(old, report)
        new = dedupe_icons(new, report)
        new = infer_anchors(new, e.get('uiStates', []), report)
        if new != old:
            f.write_text(new, encoding='utf-8')
        left = problems(new, e.get('uiStates', []))
        todo += bool(left)
        if report or left:
            print(f'{kind} {e["id"]}  {len(old) // 1000}K -> {len(new) // 1000}K 字符')
            for r in report:
                print(f'  - {r}')
            for p in left:
                print(f'  ! 待补：{p}')
    print('全部合规' if not todo else f'{todo} 份仍需补标记')


def cmd_check(manifest_path):
    bad = 0
    for kind, e, f in entries(manifest_path):
        if not f.exists():
            print(f'[缺文件] {kind} {e["id"]}: {e["htmlFile"]}')
            continue
        text = f.read_text(encoding='utf-8')
        ps = problems(text, e.get('uiStates', []))
        if ps:
            bad += 1
            print(f'[待迁移] {kind} {e["id"]} ({len(text) // 1000}K 字符): ' + '；'.join(ps))
    print('全部合规' if not bad else f'{bad} 份待迁移')
    return 1 if bad else 0


def strip_markers(text):
    text = re.sub(r'<!--(.*?)-->', lambda m: '' if ANCHOR.match(m.group(1)) else m.group(0), text, flags=re.S)
    return re.sub(r'>\s+<', '><', text).strip()


def cmd_verify(before, after):
    a = strip_markers(Path(before).read_text(encoding='utf-8'))
    b = strip_markers(Path(after).read_text(encoding='utf-8'))
    if a == b:
        print('一致：只动了状态标记和标签间空白')
        return 0
    i = next(i for i in range(min(len(a), len(b)) + 1) if i == min(len(a), len(b)) or a[i] != b[i])
    print(f'不一致：除状态标记外还有改动，首个差异附近\n  改前：{a[max(0, i - 60):i + 60]!r}\n  改后：{b[max(0, i - 60):i + 60]!r}')
    return 1


if __name__ == '__main__':
    cmds = {'outline': cmd_outline, 'migrate': cmd_migrate, 'check': cmd_check, 'verify': cmd_verify}
    if len(sys.argv) < 3 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    sys.exit(cmds[sys.argv[1]](*sys.argv[2:]))
