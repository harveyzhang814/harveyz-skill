# site_rules 三档抽取 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 site_rules 从单档 selector 扩成三档（selector / selector+transform / script），表达力逐档放开而执行能力逐档收紧，且升到 script 档只能由人发起。

**Architecture:** 规则从扁平 `<domain>.json` 改成 `<domain>/` 目录，JS 存成真正的 `.js` 文件。归一化（trim + urljoin）从 JS 侧模板挪到 Python 侧、在 `page.evaluate` 返回之后统一执行，三档都绕不过去。二档的 transform 在 `about:blank` 的独立浏览器上下文里求值，拿不到目标站 DOM 与 cookie——这是"二档可自动、三档要人批"这条分级成立的支点。

**Tech Stack:** Python 3.11+，playwright（已有），pytest。browser-fetch 侧可用第三方依赖；**sync-website skill 侧只能用标准库 + 同目录模块**。

**Spec:** `docs/superpowers/specs/2026-09-03-site-rules-tiers-design.md`
（前置设计 `docs/superpowers/specs/2026-09-02-sync-website-design.md` 的 §3.2 被本设计取代，其余小节仍然有效）

## Global Constraints

- **不改 `dispatch_site()`**，不改 browser-fetch 已有的四个抽取器（generic / wechat / arxiv / youtube）。
- **不改 `core.py` 里 `fetch_page` / `fetch_article` / `fetch_user_timeline` / `fetch_channel_videos` / `evaluate_js` 的签名或行为。**
- **共享设施只读复用，不改签名不改语义**：`_get_context(key)`、`_profile_key()`、`config.get_default_chrome_profile(_data_dir())`、`extract_cookies()`。需要改它们才能实现 = 设计走偏，停下来回报。
- **一档（`mode: "selector"`）的抽取结果必须逐字不变。** `urljoin` 对已经绝对的 URL 幂等，所以一档模板里的 `linkEl.href` 保留不动。
- **`mode` 与文件存在性不一致时报错，不静默降级。**
- **静态扫描只作评审材料，不作门禁。**
- **sync-website skill 的 `scripts/*.py` 只能 import 标准库和同目录模块**，不得引入第三方包。
- **已有测试的单一例外**：`tools/browser-fetch/tests/test_site_rules.py:38` 的 `test_rule_file_written_under_site_rules_subdir` 断言扁平路径 `site_rules/example.com.json`，本计划故意改存储契约，Task 3 会重写它。**这是唯一被许可修改的已有测试。** 其余任何已有测试若失败，都是隔离被破坏，停下来回报，不要改测试去迁就实现。
- **分支**：在 `feature/site-rules-tiers` 上做（从 `staging` 切出）。commit 类型限 `feat|fix|chore|docs|refactor|test|style|perf`（**是 `docs` 不是 `doc`**），首行 ≤ 80 字符。分支前缀反过来是 `doc/` 不是 `docs/`。
- **阶段边界**：Task 1–8 是阶段一，交付"一档不变 + 二档可用"。Task 9–15 是阶段二，交付三档。**阶段一结束后停下来等用户决定要不要做阶段二**——spec §10 的产品判断认为目前样本量（2 个站、0 个真的需要三档）支撑不了"现在就做三档"。

---

## File Structure

**新建**

| 文件 | 职责 |
|---|---|
| `tools/browser-fetch/browser_fetch/normalize.py` | 归一化管线。纯函数，不碰磁盘不碰浏览器 |
| `tools/browser-fetch/browser_fetch/static_scan.py` | JS 静态扫描（阶段二）。纯函数，产出材料 |
| `tools/browser-fetch/tests/test_normalize.py` | Task 1 |
| `tools/browser-fetch/tests/test_site_rules_dirs.py` | Task 2–4、9 的目录格式测试 |
| `tools/browser-fetch/tests/test_cli_articles_transform.py` | Task 6–8 |
| `tools/browser-fetch/tests/test_static_scan.py` | Task 10 |
| `tools/browser-fetch/tests/test_cli_articles_script.py` | Task 11–12 |

**修改**

| 文件 | 改什么 |
|---|---|
| `browser_fetch/site_rules.py` | 全面改写：目录格式、mode、原子交换、扁平迁移、script 档 |
| `browser_fetch/core.py` | `_scrape_articles` 接归一化；新增 `_run_transform`；`fetch_articles` 走 mode 分发；`set_site_rule` 扩参 |
| `browser_fetch/cli.py` | `articles-probe` 加 `--transform-file`；`articles-rule set` 加 `--mode` / `--transform-file` / `--script-file` / `--review-file` |
| `browser_fetch/extractors.py` | **阶段一不动。** 阶段二无改动 |
| `skills/feed/sync-website/SKILL.md` | calibrate 流程加二档/三档分支；run 的自愈上限 |
| `skills/feed/sync-website/scripts/fetch_new_articles.py` | 三档不自愈；`allow_script=False` 显式守卫 |
| `skills/feed/sync-website/scripts/digest.py` | 标注三档渠道 |

---

# 阶段一：schema 迁移 + 归一化 + 二档

---

### Task 1: 归一化管线

**Files:**
- Create: `tools/browser-fetch/browser_fetch/normalize.py`
- Test: `tools/browser-fetch/tests/test_normalize.py`

**Interfaces:**
- Consumes: 无
- Produces: `normalize_articles(raw_items: list, list_url: str) -> list[dict]`，返回的每个 dict 恰好三个键 `title` / `url` / `date_text`，全为 `str`

- [ ] **Step 1: 写失败的测试**

```python
"""normalize_articles 的单元测试 —— 纯函数，不碰浏览器不碰磁盘。
这层是 spec §7.3 的"结构上绕不过去"：三档 JS 返回什么都要过它。"""
from browser_fetch.normalize import normalize_articles

LIST_URL = "https://example.com/blog"


def test_absolute_url_passes_through_unchanged():
    items = [{"title": "T", "url": "https://example.com/a", "date_text": "d"}]
    assert normalize_articles(items, LIST_URL)[0]["url"] == "https://example.com/a"


def test_relative_url_is_resolved_against_list_url():
    items = [{"title": "T", "url": "/posts/1", "date_text": ""}]
    assert normalize_articles(items, LIST_URL)[0]["url"] == "https://example.com/posts/1"


def test_whitespace_in_title_and_date_is_collapsed():
    items = [{"title": "  a\n\t b  ", "url": "https://example.com/a", "date_text": " x \n y "}]
    out = normalize_articles(items, LIST_URL)[0]
    assert out["title"] == "a b"
    assert out["date_text"] == "x y"


def test_items_without_a_url_are_dropped():
    items = [
        {"title": "keep", "url": "https://example.com/a", "date_text": ""},
        {"title": "drop", "url": "", "date_text": ""},
        {"title": "drop too", "url": "   ", "date_text": ""},
    ]
    out = normalize_articles(items, LIST_URL)
    assert [a["title"] for a in out] == ["keep"]


def test_missing_keys_become_empty_strings():
    items = [{"url": "https://example.com/a"}]
    out = normalize_articles(items, LIST_URL)[0]
    assert out == {"title": "", "url": "https://example.com/a", "date_text": ""}


def test_non_dict_entries_are_dropped():
    items = [{"title": "T", "url": "https://example.com/a", "date_text": ""}, "junk", None, 42]
    assert len(normalize_articles(items, LIST_URL)) == 1


def test_non_string_field_values_become_empty_strings():
    items = [{"title": 123, "url": "https://example.com/a", "date_text": {"x": 1}}]
    out = normalize_articles(items, LIST_URL)[0]
    assert out["title"] == ""
    assert out["date_text"] == ""


def test_output_has_exactly_the_three_contract_keys():
    items = [{"title": "T", "url": "https://example.com/a", "date_text": "d", "extra": "gone"}]
    assert set(normalize_articles(items, LIST_URL)[0]) == {"title", "url", "date_text"}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'browser_fetch.normalize'`

- [ ] **Step 3: 写实现**

```python
"""page.evaluate 返回之后的共享归一化 —— spec §7.3。

跑在 Python 侧、在 JS 边界之外，所以三档（selector / selector+transform /
script）都绕不过去。一档模板已经用 linkEl.href 解析成绝对 URL，而 urljoin
对绝对 URL 幂等，所以无条件跑它不改变一档行为，同时兜住一个返回原始相对
href 的三档脚本 —— 相对 URL 会静默破坏游标与归档去重（两者都拿 URL 当主键）。

已知上限：三档 JS 返回原始相对属性、且页面带 <base href> 时，浏览器的
.href 是对的而 urljoin(list_url, ...) 会算错。三档写作约定要求返回 .href，
评审 subagent 检查这一条。
"""
import re
from urllib.parse import urljoin

_WHITESPACE = re.compile(r"\s+")


def _clean(value) -> str:
    """非字符串一律归零 —— 抽取 JS 是不可信输出，不假设它给的是字符串。"""
    if not isinstance(value, str):
        return ""
    return _WHITESPACE.sub(" ", value).strip()


def normalize_articles(raw_items, list_url: str) -> list[dict]:
    """把抽取 JS 的原始输出收敛成契约形状：恰好 title/url/date_text 三个
    字符串键。无法解析出 url 的条目丢弃 —— 一个没有可解析链接的条目永远
    不是一篇可用的文章。"""
    out = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        raw_url = item.get("url")
        url = urljoin(list_url, raw_url.strip()) if isinstance(raw_url, str) and raw_url.strip() else ""
        if not url:
            continue
        out.append({
            "title": _clean(item.get("title")),
            "url": url,
            "date_text": _clean(item.get("date_text")),
        })
    return out
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_normalize.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch/browser_fetch/normalize.py tools/browser-fetch/tests/test_normalize.py
git commit -m "feat(browser-fetch): 抽取结果归一化管线，三档共用"
```

