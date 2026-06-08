#!/usr/bin/env python3
"""
Check URL dedup in SQLite. Creates table if not exists (safe for first run).
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
        url          TEXT PRIMARY KEY,
        title        TEXT,
        fetched_at   TEXT,
        issues       TEXT,
        category     TEXT,
        origin_path  TEXT,
        article_path TEXT
    )
""")
conn.commit()
row = conn.execute('SELECT url FROM url_index WHERE url=?', (url,)).fetchone()
conn.close()
print('ALREADY_FETCHED' if row else 'OK')
