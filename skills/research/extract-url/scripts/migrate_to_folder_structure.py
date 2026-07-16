#!/usr/bin/env python3
"""
Migrate extract-url Vault from flat structure (root .md + Origin/ + shared Image/)
to per-article folders (<hash8>/{Origin,Translation,Image}/).

Usage:
  python3 migrate_to_folder_structure.py plan
  python3 migrate_to_folder_structure.py apply [--no-backup]
  python3 migrate_to_folder_structure.py find-merges
  python3 migrate_to_folder_structure.py apply-merge --keep <hash8> --drop <hash8>

Reads VAULT_PATH from ~/.hskill/url-extract/config.json (via config.get_vault_path()).
"""
import argparse, os, re, shutil, sqlite3, sys, tarfile, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from config import get_vault_path, get_url_hash

_IMG_RE = re.compile(r'!\[([^\]]*)\]\(\.{0,2}/?Image/([^)]+)\)')
_WIKILINK_RE = re.compile(r'\[\[Origin/([^\]]+)\]\]')
_HASH_PREFIX_RE = re.compile(r'^[0-9a-f]{8}_(img_\d+\..+)$')


def _read_frontmatter(path):
    text = Path(path).read_text(encoding='utf-8')
    if not text.startswith('---'):
        return {}
    parts = text.split('---', 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _extract_origin_link_target(content):
    m = _WIKILINK_RE.search(content)
    if not m:
        return None
    name = m.group(1)
    if not name.endswith('.md'):
        name += '.md'
    return name


def _extract_image_filenames(content):
    return [m.group(2) for m in _IMG_RE.finditer(content)]


def _strip_hash_prefix(filename):
    m = _HASH_PREFIX_RE.match(filename)
    return m.group(1) if m else filename


def _rewrite_image_refs(content, filename_map):
    def _sub(m):
        alt, old_name = m.group(1), m.group(2)
        new_name = filename_map.get(old_name, old_name)
        return f'![{alt}](../Image/{new_name})'
    return _IMG_RE.sub(_sub, content)


def _rewrite_wikilink(content, url_hash, origin_filename):
    new_link = f'[[{url_hash}/Origin/{origin_filename}]]'
    return _WIKILINK_RE.sub(new_link, content, count=1)


def _scan_dir(dir_path, pattern='*.md'):
    entries = []
    dir_path = Path(dir_path)
    if not dir_path.exists():
        return entries
    for p in sorted(dir_path.glob(pattern)):
        if '.sync-conflict-' in p.name:
            continue
        fm = _read_frontmatter(p)
        entries.append({'path': p, 'source_url': fm.get('source_url'), 'frontmatter': fm})
    return entries


def _find_orphan_images(vault_path, origin_entries, translation_entries):
    referenced = set()
    for e in origin_entries + translation_entries:
        content = e['path'].read_text(encoding='utf-8')
        referenced.update(_extract_image_filenames(content))
    image_dir = Path(vault_path) / 'Image'
    if not image_dir.exists():
        return []
    all_images = {p.name for p in image_dir.glob('*') if p.is_file()}
    return sorted(all_images - referenced)


def build_plan(vault_path):
    vault_path = Path(vault_path)
    origin_entries = _scan_dir(vault_path / 'Origin')
    translation_entries = _scan_dir(vault_path, pattern='*.md')

    anomalies = {'missing_source_url': [], 'link_url_mismatch': [], 'missing_link': [], 'duplicate_source_url': []}

    origin_by_url = {}
    for e in origin_entries:
        if not e['source_url']:
            anomalies['missing_source_url'].append(str(e['path']))
            continue
        if e['source_url'] in origin_by_url:
            anomalies['duplicate_source_url'].append({
                'kind': 'origin',
                'source_url': e['source_url'],
                'kept': str(origin_by_url[e['source_url']]['path']),
                'dropped': str(e['path']),
            })
        else:
            origin_by_url[e['source_url']] = e

    translation_by_url = {}
    for e in translation_entries:
        if not e['source_url']:
            anomalies['missing_source_url'].append(str(e['path']))
            continue
        if e['source_url'] in translation_by_url:
            anomalies['duplicate_source_url'].append({
                'kind': 'translation',
                'source_url': e['source_url'],
                'kept': str(translation_by_url[e['source_url']]['path']),
                'dropped': str(e['path']),
            })
            continue
        translation_by_url[e['source_url']] = e

        content = e['path'].read_text(encoding='utf-8')
        link_target = _extract_origin_link_target(content)
        if link_target is None:
            anomalies['missing_link'].append(str(e['path']))
            continue
        linked_origin_path = vault_path / 'Origin' / link_target
        if not linked_origin_path.exists():
            anomalies['missing_link'].append(str(e['path']))
            continue
        linked_fm = _read_frontmatter(linked_origin_path)
        if linked_fm.get('source_url') != e['source_url']:
            anomalies['link_url_mismatch'].append({
                'translation': str(e['path']),
                'linked_origin': str(linked_origin_path),
                'translation_url': e['source_url'],
                'linked_origin_url': linked_fm.get('source_url'),
            })

    all_urls = set(origin_by_url) | set(translation_by_url)
    complete, partial = [], []
    for url in sorted(all_urls):
        origin_e = origin_by_url.get(url)
        translation_e = translation_by_url.get(url)
        entry = {
            'source_url': url,
            'url_hash': get_url_hash(url),
            'origin': origin_e,
            'translation': translation_e,
        }
        (complete if (origin_e and translation_e) else partial).append(entry)

    return {
        'complete': complete,
        'partial': partial,
        'anomalies': anomalies,
        'orphan_images': _find_orphan_images(vault_path, origin_entries, translation_entries),
    }


def _migrate_entry(vault_path, entry):
    url_hash = entry['url_hash']
    article_dir = Path(vault_path) / url_hash
    origin_e = entry['origin']
    translation_e = entry['translation']

    origin_content = origin_e['path'].read_text(encoding='utf-8') if origin_e else ''
    translation_content = translation_e['path'].read_text(encoding='utf-8') if translation_e else ''

    image_filename_map = {}
    for content in (origin_content, translation_content):
        for old_name in _extract_image_filenames(content):
            image_filename_map[old_name] = _strip_hash_prefix(old_name)

    if image_filename_map:
        image_dir = article_dir / 'Image'
        image_dir.mkdir(parents=True, exist_ok=True)
        src_image_dir = Path(vault_path) / 'Image'
        for old_name, new_name in image_filename_map.items():
            src = src_image_dir / old_name
            if src.exists():
                shutil.move(str(src), str(image_dir / new_name))

    if origin_e:
        origin_dir = article_dir / 'Origin'
        origin_dir.mkdir(parents=True, exist_ok=True)
        new_content = _rewrite_image_refs(origin_content, image_filename_map)
        target = origin_dir / origin_e['path'].name
        target.write_text(new_content, encoding='utf-8')
        origin_e['path'].unlink()
        entry['new_origin_path'] = str(target)

    if translation_e:
        translation_dir = article_dir / 'Translation'
        translation_dir.mkdir(parents=True, exist_ok=True)
        new_content = _rewrite_image_refs(translation_content, image_filename_map)
        if origin_e:
            new_content = _rewrite_wikilink(new_content, url_hash, origin_e['path'].name)
        target = translation_dir / translation_e['path'].name
        target.write_text(new_content, encoding='utf-8')
        translation_e['path'].unlink()
        entry['new_translation_path'] = str(target)


def _rebuild_db(db_path, plan):
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS url_index (
            source_url   TEXT PRIMARY KEY,
            title        TEXT,
            fetched_at   TEXT,
            issues       TEXT,
            category     TEXT,
            origin_path  TEXT,
            article_path TEXT
        )
    """)
    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    for entry in plan['complete'] + plan['partial']:
        if 'new_origin_path' not in entry and 'new_translation_path' not in entry:
            continue
        origin_e = entry.get('origin')
        translation_e = entry.get('translation')
        fm = (translation_e or origin_e)['frontmatter']
        title_path = entry.get('new_translation_path') or entry.get('new_origin_path')
        conn.execute(
            "INSERT OR REPLACE INTO url_index "
            "(source_url, title, fetched_at, issues, category, origin_path, article_path) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                entry['source_url'], Path(title_path).stem, fetch_date, '',
                fm.get('category') or '',
                entry.get('new_origin_path') or '',
                entry.get('new_translation_path') or '',
            )
        )
    conn.commit()
    conn.close()


def apply_plan(vault_path, plan, db_path):
    moved, failed = [], []
    for entry in plan['complete'] + plan['partial']:
        try:
            _migrate_entry(vault_path, entry)
            moved.append(entry['source_url'])
        except Exception as exc:
            failed.append({'source_url': entry['source_url'], 'error': str(exc)})

    _rebuild_db(db_path, plan)
    return {'moved': moved, 'failed': failed}


def _backup_vault(vault_path):
    vault_path = Path(vault_path)
    ts = time.strftime('%Y%m%d-%H%M%S')
    backup_path = vault_path.parent / f'{vault_path.name}-backup-{ts}.tar.gz'
    with tarfile.open(backup_path, 'w:gz') as tar:
        tar.add(vault_path, arcname=vault_path.name)
    return str(backup_path)


def _normalize_url(url):
    p = urlparse(url or '')
    netloc = p.netloc.lower()
    path = p.path.rstrip('/')
    query = '&'.join(
        kv for kv in p.query.split('&')
        if kv and not kv.split('=')[0].startswith('utm_')
    )
    normalized = f'{netloc}{path}'
    if query:
        normalized += f'?{query}'
    return normalized


def find_merge_candidates(vault_path):
    vault_path = Path(vault_path)
    partial_folders = []
    for d in sorted(vault_path.iterdir()):
        if not d.is_dir() or len(d.name) != 8:
            continue
        has_origin = (d / 'Origin').exists() and any((d / 'Origin').glob('*.md'))
        has_translation = (d / 'Translation').exists() and any((d / 'Translation').glob('*.md'))
        if has_origin and not has_translation:
            side = 'origin'
        elif has_translation and not has_origin:
            side = 'translation'
        else:
            continue
        sub = 'Origin' if side == 'origin' else 'Translation'
        md_file = next((d / sub).glob('*.md'))
        fm = _read_frontmatter(md_file)
        partial_folders.append({
            'hash': d.name, 'side': side, 'path': str(md_file),
            'source_url': fm.get('source_url', ''),
        })

    candidates = []
    for i, a in enumerate(partial_folders):
        for b in partial_folders[i + 1:]:
            if a['side'] == b['side']:
                continue
            if _normalize_url(a['source_url']) == _normalize_url(b['source_url']):
                candidates.append({'a': a, 'b': b})
    return candidates


def apply_merge(vault_path, keep_hash, drop_hash):
    vault_path = Path(vault_path)
    keep_dir = vault_path / keep_hash
    drop_dir = vault_path / drop_hash

    for side in ('Origin', 'Translation'):
        src_dir = drop_dir / side
        if not src_dir.exists():
            continue
        dst_dir = keep_dir / side
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in src_dir.glob('*.md'):
            shutil.move(str(f), str(dst_dir / f.name))

    drop_image_dir = drop_dir / 'Image'
    if drop_image_dir.exists():
        keep_image_dir = keep_dir / 'Image'
        keep_image_dir.mkdir(parents=True, exist_ok=True)
        for f in drop_image_dir.glob('*'):
            shutil.move(str(f), str(keep_image_dir / f.name))

    shutil.rmtree(drop_dir, ignore_errors=True)

    translation_files = list((keep_dir / 'Translation').glob('*.md')) if (keep_dir / 'Translation').exists() else []
    origin_files = list((keep_dir / 'Origin').glob('*.md')) if (keep_dir / 'Origin').exists() else []
    if translation_files and origin_files:
        t_path = translation_files[0]
        content = t_path.read_text(encoding='utf-8')
        content = _rewrite_wikilink(content, keep_hash, origin_files[0].name)
        t_path.write_text(content, encoding='utf-8')


def _print_plan_summary(plan):
    print(f"完整配对：{len(plan['complete'])}")
    print(f"部分完成：{len(plan['partial'])}")
    for k, v in plan['anomalies'].items():
        print(f"异常[{k}]：{len(v)}")
    print(f"孤儿图片：{len(plan['orphan_images'])}")


def main():
    parser = argparse.ArgumentParser(description='Migrate extract-url Vault to per-article folder structure')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('plan')
    p_apply = sub.add_parser('apply')
    p_apply.add_argument('--no-backup', action='store_true')
    sub.add_parser('find-merges')
    p_merge = sub.add_parser('apply-merge')
    p_merge.add_argument('--keep', required=True)
    p_merge.add_argument('--drop', required=True)

    args = parser.parse_args()
    vault_path = get_vault_path()
    db_path = os.path.join(vault_path, 'url-index.db')

    if args.command == 'plan':
        _print_plan_summary(build_plan(vault_path))
    elif args.command == 'apply':
        plan = build_plan(vault_path)
        _print_plan_summary(plan)
        if not args.no_backup:
            print(f'备份已创建：{_backup_vault(vault_path)}')
        result = apply_plan(vault_path, plan, db_path)
        print(f"迁移完成：{len(result['moved'])} 篇成功，{len(result['failed'])} 篇失败")
        for f in result['failed']:
            print(f"  失败：{f['source_url']} - {f['error']}")
    elif args.command == 'find-merges':
        candidates = find_merge_candidates(vault_path)
        if not candidates:
            print('未发现合并候选')
        for c in candidates:
            print(f"候选：{c['a']['hash']} ({c['a']['side']}) <-> {c['b']['hash']} ({c['b']['side']})")
            print(f"  URL A: {c['a']['source_url']}")
            print(f"  URL B: {c['b']['source_url']}")
    elif args.command == 'apply-merge':
        apply_merge(vault_path, args.keep, args.drop)
        print(f'已合并 {args.drop} → {args.keep}')


if __name__ == '__main__':
    main()
