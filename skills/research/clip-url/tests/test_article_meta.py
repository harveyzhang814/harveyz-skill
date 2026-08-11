"""Unit tests for article_meta.py's dedup-write and tag-separation
helpers — pure filesystem I/O, no network, no MCP."""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from article_meta import (  # noqa: E402
    enforce_tag_separation,
    load_fixed_tags,
    write_meta_json,
)


def test_load_fixed_tags_skips_comments_and_blank_lines(tmp_path):
    tags_file = tmp_path / "fixed_tags.txt"
    tags_file.write_text(
        "# topic\nai\nweb-standards\n\n# language\nenglish\n", encoding="utf-8"
    )
    assert load_fixed_tags(tags_file) == {"ai", "web-standards", "english"}


def test_load_fixed_tags_missing_file_returns_empty_set(tmp_path):
    assert load_fixed_tags(tmp_path / "does-not-exist.txt") == set()


def test_write_meta_json_writes_expected_fields(tmp_path):
    meta_path = tmp_path / "hash8" / "meta.json"
    article_path = tmp_path / "hash8" / "Translation" / "article.md"
    article_path.parent.mkdir(parents=True)
    article_path.write_text("dummy", encoding="utf-8")

    write_meta_json("https://example.com/article", meta_path, str(article_path))

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["source_url"] == "https://example.com/article"
    assert meta["title"] == "article.md"
    assert meta["category"] == ""
    assert meta["issues"] == ""
    assert meta["fetched_at"]  # non-empty date string


def test_enforce_tag_separation_moves_matching_candidate_into_tags(tmp_path):
    fixed_tags_path = tmp_path / "fixed_tags.txt"
    fixed_tags_path.write_text("ai\nweb-standards\n", encoding="utf-8")

    article_path = tmp_path / "article.md"
    article_path.write_text(
        "---\n"
        "source_url: https://example.com/article\n"
        "tags:\n"
        "  - existing-tag\n"
        "candidate_tags:\n"
        "  - ai\n"
        "  - some-other-topic\n"
        "---\n\n"
        "Body text.\n",
        encoding="utf-8",
    )

    enforce_tag_separation(article_path, fixed_tags_path)

    content = article_path.read_text(encoding="utf-8")
    fm = yaml.safe_load(content.split("---")[1])
    assert set(fm["tags"]) == {"existing-tag", "ai"}
    assert fm["candidate_tags"] == ["some-other-topic"]


def test_enforce_tag_separation_no_op_when_no_candidate_tags(tmp_path):
    fixed_tags_path = tmp_path / "fixed_tags.txt"
    fixed_tags_path.write_text("ai\n", encoding="utf-8")

    article_path = tmp_path / "article.md"
    original = (
        "---\n"
        "source_url: https://example.com/article\n"
        "tags:\n"
        "  - existing-tag\n"
        "---\n\n"
        "Body text.\n"
    )
    article_path.write_text(original, encoding="utf-8")

    enforce_tag_separation(article_path, fixed_tags_path)

    assert article_path.read_text(encoding="utf-8") == original


def test_enforce_tag_separation_no_op_when_fixed_tags_missing(tmp_path):
    article_path = tmp_path / "article.md"
    original = (
        "---\n"
        "source_url: https://example.com/article\n"
        "candidate_tags:\n"
        "  - ai\n"
        "---\n\n"
        "Body text.\n"
    )
    article_path.write_text(original, encoding="utf-8")

    enforce_tag_separation(article_path, tmp_path / "does-not-exist.txt")

    assert article_path.read_text(encoding="utf-8") == original
