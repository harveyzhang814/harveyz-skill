import json, os, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from config import get_url_hash

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
def write_meta_json_fixture(skill_config):
    """Factory: write a meta.json for a given URL into the vault's <hash8> dir."""
    def _write(url, **fields):
        hash8 = get_url_hash(url)
        article_dir = skill_config['vault'] / hash8
        article_dir.mkdir(parents=True, exist_ok=True)
        meta = {'source_url': url, 'title': '', 'category': '', 'fetched_at': '', 'issues': ''}
        meta.update(fields)
        meta_path = article_dir / 'meta.json'
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
        return meta_path
    return _write


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
def valid_article_files(skill_config):
    """Create origin + translated article files with valid frontmatter."""
    url = 'https://example.com/test-article'
    content = _ARTICLE_CONTENT.format(url=url)
    origin = skill_config['vault'] / 'Origin' / 'test-article.md'
    article = skill_config['vault'] / 'test-article.md'
    origin.write_text(content, encoding='utf-8')
    article.write_text(content, encoding='utf-8')
    return {'origin': origin, 'article': article, 'url': url}
