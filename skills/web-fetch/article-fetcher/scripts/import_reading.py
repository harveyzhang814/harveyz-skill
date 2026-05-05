#!/usr/bin/env python3
"""
一次性脚本：将 Reading 目录下（不含子文件夹）的 Markdown 文档
frontmatter 信息解析后存入 url-index.db。
"""
import sqlite3, os, re, glob

BASE_DIR = "{{VAULT_PATH}}"
DB_PATH  = os.path.expanduser("{{SKILL_DIR}}/scripts/url-index.db")

def parse_frontmatter(content):
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            fm[key.strip()] = val.strip()
    return fm

def extract_title(content, filepath):
    # 先从 frontmatter 读 title
    fm = parse_frontmatter(content)
    if fm.get('title'):
        return fm['title']
    # 再从文件名
    name = os.path.splitext(os.path.basename(filepath))[0]
    return name

conn = sqlite3.connect(DB_PATH)
files = glob.glob(os.path.join(BASE_DIR, "*.md"))

inserted = 0
skipped  = 0
errors   = []

for fp in files:
    name = os.path.basename(fp)
    try:
        with open(fp, encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        errors.append(f"{name}: 读取失败 {e}")
        continue

    fm = parse_frontmatter(content)

    source_url   = fm.get('source_url', '')
    publish_date = fm.get('publish_date', '')
    author       = fm.get('author', '')
    origin_title = fm.get('origin_title', '')
    title        = extract_title(content, fp)

    if not source_url:
        # 无 source_url 视为无法去重，跳过
        skipped += 1
        print(f"  跳过（无 source_url）: {name}")
        continue

    try:
        conn.execute("""
            INSERT OR IGNORE INTO url_index
                (source_url, title, origin_title, author, publish_date)
            VALUES (?, ?, ?, ?, ?)
        """, (source_url, title, origin_title, author, publish_date))
        inserted += 1
        print(f"  ✓ {name}")
    except Exception as e:
        errors.append(f"{name}: 写入失败 {e}")

conn.commit()
print(f"\n完成：插入 {inserted} 条，跳过 {skipped} 条，错误 {len(errors)} 条")
for e in errors:
    print(f"  ✗ {e}")
