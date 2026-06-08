#!/usr/bin/env python3
"""
Check URL dedup in SQLite. Creates table if not exists (safe for first run).
Migrates existing DBs (e.g. old article-fetcher schema) by adding missing columns.
Parameters via env vars to avoid shell injection:
  CHECK_URL - URL to check
  DB_PATH   - path to url-index.db
Prints: ALREADY_FETCHED or OK
"""
import sqlite3, os

url     = os.environ['CHECK_URL']
db_path = os.environ['DB_PATH']

os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

conn = sqlite3.connect(db_path)
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
conn.commit()

# Migrate: add columns missing from older DB schemas
existing_cols = {row[1] for row in conn.execute('PRAGMA table_info(url_index)')}
for col, typedef in [('fetched_at', 'TEXT'), ('issues', 'TEXT'),
                     ('category', 'TEXT'), ('origin_path', 'TEXT'), ('article_path', 'TEXT')]:
    if col not in existing_cols:
        conn.execute(f'ALTER TABLE url_index ADD COLUMN {col} {typedef}')
conn.commit()

row = conn.execute('SELECT source_url FROM url_index WHERE source_url=?', (url,)).fetchone()
conn.close()
print('ALREADY_FETCHED' if row else 'OK')