---

### Task 2: site_rules 读路径 —— 目录格式 + 扁平回退 + mode 校验

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/site_rules.py`
- Test: `tools/browser-fetch/tests/test_site_rules_dirs.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `class RuleCorruptError(RuntimeError)`
  - `get_rule(data_dir: Path, domain: str) -> dict | None` —— 返回 rule.json 内容，`mode == "selector+transform"` 时额外带 `"transform_js": str`
  - `SUPPORTED_MODES: frozenset` —— 阶段一为 `{"selector", "selector+transform"}`

- [ ] **Step 1: 写失败的测试**

```python
"""site_rules 目录格式的读路径 —— spec §3.1/§3.2/§3.4。
写路径在 Task 3，本文件只造目录再读。"""
import json
from pathlib import Path

import pytest

from browser_fetch import site_rules

SELECTORS = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}


def _write_dir_rule(data_dir: Path, domain: str, rule: dict, files: dict | None = None) -> Path:
    d = data_dir / "site_rules" / domain
    d.mkdir(parents=True, exist_ok=True)
    (d / "rule.json").write_text(json.dumps(rule), encoding="utf-8")
    for name, body in (files or {}).items():
        (d / name).write_text(body, encoding="utf-8")
    return d


def _selector_rule(domain="example.com", mode="selector", **extra) -> dict:
    rule = {
        "schema_version": 2, "domain": domain,
        "list_url": f"https://{domain}/", "mode": mode,
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
    }
    rule.update(extra)
    return rule


def test_reads_a_directory_format_selector_rule(tmp_path):
    _write_dir_rule(tmp_path, "example.com", _selector_rule())
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["mode"] == "selector"
    assert rule["selectors"] == SELECTORS


def test_reads_transform_source_alongside_the_rule(tmp_path):
    _write_dir_rule(
        tmp_path, "example.com",
        _selector_rule(mode="selector+transform"),
        {"transform.js": "(a) => a"},
    )
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["transform_js"] == "(a) => a"


def test_flat_legacy_file_is_read_as_a_selector_rule(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "example.com.json").write_text(json.dumps({
        "domain": "example.com", "list_url": "https://example.com/",
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
    }), encoding="utf-8")
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["mode"] == "selector"
    assert rule["schema_version"] == 1
    assert rule["selectors"] == SELECTORS


def test_directory_format_wins_over_a_leftover_flat_file(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "example.com.json").write_text(json.dumps({
        "domain": "example.com", "list_url": "https://stale/",
        "selectors": {}, "calibrated_at": "old", "sample": [],
    }), encoding="utf-8")
    _write_dir_rule(tmp_path, "example.com", _selector_rule())
    assert site_rules.get_rule(tmp_path, "example.com")["list_url"] == "https://example.com/"


def test_missing_rule_returns_none(tmp_path):
    assert site_rules.get_rule(tmp_path, "nope.example") is None


def test_transform_mode_without_the_js_file_is_corrupt(tmp_path):
    _write_dir_rule(tmp_path, "example.com", _selector_rule(mode="selector+transform"))
    with pytest.raises(site_rules.RuleCorruptError, match="transform.js"):
        site_rules.get_rule(tmp_path, "example.com")


def test_selector_mode_with_a_stray_transform_file_is_corrupt(tmp_path):
    _write_dir_rule(tmp_path, "example.com", _selector_rule(), {"transform.js": "(a) => a"})
    with pytest.raises(site_rules.RuleCorruptError, match="transform.js"):
        site_rules.get_rule(tmp_path, "example.com")


def test_unsupported_mode_is_corrupt_not_silently_downgraded(tmp_path):
    _write_dir_rule(tmp_path, "example.com", _selector_rule(mode="script"))
    with pytest.raises(site_rules.RuleCorruptError, match="mode"):
        site_rules.get_rule(tmp_path, "example.com")


def test_selector_mode_missing_selectors_is_corrupt(tmp_path):
    rule = _selector_rule()
    del rule["selectors"]
    _write_dir_rule(tmp_path, "example.com", rule)
    with pytest.raises(site_rules.RuleCorruptError, match="selectors"):
        site_rules.get_rule(tmp_path, "example.com")


def test_path_traversal_domain_still_rejected(tmp_path):
    for bad in ("../../../tmp/evil", "a/b", "a\\b"):
        with pytest.raises(ValueError):
            site_rules.get_rule(tmp_path, bad)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules_dirs.py -v`
Expected: FAIL — `AttributeError: module 'browser_fetch.site_rules' has no attribute 'RuleCorruptError'`

- [ ] **Step 3: 写实现**

把 `site_rules.py` 顶部的 docstring 和读路径替换成下面这段（`set_rule` / `list_rules` / `remove_rule` 暂时保持原样，Task 3、4 再改）：

```python
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
        rule.setdefault("mode", "selector")
        return rule

    return None
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules_dirs.py -v`
Expected: 10 passed

- [ ] **Step 5: 确认已有 site_rules 测试仍然全绿**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules.py -v`
Expected: 12 passed（读路径对扁平文件回退兼容，`set_rule` 还没动）

- [ ] **Step 6: Commit**

```bash
git add tools/browser-fetch/browser_fetch/site_rules.py tools/browser-fetch/tests/test_site_rules_dirs.py
git commit -m "feat(browser-fetch): site_rules 读目录格式，扁平文件兼容"
```

---

### Task 3: site_rules 写路径 —— 原子目录交换 + 迁移

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/site_rules.py`
- Modify: `tools/browser-fetch/tests/test_site_rules.py:38`（**Global Constraints 里点名的唯一例外**）
- Test: `tools/browser-fetch/tests/test_site_rules_dirs.py`（追加）

**Interfaces:**
- Consumes: Task 2 的 `_domain_dir` / `_flat_path` / `SUPPORTED_MODES` / `TRANSFORM_FILE`
- Produces: `set_rule(data_dir, domain, list_url, selectors, sample, calibrated_at, mode="selector", transform_js=None) -> None`
  —— 位置参数顺序与改动前一致，新增两个都是带默认值的关键字参数，所以已有调用方无需改动

- [ ] **Step 1: 写失败的测试（追加到 test_site_rules_dirs.py 末尾）**

```python
def test_set_rule_writes_the_directory_format(tmp_path):
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")
    d = tmp_path / "site_rules" / "example.com"
    assert (d / "rule.json").exists()
    assert json.loads((d / "rule.json").read_text())["schema_version"] == 2
    assert json.loads((d / "rule.json").read_text())["mode"] == "selector"


def test_set_rule_with_transform_writes_the_js_file(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
        mode="selector+transform", transform_js="(a) => a.slice(1)",
    )
    d = tmp_path / "site_rules" / "example.com"
    assert (d / "transform.js").read_text(encoding="utf-8") == "(a) => a.slice(1)"
    assert site_rules.get_rule(tmp_path, "example.com")["transform_js"] == "(a) => a.slice(1)"


def test_transform_mode_without_source_is_rejected_at_write_time(tmp_path):
    with pytest.raises(ValueError, match="transform_js"):
        site_rules.set_rule(
            tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
            mode="selector+transform",
        )


def test_unsupported_mode_is_rejected_at_write_time(tmp_path):
    with pytest.raises(ValueError, match="mode"):
        site_rules.set_rule(
            tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
            mode="script",
        )


def test_rewriting_a_rule_drops_the_previous_transform_file(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t1",
        mode="selector+transform", transform_js="(a) => a",
    )
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t2")
    d = tmp_path / "site_rules" / "example.com"
    assert not (d / "transform.js").exists()
    assert site_rules.get_rule(tmp_path, "example.com")["mode"] == "selector"


def test_writing_migrates_away_from_a_legacy_flat_file(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    flat = rules_dir / "example.com.json"
    flat.write_text(json.dumps({
        "domain": "example.com", "list_url": "https://old/",
        "selectors": {}, "calibrated_at": "old", "sample": [],
    }), encoding="utf-8")

    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")

    assert not flat.exists()
    assert (rules_dir / "example.com" / "rule.json").exists()


def test_no_tmp_or_old_directory_survives_a_successful_write(tmp_path):
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t2")
    names = {p.name for p in (tmp_path / "site_rules").iterdir()}
    assert names == {"example.com"}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules_dirs.py -k "set_rule or migrat or tmp_or_old or rewriting" -v`
Expected: FAIL — 现有 `set_rule` 仍写扁平文件，`rule.json` 不存在

- [ ] **Step 3: 写实现（替换 `site_rules.py` 里的 `set_rule`）**

```python
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
```

- [ ] **Step 4: 改写被点名的那条已有测试**

把 `tools/browser-fetch/tests/test_site_rules.py` 第 38–40 行的

```python
def test_rule_file_written_under_site_rules_subdir(tmp_path):
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")
    assert (tmp_path / "site_rules" / "example.com.json").exists()
```

替换为

```python
def test_rule_written_under_a_per_domain_directory(tmp_path):
    # 存储契约在 2026-09-03-site-rules-tiers 里从扁平 <domain>.json 改成
    # <domain>/ 目录，好让 JS 存成真正的 .js 文件。
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")
    assert (tmp_path / "site_rules" / "example.com" / "rule.json").exists()
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules.py tests/test_site_rules_dirs.py -v`
Expected: 全部 passed（`test_site_rules.py` 12 条 + `test_site_rules_dirs.py` 17 条）

若 `test_site_rules.py` 里除被点名那条之外还有失败，**停下来回报**——那说明改动溢出了预期范围。

- [ ] **Step 6: Commit**

