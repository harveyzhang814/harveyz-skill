import sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
import migrate_to_folder_structure as migrate

ORIGIN_TMPL = """---
publish_date: 2026-01-01
fetch_date: 2026-01-02
author: Test Author
source_url: {url}
origin_title: "{title}"
---

# {title}

Body text here.
{img_line}
"""

TRANSLATION_TMPL = """---
publish_date: 2026-01-01
fetch_date: 2026-01-02
author: Test Author
source_url: {url}
origin_title: "{title}"
tags: []
description: A test article.
---

{wikilink}

---

# {title}（译文）

正文内容。
{img_line}
"""


def _make_vault(tmp_path):
    vault = tmp_path / 'vault'
    (vault / 'Origin').mkdir(parents=True)
    (vault / 'Image').mkdir(parents=True)
    return vault


def _write_pair(vault, url, title, filename, image_names=None,
                 wikilink_target=None, translation_filename=None):
    image_names = image_names or []
    img_line = '\n'.join(f'![](Image/{n})' for n in image_names)
    origin_content = ORIGIN_TMPL.format(url=url, title=title, img_line=img_line)
    (vault / 'Origin' / f'{filename}.md').write_text(origin_content, encoding='utf-8')

    for n in image_names:
        (vault / 'Image' / n).write_bytes(b'fake-image-bytes')

    t_filename = translation_filename or filename
    wikilink = f'[[Origin/{wikilink_target or filename}.md]]'
    translation_content = TRANSLATION_TMPL.format(url=url, title=title, wikilink=wikilink, img_line=img_line)
    (vault / f'{t_filename}.md').write_text(translation_content, encoding='utf-8')


def test_build_plan_pairs_complete_article(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/a', 'Article A', 'article-a',
                image_names=['abcd1234_img_1.jpg'])

    plan = migrate.build_plan(vault)

    assert len(plan['complete']) == 1
    assert len(plan['partial']) == 0
    assert plan['complete'][0]['source_url'] == 'https://example.com/a'
    assert plan['complete'][0]['url_hash'] == migrate.get_url_hash('https://example.com/a')


def test_build_plan_pairs_by_own_url_even_if_filename_differs(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/b', 'Article B', 'article-b',
                translation_filename='article-b-translated-title')

    plan = migrate.build_plan(vault)

    assert len(plan['complete']) == 1
    assert plan['complete'][0]['origin']['path'].name == 'article-b.md'
    assert plan['complete'][0]['translation']['path'].name == 'article-b-translated-title.md'


def test_build_plan_detects_partial_origin_only(tmp_path):
    vault = _make_vault(tmp_path)
    origin_content = ORIGIN_TMPL.format(url='https://example.com/c', title='Article C', img_line='')
    (vault / 'Origin' / 'article-c.md').write_text(origin_content, encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['partial']) == 1
    assert plan['partial'][0]['origin'] is not None
    assert plan['partial'][0]['translation'] is None


def test_build_plan_detects_partial_translation_only(tmp_path):
    vault = _make_vault(tmp_path)
    translation_content = TRANSLATION_TMPL.format(
        url='https://example.com/d', title='Article D', wikilink='[[Origin/article-d.md]]', img_line=''
    )
    (vault / 'article-d.md').write_text(translation_content, encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['partial']) == 1
    assert plan['partial'][0]['translation'] is not None
    assert plan['partial'][0]['origin'] is None
    assert plan['anomalies']['missing_link'] == [str(vault / 'article-d.md')]


