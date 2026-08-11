#!/usr/bin/env python3
"""Dedup-record and tag-separation helpers for clip-url — the
write side of dedup (write_meta_json) and the fixed-vocabulary tag
matching (load_fixed_tags/enforce_tag_separation), reimplemented from
extract-url's references/article_utils.py. Only the pieces this skill
needs — no repair_frontmatter, no sanitize_filename, no
build_article_from_json.
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


def load_fixed_tags(path) -> set:
    """Read a grouped-comment plain-text word list, skipping '#' lines
    and blank lines. Returns an empty set if path doesn't exist."""
    try:
        with open(path, encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip() and not line.startswith("#")}
    except FileNotFoundError:
        return set()


def write_meta_json(url: str, meta_path, article_path, category: str = "") -> None:
    """Write (or overwrite) <hash8>/meta.json after a successful
    fetch+translate."""
    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    meta_path = Path(meta_path)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "source_url": url,
        "title": os.path.basename(article_path),
        "category": category,
        "fetched_at": fetch_date,
        "issues": "",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _move_fixed_from_candidate(tags, candidate_tags, fixed_tags):
    new_tags = list(tags)
    new_candidate = []
    for t in candidate_tags:
        if t in fixed_tags and t not in new_tags:
            new_tags.append(t)
        elif t not in fixed_tags:
            new_candidate.append(t)
    return new_tags, new_candidate


def _replace_yaml_list_field(fm_raw, field, values):
    if values:
        new_block = f"{field}:\n" + "".join(f"  - {v}\n" for v in values)
    else:
        new_block = f"{field}: []\n"
    pattern = re.compile(
        rf"^{re.escape(field)}:[ \t]*(?:\[\])?[ \t]*\n(?:  -[^\n]*(?:\n|$))*",
        re.MULTILINE,
    )
    if pattern.search(fm_raw):
        return pattern.sub(new_block, fm_raw)
    return fm_raw.rstrip("\n") + "\n" + new_block


def enforce_tag_separation(article_path, fixed_tags_path) -> None:
    """Move any candidate_tags entries that match the fixed vocabulary
    into tags, rewriting article_path's frontmatter in place. No-op if
    fixed_tags_path has no entries, or if there's nothing to move."""
    fixed = load_fixed_tags(fixed_tags_path)
    if not fixed:
        return

    with open(article_path, encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return

    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return

    fm_raw = m.group(1)
    rest = content[m.end():]

    fm_parsed = yaml.safe_load(fm_raw) or {}
    tags = [t for t in (fm_parsed.get("tags") or []) if t]
    candidate_tags = [t for t in (fm_parsed.get("candidate_tags") or []) if t]

    if not candidate_tags:
        return

    new_tags, new_candidate = _move_fixed_from_candidate(tags, candidate_tags, fixed)
    if new_tags == tags and new_candidate == candidate_tags:
        return

    fm_raw = _replace_yaml_list_field(fm_raw, "tags", new_tags)
    fm_raw = _replace_yaml_list_field(fm_raw, "candidate_tags", new_candidate)

    with open(article_path, "w", encoding="utf-8") as f:
        f.write("---\n" + fm_raw.rstrip("\n") + "\n---" + rest)