```bash
git add tools/browser-fetch/browser_fetch/site_rules.py tools/browser-fetch/tests/
git commit -m "feat(browser-fetch): site_rules 写目录格式，原子交换与扁平迁移"
```

---

### Task 4: list_rules / remove_rule 适配目录格式

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/site_rules.py`
- Test: `tools/browser-fetch/tests/test_site_rules_dirs.py`（追加）

**Interfaces:**
- Consumes: Task 2/3 的 `get_rule` / `_domain_dir` / `_flat_path`
- Produces: `list_rules(data_dir) -> list[dict]`、`remove_rule(data_dir, domain) -> bool`（签名不变，行为扩展）

- [ ] **Step 1: 写失败的测试（追加）**

```python
def test_list_rules_covers_both_directory_and_flat_rules(tmp_path):
    site_rules.set_rule(tmp_path, "a.example", "https://a.example/", SELECTORS, [], "t")
    rules_dir = tmp_path / "site_rules"
    (rules_dir / "b.example.json").write_text(json.dumps({
        "domain": "b.example", "list_url": "https://b.example/",
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
    }), encoding="utf-8")
    assert {r["domain"] for r in site_rules.list_rules(tmp_path)} == {"a.example", "b.example"}


def test_list_rules_ignores_tmp_and_old_leftovers(tmp_path):
    site_rules.set_rule(tmp_path, "a.example", "https://a.example/", SELECTORS, [], "t")
    rules_dir = tmp_path / "site_rules"
    (rules_dir / "a.example.tmp").mkdir()
    (rules_dir / "a.example.old").mkdir()
    assert {r["domain"] for r in site_rules.list_rules(tmp_path)} == {"a.example"}


def test_list_rules_skips_a_corrupt_rule_instead_of_failing_the_whole_listing(tmp_path):
    site_rules.set_rule(tmp_path, "good.example", "https://good.example/", SELECTORS, [], "t")
    _write_dir_rule(tmp_path, "bad.example", _selector_rule("bad.example", mode="script"))
    listed = site_rules.list_rules(tmp_path)
    assert {r["domain"] for r in listed} == {"good.example"}


def test_remove_rule_deletes_the_whole_directory(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
        mode="selector+transform", transform_js="(a) => a",
    )
    assert site_rules.remove_rule(tmp_path, "example.com") is True
    assert not (tmp_path / "site_rules" / "example.com").exists()
    assert site_rules.get_rule(tmp_path, "example.com") is None


def test_remove_rule_also_deletes_a_legacy_flat_file(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "example.com.json").write_text(json.dumps({
        "domain": "example.com", "list_url": "https://example.com/",
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
    }), encoding="utf-8")
    assert site_rules.remove_rule(tmp_path, "example.com") is True
    assert site_rules.get_rule(tmp_path, "example.com") is None


def test_remove_rule_returns_false_when_nothing_to_remove(tmp_path):
    assert site_rules.remove_rule(tmp_path, "nope.example") is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules_dirs.py -k "list_rules or remove_rule" -v`
Expected: FAIL — 现有 `list_rules` 只 glob `*.json`，`remove_rule` 只 unlink 扁平文件

- [ ] **Step 3: 写实现（替换 `list_rules` 与 `remove_rule`）**

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules.py tests/test_site_rules_dirs.py -v`
Expected: 全部 passed

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch/browser_fetch/site_rules.py tools/browser-fetch/tests/test_site_rules_dirs.py
git commit -m "feat(browser-fetch): list/remove 适配规则目录，跳过损坏条目"
```

---

### Task 5: `_scrape_articles` 接归一化管线

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/core.py`（`_scrape_articles` 结尾，约 `core.py:838`）
- Test: `tools/browser-fetch/tests/test_cli_articles.py`（**只追加新用例，不动已有的**）

**Interfaces:**
- Consumes: Task 1 的 `normalize_articles`
- Produces: `_scrape_articles(list_url, selectors, chrome_profile) -> list[dict]`（返回值形状不变，只是保证过了归一化）

- [ ] **Step 1: 写失败的测试（追加到 `test_cli_articles.py` 末尾）**

```python
def test_articles_output_carries_exactly_the_contract_keys(run_cli, articles_fixture_server):
    run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(ARTICLE_SELECTORS),
        "--list-url", articles_fixture_server,
    )
    _, payload = run_cli("articles", articles_fixture_server)
    for article in payload["articles"]:
        assert set(article) == {"title", "url", "date_text"}


def test_articles_urls_stay_absolute_after_normalization(run_cli, articles_fixture_server):
    # fixture 页面里的 href 是相对的（/posts/1），一档模板用 linkEl.href 已经
    # 解析成绝对；urljoin 幂等，所以这里断言的是"归一化没有把它弄坏"。
    run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(ARTICLE_SELECTORS),
        "--list-url", articles_fixture_server,
    )
    _, payload = run_cli("articles", articles_fixture_server)
    assert all(a["url"].startswith("http://127.0.0.1:") for a in payload["articles"])
    assert payload["articles"][0]["url"].endswith("/posts/1")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles.py -k contract_keys -v`
Expected: FAIL —— 现有实现原样透传 JS 返回的键

（若因为 fixture 只返回这三个键而意外通过，仍然继续 Step 3：归一化必须显式存在，不能靠 JS 恰好只返回三个键。）

- [ ] **Step 3: 写实现**

在 `core.py` 的 import 区加：

```python
from browser_fetch.normalize import normalize_articles
```

把 `_scrape_articles` 结尾的

```python
    return [item for item in raw_items if item["url"]]
```

替换为

```python
    # 归一化跑在 JS 边界之外，所以三档都绕不过去（spec §7.3）。
    return normalize_articles(raw_items, list_url)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles.py -v`
Expected: 9 passed（原 7 条 + 新 2 条），**原 7 条一条不改**

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch/browser_fetch/core.py tools/browser-fetch/tests/test_cli_articles.py
git commit -m "refactor(browser-fetch): 抽取结果统一过归一化管线"
```

---

### Task 6: transform 的隔离上下文求值

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/core.py`（新增常量与函数）
- Test: `tools/browser-fetch/tests/test_cli_articles_transform.py`（新建）

**Interfaces:**
- Consumes: `_get_context`、Task 1 的 `normalize_articles`
- Produces:
  - `TRANSFORM_KEY = "__transform__"`
  - `async def _run_transform(articles: list[dict], transform_js: str, list_url: str) -> list[dict]`

- [ ] **Step 1: 写失败的测试**

```python
"""二档 transform 的隔离求值 —— spec §2。

这套分级的支点：transform 必须拿不到目标站的 DOM 与 cookie，否则它跟三档
能力相同，"二档可自动、三档要人批"就没有实质差别。这里的三条隔离断言是
那条设计主张的可证伪形式。
"""
import json

import pytest

from browser_fetch import core

ARTICLES = [
    {"title": "a", "url": "https://example.com/1", "date_text": "d1"},
    {"title": "b", "url": "https://example.com/2", "date_text": "d2"},
]
LIST_URL = "https://example.com/blog"


async def test_transform_receives_the_articles_array():
    out = await core._run_transform(ARTICLES, "(items) => items.slice(1)", LIST_URL)
    assert [a["title"] for a in out] == ["b"]


async def test_transform_output_goes_through_normalization():
    js = "(items) => items.map(i => ({...i, title: '  x  y  ', url: '/rel'}))"
    out = await core._run_transform(ARTICLES, js, LIST_URL)
    assert out[0]["title"] == "x y"
    assert out[0]["url"] == "https://example.com/rel"


async def test_transform_cannot_read_target_site_cookies():
    js = "(items) => [{title: document.cookie || 'EMPTY', url: 'https://x/1', date_text: ''}]"
    out = await core._run_transform(ARTICLES, js, LIST_URL)
    assert out[0]["title"] == "EMPTY"


async def test_transform_does_not_run_on_the_target_page():
    js = "(items) => [{title: location.href, url: 'https://x/1', date_text: ''}]"
    out = await core._run_transform(ARTICLES, js, LIST_URL)
    assert out[0]["title"] == "about:blank"


async def test_transform_returning_a_non_array_yields_no_articles():
    out = await core._run_transform(ARTICLES, "(items) => 42", LIST_URL)
    assert out == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles_transform.py -v`
Expected: FAIL — `AttributeError: module 'browser_fetch.core' has no attribute '_run_transform'`

- [ ] **Step 3: 写实现**

在 `core.py` 的 `ANON_KEY = "__anon__"`（`core.py:38`）下面加一行：

```python
TRANSFORM_KEY = "__transform__"
```

在 `_scrape_articles` 之后加：

```python
async def _run_transform(articles: list[dict], transform_js: str, list_url: str) -> list[dict]:
    """在隔离上下文里对 selector 抽出的数组做后处理 —— spec §2。

    刻意跑在 about:blank 而不是目标页面上：transform 因此拿不到目标站的
    DOM、cookie 和登录态，只拿得到传进去的 JSON 数组。这是"二档可由自愈
    自动写、三档必须人批"这条分级的支点 —— 若 transform 在目标页面里跑，
    它的能力与三档全 JS 完全相同，分级就只是输入变干净了、能力没变。

    另起一个 context key（不复用 ANON_KEY）是为了不跟任何抓取路径共享
    浏览器状态。**这不是真沙箱** —— fetch 仍然可用，只是没有目标站凭据。

    输出照样过归一化：transform 可能造出新的或相对的 URL。
    """
    ctx = await _get_context(TRANSFORM_KEY)
    page = await ctx.new_page()
    try:
        await page.goto("about:blank")
        raw = await page.evaluate(transform_js, articles)
    finally:
        await page.close()

    if not isinstance(raw, list):
        return []
    return normalize_articles(raw, list_url)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles_transform.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch/browser_fetch/core.py tools/browser-fetch/tests/test_cli_articles_transform.py
git commit -m "feat(browser-fetch): transform 在隔离上下文求值，无目标站凭据"
```

