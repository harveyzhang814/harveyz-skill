import json, os, sqlite3, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def skill_config(tmp_path):
    """Temp vault + config.json + env with HSKILL_EXTRACT_URL_CONFIG set."""
    vault = tmp_path / 'vault'
    vault.mkdir()
    (vault / 'Origin').mkdir()
    (vault / 'Image').mkdir()
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({
        'VAULT_PATH': str(vault),
        'CHROME_PROFILE': str(tmp_path / 'chrome-profile'),
    }), encoding='utf-8')
    env = os.environ.copy()
    env['HSKILL_EXTRACT_URL_CONFIG'] = str(cfg)
    return {'config_path': cfg, 'vault': vault, 'env': env, 'tmp': tmp_path}


@pytest.fixture
def url_index_db(skill_config):
    """Create url_index table in vault's SQLite DB; return db Path."""
    db_path = skill_config['vault'] / 'url-index.db'
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
    conn.commit()
    conn.close()
    return db_path


_ARTICLE_CONTENT = """\
---
publish_date: 2024-01-01
fetch_date: 2024-01-02
author: Test Author
source_url: {url}
origin_title: "Test Article"
description: A test article for validation.
tags:
  - test
---

# Test Article

This paragraph has more than ten characters and serves as content for testing.
"""


@pytest.fixture
def valid_article_files(skill_config, url_index_db):
    """Create origin + translated article files with valid frontmatter."""
    url = 'https://example.com/test-article'
    content = _ARTICLE_CONTENT.format(url=url)
    origin = skill_config['vault'] / 'Origin' / 'test-article.md'
    article = skill_config['vault'] / 'test-article.md'
    origin.write_text(content, encoding='utf-8')
    article.write_text(content, encoding='utf-8')
    return {'origin': origin, 'article': article, 'url': url}
