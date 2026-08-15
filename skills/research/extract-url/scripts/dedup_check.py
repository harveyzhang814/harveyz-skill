#!/usr/bin/env python3
"""
Check URL dedup via meta.json existence.
Parameter via env var to avoid shell injection:
  CHECK_URL - URL to check
Reads VAULT_PATH from ~/.hskill/url-extract/config.json to locate <hash8>/meta.json.
Prints: ALREADY_FETCHED or OK
"""
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import get_vault_path, get_url_hash

url = os.environ['CHECK_URL']
vault_path = get_vault_path()
meta_path = Path(vault_path) / get_url_hash(url) / 'meta.json'

already_fetched = False
if meta_path.exists():
    try:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        already_fetched = meta.get('source_url') == url
    except (json.JSONDecodeError, OSError):
        already_fetched = False

print('ALREADY_FETCHED' if already_fetched else 'OK')
