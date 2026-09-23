"""Stage 3 validation test: real network, real browser-fetch CLI subprocess,
real fetch_article (site-aware extraction with image download) — no mocks.

Run: python3 -m pytest skills/research/clip-url/tests/ -v
(ambient system Python — matches how mcp_fetch_client.py itself runs)
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from mcp_fetch_client import fetch_and_report, fetch_and_save  # noqa: E402
from vault_config import get_url_hash  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(isolated_store_config, tmp_path, monkeypatch):
    """fetch_and_save spawns browser-fetch with env=dict(os.environ), so the
    CLI subprocess inherits this. Point it at a per-test data dir so tests
    never read or write the real ~/.hskill/browser-fetch/ state (fetch_article
    consults the persisted default chrome_profile). Also write a valid
    knowledgeRoot into the conftest-provided shared config.json so tests
    never touch the real ~/.hskill/config.json or a real Obsidian Vault."""
    monkeypatch.setenv("BROWSER_FETCH_DATA_DIR", str(tmp_path / "data"))
    root = tmp_path / "knowledge"
    isolated_store_config.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")


def test_fetch_and_save_writes_real_content(tmp_path, local_article_url):
    origin_path = fetch_and_save(local_article_url)

    assert origin_path == tmp_path / "knowledge" / "articles" / get_url_hash(local_article_url) / "Origin" / "Example Domain.md"
    assert origin_path.exists()
    assert origin_path.name == "Example Domain.md"
    assert origin_path.parent.name == "Origin"
    content = origin_path.read_text(encoding="utf-8")

    assert f"source_url: {local_article_url}" in content
    assert 'origin_title: "Example Domain"' in content
    assert "author:" in content
    assert "publish_date:" in content
    assert "# Example Domain" in content
    assert "This domain is for use in documentation examples" in content
    # title dedup: the heading should not repeat as a body block
    assert content.count("Example Domain") == 2  # frontmatter + heading only


def test_fetch_and_save_extracts_multiple_blocks(tmp_path, local_article_url):
    origin_path = fetch_and_save(local_article_url)

    content = origin_path.read_text(encoding="utf-8")
    paragraphs = [p for p in content.split("\n\n") if p.strip() and not p.startswith("---")]
    # frontmatter block + heading + at least a few real paragraphs
    assert len(paragraphs) >= 5
    assert "Each paragraph gives the generic extractor" in content


def test_fetch_and_save_accepts_chrome_profile_without_crashing(tmp_path, local_article_url):
    """Doesn't assert on retry content (needs real auth cookies, out of
    scope for an automated test) — just confirms chrome_profile is
    correctly forwarded to fetch_article and the call completes."""
    empty_profile = tmp_path / "EmptyProfile"
    origin_path = fetch_and_save(local_article_url, chrome_profile=str(empty_profile))
    assert origin_path.exists()


def test_fetch_and_report_returns_diagnostics(tmp_path, local_article_url):
    payload = fetch_and_report(local_article_url)
    assert payload["origin_path"].exists()
    assert payload["site"] == "generic"
    assert payload["content_thin"] is True
    assert payload["block_count"] < 20
    assert payload["char_count"] < 3000
    assert payload["thin_retry_used"] is False
    assert isinstance(payload["code_block_count"], int)
    assert payload["image_count"] == 0
