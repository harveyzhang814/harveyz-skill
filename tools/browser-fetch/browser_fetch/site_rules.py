"""Per-domain article-list extraction rules — the persistent knowledge
`fetch_articles` (production path) reads and `articles-rule set`
(calibration path) writes. Pure I/O against
`_data_dir()/site_rules/<domain>.json`, mirroring config.py's pattern: the
caller (core.py) resolves and passes in `data_dir`, this module never
resolves it itself — same reason config.py doesn't: BROWSER_FETCH_DATA_DIR
overrides need to work in tests without this module knowing about env vars.
"""
import json
from pathlib import Path
from typing import Optional


def _rules_dir(data_dir: Path) -> Path:
    return data_dir / "site_rules"


def _rule_path(data_dir: Path, domain: str) -> Path:
    return _rules_dir(data_dir) / f"{domain}.json"


def get_rule(data_dir: Path, domain: str) -> Optional[dict]:
    path = _rule_path(data_dir, domain)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def set_rule(
    data_dir: Path,
    domain: str,
    list_url: str,
    selectors: dict,
    sample: list,
    calibrated_at: str,
) -> None:
    path = _rule_path(data_dir, domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "domain": domain,
        "list_url": list_url,
        "selectors": selectors,
        "calibrated_at": calibrated_at,
        "sample": sample,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


def list_rules(data_dir: Path) -> list[dict]:
    rules_dir = _rules_dir(data_dir)
    if not rules_dir.exists():
        return []
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(rules_dir.glob("*.json"))
    ]


def remove_rule(data_dir: Path, domain: str) -> bool:
    path = _rule_path(data_dir, domain)
    if not path.exists():
        return False
    path.unlink()
    return True