---

### Task 7: `fetch_articles` / `fetch_articles_probe` 走 mode 分发

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/core.py`（`fetch_articles`、`fetch_articles_probe`、`set_site_rule`）
- Test: `tools/browser-fetch/tests/test_cli_articles_transform.py`（追加）

**Interfaces:**
- Consumes: Task 2 的 `get_rule`、Task 6 的 `_run_transform`
- Produces:
  - `async def fetch_articles(url, chrome_profile=None) -> dict`（形状不变：`{"domain", "articles"}`）
  - `async def fetch_articles_probe(url, selectors, chrome_profile=None, transform_js=None) -> dict`
  - `async def set_site_rule(domain, list_url, selectors, sample, mode="selector", transform_js=None) -> dict`

- [ ] **Step 1: 写失败的测试（追加）**

```python
def test_transform_rule_is_applied_on_the_production_path(run_cli, articles_fixture_server, tmp_path):
    transform = tmp_path / "t.js"
    transform.write_text("(items) => items.slice(0, 1)", encoding="utf-8")
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}

    proc, _ = run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(selectors),
        "--list-url", articles_fixture_server,
        "--mode", "selector+transform",
        "--transform-file", str(transform),
    )
    assert proc.returncode == 0, proc.stderr

    proc, payload = run_cli("articles", articles_fixture_server)
    assert proc.returncode == 0, proc.stderr
    assert len(payload["articles"]) == 1  # selector 抽 3 条，transform 砍到 1 条


def test_probe_can_try_a_transform_without_persisting_anything(run_cli, articles_fixture_server, tmp_path):
    transform = tmp_path / "t.js"
    transform.write_text("(items) => items.slice(0, 2)", encoding="utf-8")
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}

    proc, payload = run_cli(
        "articles-probe", articles_fixture_server,
        "--selectors", json.dumps(selectors),
        "--transform-file", str(transform),
    )
    assert proc.returncode == 0, proc.stderr
    assert len(payload["articles"]) == 2

    _, listing = run_cli("articles-rule", "list")
    assert listing["rules"] == []


def test_a_corrupt_rule_fails_the_run_instead_of_downgrading(run_cli, articles_fixture_server, tmp_path):
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}
    transform = tmp_path / "t.js"
    transform.write_text("(items) => items", encoding="utf-8")
    run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(selectors),
        "--list-url", articles_fixture_server,
        "--mode", "selector+transform",
        "--transform-file", str(transform),
    )
    # 手工删掉 transform.js，模拟规则目录被破坏
    (tmp_path / "data" / "site_rules" / "127.0.0.1" / "transform.js").unlink()

    proc, _ = run_cli("articles", articles_fixture_server)
    assert proc.returncode == 1
    assert "transform.js" in proc.stderr
```

**注意**：第三条测试依赖 `run_cli` 把 `BROWSER_FETCH_DATA_DIR` 设成 `tmp_path / "data"`（见 `tests/conftest.py:19`），但 `run_cli` 每次调用共用同一个 `tmp_path`，所以同一测试内多次调用共享规则库。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles_transform.py -k "production_path or probe_can_try or corrupt_rule" -v`
Expected: FAIL —— CLI 还不认 `--mode` / `--transform-file`（`unrecognized arguments`）

- [ ] **Step 3: 写实现（`core.py`）**

把 `fetch_articles` 的结尾

```python
    articles = await _scrape_articles(url, rule["selectors"], chrome_profile)
    return {"domain": domain, "articles": articles}
```

替换为

```python
    articles = await _scrape_articles(url, rule["selectors"], chrome_profile)
    if rule.get("mode") == "selector+transform":
        articles = await _run_transform(articles, rule["transform_js"], url)
    return {"domain": domain, "articles": articles}
```

把 `fetch_articles_probe` 的签名与结尾改成：

```python
async def fetch_articles_probe(
    url: str,
    selectors: dict,
    chrome_profile: Optional[str] = None,
    transform_js: Optional[str] = None,
) -> dict:
    """标定路径：用候选规则试跑并返回抽取结果。**从不读写规则库** ——
    只有 `articles-rule set` 落盘，所以一轮失败的标定不留痕迹
    （spec §3.2："probe 与 set 分离是关键"）。"""
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(f"Rejected URL with scheme '{parsed_url.scheme}' — only http/https allowed")

    articles = await _scrape_articles(url, selectors, chrome_profile)
    if transform_js:
        articles = await _run_transform(articles, transform_js, url)
    return {"articles": articles}
```

把 `set_site_rule` 改成：

```python
async def set_site_rule(
    domain: str,
    list_url: str,
    selectors: dict,
    sample: list,
    mode: str = "selector",
    transform_js: Optional[str] = None,
) -> dict:
    from datetime import datetime, timezone

    calibrated_at = datetime.now(timezone.utc).isoformat()
    site_rules.set_rule(
        _data_dir(), domain, list_url, selectors, sample, calibrated_at,
        mode=mode, transform_js=transform_js,
    )
    return {"ok": True, "domain": domain, "mode": mode, "calibrated_at": calibrated_at}
```

- [ ] **Step 4: 写实现（`cli.py`）**

在 `cli.py` 顶部的 `_read_js` 旁边加一个读文件的小工具（`_read_js` 只处理 `-`/文件两种，直接复用即可）。

把 `p_articles_probe` 那段（`cli.py:87-92`）替换为：

```python
    p_articles_probe = sub.add_parser("articles-probe", help="标定路径：用候选规则试跑，不落盘")
    p_articles_probe.add_argument("url")
    p_articles_probe.add_argument("--selectors", required=True, help="JSON: {item,title,link,date}")
    p_articles_probe.add_argument("--transform-file", default=None, dest="transform_file",
                                  help="二档：transform JS 源文件，'-' 读 stdin")
    p_articles_probe.add_argument("--chrome-profile", default=None)
    p_articles_probe.set_defaults(handler=lambda a: core.fetch_articles_probe(
        a.url, json.loads(a.selectors), a.chrome_profile,
        _read_js(a.transform_file) if a.transform_file else None))
```

把 `ar_set` 那段（`cli.py:97-104`）替换为：

```python
    ar_set = ar_sub.add_parser("set")
    ar_set.add_argument("domain")
    ar_set.add_argument("--selectors", required=True)
    ar_set.add_argument("--list-url", required=True, dest="list_url")
    ar_set.add_argument("--sample", default="[]")
    ar_set.add_argument("--mode", default="selector",
                        choices=("selector", "selector+transform"))
    ar_set.add_argument("--transform-file", default=None, dest="transform_file",
                        help="mode=selector+transform 必需；'-' 读 stdin")
    ar_set.set_defaults(handler=lambda a: core.set_site_rule(
        a.domain, a.list_url, json.loads(a.selectors), json.loads(a.sample),
        mode=a.mode,
        transform_js=_read_js(a.transform_file) if a.transform_file else None))
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles_transform.py -v`
Expected: 8 passed

- [ ] **Step 6: 跑 browser-fetch 全量，确认无回归**

Run: `cd tools/browser-fetch && .venv/bin/pytest -q`
Expected: 全绿。基线是本计划开工前的数字（`pytest -q` 自己跑一遍记下来），新增用例只增不减，**已有用例只有被点名的那一条被改过**。

- [ ] **Step 7: Commit**

```bash
git add tools/browser-fetch/browser_fetch/core.py tools/browser-fetch/browser_fetch/cli.py tools/browser-fetch/tests/test_cli_articles_transform.py
git commit -m "feat(browser-fetch): articles 走 mode 分发，probe 支持二档试跑"
```

---

### Task 8: sync-website 侧接二档 + 自愈上限守卫

**Files:**
- Modify: `skills/feed/sync-website/scripts/articles_client.py`
- Modify: `skills/feed/sync-website/SKILL.md`（calibrate 小节）
- Test: `skills/feed/sync-website/tests/test_articles_client.py`（追加）

**Interfaces:**
- Consumes: Task 7 的 CLI 形状
- Produces: `async def probe_articles(list_url, selectors, transform_file=None, chrome_profile=None) -> list[dict]`、`async def set_rule(domain, list_url, selectors, sample, mode="selector", transform_file=None) -> dict`

- [ ] **Step 1: 写失败的测试（追加到 `test_articles_client.py`）**

```python
def test_probe_articles_passes_transform_file_when_given(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"articles": []}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    asyncio.run(articles_client.probe_articles(
        "https://e.com/", {"item": "div"}, transform_file="/tmp/t.js"))
    assert "--transform-file" in seen["args"]
    assert "/tmp/t.js" in seen["args"]


def test_probe_articles_omits_transform_file_when_absent(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"articles": []}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    asyncio.run(articles_client.probe_articles("https://e.com/", {"item": "div"}))
    assert "--transform-file" not in seen["args"]


def test_set_rule_rejects_an_unsupported_mode_before_shelling_out(monkeypatch):
    def boom(*args):
        raise AssertionError("不该走到 CLI")

    monkeypatch.setattr(browser_fetch_cli, "call", boom)
    with pytest.raises(ValueError, match="mode"):
        asyncio.run(articles_client.set_rule(
            "e.com", "https://e.com/", {"item": "div"}, [], mode="script"))
```

