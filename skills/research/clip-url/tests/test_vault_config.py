"""Unit tests for vault_config.py's shared-VAULT_PATH resolution — pure
filesystem I/O against a fake config.json, never the real
~/.hskill/url-extract/ directory."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from vault_config import get_article_paths, get_url_hash, get_vault_path  # noqa: E402


def test_get_vault_path_raises_when_config_missing(isolated_vault_config):
    with pytest.raises(FileNotFoundError):
        get_vault_path()


def test_get_vault_path_raises_when_vault_path_key_missing(isolated_vault_config):
    isolated_vault_config.write_text(json.dumps({"CHROME_PROFILE": "/some/path"}), encoding="utf-8")
    with pytest.raises(KeyError):
        get_vault_path()


def test_get_vault_path_reads_configured_value(isolated_vault_config):
    isolated_vault_config.write_text(json.dumps({"VAULT_PATH": "/fake/vault"}), encoding="utf-8")
    assert get_vault_path() == "/fake/vault"


def test_get_url_hash_matches_md5_first_8_chars():
    url = "https://example.com/article"
    expected = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    assert get_url_hash(url) == expected


def test_get_article_paths_layout(isolated_vault_config):
    isolated_vault_config.write_text(json.dumps({"VAULT_PATH": "/fake/vault"}), encoding="utf-8")
    url = "https://example.com/article"
    paths = get_article_paths(url)
    url_hash = get_url_hash(url)
    assert paths["article_dir"] == Path("/fake/vault") / url_hash
    assert paths["meta_path"] == Path("/fake/vault") / url_hash / "meta.json"


def test_missing_config_error_points_at_clip_url_not_extract_url(isolated_vault_config):
    import vault_config
    with pytest.raises(FileNotFoundError) as e:
        vault_config.get_vault_path()
    msg = str(e.value)
    assert "extract-url" not in msg
    assert "clip-url" in msg


def test_missing_vault_path_key_error_points_at_clip_url(isolated_vault_config):
    import json
    import vault_config
    isolated_vault_config.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(KeyError) as e:
        vault_config.get_vault_path()
    assert "extract-url" not in str(e.value)
