# 名册渠道键归一化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修掉一个现行缺陷——同一个 YouTube/X 渠道用不同大小写的 URL `add` 两次会变成两个人——办法是在 roster 里加一个归一化的 `key` 字段，所有查询入口（`registry` 查找、`state` 的 `get`/`set`/`fail`/`drop`）都按 `key` 比较而不是按原始 `handle` 精确比较，并提供一个幂等的 schema 迁移命令。

**Architecture:** `urls.py` 新增 `normalize()`（去前导 `@`、strip、转小写），`channel_key()` 内部改用它，这样 `state.py` 的三个入口函数自动受益、不用改代码。`registry.py` 的每个渠道对象新增 `key` 字段（写入时算好，`handle` 保留原始大小写做展示），`find_channel` 改成按 `key` 比较。新增 `migrate_schema.py` 一次性把 `registry.json` 回填 `key`、把 `state.json` 的游标键重写成归一形态，两个文件在同一次调用里一起改。

**Tech Stack:** Python 3.11+，`tools/roster`（`roster` CLI），pytest。

**Spec:** `docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md`（本次权威依据，含实测复现、九条验收标准、四项未验证项）。

**范围边界（本计划只覆盖 `harveyz-skill` 仓库）：** spec §4（scholia 的 join 精确比较）**不在本计划内**——那部分在另一个不隔离的会话里、在 `~/Projects/scholia` 仓库单独开分支做，因为当前会话被 worktree 隔离，git 命令无法作用到别的仓库。本计划完成后，criterion 6（scholia 的 `watched` 结果不变）需要等 scholia 那边完成后才能验。

## Global Constraints

- 归一规则固定为：去前导 `@`、`strip()`、转小写（spec §2.1，定义原文在 `2026-09-15-video-creator-index-design.md` §2.3）。
- `handle` 字段保留原始大小写，不能被 `key` 取代（spec §2.2）——它是 `list` 的展示字段。
- `schema_version` 1 → 2（spec §2.1）。
- 新增 CLI 子命令必须叫 `roster migrate-schema`，不能复用现有的 `migrate`（后者是旧 watchlist 导入，语义不同，spec §3.3）。
- `registry.json` 与 `state.json` 的迁移必须在同一次 `migrate_schema()` 调用里完成，不能拆成两步（spec §3.3，"两个文件必须一起迁"）。
- **不改** `sync-xtimeline` / `sync-ytchannel` / `sync-website` 的代码（spec §3.0，零改动是验收第 9 条守的承诺）。
- **不动** creator 的主键 `id`，不碰画像层 `profiles.py`。
- **不删** scholia 侧的归一函数——不在本计划范围内（那是 scholia 仓库的事）。
- **不做** spec §5.1 提到的加固（`registry list` 时校验 `key == normalize(handle)`）——已知有价值，本次不做。
- **不修** state.json 里的孤儿游标 `x:fanli1688`——只需在 Task 8 给出成因结论，不做修复。

---

## Task 1: `urls.py` —— 归一函数 + `channel_key` 内建归一

**Files:**
- Modify: `tools/roster/roster/urls.py`
- Test: `tools/roster/tests/test_urls.py`

**Interfaces:**
- Produces: `normalize(handle: str) -> str`；`channel_key(platform: str, handle: str) -> str`（签名不变，内部行为变了——现在会先归一 `handle` 再拼接）。

- [ ] **Step 1: 写失败测试**

在 `tools/roster/tests/test_urls.py` 末尾追加：

```python
@pytest.mark.parametrize("handle,expected", [
    ("TingHu888", "tinghu888"),
    ("@TingHu888", "tinghu888"),
    ("  @Foo  ", "foo"),
    ("already-lower", "already-lower"),
])
def test_normalize(handle, expected):
    assert urls.normalize(handle) == expected


def test_channel_key_normalizes_handle():
    assert urls.channel_key("x", "TingHu888") == "x:tinghu888"
    assert urls.channel_key("x", "@TingHu888") == "x:tinghu888"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_urls.py -q
```