测试文件顶部需要 `import asyncio`、`import pytest`、`import articles_client`（若尚未 import）。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd skills/feed/sync-website && python3 -m pytest tests/test_articles_client.py -v`
Expected: FAIL — `AttributeError: module 'articles_client' has no attribute 'probe_articles'`

- [ ] **Step 3: 写实现（追加到 `articles_client.py`）**

```python
ALLOWED_MODES = ("selector", "selector+transform")


async def probe_articles(
    list_url: str,
    selectors: dict,
    transform_file: Optional[str] = None,
    chrome_profile: Optional[str] = None,
) -> list[dict]:
    """标定试跑，不落盘。"""
    import json as _json
    args = ["articles-probe", list_url, "--selectors", _json.dumps(selectors, ensure_ascii=False)]
    if transform_file:
        args += ["--transform-file", transform_file]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    return browser_fetch_cli.call(*args)["articles"]


async def set_rule(
    domain: str,
    list_url: str,
    selectors: dict,
    sample: list,
    mode: str = "selector",
    transform_file: Optional[str] = None,
) -> dict:
    """固化规则。

    mode 白名单在这里再挡一道 —— 自愈路径上限是二档（spec §4），而 skill
    这一层是自愈唯一的调用入口。CLI 侧也有 choices 限制，但那道限制随时
    可能因为加三档支持而放开；这一道是给自愈路径专用的，不随之放开。
    """
    import json as _json
    if mode not in ALLOWED_MODES:
        raise ValueError(f"sync-website 不能写 mode={mode!r}：自愈与常规标定上限是二档")
    args = [
        "articles-rule", "set", domain,
        "--selectors", _json.dumps(selectors, ensure_ascii=False),
        "--list-url", list_url,
        "--sample", _json.dumps(sample, ensure_ascii=False),
        "--mode", mode,
    ]
    if transform_file:
        args += ["--transform-file", transform_file]
    return browser_fetch_cli.call(*args)
```

- [ ] **Step 4: 更新 `SKILL.md` 的 calibrate 小节**

在现有第 3 步（"你（模型）读这段 HTML，写一组候选 selector"）之后插入：

```markdown
3b. 若单靠 selector 表达不了（字段要拼接或清洗、条目要过滤），再写一段
    `transform.js` 存成临时文件。它的形状是 `(items) => items`：**输入是
    第 4 步 selector 抽出的数组，不是页面**，跑在 `about:blank` 的隔离
    上下文里，拿不到目标站的 DOM、cookie 和登录态。第 4 步用
    `--transform-file <路径>` 一起试跑。
```

第 7 步固化改成：

```markdown
7. 两关都过 → 固化：
   - 只用 selector：`<browser-fetch> articles-rule set <domain> --selectors '<json>' --list-url '<url>' --sample '<前3条JSON>'`
   - 用了 transform：同上再加 `--mode selector+transform --transform-file <路径>`
```

在 calibrate 小节末尾加一句：

```markdown
**本流程的上限是二档。** 需要在目标页面里跑任意 JS 才能抽的站，走的是另一条
需要人工发起的路径，不在这里，也不会被 `run` 的自愈自动触发。
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd skills/feed/sync-website && python3 -m pytest tests -q`
Expected: 全绿（原 80 条 + 新 3 条 = 83 passed）

- [ ] **Step 6: Commit**

```bash
git add skills/feed/sync-website/
git commit -m "feat(sync-website): 标定支持二档 transform，自愈上限守卫"
```

---

### Task 8.5: 阶段一验收 —— 真实站点回归

**Files:** 无改动，只跑验证

- [ ] **Step 1: 三套测试全绿**

```bash
cd tools/browser-fetch && .venv/bin/pytest -q
cd ../roster && .venv/bin/pytest -q
cd ../.. && npm test
```

Expected: browser-fetch 与 sync-website 均只增不减；roster 与 npm test 与开工前基线一致（本计划不碰它们）。

- [ ] **Step 2: 确认现有两条规则被自动迁移且行为不变**

```bash
cd tools/browser-fetch
./browser-fetch.sh articles-rule list | python3 -m json.tool | head -30
./browser-fetch.sh articles https://simonwillison.net/ | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d['articles']),'条');print(d['articles'][0])"
./browser-fetch.sh articles https://claude.com/blog | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d['articles']),'条');print(d['articles'][0])"
```

Expected: 两个站都仍然抽得到条目，`claude.com` 15 条、URL 绝对、`date_text` 形如 `Sep 2, 2026`。**两条规则此时可能仍是扁平文件**（读路径兼容，迁移只在写入时发生）——这是设计意图，不是缺陷。

- [ ] **Step 3: 触发一次写入，确认迁移真的发生**

对 `simonwillison.net` 重跑一次 `articles-rule set`（selector 用 `articles-rule get` 里现有的那组），然后：

```bash
ls ~/.hskill/browser-fetch/contexts/site_rules/
```

Expected: 出现 `simonwillison.net/` 目录，且 `simonwillison.net.json` 已消失。

- [ ] **Step 4: 停下来，把结果报给用户**

阶段一到此结束。**不要自动开始阶段二。** spec §10 的产品判断认为目前 2 个站、0 个真的需要三档，样本量支撑不了"现在就做三档"；是否继续由用户决定。

---

# 阶段二：三档全 JS + 评审流程

> **开工前提**：用户在阶段一验收后明确要求继续。

---

### Task 9: site_rules 支持 script 档

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/site_rules.py`
- Test: `tools/browser-fetch/tests/test_site_rules_dirs.py`（追加）

**Interfaces:**
- Consumes: Task 2–4
- Produces: `SUPPORTED_MODES` 扩为 `{"selector", "selector+transform", "script"}`；`get_rule` 在 script 档返回 `"extract_js": str`；`set_rule` 新增 `script_js` / `review_md` / `reviewer` 参数

- [ ] **Step 1: 写失败的测试（追加）**

```python
def test_script_rule_round_trips_with_its_review(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", None, [], "t",
        mode="script", script_js="() => []", review_md="# 评估\n可批准\n",
        reviewer="review-subagent",
    )
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["mode"] == "script"
    assert rule["extract_js"] == "() => []"
    assert rule["approval"]["reviewer"] == "review-subagent"
    d = tmp_path / "site_rules" / "example.com"
    assert (d / "extract.js").exists()
    assert (d / "review.md").read_text(encoding="utf-8").startswith("# 评估")


def test_script_mode_must_not_carry_selectors(tmp_path):
    with pytest.raises(ValueError, match="selectors"):
        site_rules.set_rule(
            tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
            mode="script", script_js="() => []", review_md="ok", reviewer="r",
        )


def test_script_mode_without_a_review_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="review"):
        site_rules.set_rule(
            tmp_path, "example.com", "https://example.com/", None, [], "t",
            mode="script", script_js="() => []", reviewer="r",
        )


def test_script_rule_missing_extract_js_on_disk_is_corrupt(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", None, [], "t",
        mode="script", script_js="() => []", review_md="ok", reviewer="r",
    )
    (tmp_path / "site_rules" / "example.com" / "extract.js").unlink()
    with pytest.raises(site_rules.RuleCorruptError, match="extract.js"):
        site_rules.get_rule(tmp_path, "example.com")


def test_script_rule_missing_review_on_disk_is_corrupt(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", None, [], "t",
        mode="script", script_js="() => []", review_md="ok", reviewer="r",
    )
    (tmp_path / "site_rules" / "example.com" / "review.md").unlink()
    with pytest.raises(site_rules.RuleCorruptError, match="review.md"):
        site_rules.get_rule(tmp_path, "example.com")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules_dirs.py -k script -v`
Expected: FAIL — `ValueError: unsupported mode: 'script'`

- [ ] **Step 3: 写实现**

`site_rules.py` 顶部常量改为：

```python
SUPPORTED_MODES = frozenset({"selector", "selector+transform", "script"})

TRANSFORM_FILE = "transform.js"
SCRIPT_FILE = "extract.js"
REVIEW_FILE = "review.md"
```

`_validate` 改为：

```python
def _validate(rule: dict, domain_dir: Path) -> None:
    domain = rule.get("domain")
    mode = rule.get("mode")
    if mode not in SUPPORTED_MODES:
        raise RuleCorruptError(f"{domain}: 不支持的 mode {mode!r}")

    has_transform = (domain_dir / TRANSFORM_FILE).exists()
    has_script = (domain_dir / SCRIPT_FILE).exists()
    has_review = (domain_dir / REVIEW_FILE).exists()

    if mode == "script":
        if rule.get("selectors"):
            raise RuleCorruptError(f"{domain}: mode 'script' 不该带 selectors")
        if not has_script:
            raise RuleCorruptError(f"{domain}: mode 'script' 缺少 {SCRIPT_FILE}")
        if not has_review:
            raise RuleCorruptError(f"{domain}: mode 'script' 缺少 {REVIEW_FILE}")
        if not rule.get("approval"):
            raise RuleCorruptError(f"{domain}: mode 'script' 缺少 approval")
        if has_transform:
            raise RuleCorruptError(f"{domain}: mode 'script' 不该存在 {TRANSFORM_FILE}")
        return

    if not rule.get("selectors"):
        raise RuleCorruptError(f"{domain}: mode {mode!r} 缺少 selectors")
    if has_script:
        raise RuleCorruptError(f"{domain}: mode {mode!r} 不该存在 {SCRIPT_FILE}")
    if mode == "selector+transform" and not has_transform:
        raise RuleCorruptError(f"{domain}: mode {mode!r} 缺少 {TRANSFORM_FILE}")
    if mode == "selector" and has_transform:
        raise RuleCorruptError(f"{domain}: mode {mode!r} 不该存在 {TRANSFORM_FILE}")
```

`get_rule` 里读代码那段改为：

