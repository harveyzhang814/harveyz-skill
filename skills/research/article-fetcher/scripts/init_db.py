#!/usr/bin/env python3
"""初始化 SQLite url_index 表"""
import sqlite3, os

DB_PATH = os.path.expanduser(
    '{{SKILL_DIR}}/scripts/url-index.db'
)

# 确保目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS url_index (
        source_url   TEXT PRIMARY KEY,
        title        TEXT,
        origin_title TEXT,
        author       TEXT,
        publish_date TEXT,
        fetch_date   TEXT,
        tags         TEXT,
        description  TEXT,
        issues       TEXT,
        origin_path  TEXT,
        article_path TEXT
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_publish_date ON url_index(publish_date)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_author ON url_index(author)")
conn.commit()
conn.close()

print(f"✅ url_index 表初始化完成: {DB_PATH}")
