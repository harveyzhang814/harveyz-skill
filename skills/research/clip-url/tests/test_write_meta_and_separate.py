"""Unit tests for write_meta_and_separate.py's CLI wrapper — pure
filesystem I/O against fake config/fixed-tags files."""
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from write_meta_and_separate import run  # noqa: E402
import vault_config  # noqa: E402


@pytest.fixture(autouse=True)
def valid_vault_config(isolated_vault_config, tmp_path, monkeypatch):
    vault_path = isolated_vault_config.parent / "vault"
    isolated_vault_config.write_text(json.dumps({"VAULT_PATH": str(vault_path)}), encoding="utf-8")
    fixed_tags_path = tmp_path / "fixed_tags.txt"
    fixed_tags_path.write_text("ai\n", encoding="utf-8")
    monkeypatch.setenv("FIXED_TAGS_PATH", str(fixed_tags_path))


def test_run_writes_meta_json_and_moves_candidate_tags(tmp_path, monkeypatch):
    url = "https://example.com/article"
    article_path = vault_config.get_article_paths(url)["article_dir"] / "Translation" / "Example Domain.md"
    article_path.parent.mkdir(parents=True)
    article_path.write_text(
        "---\n"
        "source_url: https://example.com/article\n"
        "tags:\n"
        "  - existing\n"
        "candidate_tags:\n"
        "  - ai\n"
        "---\n\n"
        "Body.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARTICLE_URL", url)
    monkeypatch.setenv("ARTICLE_PATH", str(article_path))

    meta_path = run()

    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["source_url"] == url

    content = article_path.read_text(encoding="utf-8")
    fm = yaml.safe_load(content.split("---")[1])
    assert "ai" in fm["tags"]
    assert fm.get("candidate_tags") in ([], None)
    assert meta["category"] == ""


def test_run_stores_article_category_when_provided(tmp_path, monkeypatch):
    url = "https://example.com/article"
    article_path = vault_config.get_article_paths(url)["article_dir"] / "Translation" / "Example Domain.md"
    article_path.parent.mkdir(parents=True)
    article_path.write_text(
        "---\nsource_url: https://example.com/article\ntags: []\n---\n\nBody.\n", encoding="utf-8"
    )
    monkeypatch.setenv("ARTICLE_URL", url)
    monkeypatch.setenv("ARTICLE_PATH", str(article_path))
    monkeypatch.setenv("ARTICLE_CATEGORY", "AI/Research")

    meta_path = run()

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["category"] == "AI/Research"


def test_run_raises_when_article_url_mismatches_article_path(tmp_path, monkeypatch):
    """ARTICLE_URL must hash to the same <hash8> directory ARTICLE_PATH lives
    in — a mismatch means dedup would silently write a stray meta.json
    elsewhere in the vault. Must fail loudly instead."""
    real_url = "https://example.com/real-article"
    wrong_url = "https://example.com/a-totally-different-article"
    article_path = tmp_path / "vault" / "somehash" / "Translation" / "article.md"
    article_path.parent.mkdir(parents=True)
    article_path.write_text(
        "---\nsource_url: " + real_url + "\ntags: []\n---\n\nBody.\n", encoding="utf-8"
    )
    monkeypatch.setenv("ARTICLE_URL", wrong_url)
    monkeypatch.setenv("ARTICLE_PATH", str(article_path))

    with pytest.raises(RuntimeError):
        run()