```python
        if rule["mode"] == "selector+transform":
            rule["transform_js"] = (domain_dir / TRANSFORM_FILE).read_text(encoding="utf-8")
        elif rule["mode"] == "script":
            rule["extract_js"] = (domain_dir / SCRIPT_FILE).read_text(encoding="utf-8")
```

`set_rule` 改为：

```python
def set_rule(
    data_dir: Path,
    domain: str,
    list_url: str,
    selectors: Optional[dict],
    sample: list,
    calibrated_at: str,
    mode: str = "selector",
    transform_js: Optional[str] = None,
    script_js: Optional[str] = None,
    review_md: Optional[str] = None,
    reviewer: Optional[str] = None,
) -> None:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported mode: {mode!r}")

    if mode == "script":
        if selectors:
            raise ValueError("mode 'script' must not carry selectors")
        if not script_js:
            raise ValueError("mode 'script' requires script_js")
        if not review_md or not reviewer:
            raise ValueError("mode 'script' requires review_md and reviewer")
        if transform_js:
            raise ValueError("mode 'script' must not carry transform_js")
    else:
        if not selectors:
            raise ValueError(f"mode {mode!r} requires selectors")
        if script_js or review_md:
            raise ValueError(f"mode {mode!r} must not carry script_js/review_md")
        if mode == "selector+transform" and not transform_js:
            raise ValueError("mode 'selector+transform' requires transform_js")
        if mode == "selector" and transform_js:
            raise ValueError("mode 'selector' must not carry transform_js")

    target = _domain_dir(data_dir, domain)
    tmp = target.with_name(target.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    payload = {
        "schema_version": 2,
        "domain": domain,
        "list_url": list_url,
        "mode": mode,
        "calibrated_at": calibrated_at,
        "sample": sample,
    }
    if selectors:
        payload["selectors"] = selectors
    if mode == "script":
        payload["approval"] = {
            "approved_at": calibrated_at,
            "reviewer": reviewer,
            "review_file": REVIEW_FILE,
        }

    (tmp / "rule.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if transform_js:
        (tmp / TRANSFORM_FILE).write_text(transform_js, encoding="utf-8")
    if script_js:
        (tmp / SCRIPT_FILE).write_text(script_js, encoding="utf-8")
    if review_md:
        (tmp / REVIEW_FILE).write_text(review_md, encoding="utf-8")

    _swap_dir(tmp, target)

    flat = _flat_path(data_dir, domain)
    if flat.exists():
        flat.unlink()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_site_rules.py tests/test_site_rules_dirs.py -v`
Expected: 全绿

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch/browser_fetch/site_rules.py tools/browser-fetch/tests/test_site_rules_dirs.py
git commit -m "feat(browser-fetch): site_rules 支持 script 档与批准记录"
```

---

### Task 10: JS 静态扫描（材料，非门禁）

**Files:**
- Create: `tools/browser-fetch/browser_fetch/static_scan.py`
- Test: `tools/browser-fetch/tests/test_static_scan.py`

**Interfaces:**
- Consumes: 无
- Produces: `scan_js(source: str) -> dict`，形如 `{"hits": [{"pattern": str, "line": int, "text": str}], "note": str}`

- [ ] **Step 1: 写失败的测试**

```python
"""静态扫描的单元测试 —— spec §5.3。

刻意不测"能挡住绕过"：这是评审材料不是门禁，黑名单靠字符串拼接就能绕。
测的是"命中时点得准"，以及"输出里始终带着它不是门禁的声明"。
"""
from browser_fetch.static_scan import scan_js


def test_clean_script_has_no_hits():
    assert scan_js("() => [...document.querySelectorAll('a')].map(a => a.href)")["hits"] == []


def test_flags_network_access():
    hits = scan_js("() => { fetch('https://evil'); return []; }")["hits"]
    assert [h["pattern"] for h in hits] == ["fetch"]
    assert hits[0]["line"] == 1


def test_flags_cookie_and_storage_access():
    src = "() => {\n  const c = document.cookie;\n  localStorage.setItem('k', c);\n  return [];\n}"
    patterns = {h["pattern"] for h in scan_js(src)["hits"]}
    assert patterns == {"document.cookie", "localStorage"}


def test_reports_the_line_number_of_each_hit():
    src = "() => {\n\n  return eval('1');\n}"
    hit = scan_js(src)["hits"][0]
    assert hit["pattern"] == "eval"
    assert hit["line"] == 3


