import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'
SCRIPT = str(SCRIPTS_DIR / 'count_article_stats.py')

_ARTICLE = """\
---
title: Test Article
description: Test description.
---

Body text here.

```python
print("hello")
```

```bash
echo "world"
```

![img1](Image/img1.png)
![img2](Image/img2.png)
"""


def _parse(stdout: str) -> dict:
    result = {}
    for line in stdout.strip().splitlines():
        k, v = line.split(':', 1)
        result[k.strip()] = int(v.strip())
    return result


def test_counts_code_and_images(tmp_path):
    f = tmp_path / 'article.md'
    f.write_text(_ARTICLE, encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = _parse(r.stdout)
    assert d['CODE_BLOCKS'] == 2
    assert d['IMAGES'] == 2


def test_chars_exclude_frontmatter(tmp_path):
    f = tmp_path / 'article.md'
    f.write_text(_ARTICLE, encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    d = _parse(r.stdout)
    expected_body = _ARTICLE.split('---\n', 2)[2]
    assert d['CHARS'] == len(expected_body)


def test_no_code_no_images(tmp_path):
    f = tmp_path / 'plain.md'
    f.write_text('---\ntitle: X\n---\n\nJust plain text.\n', encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    d = _parse(r.stdout)
    assert d['CODE_BLOCKS'] == 0
    assert d['IMAGES'] == 0


def test_missing_file_exits_nonzero(tmp_path):
    r = subprocess.run(['python3', SCRIPT, str(tmp_path / 'missing.md')],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert 'not found' in r.stderr


def test_no_frontmatter(tmp_path):
    body = 'Just text, no frontmatter.\n'
    f = tmp_path / 'nofm.md'
    f.write_text(body, encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    assert r.returncode == 0
    d = _parse(r.stdout)
    assert d['CHARS'] == len(body)


def test_frontmatter_without_trailing_newline(tmp_path):
    # Frontmatter regex requires '\n' after closing '---'; without it,
    # stripping is skipped and the whole file is counted as body.
    content = '---\ntitle: X\n---'  # no trailing newline
    f = tmp_path / 'noeol.md'
    f.write_text(content, encoding='utf-8')
    r = subprocess.run(['python3', SCRIPT, str(f)], capture_output=True, text=True)
    assert r.returncode == 0
    d = _parse(r.stdout)
    # Whole file treated as body (no stripping) — documented fallback behavior
    assert d['CHARS'] == len(content)
