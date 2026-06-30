import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'references'))
from article_utils import load_fixed_tags, move_fixed_from_candidate, enforce_tag_separation


def test_load_fixed_tags_skips_comments_and_blanks(tmp_path):
    f = tmp_path / 'fixed_tags.txt'
    f.write_text('# topic\nloop-engineering\nai\n\n# language\nenglish\n', encoding='utf-8')
    assert load_fixed_tags(str(f)) == {'loop-engineering', 'ai', 'english'}


def test_load_fixed_tags_missing_file_returns_empty():
    assert load_fixed_tags('/nonexistent/path/fixed_tags.txt') == set()


def test_load_fixed_tags_strips_whitespace(tmp_path):
    f = tmp_path / 'fixed_tags.txt'
    f.write_text('  ai  \nloop-engineering\n', encoding='utf-8')
    assert load_fixed_tags(str(f)) == {'ai', 'loop-engineering'}


def test_move_fixed_from_candidate_moves_matching_tag():
    tags, cand = move_fixed_from_candidate(
        ['ai'], ['loop-engineering', 'productivity'], {'loop-engineering', 'ai'}
    )
    assert 'loop-engineering' in tags
    assert 'productivity' in cand
    assert 'loop-engineering' not in cand


def test_move_fixed_from_candidate_no_duplicates_in_tags():
    tags, cand = move_fixed_from_candidate(
        ['ai'], ['ai', 'productivity'], {'ai'}
    )
    assert tags.count('ai') == 1
    assert 'productivity' in cand


def test_move_fixed_from_candidate_empty_inputs():
    tags, cand = move_fixed_from_candidate([], [], {'loop-engineering'})
    assert tags == []
    assert cand == []


def test_move_fixed_from_candidate_no_match_leaves_all_in_candidate():
    tags, cand = move_fixed_from_candidate(
        [], ['novel-concept', 'another-tag'], {'loop-engineering'}
    )
    assert tags == []
    assert set(cand) == {'novel-concept', 'another-tag'}


_ARTICLE_WITH_CANDIDATE = """\
---
publish_date: 2026-01-01
fetch_date: 2026-01-01
author: Test Author
source_url: https://example.com/test
origin_title: "Test Article"
tags:
  - ai
candidate_tags:
  - loop-engineering
  - productivity
description: A test article.
---

[[Origin/test.md]]

---

Content here.
"""

def test_enforce_tag_separation_moves_fixed_from_candidate(tmp_path):
    article = tmp_path / 'article.md'
    article.write_text(_ARTICLE_WITH_CANDIDATE, encoding='utf-8')
    fixed = tmp_path / 'fixed_tags.txt'
    fixed.write_text('# topic\nloop-engineering\nai\n', encoding='utf-8')

    enforce_tag_separation(str(article), str(fixed))

    import yaml
    content = article.read_text(encoding='utf-8')
    parts = content.split('---', 2)
    fm = yaml.safe_load(parts[1])
    assert 'loop-engineering' in fm['tags']
    assert 'ai' in fm['tags']
    assert 'loop-engineering' not in fm.get('candidate_tags', [])
    assert 'productivity' in fm['candidate_tags']


def test_enforce_tag_separation_no_fixed_tags_file_is_noop(tmp_path):
    article = tmp_path / 'article.md'
    article.write_text(_ARTICLE_WITH_CANDIDATE, encoding='utf-8')
    original = article.read_text(encoding='utf-8')

    enforce_tag_separation(str(article), str(tmp_path / 'nonexistent.txt'))

    assert article.read_text(encoding='utf-8') == original


def test_enforce_tag_separation_no_candidate_tags_is_noop(tmp_path):
    content = """\
---
publish_date: 2026-01-01
fetch_date: 2026-01-01
author: Test Author
source_url: https://example.com/test
origin_title: "Test Article"
tags:
  - ai
description: A test article.
---

Content here.
"""
    article = tmp_path / 'article.md'
    article.write_text(content, encoding='utf-8')
    fixed = tmp_path / 'fixed_tags.txt'
    fixed.write_text('loop-engineering\nai\n', encoding='utf-8')
    original = article.read_text(encoding='utf-8')

    enforce_tag_separation(str(article), str(fixed))

    assert article.read_text(encoding='utf-8') == original


def test_enforce_tag_separation_no_overlap_is_noop(tmp_path):
    ft = tmp_path / "fixed_tags.txt"
    ft.write_text("loop-engineering\n")
    article = tmp_path / "article.md"
    content = "---\ntags: []\ncandidate_tags:\n  - productivity\n---\nBody\n"
    article.write_text(content, encoding="utf-8")
    enforce_tag_separation(str(article), str(ft))
    assert article.read_text(encoding="utf-8") == content
