"""Unit tests for vault_config.py — pure delegation to store_config for
the storage root; own logic only covers md5 hashing and path
composition."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from vault_config import get_article_paths, get_url_hash, get_vault_path  # noqa: E402


def _write_root(isolated_store_config, root: Path) -> None:
    isolated_store_config.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")


def test_get_vault_path_delegates_to_store_config(isolated_store_config, tmp_path):
    root = tmp_path / "knowledge"
    _write_root(isolated_store_config, root)
    assert get_vault_path() == str(root / "articles")


def test_get_url_hash_matches_md5_first_8_chars():
    url = "https://example.com/article"
    expected = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    assert get_url_hash(url) == expected


def test_get_article_paths_layout(isolated_store_config, tmp_path):
    root = tmp_path / "knowledge"
    _write_root(isolated_store_config, root)
    url = "https://example.com/article"
    paths = get_article_paths(url)
    url_hash = get_url_hash(url)
    assert paths["article_dir"] == root / "articles" / url_hash
    assert paths["meta_path"] == root / "articles" / url_hash / "meta.json"