def test_output_always_states_it_is_not_a_gate():
    for src in ("() => []", "() => fetch('x')"):
        assert "不是门禁" in scan_js(src)["note"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_static_scan.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'browser_fetch.static_scan'`

- [ ] **Step 3: 写实现**

```python
"""三档 extract.js 的静态扫描 —— spec §5.3。

**产出是评审 subagent 的输入材料，不是门禁。** 黑名单靠字符串拼接就能绕
（`window["fe"+"tch"]`），当门禁只会给假安全感 —— 一段"通过了安全扫描"的
代码比一段没扫过的更难被怀疑。所以 scan_js 只报告，从不拒绝，且输出里
始终带着这句声明。
"""
import re

_NOTE = (
    "以下命中是评审材料，不是门禁：黑名单可被字符串拼接绕过，"
    "没有命中不代表这段代码安全。"
)

_PATTERNS = [
    ("fetch", re.compile(r"\bfetch\s*\(")),
    ("XMLHttpRequest", re.compile(r"\bXMLHttpRequest\b")),
    ("document.cookie", re.compile(r"\bdocument\s*\.\s*cookie\b")),
    ("localStorage", re.compile(r"\blocalStorage\b")),
    ("sessionStorage", re.compile(r"\bsessionStorage\b")),
    ("indexedDB", re.compile(r"\bindexedDB\b")),
    ("eval", re.compile(r"\beval\s*\(")),
    ("Function", re.compile(r"\bnew\s+Function\s*\(|\bFunction\s*\(")),
    ("sendBeacon", re.compile(r"\bsendBeacon\s*\(")),
    ("WebSocket", re.compile(r"\bWebSocket\b")),
]


def scan_js(source: str) -> dict:
    hits = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        for name, pattern in _PATTERNS:
            if pattern.search(line):
                hits.append({"pattern": name, "line": lineno, "text": line.strip()})
    return {"hits": hits, "note": _NOTE}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_static_scan.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch/browser_fetch/static_scan.py tools/browser-fetch/tests/test_static_scan.py
git commit -m "feat(browser-fetch): 三档 JS 静态扫描，只产材料不做门禁"
```

---

### Task 11: script 档求值 + `allow_script` 显式守卫

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/core.py`
- Test: `tools/browser-fetch/tests/test_cli_articles_script.py`（新建）

**Interfaces:**
- Consumes: Task 9 的 `get_rule`、Task 1 的 `normalize_articles`
- Produces:
  - `async def _run_script(list_url, script_js, chrome_profile) -> list[dict]`
  - `async def fetch_articles_probe(url, selectors=None, chrome_profile=None, transform_js=None, script_js=None, allow_script=False) -> dict`
  - `async def set_site_rule(..., allow_script: bool = False)`

- [ ] **Step 1: 写失败的测试**

```python
"""三档 script 的求值与守卫 —— spec §4/§10。

spec §10 点名："--allow-script 只能由人发起"这条是**不可测的**，它靠的是
调用路径里没传那个参数。所以实现要求把它写成显式 allow_script=False 参数
并在入口拒绝，而不是靠"没传"。这里测的正是那道显式拒绝。
"""
import json

from browser_fetch import core

SCRIPT = (
    "() => [...document.querySelectorAll('div.entry')].map(el => ({"
    "title: el.querySelector('h3 a').textContent,"
    "url: el.querySelector('h3 a').href, date_text: ''}))"
)


async def test_script_probe_requires_allow_script():
    try:
        await core.fetch_articles_probe(
            "https://example.com/", script_js=SCRIPT, allow_script=False)
    except ValueError as e:
        assert "allow_script" in str(e)
    else:
        raise AssertionError("未设 allow_script 时不该放行 script 试跑")


async def test_set_site_rule_requires_allow_script_for_script_mode():
    try:
        await core.set_site_rule(
            "example.com", "https://example.com/", None, [],
            mode="script", script_js=SCRIPT, review_md="ok",
            reviewer="r", allow_script=False)
    except ValueError as e:
        assert "allow_script" in str(e)
    else:
        raise AssertionError("未设 allow_script 时不该放行 script 落盘")


def test_script_probe_runs_on_the_target_page(run_cli, articles_fixture_server, tmp_path):
    script = tmp_path / "s.js"
    script.write_text(SCRIPT, encoding="utf-8")
    proc, payload = run_cli(
        "articles-probe", articles_fixture_server,
        "--script-file", str(script), "--allow-script")
    assert proc.returncode == 0, proc.stderr
    assert len(payload["articles"]) == 3
    assert payload["articles"][0]["url"].endswith("/posts/1")


def test_script_probe_without_the_flag_is_rejected(run_cli, articles_fixture_server, tmp_path):
    script = tmp_path / "s.js"
    script.write_text(SCRIPT, encoding="utf-8")
    proc, _ = run_cli("articles-probe", articles_fixture_server, "--script-file", str(script))
    assert proc.returncode == 2
    assert "allow_script" in proc.stderr or "allow-script" in proc.stderr


def test_script_rule_is_applied_on_the_production_path(run_cli, articles_fixture_server, tmp_path):
    script = tmp_path / "s.js"
    script.write_text(SCRIPT, encoding="utf-8")
    review = tmp_path / "r.md"
    review.write_text("# 评估\n可批准\n", encoding="utf-8")
    proc, _ = run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--list-url", articles_fixture_server,
        "--mode", "script", "--script-file", str(script),
        "--review-file", str(review), "--allow-script")
    assert proc.returncode == 0, proc.stderr

    proc, payload = run_cli("articles", articles_fixture_server)
    assert proc.returncode == 0, proc.stderr
    assert len(payload["articles"]) == 3


def test_script_relative_href_is_still_absolutized(run_cli, articles_fixture_server, tmp_path):
    # 三档 JS 若返回 getAttribute('href') 这种原始相对值，Python 侧的
    # urljoin 必须兜住 —— 相对 URL 会静默破坏游标与归档去重（spec §7.2）。
    script = tmp_path / "s.js"
    script.write_text(
        "() => [...document.querySelectorAll('div.entry')].map(el => ({"
        "title: 'x', url: el.querySelector('h3 a').getAttribute('href'), date_text: ''}))",
        encoding="utf-8")
    proc, payload = run_cli(
        "articles-probe", articles_fixture_server,
        "--script-file", str(script), "--allow-script")
    assert proc.returncode == 0, proc.stderr
    assert all(a["url"].startswith("http://127.0.0.1:") for a in payload["articles"])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles_script.py -v`
Expected: FAIL — `fetch_articles_probe() got an unexpected keyword argument 'script_js'`

- [ ] **Step 3: 写实现（`core.py`）**

新增：

```python
async def _run_script(list_url: str, script_js: str, chrome_profile: Optional[str]) -> list[dict]:
    """三档：在目标页面里跑任意抽取 JS。

    能力等同于 evaluate_js，所以进入这条路径必须经过人工发起的
    allow_script（spec §4）。登录态照旧在 JS 之外注入 —— 抽取脚本不需要、
    也不应该碰任何凭据（spec §7.1）。
    """
    return await _scrape_with_js(list_url, script_js, chrome_profile)
```

把 `_scrape_articles` 里"构建 JS → 建上下文 → goto → evaluate → 归一化"这段抽成共用的 `_scrape_with_js(list_url, js, chrome_profile)`，`_scrape_articles` 改为：

```python
async def _scrape_articles(
    list_url: str, selectors: dict, chrome_profile: Optional[str]
) -> list[dict]:
    from browser_fetch.extractors import build_articles_js
    return await _scrape_with_js(list_url, build_articles_js(selectors), chrome_profile)
```

`fetch_articles` 加 script 分支：

```python
    mode = rule.get("mode", "selector")
    if mode == "script":
        articles = await _run_script(url, rule["extract_js"], chrome_profile)
    else:
        articles = await _scrape_articles(url, rule["selectors"], chrome_profile)
        if mode == "selector+transform":
            articles = await _run_transform(articles, rule["transform_js"], url)
    return {"domain": domain, "articles": articles}
```

`fetch_articles_probe` 与 `set_site_rule` 加守卫：

```python
async def fetch_articles_probe(
    url: str,
    selectors: Optional[dict] = None,
    chrome_profile: Optional[str] = None,
    transform_js: Optional[str] = None,
    script_js: Optional[str] = None,
    allow_script: bool = False,
) -> dict:
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(f"Rejected URL with scheme '{parsed_url.scheme}' — only http/https allowed")

    if script_js and not allow_script:
        raise ValueError("script 试跑需要 allow_script —— 三档只能由人发起（spec §4）")
    if script_js:
        return {"articles": await _run_script(url, script_js, chrome_profile)}

    if not selectors:
        raise ValueError("selectors is required unless script_js is given")
    articles = await _scrape_articles(url, selectors, chrome_profile)
    if transform_js:
        articles = await _run_transform(articles, transform_js, url)
    return {"articles": articles}


async def set_site_rule(
    domain: str,
    list_url: str,
    selectors: Optional[dict],
    sample: list,
    mode: str = "selector",
    transform_js: Optional[str] = None,
    script_js: Optional[str] = None,
    review_md: Optional[str] = None,
    reviewer: Optional[str] = None,
    allow_script: bool = False,
) -> dict:
    from datetime import datetime, timezone

    if mode == "script" and not allow_script:
        raise ValueError("写 script 档需要 allow_script —— 三档只能由人发起（spec §4）")

    calibrated_at = datetime.now(timezone.utc).isoformat()
    site_rules.set_rule(
        _data_dir(), domain, list_url, selectors, sample, calibrated_at,
        mode=mode, transform_js=transform_js, script_js=script_js,
        review_md=review_md, reviewer=reviewer,
    )
    return {"ok": True, "domain": domain, "mode": mode, "calibrated_at": calibrated_at}
```

- [ ] **Step 4: 写实现（`cli.py`）**

`articles-probe` 与 `articles-rule set` 各加三个参数：

```python
    p_articles_probe.add_argument("--script-file", default=None, dest="script_file",
                                  help="三档：抽取 JS 源文件，'-' 读 stdin。需配 --allow-script")
    p_articles_probe.add_argument("--allow-script", action="store_true", dest="allow_script",
                                  help="放行三档。只应由人在会话里主动给出")
```

`--selectors` 在 probe 上从 `required=True` 改为 `default=None`（三档不需要它），核心的必填校验由 `core.fetch_articles_probe` 承担。

```python
    ar_set.add_argument("--script-file", default=None, dest="script_file")
    ar_set.add_argument("--review-file", default=None, dest="review_file")
    ar_set.add_argument("--reviewer", default=None)
    ar_set.add_argument("--allow-script", action="store_true", dest="allow_script")
```

`--mode` 的 `choices` 扩为 `("selector", "selector+transform", "script")`；`--selectors` 从 `required=True` 改为 `default=None`。

handler 更新为把这些参数传下去，`--review-file` 用 `_read_js` 读（它只是"读文件或 stdin"，不限 JS）。

- [ ] **Step 5: 跑测试确认通过**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles_script.py -v`
Expected: 6 passed

- [ ] **Step 6: 跑 browser-fetch 全量**

Run: `cd tools/browser-fetch && .venv/bin/pytest -q`
Expected: 全绿，已有用例除被点名那条外零改动

- [ ] **Step 7: Commit**

```bash
git add tools/browser-fetch/
git commit -m "feat(browser-fetch): script 档求值与 allow_script 显式守卫"
```

---

### Task 12: sync-website 的三档流程与评审（SKILL.md）

**Files:**
- Modify: `skills/feed/sync-website/SKILL.md`
- Create: `skills/feed/sync-website/references/script-tier-review.md`

**Interfaces:**
- Consumes: Task 10 的 `static_scan`、Task 11 的 CLI 形状
- Produces: 无代码接口，只有流程文档

- [ ] **Step 1: 写 `references/script-tier-review.md`**

```markdown
# 三档（全 JS）抽取器的评审规程

三档意味着一段任意 JS 会在目标页面里执行，而该页面带着共享 `chrome_profile`
的登录态。所以它只能由人在会话里主动发起（`--allow-script`），且必须走完
下面的评审。

## 谁评审

**写这段 JS 的 Agent 不能给自己签字。** 必须派一个独立 subagent 做评审。

理由跟 handoff skill 里"`已验收` 只能由第二方写"完全一样：写的人一旦能自己
签字，签字这个动作的信息量就退化成"写的人说没问题"——而这个信息在"我写完了"
里已经有了，两者变成同义词。风险还会反向放大，一份自我认证的评估通常附着
一套看起来很可信的理由，比没有评估更难被怀疑。

## 评审 subagent 的输入

1. `extract.js` 全文
2. `articles-probe --script-file ... --allow-script` 的抽取结果（前 5 条）
3. 目标站域名与列表页 URL
4. 静态扫描结果：
   `python3 -c "import sys;sys.path.insert(0,'<browser-fetch>/');from browser_fetch.static_scan import scan_js;import json;print(json.dumps(scan_js(open('<extract.js>').read()),ensure_ascii=False,indent=2))"`

**静态扫描是材料不是门禁。** 没有命中不代表安全，有命中也不自动否决 ——
它只是让评审知道该重点看哪几行。

## 评估意见必须回答的四件事

1. **这段代码读了什么** —— DOM 选择器、全局变量、`window.*`
2. **有没有网络请求 / cookie / storage 访问** —— 有就点名在哪一行、做什么。
   一个正当的抽取器**没有任何理由碰 cookie**：登录态在 JS 之外注入，页面
   拿到手时已经是登录态视角（spec §7.1）。碰了就是异常信号。
3. **抽取逻辑一句话概括**
4. **为什么 selector 或 selector+transform 做不到** —— 答不上来就说明不该
   升三档，结论应给"不建议"

另外检查一条：**返回的 `url` 是不是 `.href` 而不是 `getAttribute('href')`**。
Python 侧的 `urljoin` 会兜住相对 URL，但页面带 `<base href>` 时 urljoin 会
算错（spec §7.3 的已知上限）。

## 结论格式

三选一：`可批准` / `有条件可批准（附条件）` / `不建议（附理由）`。

## 落盘

评估意见全文写进 `review.md`，随规则一起存。没有它，三个月后没人知道当初
批的是什么、基于什么理由批的。
```

- [ ] **Step 2: 更新 `SKILL.md`**

在 calibrate 小节之后新增：

```markdown
### calibrate --allow-script（三档，只能由用户主动发起）

**`run` 的自愈路径永远到不了这里。** 只有用户在会话里显式说
`/sync-website calibrate <handle> --allow-script` 才进入。

1. 先确认二档真的不够：selector + transform 都试过并说明为什么不行。
   说不出来就不要升三档。
2. 写 `extract.js`（形状 `() => [{title, url, date_text}, ...]`，`url` 必须
   用 `.href`），存成临时文件。
3. `<browser-fetch> articles-probe <url> --script-file <路径> --allow-script`
   试跑，过 `scripts/calibration_gate.py` 的机械门槛。
4. **派独立 subagent 评审**，规程见
   [references/script-tier-review.md](references/script-tier-review.md)。
   写 JS 的这个会话不能自己评自己。
5. 把评估意见摆给用户。**用户批准的是这份意见，不是代码。**
6. 用户通过后落盘：
   `<browser-fetch> articles-rule set <domain> --list-url '<url>' --mode script --script-file <路径> --review-file <评估意见文件> --reviewer '<subagent 标识>' --allow-script`

三档规则失效后**不自愈、不自动降级**——自愈会绕过评审这道门。`run` 只会
把它记进 `failures` 等你处理。
```

在 `run` 小节的自愈段落里加一句：

```markdown
自愈的上限是二档。渠道当前是三档（`mode: "script"`）时，抽空或报错一律记入
`failures`，**不重新标定**——自愈重写 JS 等于绕过人工批准。
```

- [ ] **Step 3: 验证 SKILL.md 格式**

Run: `npm test`
Expected: fail 0；`skills.bats` 的 8 条格式校验全过

- [ ] **Step 4: Commit**

```bash
git add skills/feed/sync-website/
git commit -m "docs(sync-website): 三档评审规程与 allow-script 流程"
```

---

### Task 13: run 侧三档不自愈 + digest 标注

**Files:**
- Modify: `skills/feed/sync-website/scripts/fetch_new_articles.py`
- Modify: `skills/feed/sync-website/scripts/digest.py`
- Modify: `skills/feed/sync-website/scripts/articles_client.py`
- Test: `skills/feed/sync-website/tests/test_fetch_new_articles.py`、`tests/test_digest.py`（各追加）

**Interfaces:**
- Consumes: Task 11 的 CLI
- Produces: `report` 新增 `"script_tier": [handle, ...]`；`articles_client.get_rule_mode(domain) -> str | None`

- [ ] **Step 1: 写失败的测试**

追加到 `tests/test_fetch_new_articles.py`：

```python
def test_script_tier_channel_is_not_recalibrated_on_empty(fake_roster, fake_fetch, monkeypatch):
    """三档抽空只记 failures —— 自愈重写 JS 等于绕过人工批准（spec §6）。"""
    fake_roster([{"handle": "a", "url": "https://a.example/"}])
    fake_fetch({"https://a.example/": []})
    monkeypatch.setattr(articles_client, "get_rule_mode", lambda domain: "script")

    report = run_fetch()
    assert "a" in report["failures"]
    assert report["needs_calibration"] == {}
    assert report["script_tier"] == ["a"]


def test_selector_tier_channel_still_gets_recalibrated_on_empty(fake_roster, fake_fetch, monkeypatch):
    fake_roster([{"handle": "a", "url": "https://a.example/"}])
    fake_fetch({"https://a.example/": []})
    monkeypatch.setattr(articles_client, "get_rule_mode", lambda domain: "selector")

    report = run_fetch()
    assert "a" in report["needs_calibration"]
```

（`fake_roster` / `fake_fetch` / `run_fetch` 沿用该文件里已有的同名 fixture 与 helper，不新造。）

追加到 `tests/test_digest.py`：

```python
def test_script_tier_channels_are_marked_in_the_digest(tmp_path):
    report = {
        "run_time": "2026-09-03T00:00:00+00:00",
        "new": {"a": [{"title": "T", "translated": "标题", "url": "https://a.example/1", "date_text": "d"}]},
        "baselines": {}, "failures": {}, "needs_calibration": {},
        "recalibrated": [], "script_tier": ["a"],
    }
    out = render(report)
    assert "人工批准的 JS 规则" in out


def test_non_script_channels_carry_no_such_mark(tmp_path):
    report = {
        "run_time": "2026-09-03T00:00:00+00:00",
        "new": {"a": [{"title": "T", "translated": "标题", "url": "https://a.example/1", "date_text": "d"}]},
        "baselines": {}, "failures": {}, "needs_calibration": {},
        "recalibrated": [], "script_tier": [],
    }
    assert "人工批准的 JS 规则" not in render(report)
```

（`render` 沿用该文件里已有的 helper。）

- [ ] **Step 2: 跑测试确认失败**

Run: `cd skills/feed/sync-website && python3 -m pytest tests/test_fetch_new_articles.py tests/test_digest.py -k "script_tier or selector_tier" -v`
Expected: FAIL — `articles_client` 没有 `get_rule_mode`；`report` 没有 `script_tier`

- [ ] **Step 3: 写实现**

`articles_client.py` 追加：

```python
async def get_rule_mode(domain: str) -> Optional[str]:
    """读该域名当前规则的档位；没有规则时返回 None。

    run 用它区分"该自愈"和"该记 failures"：三档不自愈（spec §6）。
    """
    try:
        return browser_fetch_cli.call("articles-rule", "get", domain).get("mode", "selector")
    except RuntimeError as e:
        if str(e).startswith("NO_RULE:"):
            return None
        raise
```

`fetch_new_articles.py` 里，抽空/`NoRuleError` 的分支改为先查档位：三档进
`failures` 并记入 `report["script_tier"]`，其余照旧进 `needs_calibration`。
`report` 初始化处加 `"script_tier": []`。

`digest.py` 里，渲染某渠道小节时若该 handle 在 `report.get("script_tier", [])`
中，标题行追加 `[人工批准的 JS 规则]`，与已有的 `[本轮重新标定过]` 标注并列。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd skills/feed/sync-website && python3 -m pytest tests -q`
Expected: 全绿

- [ ] **Step 5: Commit**

```bash
git add skills/feed/sync-website/
git commit -m "feat(sync-website): 三档不自愈，摘要标注人工批准的规则"
```

---

### Task 14: 阶段二验收

**Files:** 无改动

- [ ] **Step 1: 三套测试全绿**

```bash
cd tools/browser-fetch && .venv/bin/pytest -q
cd ../roster && .venv/bin/pytest -q
cd ../.. && npm test
cd skills/feed/sync-website && python3 -m pytest tests -q
```

- [ ] **Step 2: 确认守卫真的挡得住**

```bash
cd tools/browser-fetch
echo '() => []' > /tmp/s.js
./browser-fetch.sh articles-probe https://example.com/ --script-file /tmp/s.js; echo "exit=$?"
```

Expected: exit 2，stderr 提到 `allow_script`。

```bash
grep -rn "allow_script\|allow-script" ../../skills/feed/sync-website/scripts/
```

Expected: skill 的 `scripts/` 下**没有任何一处传 `--allow-script`** —— 自愈路径够不着三档。有的话就是守卫被破坏。

- [ ] **Step 3: 确认二档隔离仍成立**

Run: `cd tools/browser-fetch && .venv/bin/pytest tests/test_cli_articles_transform.py -k "cookies or target_page" -v`
Expected: 2 passed

- [ ] **Step 4: 报告结果，等用户验收**

不要自行把状态标成完成 —— 按仓库惯例，验收由发起方逐条实跑后判定。

---

## Self-Review

**Spec 覆盖检查**

| spec 小节 | 实现任务 |
|---|---|
| §2 三档与执行环境 | Task 6（二档隔离）、Task 11（三档求值） |
| §3.1 目录即规则 | Task 3 |
| §3.2 rule.json / mode / approval | Task 2、3、9 |
| §3.3 一致性与原子性 | Task 3（`_swap_dir`）、Task 4（跳过 `.tmp`/`.old`） |
| §3.4 迁移 | Task 2（读兼容）、Task 3（写迁移）、Task 8.5 Step 3（实测） |
| §4 谁能写到哪一档 | Task 8（skill 侧白名单）、Task 11（`allow_script`）、Task 14 Step 2（实测守卫） |
| §5 三档评审 | Task 10（静态扫描）、Task 12（规程与流程） |
| §6 失效与维护 | Task 13 |
| §7.1 登录态本来就有 | 无需实现；Task 12 的评审规程引用它作为"碰 cookie 即异常"的依据 |
| §7.2/§7.3 归一化 | Task 1、Task 5、Task 11 Step 1 的相对 href 用例 |
| §8 边界 | Global Constraints |

**未覆盖且刻意不做**：spec §9 代价表、§10 判断、§11 把握度是设计论证，不产生实现任务。

**类型一致性**：`normalize_articles(raw_items, list_url)` 在 Task 1 定义，Task 5、6、11 调用签名一致。`set_rule` 的参数顺序在 Task 3 定下（`data_dir, domain, list_url, selectors, sample, calibrated_at, mode=, transform_js=`），Task 9 只在末尾追加关键字参数，已有位置调用不受影响。`get_rule_mode` 在 Task 13 定义并在同一任务内使用。

**已知的计划弱点**（实现时若撞上，停下来回报而不是自行绕开）：

1. Task 7 第三条测试依赖 `run_cli` 同测试内共享 `tmp_path` 下的规则库，且直接按路径 `tmp_path/"data"/"site_rules"/...` 去删文件。若 `conftest.py` 的 `run_cli` 后续改了数据目录布局，这条测试会以令人困惑的方式失败。
2. Task 13 的三条改动（`articles_client` / `fetch_new_articles` / `digest`）没有给出逐行的最终代码，只给了改动位置与语义。这三个文件的现有结构需要执行者先读一遍再改——这是本计划里最不"照抄即可"的一个任务。
3. `_swap_dir` 在"改名后、替换前"崩溃会留下 `.old` 目录且规则暂时读不到。Task 4 的 `list_rules` 会跳过 `.old`，但**没有任何代码会自动恢复它**——spec §3.3 说"留着给人看是怎么断的"，这是刻意的，但没有任何测试覆盖这个中断点。
