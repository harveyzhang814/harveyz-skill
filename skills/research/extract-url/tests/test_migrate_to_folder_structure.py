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
