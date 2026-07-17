#!/usr/bin/env python3
"""
Post-translate validation + meta.json write for Subagent 2.
Parameters via environment variables:
  ARTICLE_URL       - source URL
  ARTICLE_ORIGIN    - path to origin .md file
  ARTICLE_PATH      - path to translated article .md file
  ARTICLE_CATEGORY  - (optional) category tag
  FIXED_TAGS_PATH   - (optional) override path for fixed_tags.txt
Reads VAULT_PATH from ~/.hskill/url-extract/config.json to locate <hash8>/meta.json.
"""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import get_vault_path, get_url_hash

url          = os.environ['ARTICLE_URL']
origin_path  = os.environ['ARTICLE_ORIGIN']
article_path = os.environ['ARTICLE_PATH']
category     = os.environ.get('ARTICLE_CATEGORY', '')

skill_dir  = str(Path(__file__).parent.parent)
vault_path = get_vault_path()
meta_path  = str(Path(vault_path) / get_url_hash(url) / 'meta.json')

sys.path.insert(0, os.path.join(skill_dir, 'references'))
from article_utils import repair_frontmatter, write_meta_json, enforce_tag_separation

if not os.path.exists(article_path):
    print(f"ERROR: article file not found: {article_path}", file=sys.stderr)
    sys.exit(1)

fm, fixed_fields, remaining = repair_frontmatter(article_path, url, skip_remaining_fields={'author', 'publish_date'})
if remaining:
    print(f"ERROR: 校验未通过：{remaining}", file=sys.stderr)
    sys.exit(1)

# 兜底移位：candidate_tags 中命中固定词表的条目移入 tags
fixed_tags_path = os.environ.get(
    'FIXED_TAGS_PATH',
    str(Path.home() / '.hskill' / 'url-extract' / 'fixed_tags.txt')
)
enforce_tag_separation(article_path, fixed_tags_path)

write_meta_json(url, meta_path, article_path, category=category)
print(f"翻译完成：{article_path}")
