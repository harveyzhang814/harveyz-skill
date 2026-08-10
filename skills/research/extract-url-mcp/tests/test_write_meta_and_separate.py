"""Unit tests for write_meta_and_separate.py's CLI wrapper — pure
filesystem I/O against fake config/fixed-tags files."""
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from write_meta_and_separate import run  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"VAULT_PATH": str(tmp_path / "vault")}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_EXTRACT_URL_CONFIG", str(config_path))
    fixed_tags_path = tmp_path / "fixed_tags.txt"
    fixed_tags_path.write_text("ai\n", encoding="utf-8")
    monkeypatch.setenv("FIXED_TAGS_PATH", str(fixed_tags_path))


def test_run_writes_meta_json_and_moves_candidate_tags(tmp_path, monkeypatch):
    url = "https://example.com/article"
    article_path = tmp_path / "article.md"
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
