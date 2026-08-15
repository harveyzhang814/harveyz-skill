import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'references'))
from article_utils import repair_frontmatter, record_fetch_issues, write_meta_json


def test_repair_frontmatter_skips_excluded_fields_from_remaining(tmp_path):
    fp = tmp_path / 'origin.md'
    fp.write_text(
        "---\npublish_date: 2026-01-01\nauthor: Someone\nsource_url: https://example.com/x\n"
        "origin_title: \"X\"\n---\n\nBody\n",
        encoding='utf-8'
    )
    fm, fixed, remaining = repair_frontmatter(fp, 'https://example.com/x', skip_remaining_fields={'description'})
    assert 'description空' not in remaining


def test_repair_frontmatter_still_flags_description_when_not_skipped(tmp_path):
    fp = tmp_path / 'origin.md'
    fp.write_text(
        "---\npublish_date: 2026-01-01\nauthor: Someone\nsource_url: https://example.com/x\n"
        "origin_title: \"X\"\n---\n\nBody\n",
        encoding='utf-8'
    )
    fm, fixed, remaining = repair_frontmatter(fp, 'https://example.com/x')
    assert 'description空' in remaining


def test_record_fetch_issues_writes_temp_file(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_dir.mkdir()
    record_fetch_issues('author空', article_dir)
    assert (article_dir / '.fetch_issues.tmp').read_text(encoding='utf-8') == 'author空'


def test_record_fetch_issues_clears_temp_file_when_no_issues(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_dir.mkdir()
    (article_dir / '.fetch_issues.tmp').write_text('stale issue', encoding='utf-8')
    record_fetch_issues('', article_dir)
    assert not (article_dir / '.fetch_issues.tmp').exists()


def test_write_meta_json_creates_file_with_expected_fields(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_dir.mkdir()
    article_path = article_dir / 'article.md'
    article_path.write_text("---\ncategory: tech\n---\n\nBody\n", encoding='utf-8')
    meta_path = article_dir / 'meta.json'

    write_meta_json('https://example.com/x', meta_path, article_path)

    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['source_url'] == 'https://example.com/x'
    assert meta['title'] == 'article.md'
    assert meta['category'] == 'tech'
    assert meta['issues'] == ''


def test_write_meta_json_merges_pending_fetch_issues(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_dir.mkdir()
    (article_dir / '.fetch_issues.tmp').write_text('author空', encoding='utf-8')
    article_path = article_dir / 'article.md'
    article_path.write_text("---\n---\n\nBody\n", encoding='utf-8')
    meta_path = article_dir / 'meta.json'

    write_meta_json('https://example.com/y', meta_path, article_path)

    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['issues'] == 'author空'
    assert not (article_dir / '.fetch_issues.tmp').exists()


def test_write_meta_json_creates_parent_dir_if_missing(tmp_path):
    article_dir = tmp_path / 'a1b2c3d4'
    article_path = tmp_path / 'article.md'
    article_path.write_text("---\n---\n\nBody\n", encoding='utf-8')
    meta_path = article_dir / 'meta.json'

    write_meta_json('https://example.com/z', meta_path, article_path)

    assert meta_path.exists()
