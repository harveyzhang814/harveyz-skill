# capture-vocab 检索机制重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `skills/coding/capture-vocab/scripts/vocab.py` (lookup/list/refs sub-commands) so agents can slice `vocab.md` instead of reading it whole, without touching the vocab.md format itself; rewrite SKILL.md's add/query/update/remove flow to use it; bump the skill version.

**Architecture:** One dependency-free Python 3 script that locates `.hskill/capture-vocab/vocab.md` by walking up from cwd, parses it into `## `-delimited sections, and answers three cheap queries (`lookup`, `list`, `refs`) via normalized bidirectional substring matching — no index file, no format change.

**Tech Stack:** Python 3 stdlib only (`re`, `pathlib`, `sys`). pytest via `scripts/run-skill-tests.sh` auto-discovery (system python3, no venv).

**Spec:** `docs/superpowers/specs/2026-09-20-capture-vocab-retrieval-design.md`

## Global Constraints

- No third-party dependencies in `vocab.py` (spec §3).
- `vocab.md` format is not modified — zero migration (spec §2, §7.1).
- Script does not accept a path argument; it locates the vocab file by walking up from cwd to git root or `/` (spec §3).
- File not found → exit 2, stdout exactly `no vocab file`, for every sub-command (spec §3.1).
- Only three sub-commands: `lookup`, `list`, `refs` — no `scan` (spec §3.2, key decision table).
- `lookup` hit cap is 3; above that, degrade to a single `N matches: ...` line, never partial section dumps (spec §3.2).
- Matching = normalize both sides (casefold, fullwidth→halfwidth parens, strip backticks, strip whitespace), then bidirectional substring test (spec §3.2).
- Avoid-line aliases: split on `, ， ; ；`, strip a trailing parenthetical, keep only fragments with normalized length < 20 (spec §3.2).
- Do not touch `agent-canvas` repo, do not copy the script into any project's `.hskill/`, do not change `skills-index.json`'s `path`/`bundle`/`installScope` (handoff doc — 范围铁律).
- `contentHash` in `skills-index.json`: leave untouched, algorithm unverified (handoff doc — 验证步骤).

---

## File Structure

- `skills/coding/capture-vocab/scripts/vocab.py` — the whole script: file location, parsing, normalization, matching, path classification, three sub-command handlers, `main()`. Single file — the logic is small and tightly coupled (parser feeds matcher feeds both `lookup` and `refs`), splitting it would add import ceremony for no isolation benefit.
- `skills/coding/capture-vocab/tests/fixtures/.hskill/capture-vocab/vocab.md` — frozen snapshot of agent-canvas's real vocab.md (33 terms) plus 2 synthetic terms. Nested under `.hskill/capture-vocab/` so tests can `cwd=fixtures_dir` and exercise the real upward-search path.
- `skills/coding/capture-vocab/tests/test_vocab.py` — pytest suite, one test function per assertion in spec §6, all driving the script via `subprocess.run` (matches the "script has no path arg, tests cd into fixture" contract — testing through the CLI boundary is what actually verifies the contract, not calling internals).
- `skills/coding/capture-vocab/SKILL.md` — rewritten `add`/`query`/`update`/`remove` sections + new "Agent 加载约定" section + version bump.
- `skills-index.json` — `contentVersion` bump for the `coding/capture-vocab` entry only.

---

### Task 1: `vocab.py` — file location, parsing, normalization, `lookup`, `list`

**Files:**
- Create: `skills/coding/capture-vocab/scripts/vocab.py`
- Create: `skills/coding/capture-vocab/tests/fixtures/.hskill/capture-vocab/vocab.md`
- Create: `skills/coding/capture-vocab/tests/test_vocab.py`

**Interfaces:**
- Produces: `find_vocab_file() -> Path | None`, `parse_sections(text: str) -> list[dict]` (each dict has keys `name`, `raw`, `avoid_raw`, `ref_raw`), `normalize(s: str) -> str`, `extract_aliases(avoid_raw: str) -> list[str]`, `bidir_match(a: str, b: str) -> bool`. Task 2 (`refs`) consumes `parse_sections` and reuses each section's `ref_raw`.
- Produces (CLI): `python3 vocab.py lookup <term>` and `python3 vocab.py list` behaviors described below. Task 2 adds `refs` to the same `main()` dispatch.

