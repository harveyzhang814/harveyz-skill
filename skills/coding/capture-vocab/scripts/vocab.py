#!/usr/bin/env python3
import re
import sys
from pathlib import Path

HEADER_RE = re.compile(r'^## (.+)$', re.MULTILINE)
TRAILING_PAREN_RE = re.compile(r'[（(][^）)]*[）)]\s*$')
PATH_CANDIDATE_RE = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_./-]*(?::\d+)?')


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


def _split_top_level(s):
    parts = []
    buf = []
    depth = 0
    for ch in s:
        if ch in '（(':
            depth += 1
            buf.append(ch)
        elif ch in '）)':
            depth = max(0, depth - 1)
            buf.append(ch)
        elif depth == 0 and ch in ',，;；、':
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append(''.join(buf))
    return parts


def extract_aliases(avoid_raw):
    aliases = []
    for part in _split_top_level(avoid_raw):
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
        aliases = extract_aliases(sec['avoid_raw'])
        if aliases:
            print(f"{sec['name']} | {','.join(aliases)}")
        else:
            print(sec['name'])
    return 0


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
    if cmd == "refs":
        if len(argv) < 2:
            print("usage: vocab.py refs <path>")
            return 2
        return cmd_refs(sections, argv[1])
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
