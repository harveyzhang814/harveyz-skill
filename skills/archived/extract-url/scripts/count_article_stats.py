#!/usr/bin/env python3
"""
Count article stats for the completion report card.
Usage: python3 count_article_stats.py <article_path>
Output:
  CHARS: N
  CODE_BLOCKS: N
  IMAGES: N
"""
import sys, re
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: count_article_stats.py <article_path>", file=sys.stderr)
    sys.exit(1)

article_path = Path(sys.argv[1])
if not article_path.exists():
    print(f"ERROR: file not found: {article_path}", file=sys.stderr)
    sys.exit(1)

text = article_path.read_text(encoding='utf-8')

body = text
fm_match = re.match(r'^---\n.*?\n---\n', text, re.DOTALL)
if fm_match:
    body = text[fm_match.end():]

chars = len(body)
code_blocks = len(re.findall(r'^```', body, re.MULTILINE)) // 2
images = len(re.findall(r'!\[', body))

print(f"CHARS: {chars}")
print(f"CODE_BLOCKS: {code_blocks}")
print(f"IMAGES: {images}")