def test_build_plan_flags_missing_source_url(tmp_path):
    vault = _make_vault(tmp_path)
    (vault / 'Origin' / 'no-url.md').write_text('---\ntitle: x\n---\nbody', encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert str(vault / 'Origin' / 'no-url.md') in plan['anomalies']['missing_source_url']
    assert len(plan['complete']) == 0
    assert len(plan['partial']) == 0


def test_build_plan_flags_link_url_mismatch(tmp_path):
    vault = _make_vault(tmp_path)
    origin_content = ORIGIN_TMPL.format(url='https://example.com/e-origin', title='Article E', img_line='')
    (vault / 'Origin' / 'article-e.md').write_text(origin_content, encoding='utf-8')
    translation_content = TRANSLATION_TMPL.format(
        url='https://example.com/e-translation', title='Article E',
        wikilink='[[Origin/article-e.md]]', img_line=''
    )
    (vault / 'article-e.md').write_text(translation_content, encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['anomalies']['link_url_mismatch']) == 1
    mismatch = plan['anomalies']['link_url_mismatch'][0]
    assert mismatch['translation_url'] == 'https://example.com/e-translation'
    assert mismatch['linked_origin_url'] == 'https://example.com/e-origin'
    assert len(plan['partial']) == 2


def test_build_plan_skips_sync_conflict_files(tmp_path):
    vault = _make_vault(tmp_path)
    (vault / 'article-f.sync-conflict-20260101-abc.md').write_text('irrelevant', encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['complete']) == 0
    assert len(plan['partial']) == 0
    assert all(v == [] for v in plan['anomalies'].values())


def test_build_plan_finds_orphan_images(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/g', 'Article G', 'article-g',
                image_names=['abcd1234_img_1.jpg'])
    (vault / 'Image' / 'orphan_img.jpg').write_bytes(b'orphan')

    plan = migrate.build_plan(vault)

    assert plan['orphan_images'] == ['orphan_img.jpg']


def test_apply_plan_moves_files_strips_hash_prefix_and_rewrites_links(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/h', 'Article H', 'article-h',
                image_names=['deadbeef_img_1.jpg'])
    plan = migrate.build_plan(vault)
    db_path = vault / 'url-index.db'

    result = migrate.apply_plan(vault, plan, db_path)

    assert result['failed'] == []
    url_hash = migrate.get_url_hash('https://example.com/h')
    article_dir = vault / url_hash

    origin_file = article_dir / 'Origin' / 'article-h.md'
    translation_file = article_dir / 'Translation' / 'article-h.md'
    image_file = article_dir / 'Image' / 'img_1.jpg'
    assert origin_file.exists()
    assert translation_file.exists()
    assert image_file.exists()
    assert not (vault / 'Origin' / 'article-h.md').exists()
    assert not (vault / 'article-h.md').exists()
    assert not (vault / 'Image' / 'deadbeef_img_1.jpg').exists()

    origin_content = origin_file.read_text(encoding='utf-8')
    translation_content = translation_file.read_text(encoding='utf-8')
    assert '![](../Image/img_1.jpg)' in origin_content
    assert '![](../Image/img_1.jpg)' in translation_content
    assert f'[[{url_hash}/Origin/article-h.md]]' in translation_content


def test_apply_plan_writes_url_index_db(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/i', 'Article I', 'article-i')
    plan = migrate.build_plan(vault)
    db_path = vault / 'url-index.db'

    migrate.apply_plan(vault, plan, db_path)

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        'SELECT origin_path, article_path FROM url_index WHERE source_url=?',
        ('https://example.com/i',)
    ).fetchone()
    conn.close()
    assert row is not None
    url_hash = migrate.get_url_hash('https://example.com/i')
    assert row[0] == str(vault / url_hash / 'Origin' / 'article-i.md')
    assert row[1] == str(vault / url_hash / 'Translation' / 'article-i.md')


def test_apply_plan_is_idempotent_on_rerun(tmp_path):
    vault = _make_vault(tmp_path)
    _write_pair(vault, 'https://example.com/j', 'Article J', 'article-j')
    db_path = vault / 'url-index.db'

    plan1 = migrate.build_plan(vault)
    migrate.apply_plan(vault, plan1, db_path)

    plan2 = migrate.build_plan(vault)
    assert plan2['complete'] == []
    assert plan2['partial'] == []
    result2 = migrate.apply_plan(vault, plan2, db_path)
    assert result2['moved'] == []
    assert result2['failed'] == []


def test_build_plan_flags_duplicate_source_url_and_keeps_first(tmp_path):
    vault = _make_vault(tmp_path)
    url = 'https://example.com/dup'
    origin1 = ORIGIN_TMPL.format(url=url, title='Dup Article One', img_line='')
    (vault / 'Origin' / 'dup-article-one.md').write_text(origin1, encoding='utf-8')
    origin2 = ORIGIN_TMPL.format(url=url, title='Dup Article Two', img_line='')
    (vault / 'Origin' / 'dup-article-two.md').write_text(origin2, encoding='utf-8')

    plan = migrate.build_plan(vault)

    assert len(plan['anomalies']['duplicate_source_url']) == 1
    dup = plan['anomalies']['duplicate_source_url'][0]
    assert dup['kind'] == 'origin'
    assert dup['source_url'] == url
    assert dup['kept'] == str(vault / 'Origin' / 'dup-article-one.md')
    assert dup['dropped'] == str(vault / 'Origin' / 'dup-article-two.md')
    # exactly one partial entry created (for the kept file), the dropped one is absent from the plan
    matching = [e for e in plan['partial'] if e['source_url'] == url]
    assert len(matching) == 1
    assert matching[0]['origin']['path'].name == 'dup-article-one.md'


def _make_partial_article_folder(vault, url, title, side):
    url_hash = migrate.get_url_hash(url)
    article_dir = vault / url_hash
    sub = 'Origin' if side == 'origin' else 'Translation'
    (article_dir / sub).mkdir(parents=True)
    content = ORIGIN_TMPL.format(url=url, title=title, img_line='')
    filename = title.lower().replace(' ', '-') + '.md'
    (article_dir / sub / filename).write_text(content, encoding='utf-8')
    return url_hash


def test_find_merge_candidates_matches_normalized_urls(tmp_path):
    vault = _make_vault(tmp_path)
    hash_a = _make_partial_article_folder(
        vault, 'https://example.com/l?utm_source=newsletter', 'Article L', 'origin')
    hash_b = _make_partial_article_folder(vault, 'https://example.com/l', 'Article L', 'translation')

    candidates = migrate.find_merge_candidates(vault)

    assert len(candidates) == 1
    hashes = {candidates[0]['a']['hash'], candidates[0]['b']['hash']}
    assert hashes == {hash_a, hash_b}


def test_find_merge_candidates_ignores_same_side_pairs(tmp_path):
    vault = _make_vault(tmp_path)
    _make_partial_article_folder(vault, 'https://example.com/m', 'Article M', 'origin')
    _make_partial_article_folder(vault, 'https://example.com/m-different', 'Article M2', 'origin')

    assert migrate.find_merge_candidates(vault) == []


def test_find_merge_candidates_no_match_returns_empty(tmp_path):
    vault = _make_vault(tmp_path)
    _make_partial_article_folder(vault, 'https://example.com/n1', 'Article N1', 'origin')
    _make_partial_article_folder(vault, 'https://example.com/n2', 'Article N2', 'translation')

    assert migrate.find_merge_candidates(vault) == []


def test_apply_merge_combines_origin_and_translation_folders(tmp_path):
    vault = _make_vault(tmp_path)
    hash_a = _make_partial_article_folder(
        vault, 'https://example.com/o?utm_source=x', 'Article O', 'origin')
    hash_b = _make_partial_article_folder(vault, 'https://example.com/o', 'Article O', 'translation')

    migrate.apply_merge(vault, keep_hash=hash_a, drop_hash=hash_b)

    assert (vault / hash_a / 'Origin').exists()
    assert (vault / hash_a / 'Translation').exists()
    assert not (vault / hash_b).exists()


def test_apply_merge_rewrites_wikilink_to_keep_hash(tmp_path):
    vault = _make_vault(tmp_path)
    url = 'https://example.com/p'
    hash_a = migrate.get_url_hash(url)
    (vault / hash_a / 'Origin').mkdir(parents=True)
    (vault / hash_a / 'Origin' / 'article-p.md').write_text(
        ORIGIN_TMPL.format(url=url, title='Article P', img_line=''), encoding='utf-8'
    )
    hash_b = migrate.get_url_hash(url + '?utm_source=x')
    (vault / hash_b / 'Translation').mkdir(parents=True)
    (vault / hash_b / 'Translation' / 'article-p.md').write_text(
        TRANSLATION_TMPL.format(
            url=url + '?utm_source=x', title='Article P',
            wikilink='[[Origin/some-other-name.md]]', img_line=''
        ),
        encoding='utf-8'
    )

    migrate.apply_merge(vault, keep_hash=hash_a, drop_hash=hash_b)

    merged_content = (vault / hash_a / 'Translation' / 'article-p.md').read_text(encoding='utf-8')
    assert f'[[{hash_a}/Origin/article-p.md]]' in merged_content


def test_apply_merge_renames_colliding_image_instead_of_overwriting(tmp_path):
    vault = _make_vault(tmp_path)
    url_a = 'https://example.com/q?utm_source=x'
    url_b = 'https://example.com/q'
    hash_a = migrate.get_url_hash(url_a)
    hash_b = migrate.get_url_hash(url_b)

    (vault / hash_a / 'Origin').mkdir(parents=True)
    (vault / hash_a / 'Origin' / 'article-q.md').write_text(
        ORIGIN_TMPL.format(url=url_a, title='Article Q', img_line=''), encoding='utf-8'
    )
    (vault / hash_a / 'Image').mkdir(parents=True)
    (vault / hash_a / 'Image' / 'img_1.jpg').write_bytes(b'ORIGIN_IMAGE_BYTES')

    (vault / hash_b / 'Translation').mkdir(parents=True)
    (vault / hash_b / 'Translation' / 'article-q.md').write_text(
        TRANSLATION_TMPL.format(url=url_b, title='Article Q', wikilink='[[Origin/article-q.md]]', img_line=''),
        encoding='utf-8'
    )
    (vault / hash_b / 'Image').mkdir(parents=True)
    (vault / hash_b / 'Image' / 'img_1.jpg').write_bytes(b'TRANSLATION_IMAGE_BYTES')

    migrate.apply_merge(vault, keep_hash=hash_a, drop_hash=hash_b)

    kept_image_dir = vault / hash_a / 'Image'
    images = {f.name: f.read_bytes() for f in kept_image_dir.glob('*')}
    assert len(images) == 2, f'expected both images preserved, got {list(images.keys())}'
    assert b'ORIGIN_IMAGE_BYTES' in images.values()
    assert b'TRANSLATION_IMAGE_BYTES' in images.values()


def test_apply_merge_rejects_same_hash(tmp_path):
    vault = _make_vault(tmp_path)
    hash_a = _make_partial_article_folder(vault, 'https://example.com/r', 'Article R', 'origin')
    import pytest
    with pytest.raises(ValueError):
        migrate.apply_merge(vault, keep_hash=hash_a, drop_hash=hash_a)


def test_apply_merge_moves_non_md_content_instead_of_deleting(tmp_path):
    """Regression: rmtree must not silently destroy content the move loop didn't glob for."""
    vault = _make_vault(tmp_path)
    hash_a = _make_partial_article_folder(vault, 'https://example.com/s?utm_source=x', 'Article S', 'origin')
    hash_b = _make_partial_article_folder(vault, 'https://example.com/s', 'Article S', 'translation')
    (vault / hash_b / 'Translation' / 'stray-note.txt').write_text('not markdown', encoding='utf-8')

    migrate.apply_merge(vault, keep_hash=hash_a, drop_hash=hash_b)

    assert (vault / hash_a / 'Translation' / 'stray-note.txt').exists()
