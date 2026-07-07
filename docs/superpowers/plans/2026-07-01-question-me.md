# question-me Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `question-me` skill that clarifies ambiguous tasks before execution through a structured, decision-tree-driven Q&A session, with a live HTML visual tree rendered from an internal text format.

**Architecture:** The skill has two components: (1) `SKILL.md` containing Claude's execution instructions (Phase 0 self-check → Phase 1 fixed 3 questions → Phase 2 dynamic deep-dive → summary output), and (2) `render_tree.py`, a standalone Python script that parses the internal tree text format and generates a visual HTML card tree. Claude maintains only the internal tree text; HTML is a one-way derivation. The internal format encodes hierarchy via `dep=ID` references — no indentation-based nesting, so Claude's edits are always single-line updates.

**Tech Stack:** Python 3.8+, pure HTML/CSS/JS (no external deps), bats-core for repo tests.

## Global Constraints

- Skill lives at: `skills/coding/question-me/`
- Runtime data dir: `~/.hskill/question-me/` (reserved for future use; not used in v1)
- render_tree.py: reads tree from stdin, writes HTML to path arg, no external Python deps
- SKILL.md frontmatter: `user_invocable: true`, `version: "1.0.0"`, bundle `coding`
- HTML output: self-contained single file, `<meta http-equiv="refresh" content="3">` auto-reload
- Internal tree node format: `[label:status]  id=XX  [dep=YY]  text` — one node per line
- Status values: `done` / `open` / `infer` / `skip`

---

### Task 1: Feature branch + render_tree.py

**Files:**
- Create: `skills/coding/question-me/scripts/render_tree.py`

**Interfaces:**
- Produces: `render_tree.render_html(tree_text: str) -> str` (used by Task 1 tests and by SKILL.md call instructions)
- CLI: `echo "<tree>" | python3 render_tree.py OUTPUT_PATH [--open]`

- [ ] **Step 1: Create feature branch from staging**

```bash
git fetch origin
git checkout staging
git checkout -b feature/init-question-me
```

- [ ] **Step 2: Create skill directory**

```bash
mkdir -p skills/coding/question-me/scripts
```

- [ ] **Step 3: Write the failing parser test**

Create `skills/coding/question-me/scripts/test_render_tree.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from render_tree import parse_nodes, build_tree, find_current, Node

SAMPLE = """\
[goal:done]     id=G              将 tags 拆为 fixed_tags + candidate_tags
[success:done]  id=S              新文章有两字段；旧文章不迁移
[scope:done]    id=SC             只改 Python 脚本；SKILL.md 可补充
[storage:done]  id=ST  dep=SC     ~/.hskill/extract-url/fixed_tags.txt
[format:open]   id=FF  dep=ST     frontmatter 字段结构变化
[compat:infer]  id=CP  dep=FF     旧文章不迁移，新旧格式共存
[review:open]   id=RV  dep=SC     candidate_tags review 流程
"""

def test_parse_count():
    nodes = parse_nodes(SAMPLE)
    assert len(nodes) == 7

def test_parse_fields():
    nodes = parse_nodes(SAMPLE)
    g = next(n for n in nodes if n.node_id == 'G')
    assert g.label == 'goal'
    assert g.status == 'done'
    assert g.dep_id is None
    assert '将 tags' in g.text

def test_parse_dep():
    nodes = parse_nodes(SAMPLE)
    st = next(n for n in nodes if n.node_id == 'ST')
    assert st.dep_id == 'SC'

def test_build_roots():
    nodes = parse_nodes(SAMPLE)
    roots, id_map = build_tree(nodes)
    root_ids = {r.node_id for r in roots}
    assert root_ids == {'G', 'S', 'SC'}

def test_build_children():
    nodes = parse_nodes(SAMPLE)
    roots, id_map = build_tree(nodes)
    sc = id_map['SC']
    child_ids = {c.node_id for c in sc.children}
    assert 'ST' in child_ids
    assert 'RV' in child_ids

def test_find_current_highest_impact():
    # FF has CP depending on it (impact=1), RV has none (impact=0)
    # Both have satisfied deps (ST done, SC done)
    nodes = parse_nodes(SAMPLE)
    _, id_map = build_tree(nodes)
    current = find_current(nodes, id_map)
    assert current == 'FF'  # FF has higher impact (CP depends on it)

def test_find_current_none_when_all_done():
    text = "[goal:done] id=G 目标\n[success:done] id=S 成功\n"
    nodes = parse_nodes(text)
    _, id_map = build_tree(nodes)
    assert find_current(nodes, id_map) is None

if __name__ == '__main__':
    import traceback
    passed = failed = 0
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith('test_')]:
        try:
            fn()
            print(f'  PASS  {name}')
            passed += 1
        except Exception as e:
            print(f'  FAIL  {name}: {e}')
            traceback.print_exc()
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
```

