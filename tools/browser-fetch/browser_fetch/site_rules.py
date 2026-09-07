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
        rule["mode"] = "selector"
        return rule

    return None


def _swap_dir(tmp: Path, target: Path) -> None:
    """把 tmp 目录换成 target。os.replace 对目录只在目标不存在或为空时成立，
    所以先把旧目录改名让出位置，换完再删。

    崩溃点的状态：改名后崩 → 规则暂时读不到但 .old 还在，可人工恢复；
    替换后崩 → 新规则已生效，只剩一个 .old 待清理。任何一步都不会产生
    "半条规则"，因为 target 下的文件永远是一次性整批换进去的。
    """
    backup = target.with_name(target.name + ".old")
    if backup.exists():
        shutil.rmtree(backup)
    if target.exists():
        os.replace(target, backup)
    os.replace(tmp, target)
    if backup.exists():
        shutil.rmtree(backup)


def set_rule(
    data_dir: Path,
    domain: str,
    list_url: str,
    selectors: dict,
    sample: list,
    calibrated_at: str,
    mode: str = "selector",
    transform_js: Optional[str] = None,
) -> None:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported mode: {mode!r}")
    if mode == "selector+transform" and not transform_js:
        raise ValueError("mode 'selector+transform' requires transform_js")
    if mode == "selector" and transform_js:
        raise ValueError("mode 'selector' must not carry transform_js")

    target = _domain_dir(data_dir, domain)
    tmp = target.with_name(target.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    (tmp / "rule.json").write_text(json.dumps({
        "schema_version": 2,
        "domain": domain,
        "list_url": list_url,
        "mode": mode,
        "selectors": selectors,
        "calibrated_at": calibrated_at,
        "sample": sample,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    if transform_js:
        (tmp / TRANSFORM_FILE).write_text(transform_js, encoding="utf-8")

    _swap_dir(tmp, target)

    # 迁移：目录格式落盘成功后才删旧扁平文件，中途失败仍能按旧格式读到规则。
    flat = _flat_path(data_dir, domain)
    if flat.exists():
        flat.unlink()


def list_rules(data_dir: Path) -> list[dict]:
    """目录格式与遗留扁平文件一并列出。单条规则损坏时跳过它而不是让整个
    列举失败 —— `articles-rule list` 的用途正是排查哪条坏了。"""
    rules_dir = _rules_dir(data_dir)
    if not rules_dir.exists():
        return []

    out = []
    for entry in sorted(rules_dir.iterdir()):
        if entry.is_dir():
            if entry.suffix in (".tmp", ".old"):
                continue
            domain = entry.name
        elif entry.suffix == ".json":
            domain = entry.stem
            if (rules_dir / domain).is_dir():
                continue  # 目录格式已存在，扁平文件是待清理的残留
        else:
            continue

        try:
            rule = get_rule(data_dir, domain)
        except (RuleCorruptError, ValueError, json.JSONDecodeError):
            continue
        if rule is not None:
            out.append(rule)
    return out


def remove_rule(data_dir: Path, domain: str) -> bool:
    domain_dir = _domain_dir(data_dir, domain)
    flat = _flat_path(data_dir, domain)
    removed = False
    if domain_dir.exists():
        shutil.rmtree(domain_dir)
        removed = True
    if flat.exists():
        flat.unlink()
        removed = True
    return removed
