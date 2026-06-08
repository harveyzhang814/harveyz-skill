#!/usr/bin/env python3
"""
Post-translate validation + SQLite index write for Subagent 2.
Parameters passed via environment variables to avoid shell injection:
  ARTICLE_URL       - source URL
  ARTICLE_ORIGIN    - path to origin .md file
  ARTICLE_PATH      - path to translated article .md file
  ARTICLE_DB        - path to url-index.db
  ARTICLE_SKILL_DIR - skill installation directory
  ARTICLE_CATEGORY  - (optional) category tag
"""
import sys, os

url        = os.environ['ARTICLE_URL']
origin_path  = os.environ['ARTICLE_ORIGIN']
article_path = os.environ['ARTICLE_PATH']
db_path      = os.environ['ARTICLE_DB']
skill_dir    = os.environ['ARTICLE_SKILL_DIR']
category     = os.environ.get('ARTICLE_CATEGORY', '')

sys.path.insert(0, os.path.join(skill_dir, 'references'))
from article_utils import repair_frontmatter, record_issues, write_url_index

if not os.path.exists(article_path):
    print(f"ERROR: article file not found: {article_path}", file=sys.stderr)
    sys.exit(1)

fm, fixed, remaining = repair_frontmatter(article_path, url)
if remaining:
    record_issues(url, '; '.join(remaining), db_path)
    print(f"ERROR: 校验未通过：{remaining}", file=sys.stderr)
    sys.exit(1)

record_issues(url, '', db_path)
write_url_index(url, origin_path, article_path, db_path, category=category)
print(f"翻译完成：{article_path}")