- [ ] **Step 4: Run test to verify it fails (render_tree.py doesn't exist yet)**

```bash
python3 skills/coding/question-me/scripts/test_render_tree.py
```

Expected: `ModuleNotFoundError: No module named 'render_tree'`

- [ ] **Step 5: Write render_tree.py**

Create `skills/coding/question-me/scripts/render_tree.py`:

```python
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
        if node.dep_id and node.dep_id in id_map:
            id_map[node.dep_id].children.append(node)
        else:
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
```

- [ ] **Step 6: Run parser/tree tests — expect all pass**

```bash
python3 skills/coding/question-me/scripts/test_render_tree.py
```

Expected output:
```
  PASS  test_parse_count
  PASS  test_parse_fields
  PASS  test_parse_dep
  PASS  test_build_roots
  PASS  test_build_children
  PASS  test_find_current_highest_impact
  PASS  test_find_current_none_when_all_done

7 passed, 0 failed
```

- [ ] **Step 7: Visual test — render sample tree and inspect in browser**

```bash
cat << 'EOF' | python3 skills/coding/question-me/scripts/render_tree.py /tmp/qm-test.html --open
[goal:done]     id=G              将 tags 拆为 fixed_tags + candidate_tags
[success:done]  id=S              新文章有两字段；旧文章不迁移
[scope:done]    id=SC             只改 Python 脚本；SKILL.md 可补充
[storage:done]  id=ST  dep=SC     ~/.hskill/extract-url/fixed_tags.txt
[format:open]   id=FF  dep=ST     frontmatter 字段结构变化
[compat:infer]  id=CP  dep=FF     旧文章不迁移，新旧格式共存
[review:open]   id=RV  dep=SC     candidate_tags review 流程
EOF
```

Visually verify:
- 3 root cards (G, S, SC) at top level
- SC has children: ST (with child FF, which has child CP) and RV
- FF card is highlighted blue (current, highest impact)
- CP card is semi-transparent (dep FF not yet done)
- Bottom bar shows "当前问题：frontmatter 字段结构变化"
- Progress shows "4 / 7" (G, S, SC, ST are done)

- [ ] **Step 8: Commit**

```bash
git add skills/coding/question-me/scripts/render_tree.py \
        skills/coding/question-me/scripts/test_render_tree.py
git commit -m "feat(question-me): add render_tree.py with card tree HTML output"
```

---

### Task 2: SKILL.md

**Files:**
- Create: `skills/coding/question-me/SKILL.md`

**Interfaces:**
- Consumes: `render_tree.py` CLI from Task 1 — call with `echo "<tree>" | python3 SKILL_DIR/scripts/render_tree.py /tmp/question-me-tree.html [--open]`

- [ ] **Step 1: Write SKILL.md**

Create `skills/coding/question-me/SKILL.md`:

```markdown
---
name: question-me
description: "Pre-task clarification skill — clarifies ambiguous or complex tasks before execution through structured Q&A with a live decision tree. One question at a time, each with a recommended answer, in decision-dependency order. Triggers: '/question-me', 'help me clarify this', 'question me before starting', 'let's define this first'. Claude auto-triggers when detecting ambiguous or complex requests (multiple conflicting goals, vague keywords like 'optimize/refactor/clean up', missing success criteria, unstated context assumptions)."
user_invocable: true
version: "1.0.0"
---

# question-me — 执行前指令澄清

在开始执行前，通过结构化问答帮助用户澄清指令、对齐预期。参考 grill-me 风格：一次一问、每问附推荐答案、按决策依赖顺序推进。

---

## 触发条件

**主动调用：** 用户输入 `/question-me [任务描述]`，直接进入流程。

**自动提议（等用户确认 y/n）：**
- 请求涉及多个可能互相矛盾的目标
- 关键词模糊："优化一下"、"整理"、"重构"、"改改"
- 缺少明确的成功标准或截止范围
- 任务依赖未指明的上下文假设

**不触发：** 简单明确的指令（"运行测试"、"读这个文件"、"git status"）。

---

## 执行步骤

### Step 0 — 自查

在问用户之前，先：
1. 读取任务中提到的文件/目录，推断上下文
2. 查 `git status`、近期 commit，了解当前进展
3. 对能从代码/文档直接确认的问题，自行解答——不占用用户的问答配额

自查结束后简短说明：

```
已了解：[X、Y、Z]
仍不确定：[A、B]
开始澄清...
```

---

### Step 1 — 意图校准（固定 3 问）

每问一次，等用户回答后再问下一问。每问附推荐答案。

**Q1 — 目标：** 这件事做完，最核心的变化是什么？
**Q2 — 成功标准：** 怎么判断做对了？（可测量的验收条件）
**Q3 — 范围边界：** 明确不做什么，或哪些东西不能动？

Step 1 全部回答后：
1. 初始化决策树（格式见下节）
2. 调用渲染器（首次加 `--open`）：
   ```bash
   echo '<决策树文本>' | python3 SKILL_DIR/scripts/render_tree.py /tmp/question-me-tree.html --open
   ```
3. 进入 Step 2。

---

### Step 2 — 决策树格式

**内部格式（每节点一行，平铺列出）：**

```
[label:status]  id=XX  [dep=YY]  节点文本
```

字段规则：
- `status`: `done` / `open` / `infer` / `skip`
- `id`: 全树唯一短 ID（2–3 字母），更新引用稳定
- `dep=YY`: 可选，指向另一节点 id，表示"YY 答完后此节点才可问"；渲染器用它重建树结构
- 无 `dep` 的节点为根节点

示例（Phase 1 结束后初始化的树）：
```
[goal:done]     id=G              将 tags 拆为 fixed_tags + candidate_tags
[success:done]  id=S              新文章有两字段；旧文章不迁移
[scope:done]    id=SC             只改 Python 脚本；SKILL.md 可补充
[storage:open]  id=ST  dep=SC     fixed_tags 词表存放位置
[format:open]   id=FF  dep=ST     frontmatter 字段结构变化
[compat:open]   id=CP  dep=FF     旧文章向后兼容处理
[review:open]   id=RV  dep=SC     candidate_tags review 流程
```

**更新规则：**
- 每次用户回答后，**只修改变化的行**，不重写全树
- 依赖节点变为 `done` 后，不需要手动标注其他节点的 dep 状态——渲染器自行查 ID 状态
- `infer` 节点直接填入推断内容，不追问用户

**选题逻辑（Phase 2 每轮）：**
> 找所有 `open` 节点中，`dep` 指向的节点状态为 `done` 的（或无 `dep` 的） → 优先选被其他节点依赖次数最多的（影响面最大）

**每次树更新后**立即重新渲染（不加 `--open`）：
```bash
echo '<更新后的决策树文本>' | python3 SKILL_DIR/scripts/render_tree.py /tmp/question-me-tree.html
```

---

### Step 3 — 动态深挖

按选题逻辑逐一追问，每问格式：

```
[当前节点文本]？
推荐答案：[Claude 的推荐]
```

等用户回答 → 更新树对应行 → 重新渲染 → 继续选下一问。

**停止条件：**
- 所有 `open` 节点已变为 `done` 或 `infer`
- 用户说"够了"、"开始"、"可以了"、"stop"等打断信号

**不追问的节点：** 可以合理默认处理的，标为 `infer` 并填入推断理由，在摘要中透明列出。

---

### Step 4 — 输出精炼指令摘要

```
## 任务摘要

**目标：** ...
**成功标准：** ...
**范围：** 包含 ... / 不包含 ...
**关键决策：** ...
**假设：** ...

确认后开始执行。
```

等用户确认，然后执行任务。

---

## 不在范围内

- 跨会话保存问答历史（每次会话独立）
- 强制跑完全部 open 节点（用户可随时打断）
- 问答结果写入文件（只在会话内输出摘要）
- 自动交棒特定 skill（执行方式由 Claude 自行判断）
```

- [ ] **Step 2: Verify SKILL.md frontmatter is valid**

```bash
node -e "
const fs = require('fs');
const content = fs.readFileSync('skills/coding/question-me/SKILL.md', 'utf8');
const match = content.match(/^---\n([\s\S]*?)\n---/);
if (!match) { console.error('No frontmatter'); process.exit(1); }
const yaml = match[1];
['name:', 'description:', 'user_invocable:', 'version:'].forEach(field => {
  if (!yaml.includes(field)) { console.error('Missing: ' + field); process.exit(1); }
});
console.log('Frontmatter OK');
"
```

Expected: `Frontmatter OK`

- [ ] **Step 3: Commit**

```bash
git add skills/coding/question-me/SKILL.md
git commit -m "feat(question-me): add SKILL.md with Phase 0-4 flow and decision tree format"
```

---

### Task 3: Register in skills-index.json + run test suite

**Files:**
- Modify: `skills-index.json`

**Interfaces:**
- Consumes: `skills/coding/question-me/SKILL.md` from Task 2

- [ ] **Step 1: Compute content hash**

```bash
node -e "
const crypto = require('crypto');
const fs = require('fs');
const content = fs.readFileSync('skills/coding/question-me/SKILL.md', 'utf8');
const hash = crypto.createHash('sha256').update(content).digest('hex').slice(0, 16);
console.log('contentHash:', hash);
"
```

Note the output hash for use in the next step.

- [ ] **Step 2: Add entry to skills-index.json**

Open `skills-index.json` and add to the `skills` array (after the last `coding` bundle entry):

```json
{
  "path": "coding/question-me",
  "bundle": "coding",
  "installScope": "global",
  "contentHash": "<hash from Step 1>",
  "contentVersion": "1.0.0"
}
```

- [ ] **Step 3: Run npm test**

```bash
npm test
```

Expected: all tests pass. If a test fails because of hash mismatch, re-run Step 1 and update the hash.

- [ ] **Step 4: Commit**

```bash
git add skills-index.json
git commit -m "feat(question-me): register skill in skills-index.json"
```