- [ ] **Step 1: Create the fixture directory and copy the real vocab.md snapshot**

```bash
mkdir -p skills/coding/capture-vocab/tests/fixtures/.hskill/capture-vocab
cp /Users/harveyzhang96/Projects/agent-canvas/.hskill/capture-vocab/vocab.md skills/coding/capture-vocab/tests/fixtures/.hskill/capture-vocab/vocab.md
```

- [ ] **Step 2: Append the two synthetic entries to the fixture**

Append to `skills/coding/capture-vocab/tests/fixtures/.hskill/capture-vocab/vocab.md`:

```markdown

## 测试专用-降级示例
人工构造条目，仅用于验证 lookup 命中数超过 3 条时的降级输出路径，不对应真实业务概念。
_Avoid_: 节点关系

## 测试专用-散文别名
人工构造条目，仅用于验证 Avoid 中长度不小于 20 字的散文片段不会被当成别名参与匹配。
_Avoid_: 关系改, 这是一段刻意写得很长用来验证别名清洗阈值确实生效而不会被当成短别名参与子串匹配的散文说明文字
```

(`节点关系` and `关系改` are both literal substrings of the acceptance-anchor query `把工作区的节点关系改一下`, so together with the two real hits — `工作区`, `节点` — this pushes the hit count to 4, safely over the >3 degrade threshold. The second entry's long fragment is ≥20 chars post-normalization and must never surface as a match on its own.)

- [ ] **Step 3: Write the failing tests for location, parsing, normalization, `lookup`, `list`**

Create `skills/coding/capture-vocab/tests/test_vocab.py`:

```python
import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "vocab.py"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def run_vocab(args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def test_no_vocab_file_exits_2(tmp_path):
    result = run_vocab(["lookup", "anything"], cwd=tmp_path)
    assert result.returncode == 2
    assert result.stdout.strip() == "no vocab file"


def test_no_args_does_not_crash(tmp_path):
    result = run_vocab([], cwd=tmp_path)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_lookup_hit_exit_0(tmp_path):
    result = run_vocab(["lookup", "画布"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert "## 画布区" in result.stdout


def test_lookup_miss_exit_1(tmp_path):
    result = run_vocab(["lookup", "zzz_no_such_term"], cwd=FIXTURE_DIR)
    assert result.returncode == 1
    assert result.stdout.strip() == "no match: zzz_no_such_term"


def test_lookup_input_too_short_is_a_miss(tmp_path):
    result = run_vocab(["lookup", "a"], cwd=FIXTURE_DIR)
    assert result.returncode == 1
    assert result.stdout.strip() == "no match: a"


def test_lookup_degrades_above_three_hits(tmp_path):
    result = run_vocab(["lookup", "把工作区的节点关系改一下"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    m = re.match(r"^(\d+) matches: (.+)$", result.stdout.strip())
    assert m, f"unexpected stdout: {result.stdout!r}"
    assert int(m.group(1)) > 3
    assert "\n" not in result.stdout.strip()


def test_lookup_case_insensitive(tmp_path):
    lower = run_vocab(["lookup", "tab"], cwd=FIXTURE_DIR)
    upper = run_vocab(["lookup", "Tab"], cwd=FIXTURE_DIR)
    assert lower.returncode == upper.returncode == 0
    assert lower.stdout == upper.stdout


def test_lookup_fullwidth_paren_alias(tmp_path):
    result = run_vocab(["lookup", "瓦片"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert "Widget (瓦片)" in result.stdout


def test_lookup_backtick_term_name(tmp_path):
    result = run_vocab(["lookup", "画布操控"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert "`画布操控` profile" in result.stdout


def test_lookup_avoid_alias_hits_canonical_term(tmp_path):
    result = run_vocab(["lookup", "抽屉"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert "## 工作区" in result.stdout


def test_lookup_long_avoid_prose_does_not_match(tmp_path):
    result = run_vocab(
        ["lookup", "这是一段刻意写得很长用来验证别名清洗阈值确实生效而不会被当成短别名参与子串匹配的散文说明文字"],
        cwd=FIXTURE_DIR,
    )
    assert result.returncode == 1


def test_lookup_section_boundary_exact(tmp_path):
    result = run_vocab(["lookup", "席位"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert result.stdout.startswith("## 席位")
    assert "## Pilot（主体）" not in result.stdout
    assert not result.stdout.endswith("\n\n")


def test_list_line_count_matches_section_count(tmp_path):
    vocab_path = FIXTURE_DIR / ".hskill" / "capture-vocab" / "vocab.md"
    text = vocab_path.read_text(encoding="utf-8")
    section_count = len(re.findall(r"^## ", text, flags=re.MULTILINE))
    result = run_vocab(["list"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) == section_count
```

- [ ] **Step 4: Run tests to verify they fail (no script yet)**

Run: `cd skills/coding/capture-vocab && python3 -m pytest tests/ -v`
Expected: all FAIL/ERROR (`vocab.py` does not exist)

- [ ] **Step 5: Implement `vocab.py`**

```python
#!/usr/bin/env python3
import re
import sys
from pathlib import Path

HEADER_RE = re.compile(r'^## (.+)$', re.MULTILINE)
DELIM_RE = re.compile(r'[,，;；]')
TRAILING_PAREN_RE = re.compile(r'[（(][^）)]*[）)]\s*$')


def find_vocab_file():
    cur = Path.cwd().resolve()
    while True:
        candidate = cur / ".hskill" / "capture-vocab" / "vocab.md"
        if candidate.exists():
            return candidate
        if (cur / ".git").exists():
            return None
        if cur.parent == cur:
            return None
        cur = cur.parent


def normalize(s):
    if not s:
        return ""
    s = s.replace('（', '(').replace('）', ')')
    s = s.replace('`', '')
    s = s.casefold()
    return s.strip()


def extract_aliases(avoid_raw):
    aliases = []
    for part in DELIM_RE.split(avoid_raw):
        part = part.strip()
        if not part:
            continue
        cleaned = TRAILING_PAREN_RE.sub('', part).strip()
        if cleaned and len(normalize(cleaned)) < 20:
            aliases.append(cleaned)
    return aliases


def parse_sections(text):
    headers = list(HEADER_RE.finditer(text))
    sections = []
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block_lines = text[start:end].split('\n')
        name = m.group(1).strip()
        avoid_lines, ref_lines, field = [], [], None
        for line in block_lines[1:]:
            if line.startswith('_Avoid_:'):
                field = 'avoid'
                avoid_lines.append(line[len('_Avoid_:'):].strip())
                continue
            if line.startswith('_Reference_:'):
                field = 'reference'
                ref_lines.append(line[len('_Reference_:'):].strip())
                continue
            if field == 'avoid':
                avoid_lines.append(line.strip())
            elif field == 'reference':
                ref_lines.append(line.strip())
        raw = '\n'.join(block_lines).rstrip()
        sections.append({
            'name': name,
            'raw': raw,
            'avoid_raw': ' '.join(l for l in avoid_lines if l),
            'ref_raw': ' '.join(l for l in ref_lines if l),
        })
    return sections


def bidir_match(a, b):
    if not a or not b:
        return False
    return a in b or b in a


def section_hits(sections, query_norm):
    hits = []
    for sec in sections:
        candidates = [normalize(sec['name'])] + [normalize(a) for a in extract_aliases(sec['avoid_raw'])]
        if any(bidir_match(c, query_norm) for c in candidates if c):
            hits.append(sec)
    return hits


def cmd_lookup(sections, term):
    query_norm = normalize(term)
    if len(query_norm) < 2:
        print(f"no match: {term}")
        return 1
    hits = section_hits(sections, query_norm)
    if not hits:
        print(f"no match: {term}")
        return 1
    if len(hits) > 3:
        print(f"{len(hits)} matches: {', '.join(h['name'] for h in hits)}")
        return 0
    for h in hits:
        print(h['raw'])
    return 0


def cmd_list(sections):
    for sec in sections:
        if sec['avoid_raw']:
            print(f"{sec['name']} | {sec['avoid_raw']}")
        else:
            print(sec['name'])
    return 0


def main(argv):
    if not argv:
        print("usage: vocab.py <lookup|list|refs> [args]")
        return 2
    cmd = argv[0]
    vocab_path = find_vocab_file()
    if vocab_path is None:
        print("no vocab file")
        return 2
    text = vocab_path.read_text(encoding="utf-8")
    sections = parse_sections(text)
    if cmd == "lookup":
        if len(argv) < 2:
            print("usage: vocab.py lookup <term>")
            return 2
        return cmd_lookup(sections, argv[1])
    if cmd == "list":
        return cmd_list(sections)
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 6: Run tests, fix until green (excluding `refs`-dependent tests, which don't exist yet)**

Run: `cd skills/coding/capture-vocab && python3 -m pytest tests/ -v`
Expected: all PASS. If `test_lookup_degrades_above_three_hits` fails because the count is not `> 3`, print `result.stdout` from a debug run (`python3 scripts/vocab.py lookup "把工作区的节点关系改一下"` with cwd set to the fixture dir) and adjust the synthetic aliases added in Step 2 — add one more short literal substring of the query to a synthetic entry's `_Avoid_` line until the count clears 3. Do not change the assertion; change the fixture.

- [ ] **Step 7: Commit**

```bash
git add skills/coding/capture-vocab/scripts/vocab.py skills/coding/capture-vocab/tests/
git commit -m "feat(capture-vocab): add vocab.py with lookup/list and its test fixture"
```

---

### Task 2: `vocab.py` — `refs` sub-command

**Files:**
- Modify: `skills/coding/capture-vocab/scripts/vocab.py`
- Modify: `skills/coding/capture-vocab/tests/test_vocab.py`

**Interfaces:**
- Consumes: `parse_sections` sections' `ref_raw` field, `normalize` (Task 1).
- Produces: `extract_paths(ref_raw: str) -> list[str]`, `classify_path(query: str, candidate: str) -> str | None` (returns `"same-file"`, `"dir-contains"`, or `None`), `cmd_refs(sections, path) -> int`.

- [ ] **Step 1: Write the failing tests**

Append to `skills/coding/capture-vocab/tests/test_vocab.py`:

```python
def test_refs_same_file(tmp_path):
    result = run_vocab(
        ["refs", "src/renderer/src/components/PanelArea.tsx"], cwd=FIXTURE_DIR
    )
    assert result.returncode == 0
    lines = result.stdout.splitlines()
    workspace_lines = [l for l in lines if l.startswith("工作区 |")]
    assert workspace_lines, result.stdout
    assert "same-file" in workspace_lines[0]


def test_refs_dir_contains(tmp_path):
    result = run_vocab(
        ["refs", "src/main/pilot/pilotConfig.ts"], cwd=FIXTURE_DIR
    )
    assert result.returncode == 0
    pilot_lines = [l for l in result.stdout.splitlines() if l.startswith("Pilot（主体） |")]
    assert pilot_lines, result.stdout
    assert "dir-contains" in pilot_lines[0]


def test_refs_no_hits_exit_1(tmp_path):
    result = run_vocab(["refs", "src/totally/unrelated/path.ts"], cwd=FIXTURE_DIR)
    assert result.returncode == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/coding/capture-vocab && python3 -m pytest tests/test_vocab.py -k refs -v`
Expected: FAIL (`refs` command not recognized, returns "unknown command")

- [ ] **Step 3: Implement path extraction, classification, and `cmd_refs`**

Add to `skills/coding/capture-vocab/scripts/vocab.py` (after `bidir_match`, before `cmd_lookup`):

```python
PATH_CANDIDATE_RE = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_./-]*(?::\d+)?')


def _is_path_like(token):
    if '/' in token:
        return True
    return bool(re.match(r'^[\w.\-]+\.[A-Za-z0-9]+(:\d+)?$', token))


def extract_paths(ref_raw):
    return [t for t in PATH_CANDIDATE_RE.findall(ref_raw) if _is_path_like(t)]


def _strip_line_suffix(path):
    return re.sub(r':\d+$', '', path)


def classify_path(query, candidate):
    q = _strip_line_suffix(query)
    c = _strip_line_suffix(candidate)
    if q == c:
        return "same-file"
    if c.endswith('/') and q.startswith(c):
        return "dir-contains"
    if q.endswith('/') and c.startswith(q):
        return "dir-contains"
    return None
```

Add `cmd_refs` after `cmd_list`:

```python
def cmd_refs(sections, query_path):
    found = False
    for sec in sections:
        for candidate in extract_paths(sec['ref_raw']):
            tier = classify_path(query_path, candidate)
            if tier:
                print(f"{sec['name']} | {tier} | {candidate}")
                found = True
    if not found:
        print(f"no refs: {query_path}")
        return 1
    return 0
```

Wire it into `main()` — replace the `print(f"unknown command: {cmd}")` fallback block with:

```python
    if cmd == "refs":
        if len(argv) < 2:
            print("usage: vocab.py refs <path>")
            return 2
        return cmd_refs(sections, argv[1])
    print(f"unknown command: {cmd}")
    return 2
```

- [ ] **Step 4: Run tests, fix until green**

Run: `cd skills/coding/capture-vocab && python3 -m pytest tests/ -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add skills/coding/capture-vocab/scripts/vocab.py skills/coding/capture-vocab/tests/test_vocab.py
git commit -m "feat(capture-vocab): add vocab.py refs sub-command with same-file/dir-contains classification"
```

---

### Task 3: Rewrite `SKILL.md`

**Files:**
- Modify: `skills/coding/capture-vocab/SKILL.md`

**Interfaces:**
- Consumes: nothing from prior tasks at runtime (this is instruction text, not code) — but must accurately describe the `vocab.py` CLI contract built in Tasks 1–2, and must match the `add` flow in spec §4.3.

- [ ] **Step 1: Replace frontmatter version**

In `skills/coding/capture-vocab/SKILL.md`, change:

```yaml
version: "1.1.2"
```

to:

```yaml
version: "1.2.0"
```

- [ ] **Step 2: Replace the `query` section**

Replace the existing `### query \`<term>\`` section (lines 65–70 of the current file) with:

```markdown
### query `<term>`

1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<term>"`
2. exit 0：按输出的 section 定义回答
3. exit 1：跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py list`，列出全部术语名供用户挑选
4. exit 2 或脚本不可用（如 python3 缺失）：退回读取整份 `.hskill/capture-vocab/vocab.md`，用 `## <term>` 标题手动定位（大小写不敏感）
```

- [ ] **Step 3: Replace the `add` section**

Replace the existing `### add \`<term>\`` section with:

```markdown
### add `<term>`

**分层查重，按成本从低到高，严格顺序：**

1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<term>"`。命中（exit 0）→ 输出"术语 '<term>' 已存在，请用 `update` 修改"并退出
2. 从当前对话上下文推断该词的**定义 / Avoid / Reference**（Reference 留空则跳过第 3 层）
3. 对推断出的每个 Reference 路径，跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py refs "<path>"`，收集分档候选（`same-file` / `dir-contains`）
4. **仅当第 1、3 步均空手**（`lookup` 未命中 且 `refs` 无候选）时，才跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py list`，人工比对全量术语名+别名找语义相近候选；否则跳过这一步，不付这个 O(N) 成本
5. 对已得到的候选（第 3 或第 4 步产出的）逐个 `lookup` 取完整定义，**必须显式判一个结论并说给用户**，三选一：
   - **同一实体两个名字** → 建议改用 `update`，把新叫法并进该条目的 `_Avoid_`
   - **父子实体各有其名** → 正常新增，建议在两条定义里互相点名
   - **无关** → 正常新增
6. 展示条目 + 查重结论，等用户确认（`y` 或直接输入修改内容）
7. 若目录 `.hskill/capture-vocab/` 不存在，创建它；若 `vocab.md` 不存在，创建并写入 `# Domain Vocabulary\n`
8. 在文件末尾追加新 section，Avoid/Reference 为空时省略对应行

**退路**：`vocab.py` 不存在或 python3 不可用时，退回读取整份 `vocab.md` 手动检查 `## <term>` 是否已存在，跳过第 3/4 层查重（无法自动化），仅凭对话上下文判断是否重复。
```

- [ ] **Step 4: Replace the `update` / `remove` sections' lookup step**

In `### update \`<term>\``, replace step 1:

```markdown
1. 检查词汇表存在且包含该术语；若文件不存在或术语不存在，输出对应错误后退出
```

with:

```markdown
1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<term>"` 确认存在；exit 1 或 2 → 输出对应错误后退出
```

In `### remove \`<term>\``, replace step 1:

```markdown
1. 检查词汇表存在且包含该术语；若不存在，输出对应错误后退出
```

with:

```markdown
1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<term>"` 确认存在；exit 1 或 2 → 输出对应错误后退出
```

- [ ] **Step 5: Replace the "Agent 加载约定" section**

Replace the final section with:

```markdown
## Agent 加载约定

**不要在 session 开始时读取整份 `vocab.md`。** 在项目 `CLAUDE.md` 中加入：

\`\`\`markdown
## 术语澄清

遇到定义含糊的词或特殊称谓，不要凭猜测理解。跑：

    python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<词或整句>"

exit 0：按吐出来的词条定义理解。
exit 1（`no match`）：没有定义，按字面理解，不必追问。
输出 `N matches: ...`：命中太多，挑最相关的再 lookup 一次。
exit 2 或脚本不可用：才退回 grep `.hskill/capture-vocab/vocab.md`，
不要把整篇文档读进上下文。
\`\`\`

两条触发判据：(1) 用户消息里出现不像通用软件概念、像本项目自造的名词；(2) 要在回复、文档或 commit message 里首次使用某个项目名词时（避免用上 `_Avoid_` 里的旧叫法）。这条路径完全绕开本 skill——不 invoke、不读这份 SKILL.md，成本只是那次脚本调用的输出。
```

- [ ] **Step 6: Verify the rewritten file reads coherently**

Run: `cat skills/coding/capture-vocab/SKILL.md`
Expected: version `1.2.0`; add/query/update/remove all reference `vocab.py`; add's 3-layer dedup order matches spec §4.3 exactly; Agent 加载约定 gives the copy-pasteable `CLAUDE.md` block from spec §5.1.

- [ ] **Step 7: Commit**

```bash
git add skills/coding/capture-vocab/SKILL.md
git commit -m "docs(capture-vocab): rewrite add/query/update/remove around vocab.py, bump to 1.2.0"
```

---

### Task 4: `skills-index.json` version bump and full verification

**Files:**
- Modify: `skills-index.json`

**Interfaces:** None — terminal task.

- [ ] **Step 1: Bump `contentVersion`**

In `skills-index.json`, in the `coding/capture-vocab` entry, change:

```json
"contentVersion": "1.1.2"
```

to:

```json
"contentVersion": "1.2.0"
```

Leave `contentHash`, `path`, `bundle`, `installScope` untouched (contentHash algorithm is unverified — see handoff doc's 验证步骤 section).

- [ ] **Step 2: Run the full test suite without piping**

Run: `npm test`
Expected: exit code 0. Check with `echo $?` immediately after — do not pipe through `tail` or any other command.

- [ ] **Step 3: Run the pytest collection count check**

Run: `python3 -m pytest skills/coding/capture-vocab/tests/ --collect-only -q`
Expected: collects at least 11 items (spec §6 lists ~16 distinct assertions across fewer test functions is also acceptable as long as count ≥ 11).

- [ ] **Step 4: Verify agent-canvas repo untouched**

Run: `git -C /Users/harveyzhang96/Projects/agent-canvas status --short`
Expected: empty output. If non-empty, confirm (by comparing against the pre-work baseline already captured in the handoff doc's acceptance anchor #12) that it predates this work and is unrelated.

- [ ] **Step 5: Verify no stray `.hskill/` changes in this repo**

Run: `git diff --name-only staging..HEAD`
Expected: no path under `.hskill/` appears (the handoff doc's own commit is fine, it lives under `docs/commute/`; the spec doc under `docs/superpowers/specs/`).

- [ ] **Step 6: Commit**

```bash
git add skills-index.json
git commit -m "chore(capture-vocab): bump contentVersion to 1.2.0"
```