预期：`test_normalize` 报 `AttributeError: module 'roster.urls' has no attribute 'normalize'`；`test_channel_key_normalizes_handle` 报 `AssertionError`（现在返回的是 `x:TingHu888`，没有归一）。

- [ ] **Step 3: 实现**

在 `tools/roster/roster/urls.py` 里，`slugify` 函数下方、`channel_key` 定义上方插入：

```python
def normalize(handle: str) -> str:
    return handle.strip().lstrip("@").lower()
```

把已有的 `channel_key` 改成：

```python
def channel_key(platform: str, handle: str) -> str:
    return f"{platform}:{normalize(handle)}"
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/test_urls.py -q
```

预期：全部 PASS，含原有的 `test_channel_key`（`"karpathy"` 本来就是小写，归一后不变）。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/urls.py tools/roster/tests/test_urls.py
git commit -m "feat(roster): add handle normalization, bake into channel_key"
```

---

## Task 2: `state.py` 层回归测试（验证入口归一，criterion 9）

Task 1 改完 `channel_key` 后，`state.py` 的 `_entry`/`get_cursor`/`set_cursor`/`set_error`/`drop_channel` 全部自动受益（它们都经 `channel_key` 拼键），不需要改产品代码。这一步只写测试，确认这个"自动受益"是真的。

**Files:**
- Test: `tools/roster/tests/test_state.py`

**Interfaces:**
- Consumes: Task 1 的 `channel_key`（已内建归一）。

- [ ] **Step 1: 写测试**

在 `tools/roster/tests/test_state.py` 末尾追加：

```python
def test_get_cursor_is_case_insensitive_on_handle(data_dir):
    """守住 spec §3.0 的承诺：sync-* 传大小写不同的 handle 也要查到同一条游标。"""
    st = state.load(data_dir)
    state.set_cursor(st, "youtube", "TingHu888", "seen_urls", ["u1"], RUN)
    assert state.get_cursor(st, "youtube", "tinghu888") == {
        "type": "seen_urls", "value": ["u1"]
    }
    assert state.get_cursor(st, "youtube", "TingHu888") == \
           state.get_cursor(st, "youtube", "tinghu888")


def test_set_cursor_with_different_case_handle_updates_same_entry(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "TingHu888", "last_seen_id", "1", RUN)
    state.set_cursor(st, "x", "tinghu888", "last_seen_id", "2", RUN)
    assert len(st["channels"]) == 1
    assert state.get_cursor(st, "x", "TingHu888")["value"] == "2"


def test_drop_channel_is_case_insensitive(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "TingHu888", "last_seen_id", "1", RUN)
    state.drop_channel(st, "x", "tinghu888")
    assert st["channels"] == {}
```

- [ ] **Step 2: 跑测试确认通过（不用改产品代码）**

```bash
cd tools/roster && python3 -m pytest tests/test_state.py -q
```

预期：全部 PASS——这一步纯验证，Task 1 已经把行为改对了。

- [ ] **Step 3: Commit**

```bash
git add tools/roster/tests/test_state.py
git commit -m "test(roster): pin case-insensitive state lookups via channel_key"
```

---

## Task 3: `registry.py` —— 渠道 `key` 字段 + 按 key 查找

**Files:**
- Modify: `tools/roster/roster/registry.py`
- Modify: `tools/roster/roster/__init__.py`
- Modify: `tools/roster/tests/test_registry.py`
- Modify: `tools/roster/tests/test_cli.py`

**Interfaces:**
- Consumes: `urls.normalize`（Task 1）。
- Produces: 渠道对象新增 `key` 字段；`find_channel(reg, platform, handle)` 按归一 `key` 比较（签名不变）。

- [ ] **Step 1: 更新三处对渠道字典做精确比较的既有测试**

`tools/roster/tests/test_registry.py` 第 36-38 行，把：

```python
    assert creator["channels"] == [
        {"platform": "x", "handle": "karpathy", "url": "https://x.com/karpathy"}
    ]
