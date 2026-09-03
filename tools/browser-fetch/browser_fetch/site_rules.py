"""Per-domain article-list extraction rules —— spec 2026-09-03-site-rules-tiers。

一条规则是一个目录 `<data_dir>/site_rules/<domain>/`：`rule.json` 存元数据，
JS 存成同目录下真正的 .js 文件。内联进 JSON 字符串的代码读不了、diff 不了、
linter 跑不了，而代码的维护成本主要花在"看清它现在是什么"上。

旧的扁平 `<domain>.json` 仍然认，视为 schema_version 1 的 selector 档 ——
迁移在写入时发生（Task 3），读路径不改动磁盘。

mode 与文件存在性不一致时抛 RuleCorruptError，不静默降级：静默降级意味着
删掉一个 .js 文件就能让高档规则悄悄退成低档继续跑，而摘要上看不出异常。
"""
import json
import os
import shutil
from pathlib import Path
from typing import Optional

SUPPORTED_MODES = frozenset({"selector", "selector+transform"})

TRANSFORM_FILE = "transform.js"


class RuleCorruptError(RuntimeError):
    """规则目录的 mode 与实际文件不符，或缺少该档必需的字段。

    继承 RuntimeError 而不是 ValueError：CLI 把 ValueError 映射成退出码 2
    （调用方用法错），而规则损坏是运行时故障，该走退出码 1。
    """


def _rules_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "site_rules"


def _check_domain(domain: str) -> str:
    if "/" in domain or "\\" in domain or ".." in domain:
        raise ValueError(f"invalid domain: {domain!r}")
    return domain


def _domain_dir(data_dir: Path, domain: str) -> Path:
    return _rules_dir(data_dir) / _check_domain(domain)


def _flat_path(data_dir: Path, domain: str) -> Path:
    return _rules_dir(data_dir) / f"{_check_domain(domain)}.json"


def _rule_path(data_dir: Path, domain: str) -> Path:
    """Helper for set_rule/list_rules/remove_rule — backward compat for flat files."""
    return _flat_path(data_dir, domain)


def _validate(rule: dict, domain_dir: Path) -> None:
    mode = rule.get("mode")
    if mode not in SUPPORTED_MODES:
        raise RuleCorruptError(f"{rule.get('domain')}: 不支持的 mode {mode!r}")
    if not rule.get("selectors"):
        raise RuleCorruptError(f"{rule.get('domain')}: mode {mode!r} 缺少 selectors")

    has_transform = (domain_dir / TRANSFORM_FILE).exists()
    if mode == "selector+transform" and not has_transform:
        raise RuleCorruptError(f"{rule.get('domain')}: mode {mode!r} 缺少 {TRANSFORM_FILE}")
    if mode == "selector" and has_transform:
        raise RuleCorruptError(
            f"{rule.get('domain')}: mode {mode!r} 不该存在 {TRANSFORM_FILE}")


def get_rule(data_dir: Path, domain: str) -> Optional[dict]:
    domain_dir = _domain_dir(data_dir, domain)
    rule_file = domain_dir / "rule.json"
    if rule_file.exists():
        rule = json.loads(rule_file.read_text(encoding="utf-8"))
        _validate(rule, domain_dir)
        if rule["mode"] == "selector+transform":
            rule["transform_js"] = (domain_dir / TRANSFORM_FILE).read_text(encoding="utf-8")
        return rule

    flat = _flat_path(data_dir, domain)
    if flat.exists():
        rule = json.loads(flat.read_text(encoding="utf-8"))
        rule.setdefault("schema_version", 1)
        rule.setdefault("mode", "selector")
        return rule

    return None


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