```

改成：

```python
    assert creator["channels"] == [
        {"platform": "x", "handle": "karpathy", "key": "karpathy",
         "url": "https://x.com/karpathy"}
    ]
```

同文件第 87-90 行（`test_channels_for_platform_filters_and_carries_creator_id`），把：

```python
    assert registry.channels_for_platform(reg, "x") == [
        {"creator_id": "karpathy", "platform": "x",
         "handle": "karpathy", "url": "https://x.com/karpathy"}
    ]
```

改成：

```python
    assert registry.channels_for_platform(reg, "x") == [
        {"creator_id": "karpathy", "platform": "x",
         "handle": "karpathy", "key": "karpathy", "url": "https://x.com/karpathy"}
    ]
```

`tools/roster/tests/test_cli.py` 第 67-70 行（`test_registry_channels_outputs_json`），把：

```python
    assert json.loads(out) == [{
        "creator_id": "karpathy", "platform": "x",
        "handle": "karpathy", "url": "https://x.com/karpathy",
    }]
```

改成：

```python
    assert json.loads(out) == [{
        "creator_id": "karpathy", "platform": "x",
        "handle": "karpathy", "key": "karpathy", "url": "https://x.com/karpathy",
    }]
```

- [ ] **Step 2: 追加新测试**

在 `tools/roster/tests/test_registry.py` 顶部把 import 改成：

```python
from roster import SCHEMA_VERSION, registry
from roster.urls import normalize
```

文件末尾追加：

```python
def test_find_channel_is_case_insensitive(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://www.youtube.com/@TingHu888", TODAY)
    creator, channel = registry.find_channel(reg, "youtube", "tinghu888")
    assert creator["id"] == "tinghu888"
    assert channel["handle"] == "TingHu888"


def test_add_duplicate_channel_different_case_raises(data_dir):
    """criterion 1：这是本次要修的现行缺陷。"""
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://www.youtube.com/@TingHu888", TODAY)
    with pytest.raises(ValueError, match="已在名册"):
        registry.add_channel(reg, "https://www.youtube.com/@tinghu888", TODAY)
    assert len(reg["creators"]) == 1


def test_add_channel_sets_normalized_key(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://www.youtube.com/@TingHu888", TODAY)
    _, channel = registry.find_channel(reg, "youtube", "TingHu888")
    assert channel["key"] == "tinghu888"


def test_fresh_registry_schema_version_is_2(data_dir):
    """criterion 2 的一半：新建的 registry 直接就是 v2。"""
    assert registry.load(data_dir)["schema_version"] == 2
```

在 `tools/roster/tests/test_registry_merge.py` 顶部 import 加一行 `from roster.urls import normalize`，文件末尾追加：

```python
def test_key_stays_normalized_after_rename_and_merge(data_dir):
    """criterion 8：merge/rename 不碰 handle，key 应该照旧等于 normalize(handle)。"""
    reg = _two_creators(data_dir)
    registry.rename_creator(reg, "karpathy", "Andrej Karpathy")
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    merged = registry.find_creator(reg, "karpathy")
    for ch in merged["channels"]:
        assert ch["key"] == normalize(ch["handle"])
```

- [ ] **Step 3: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_registry.py tests/test_registry_merge.py tests/test_cli.py -q
```

预期：新增的 `key` 相关断言全部失败（`KeyError: 'key'` 或字典不相等），`test_add_duplicate_channel_different_case_raises` 失败（当前会建出第二个人而不是报错）——这正是 §1.1 那个 bug 的复现。

- [ ] **Step 4: 实现**

`tools/roster/roster/__init__.py`：

```python
SCHEMA_VERSION = 2
```

`tools/roster/roster/registry.py` 第 13 行的 import 改成：

```python
from .urls import normalize, parse_channel_url, slugify
```

`find_channel` 改成：

```python
def find_channel(reg: dict, platform: str, handle: str) -> tuple[dict, dict] | None:
    key = normalize(handle)
    for c in reg["creators"]:
        for ch in c["channels"]:
            if ch["platform"] == platform and ch.get("key", normalize(ch["handle"])) == key:
                return c, ch
    return None
```

（`ch.get("key", normalize(ch["handle"]))` 这个 fallback 是给还没跑 `migrate-schema` 的旧数据用的——新代码部署到跑迁移之间那个窗口里，旧渠道对象还没有 `key` 字段，不能让 `find_channel` 直接炸。）

`add_channel` 改成：

```python
def add_channel(reg: dict, url: str, today: str) -> tuple[str, bool]:
    platform, handle = parse_channel_url(url)
    if find_channel(reg, platform, handle) is not None:
        raise ValueError(f"{platform}:{handle} 已在名册中")

    creator_id = _free_slug(reg, slugify(handle))
    reg["creators"].append({
        "id": creator_id,
        "display_name": handle,
        "aliases": [],
        "placeholder": True,
        "added_at": today,
        "channels": [{
            "platform": platform, "handle": handle,
            "key": normalize(handle), "url": url,
        }],
    })
    return creator_id, True
```

- [ ] **Step 5: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/test_registry.py tests/test_registry_merge.py tests/test_cli.py -q
```

预期：全部 PASS。

- [ ] **Step 6: Commit**

```bash
git add tools/roster/roster/registry.py tools/roster/roster/__init__.py \
        tools/roster/tests/test_registry.py tools/roster/tests/test_registry_merge.py \
        tools/roster/tests/test_cli.py
git commit -m "feat(roster): store normalized key per channel, dedupe find_channel by key"
```

---

## Task 4: `migrate_schema.py` —— 一次性 schema 迁移

**Files:**
- Create: `tools/roster/roster/migrate_schema.py`
- Create: `tools/roster/tests/test_migrate_schema.py`

**Interfaces:**
- Consumes: `registry.load/save`、`state.load/save`（已有）；`urls.channel_key`（Task 1，内建归一）；`SCHEMA_VERSION`（Task 3，=2）。
- Produces: `migrate_schema(data_dir: Path) -> dict`，返回 `{"channels_updated": int, "cursors_renamed": int}`。

- [ ] **Step 1: 写失败测试**

创建 `tools/roster/tests/test_migrate_schema.py`：

```python
from roster import SCHEMA_VERSION, migrate_schema, registry, state

TODAY = "2026-08-26"
RUN = "2026-08-26T09:14:00+08:00"


def _seed_v1(data_dir):
    """手工构一份 schema_version 1 的旧数据：渠道没有 key，游标键是原始 handle。"""
    reg = {
        "schema_version": 1,
        "creators": [
            {
                "id": "tinghu888", "display_name": "TingHu888", "aliases": [],
                "placeholder": True, "added_at": TODAY,
                "channels": [{
                    "platform": "x", "handle": "TingHu888",
                    "url": "https://x.com/TingHu888",
                }],
            },
        ],
    }
    st = {
        "schema_version": 1,
        "channels": {
            "x:TingHu888": {
                "cursor": {"type": "last_seen_id", "value": "123456"},
                "last_run": RUN, "last_error": None,
            },
        },
    }
    registry.save(data_dir, reg)
    state.save(data_dir, st)


def test_migrate_schema_backfills_key(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    channel = registry.load(data_dir)["creators"][0]["channels"][0]
    assert channel["key"] == "tinghu888"
    assert channel["handle"] == "TingHu888"          # 原始大小写保留


def test_migrate_schema_bumps_registry_schema_version(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    assert registry.load(data_dir)["schema_version"] == SCHEMA_VERSION


def test_migrate_schema_renames_cursor_key(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    st = state.load(data_dir)
    assert "x:tinghu888" in st["channels"]
    assert "x:TingHu888" not in st["channels"]


def test_migrate_schema_preserves_cursor_value_byte_for_byte(data_dir):
    _seed_v1(data_dir)
    before = state.load(data_dir)["channels"]["x:TingHu888"]["cursor"]
    migrate_schema.migrate_schema(data_dir)
    after = state.load(data_dir)["channels"]["x:tinghu888"]["cursor"]
    assert after == before


def test_migrate_schema_bumps_state_schema_version(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    assert state.load(data_dir)["schema_version"] == SCHEMA_VERSION


def test_migrate_schema_is_idempotent(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    reg_once = registry.load(data_dir)
    st_once = state.load(data_dir)
    migrate_schema.migrate_schema(data_dir)
    assert registry.load(data_dir) == reg_once
    assert state.load(data_dir) == st_once


def test_migrate_schema_reports_counts(data_dir):
    _seed_v1(data_dir)
    result = migrate_schema.migrate_schema(data_dir)
    assert result == {"channels_updated": 1, "cursors_renamed": 1}


def test_migrate_schema_second_run_reports_zero(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    result = migrate_schema.migrate_schema(data_dir)
    assert result == {"channels_updated": 0, "cursors_renamed": 0}


def test_migrate_schema_leaves_already_normalized_channel_untouched(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.save(data_dir, reg)
    result = migrate_schema.migrate_schema(data_dir)
    assert result["channels_updated"] == 0
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_migrate_schema.py -q
```

预期：`ModuleNotFoundError: No module named 'roster.migrate_schema'`（导入失败，全部报错）。

- [ ] **Step 3: 实现**

创建 `tools/roster/roster/migrate_schema.py`：

```python
"""registry.json / state.json 从 schema_version 1 升到 2 —— 一次性、幂等。

跟 migrate.py（旧 watchlist 导入）是两件事：这里只做两件事——给每条渠道
回填 key、把游标键从原始 handle 重写成归一 key。两个文件必须在同一次
调用里一起改，否则名册按 key 查、游标按 handle 存，成了新的不一致源头
（见 docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md §3.3）。
"""
from pathlib import Path

from . import SCHEMA_VERSION, registry, state
from .urls import channel_key, normalize


def migrate_schema(data_dir: Path) -> dict:
    reg = registry.load(data_dir)
    channels_updated = 0
    for creator in reg["creators"]:
        for ch in creator["channels"]:
            new_key = normalize(ch["handle"])
            if ch.get("key") != new_key:
                ch["key"] = new_key
                channels_updated += 1
    reg["schema_version"] = SCHEMA_VERSION
    registry.save(data_dir, reg)

    st = state.load(data_dir)
    cursors_renamed = 0
    new_channels: dict = {}
    for old_key, entry in st["channels"].items():
        platform, _, handle = old_key.partition(":")
        new_key = channel_key(platform, handle)
        if new_key != old_key:
            cursors_renamed += 1
        new_channels[new_key] = entry
    st["channels"] = new_channels
    st["schema_version"] = SCHEMA_VERSION
    state.save(data_dir, st)

    return {"channels_updated": channels_updated, "cursors_renamed": cursors_renamed}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/test_migrate_schema.py -q
```

预期：全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/migrate_schema.py tools/roster/tests/test_migrate_schema.py
git commit -m "feat(roster): add migrate-schema — backfill key, rename cursor keys, idempotent"
```

---

## Task 5: CLI 接入 `roster migrate-schema`

**Files:**
- Modify: `tools/roster/roster/__main__.py`
- Modify: `tools/roster/tests/test_migrate_schema.py`

**Interfaces:**
- Consumes: `migrate_schema.migrate_schema`（Task 4）。

- [ ] **Step 1: 写失败测试**

在 `tools/roster/tests/test_migrate_schema.py` 顶部追加 `import json`，文件末尾追加：

```python
def test_cli_migrate_schema(data_dir, capsys):
    from roster.__main__ import main

    reg = {
        "schema_version": 1,
        "creators": [{
            "id": "k", "display_name": "K", "aliases": [], "placeholder": True,
            "added_at": TODAY,
            "channels": [{"platform": "x", "handle": "TingHu888",
                          "url": "https://x.com/TingHu888"}],
        }],
    }
    st = {"schema_version": 1, "channels": {
        "x:TingHu888": {"cursor": {"type": "last_seen_id", "value": "1"},
                         "last_run": RUN, "last_error": None},
    }}
    registry.save(data_dir, reg)
    state.save(data_dir, st)

    code = main(["migrate-schema"])
    out = capsys.readouterr().out.strip()
    assert code == 0
    assert out == "OK channels_updated=1 cursors_renamed=1"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_migrate_schema.py::test_cli_migrate_schema -q
```

预期：`SystemExit` 或 argparse 报 `invalid choice: 'migrate-schema'`——子命令还没注册。

- [ ] **Step 3: 实现**

`tools/roster/roster/__main__.py`，在 `_cmd_migrate` 函数下方新增：

```python
def _cmd_migrate_schema(args) -> int:
    from . import migrate_schema

    data_dir = config.get_data_dir()
    result = migrate_schema.migrate_schema(data_dir)
    print(f"OK channels_updated={result['channels_updated']} "
          f"cursors_renamed={result['cursors_renamed']}")
    return 0
```

在 `_build_parser` 里，紧跟在 `p_mig.set_defaults(func=_cmd_migrate)` 那一行之后插入：

```python
    p_ms = groups.add_parser(
        "migrate-schema", help="registry/state 升级到 schema v2（回填 key、游标键归一，幂等）")
    p_ms.set_defaults(func=_cmd_migrate_schema)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/test_migrate_schema.py -q
```

预期：全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/__main__.py tools/roster/tests/test_migrate_schema.py
git commit -m "feat(roster): wire up 'roster migrate-schema' CLI subcommand"
```

---

## Task 6: 全量回归

**Files:** 无新改动，纯验证。

- [ ] **Step 1: 跑 tools/roster 全套**

```bash
cd tools/roster && python3 -m pytest tests/ -q
```

预期：PASS 数 = 140（改动前基线）+ 本计划新增的测试数，且没有任何 FAIL/ERROR。

- [ ] **Step 2: 跑仓库级 `npm test`**

```bash
npm test
```

预期：`skills/research/clip-url` 那 7 个因缺 Playwright 浏览器而失败的测试**照常失败**（跟本次改动无关，基线已经是红的），其余套件全绿。**不要用 `npm test | tail` 判断成败**——用 `npm test > /tmp/npm-test.log 2>&1; echo $?` 或直接看输出。

- [ ] **Step 3: 确认没有引入新失败**

对比 Step 2 输出与已知基线（`clip-url` 7 个失败），若出现基线之外的新失败，回到对应 Task 排查，不要跳过。

---

## Task 7: 文档跟进（manage-creators）

**Files:**
- Modify: `skills/feed/manage-creators/SKILL.md`
- Modify: `skills-index.json`

spec 范围里同时点了 `sync-xtimeline`/`sync-ytchannel`/`sync-website` 三份 SKILL.md，但检查过之后：这三个 skill 的 `roster_client.py` 只读 `registry channels` 返回的 `creator_id`/`platform`/`handle`/`url` 四个字段（`skills/feed/sync-ytchannel/scripts/roster_client.py` 等），新增的 `key` 字段是纯增量、它们不读也不用改，且三份 SKILL.md 里都没有提过大小写去重这件事——**没有内容需要改，跳过**，不是漏做。

- [ ] **Step 1: 更新 `add` 这一行，说明现在按 key 去重**

`skills/feed/manage-creators/SKILL.md` 第 51 行，把：

```
| `add <url>` | `<roster> registry add <url>` | `OK <id> <platform>:<handle>` → 告知已加入，并提示这是占位人、可用 `rename` 填正式名字。`add` 现在也吃网站文章列表页 URL（`platform` 会是 `website`） |
```

改成：

```
| `add <url>` | `<roster> registry add <url>` | `OK <id> <platform>:<handle>` → 告知已加入，并提示这是占位人、可用 `rename` 填正式名字。`add` 现在也吃网站文章列表页 URL（`platform` 会是 `website`）。渠道按归一后的 key（去 `@`、trim、转小写）去重——同一个频道换个大小写的链接再 `add` 一次会报"已在名册中"，不会建出第二个人 |
```

- [ ] **Step 2: 在"若用户此前用过 sync-xtimeline / sync-ytchannel"迁移块后追加 schema 升级说明**

在第 41 行（`migrate` 命令代码块结束）之后、第 43 行之前插入一段：

```markdown

**若已有名册是旧 schema（`registry.json` 里的渠道没有 `key` 字段）**，先跑一次：

```bash
<roster_path> migrate-schema
```

幂等，可重复跑。升级后名册按归一 `key` 去重，`state.json` 的游标键也同步改写成归一形态——不跑这一步，新版 roster 找旧游标会找不到，表现为该渠道被当成新渠道重刷一次基线。
```

- [ ] **Step 3: 更新 frontmatter 版本号**

`skills/feed/manage-creators/SKILL.md` 第 3 行：

```yaml
version: "0.2.1"
```

改成：

```yaml
version: "0.3.0"
```

- [ ] **Step 4: 同步 `skills-index.json` 的 contentVersion / contentHash**

找到 `skills-index.json` 里 `"path": "feed/manage-creators"` 那一项，把：

```json
"contentVersion": "0.2.1"
```

改成跟 SKILL.md 一致的 `"0.3.0"`，并生成一个新的 `contentHash`（16 位十六进制，纯粹用来让 skill-harness 判断内容有没有变，不是真的内容哈希——参照仓库里既有的 bump 提交，如 `40a77b6`）：

```bash
openssl rand -hex 8
```

把输出填进 `contentHash` 字段。

- [ ] **Step 5: 跑 skill 格式校验**

```bash
npm test
```

预期：`hskill` 相关的 SKILL.md 格式校验套件通过（版本号是合法 semver、`skills-index.json` 字段完整）。

- [ ] **Step 6: Commit**

```bash
git add skills/feed/manage-creators/SKILL.md skills-index.json
git commit -m "docs(manage-creators): document key-based dedup and migrate-schema upgrade path"
```

---

## Task 8: 真实数据迁移 + 验收锚点逐条实跑

**这一步操作用户真实数据。跑之前先备份。** 只覆盖本计划范围（`harveyz-skill`/`tools/roster`）——criterion 6（scholia 的 `watched` 结果不变）依赖 scholia 那边的改动，等那条分支完成后再补验。

- [ ] **Step 1: 备份**

```bash
cp ~/.hskill/roster/registry.json /tmp/registry.json.bak-2026-09-16
cp ~/.hskill/roster/state.json /tmp/state.json.bak-2026-09-16
```

- [ ] **Step 2: 跑真实迁移**

```bash
bash tools/roster/roster.sh migrate-schema
```

预期输出形如 `OK channels_updated=N cursors_renamed=M`（真实数据里 `channels_updated` 预计是 2——`x:TingHu888`、`youtube:PlatoStone` 的 `key` 都要回填；`cursors_renamed` 预计也是 2，因为两者在 `state.json` 里都有游标条目——**这跟 spec §3.2 的表格不一致，那张表说 `youtube:PlatoStone` 没有游标条目，实测数据里它有，第 7 步要把这个更正写回去**）。

- [ ] **Step 3: 验 criterion 2（key 回填 + schema_version）**

```bash
python3 -c "
import json
reg = json.load(open('$HOME/.hskill/roster/registry.json'))
assert reg['schema_version'] == 2, reg['schema_version']
for c in reg['creators']:
    for ch in c['channels']:
        assert ch['key'] == ch['handle'].strip().lstrip('@').lower(), ch
print('OK criterion 2')
"
```

- [ ] **Step 4: 验 criterion 3（游标重命名 + 值逐字节相同）**

```bash
python3 -c "
import json
before = json.load(open('/tmp/state.json.bak-2026-09-16'))
after = json.load(open('$HOME/.hskill/roster/state.json'))
assert after['schema_version'] == 2
assert 'x:tinghu888' in after['channels']
assert 'x:TingHu888' not in after['channels']
assert after['channels']['x:tinghu888']['cursor'] == before['channels']['x:TingHu888']['cursor']
print('OK criterion 3')
"
```

- [ ] **Step 5: 验 criterion 4（幂等）**

```bash
bash tools/roster/roster.sh migrate-schema
```

预期：`OK channels_updated=0 cursors_renamed=0`，且两个文件内容与 Step 2 跑完后逐字节相同（用 `diff` 或重跑 Step 3/4 的断言脚本确认）。

- [ ] **Step 6: 验 criterion 5（`sync-ytchannel run` 不重刷基线）**

```bash
/sync-ytchannel run
```

（这一步走 skill 而不是裸脚本，因为完整的抓取-归档流程要经过 `manage-creators`/`sync-ytchannel` 的 roster_client 桥。）预期：没有任何频道被当成新渠道抓基线——摘要里如果出现某个已关注很久的频道突然"发现 N 条历史视频"，说明键没接上，回 Task 5 排查。

- [ ] **Step 7: 把结论写回文档**

1. 在 `docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md` §3.2 的表格后追加一条更正：实测 `youtube:PlatoStone` 在 `state.json` 里**确实有**游标条目（跟原表述不符），真实迁移是 2 条键变、2 条游标重命名，不是 1 条；迁移逻辑本身不受影响（对所有需要归一的键一视同仁），只是这张表的具体数字要更正。
2. 在 `docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md` §7 未验证项里补上结论：
   - `x:fanli1688` 孤儿游标：`registry.json` 里确认没有对应渠道（已核实），成因待查——`remove_channel`（`registry.py`）本身不碰 `state.json`，真正调用 `state.drop_channel` 的是 `__main__.py` 的 `_cmd_registry_remove`；如果这条渠道是被脚本外的手工编辑删掉、或是被本计划范围之外的旧代码路径删掉，都不会触发 `drop_channel`。本次不修，迁移会把它原样带进新 schema。
   - `website` 平台 handle 大小写敏感性：现有两条（`simonwillison-net`、`claude-com`）都是从域名 slugify 出来的，本来就是小写，归一是恒等变换，无风险。
   - `profile` 层索引：`tools/roster/roster/profiles.py` 全部函数按 `creator_id` 索引（`profile_path`/`read`/`_write` 等），完全不碰 `handle`/`key`，不受本次改动影响。
3. 在 `docs/commute/2026-09-16-roster-normalized-key-handoff.md` 的"最小验收锚点"章节末尾，新起一个"接手方自测记录"小节，把 Step 3-6 的实跑结果（每条 pass/fail）列出来，并注明 criterion 6 依赖 scholia 分支、本次未验。

- [ ] **Step 8: Commit**

```bash
git add docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md \
        docs/commute/2026-09-16-roster-normalized-key-handoff.md
git commit -m "docs: correct §3.2 cursor count, record §7 conclusions and self-test results"
```

- [ ] **Step 9: 把 `status` 置为 `待验收`，停手**

按交接文档"交回协议"第 2 条：**不要**把 `status` 置为 `已验收`——那是验收方的写入权。改完 frontmatter 提交后停手，等验收。

```bash
git add docs/commute/2026-09-16-roster-normalized-key-handoff.md
git commit -m "docs(commute): mark 待验收"
```

**也不要合并到 staging。** 按交接文档"交回协议"第 1 条，合并只由交出方在验收通过后做。
