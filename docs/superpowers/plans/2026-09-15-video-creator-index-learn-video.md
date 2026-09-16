# learn-video: contract guard + creator index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This plan targets `skills/research/learn-video/` inside this worktree** (`harveyz-skill`, branch `feature/video-creator-index`) — already checked out, no branch/worktree setup needed here.
>
> **Sequencing note:** This is step 2 of 3. Do NOT start this plan until the Video-Learner plan's Task 4 (real backfill) is done — Task 1 here makes `archive.py` reject any `meta.json` missing `source_url`/`title`/`fetched_at`, which every backfilled `meta.json` must already have by the time this ships.

**Goal:** Demote `archive.py` from a writer to a validator (vdl now owns `meta.json` entirely — see the Video-Learner plan), and add `build_creator_index.py` (`build`/`check` subcommands) that groups every video entity by normalized uploader handle into `<knowledgeRoot>/videos/creators.json`.

**Architecture:** `archive.py` shrinks to a single read+validate function — no sqlite, no field enrichment, since vdl's `buildTaskMeta` now writes everything. `build_creator_index.py` is a new, independent script following this repo's existing `store_config.py`-per-skill pattern: it asks `store_config.videos_dir()` for the root, scans `work/*/meta.json`, and writes an atomic (`tmp` + `rename`) index. It never reads `registry.json` — matching-to-roster is scholia's job, not this repo's (spec §1.5, §3.3).

**Tech Stack:** Python 3, `pytest`, existing `conftest.py` autouse fixture (`isolated_store_config`).

**Spec:** `docs/superpowers/specs/2026-09-15-video-creator-index-design.md` (implements §1.3, §2.4, §3.1, §3.2, §3.3 first half, §3.4, §6 criteria 1/3/4/7/8).

## Global Constraints

- **`build_creator_index.py` never reads or writes `registry.json`.** It has no knowledge that a roster even exists (spec §1.5, §3.3 — "watched" is computed entirely by the consumer, not baked into the index).
- **No `creator_id` / `watched` field anywhere in the index.** These are judgments, not facts (spec's "主线").
- **Index only carries metadata** (title/upload_date/duration) — never summary or article text (spec §2.5).
- **Atomic writes only**: temp file + `rename`, matching `scholia`'s own `server/index.js:27-32` pattern already cited in the spec. A failed/killed build must leave the previous `creators.json` byte-for-byte intact.
- **Every meta.json becomes exactly one accounted-for unit** — either a video under some `creators[].videos` or a `task_id` under some `unresolved[].task_ids`. Never both, never neither (spec §6 criterion 4).
- **Test convention:** `pytest`, run from `skills/research/learn-video/`. The autouse `isolated_store_config` fixture (in `tests/conftest.py`) already isolates `HSKILL_CONFIG` per test — no manual setup needed in new test files.
- **This repo's skill-versioning convention:** bump `version:` in `SKILL.md` frontmatter, then recompute `contentHash` in `skills-index.json` using the exact recipe in `skills/mint/publish-skill/SKILL.md` (quoted in Task 4) — a hash mismatch with an unchanged version is a publish-blocking violation (F8).
- **Branch/commit convention (already active in this worktree):** `git config core.hooksPath .githooks` is already set; commit-msg hook requires Conventional Commits (`feat|fix|chore|docs|refactor|test|style|perf` — note `docs`, not `doc`). Do not merge to `staging` from here — this worktree's branch merges only when the whole cross-repo effort is reviewed and done (see the handoff doc).

---

### Task 1: Demote `archive.py` to a contract validator

**Files:**
- Modify: `skills/research/learn-video/scripts/archive.py` (full rewrite — shrinks from 93 to ~45 lines)
- Modify: `skills/research/learn-video/tests/test_archive.py` (full rewrite — the old tests exercise sqlite enrichment that no longer exists)

**Interfaces:**
- Consumes: `meta.json` already fully written by vdl (Video-Learner plan, Task 3) — must contain non-empty `source_url`, `title`, `fetched_at`.
- Produces: `archive(task_id: str) -> {"video_dir": Path, "meta_path": Path}` — same return shape as before, but the function signature drops `source_url`/`title`/`fetched_at` params entirely (nothing left to construct from them). CLI now only reads `TASK_ID` from the environment.

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `skills/research/learn-video/tests/test_archive.py`:

```python
"""Unit tests for archive.py — now a pure validator: vdl already wrote
meta.json (see docs/superpowers/specs/2026-09-15-video-creator-index-design.md
§1.3), this script just checks it satisfies the unified-store contract."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from archive import archive  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "archive.py"


def _vdl_task_dir(root: Path, task_id: str, meta: dict | None = None) -> Path:
    """Stand in for what vdl leaves behind: task dir + artifacts + meta.json
    (vdl writes meta.json itself now — this helper mirrors that)."""
    task_dir = root / "videos" / "work" / task_id
    (task_dir / "transcript").mkdir(parents=True, exist_ok=True)
    (task_dir / "writing").mkdir(parents=True, exist_ok=True)
    (task_dir / "transcript" / "original_zh.md").write_text("raw", encoding="utf-8")
    (task_dir / "writing" / "article.md").write_text("body", encoding="utf-8")
    if meta is not None:
        (task_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return task_dir


VALID_META = {
    "source_url": "https://youtube.com/watch?v=t1",
    "title": "My Video",
    "fetched_at": "2026-09-15",
    "uploader_id": "@alejandro_ao",
    "channel_id": "UC1oXUA7qgs0GZc_yk46K2OQ",
    "uploader_url": "https://www.youtube.com/@alejandro_ao",
}


def test_archive_accepts_meta_with_all_required_fields(isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1", VALID_META)

    result = archive("t1")

    assert result["video_dir"] == task_dir
    assert result["meta_path"] == task_dir / "meta.json"
    # archive() must not modify meta.json — it's read-only now
    assert json.loads(result["meta_path"].read_text(encoding="utf-8")) == VALID_META


@pytest.mark.parametrize("missing_field", ["source_url", "title", "fetched_at"])
def test_archive_rejects_meta_missing_a_required_field(isolated_store_config, missing_field):
    meta = {k: v for k, v in VALID_META.items() if k != missing_field}
    _vdl_task_dir(isolated_store_config, "t1", meta)

    with pytest.raises(SystemExit) as excinfo:
        archive("t1")

    assert missing_field in str(excinfo.value)


def test_archive_rejects_when_meta_json_absent(isolated_store_config):
    """vdl hasn't finished writing meta.json yet (task not 'completed')."""
    _vdl_task_dir(isolated_store_config, "t1", meta=None)

    with pytest.raises(SystemExit) as excinfo:
        archive("t1")

    assert "meta.json 不存在" in str(excinfo.value)


def test_archive_refuses_when_task_dir_missing(isolated_store_config):
    with pytest.raises(FileNotFoundError) as excinfo:
        archive("missing")

    assert "vdl config set work-root" in str(excinfo.value)


def test_archive_leaves_vdl_artifacts_untouched(isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1", VALID_META)

    archive("t1")

    assert (task_dir / "transcript" / "original_zh.md").read_text(encoding="utf-8") == "raw"
    assert (task_dir / "writing" / "article.md").read_text(encoding="utf-8") == "body"


def test_cli_prints_video_dir_and_meta_path(isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1", VALID_META)
    env = {**os.environ, "TASK_ID": "t1", "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"]}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert f"VIDEO_DIR: {task_dir}" in result.stdout
    assert f"META_PATH: {task_dir / 'meta.json'}" in result.stdout


def test_cli_exits_nonzero_when_task_dir_missing(isolated_store_config):
    env = {**os.environ, "TASK_ID": "nope", "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"]}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "vdl config set work-root" in result.stderr


def test_cli_exits_nonzero_when_required_field_missing(isolated_store_config):
    meta = {k: v for k, v in VALID_META.items() if k != "fetched_at"}
    _vdl_task_dir(isolated_store_config, "t1", meta)
    env = {**os.environ, "TASK_ID": "t1", "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"]}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "fetched_at" in result.stderr
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/research/learn-video && pytest tests/test_archive.py -v`
Expected: collection error or failures — `archive()` still takes `source_url`/`title`/`fetched_at` positional args, calling `archive("t1")` will raise `TypeError`.

- [ ] **Step 3: Rewrite `archive.py`**

Replace the full contents of `skills/research/learn-video/scripts/archive.py`:

```python
#!/usr/bin/env python3
"""Validates vdl's meta.json against the unified store's required contract
fields. Writing meta.json is vdl's job now — vdl's own database.sqlite is
the source of truth for uploader_id/channel_id/uploader_url and the display
fields scholia reads (url/uploader/upload_date/duration/mode/output_lang/ts).
See docs/superpowers/specs/2026-09-15-video-creator-index-design.md §1.3.

Parameters via environment variables:
  TASK_ID - vdl's task_id (this skill's entity primary key)
"""
import json
import os

import store_config

REQUIRED_FIELDS = ("source_url", "title", "fetched_at")


def archive(task_id: str) -> dict:
    videos_dir = store_config.videos_dir()
    video_dir = videos_dir / "work" / task_id
    if not video_dir.is_dir():
        raise FileNotFoundError(
            f"任务目录不存在：{video_dir}\n"
            f"vdl 的 WORK_ROOT 没有指向 {videos_dir}。\n"
            f"修复：vdl config set work-root {videos_dir}"
        )

    meta_path = video_dir / "meta.json"
    if not meta_path.is_file():
        raise SystemExit(
            f"meta.json 不存在：{meta_path}\n"
            f"vdl 尚未写入 meta.json——任务可能还没跑到 completed。"
        )

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    missing = [f for f in REQUIRED_FIELDS if not meta.get(f)]
    if missing:
        raise SystemExit(
            f"meta.json 缺少统一存储契约必填字段：{', '.join(missing)}\n{meta_path}"
        )

    return {"video_dir": video_dir, "meta_path": meta_path}


def main():
    try:
        result = archive(task_id=os.environ["TASK_ID"])
    except FileNotFoundError as e:
        raise SystemExit(str(e))
    print(f"VIDEO_DIR: {result['video_dir']}")
    print(f"META_PATH: {result['meta_path']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests again to confirm they pass**

Run: `cd skills/research/learn-video && pytest tests/test_archive.py -v`
Expected: all pass (10 tests: 1 accept + 3 parametrized-missing-field + 1 no-meta + 1 no-dir + 1 untouched + 3 CLI).

- [ ] **Step 5: Commit**

```bash
git add skills/research/learn-video/scripts/archive.py skills/research/learn-video/tests/test_archive.py
git commit -m "fix(learn-video): demote archive.py to a contract validator"
```

---

### Task 2: `build_creator_index.py` — group video entities by normalized handle

**Files:**
- Create: `skills/research/learn-video/scripts/build_creator_index.py`
- Create: `skills/research/learn-video/tests/test_build_creator_index.py`

**Interfaces:**
- Produces: `build_index(work_dir: Path) -> dict` (pure function, no I/O — testable without touching disk beyond reading fixture `meta.json` files), `write_index(index: dict, output_path: Path) -> None` (atomic tmp+rename write), `check_index(work_dir: Path, index_path: Path) -> tuple[bool, str]`. CLI: `python3 build_creator_index.py build` and `python3 build_creator_index.py check`, both resolving paths via `store_config.videos_dir()` — no new config plumbing.

- [ ] **Step 1: Write the failing tests**

Create `skills/research/learn-video/tests/test_build_creator_index.py`:

```python
"""Unit tests for build_creator_index.py — groups vdl's meta.json entities
by normalized uploader handle into <knowledgeRoot>/videos/creators.json.
Never reads registry.json (spec §1.5, §3.3) — matching to the roster is
scholia's job, not this script's."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_creator_index import build_index, check_index, write_index  # noqa: E402


def _meta(root: Path, task_id: str, **fields) -> Path:
    task_dir = root / "videos" / "work" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    meta_path = task_dir / "meta.json"
    meta_path.write_text(json.dumps(fields, ensure_ascii=False), encoding="utf-8")
    return meta_path


def test_build_groups_videos_by_normalized_handle(isolated_store_config):
    root = isolated_store_config
    _meta(root, "t1", title="V1", uploader="Alejandro AO", uploader_id="@alejandro_ao",
          uploader_url="https://www.youtube.com/@alejandro_ao",
          channel_id="UC1oXUA7qgs0GZc_yk46K2OQ", upload_date="2026-06-01", duration="120")
    # Same person, different case in the handle — must fold into the same key
    # (YouTube handles are case-insensitive, confirmed against Google's own
    # help docs — see spec §7.1).
    _meta(root, "t2", title="V2", uploader="Alejandro AO", uploader_id="@Alejandro_AO",
          upload_date="2026-07-01", duration="200")

    index = build_index(root / "videos" / "work")

    assert index["schema_version"] == 1
    assert index["scanned"]["entities"] == 2
    assert len(index["creators"]) == 1
    creator = index["creators"][0]
    assert creator["key"] == "alejandro_ao"
    assert creator["channel_id"] == "UC1oXUA7qgs0GZc_yk46K2OQ"
    assert creator["uploader_url"] == "https://www.youtube.com/@alejandro_ao"
    assert {v["task_id"] for v in creator["videos"]} == {"t1", "t2"}
    assert index["unresolved"] == []


def test_build_puts_missing_uploader_id_into_unresolved(isolated_store_config):
    root = isolated_store_config
    _meta(root, "t1", title="V1", uploader="Matt Pocock")
    _meta(root, "t2", title="V2", uploader="Matt Pocock")
    _meta(root, "t3", title="V3", uploader="Someone Else")

    index = build_index(root / "videos" / "work")

    assert index["creators"] == []
    assert len(index["unresolved"]) == 2
    matt = next(u for u in index["unresolved"] if u["display_name"] == "Matt Pocock")
    assert set(matt["task_ids"]) == {"t1", "t2"}


def test_every_scanned_entity_is_accounted_for(isolated_store_config):
    """Acceptance criterion #4: creators[].videos + unresolved[].task_ids
    total must equal the disk meta.json count — no entity may vanish."""
    root = isolated_store_config
    _meta(root, "t1", title="V1", uploader="A", uploader_id="@a")
    _meta(root, "t2", title="V2", uploader="B")
    _meta(root, "t3", title="V3", uploader="A", uploader_id="@a")

    index = build_index(root / "videos" / "work")

    video_count = sum(len(c["videos"]) for c in index["creators"])
    unresolved_count = sum(len(u["task_ids"]) for u in index["unresolved"])
    assert video_count + unresolved_count == index["scanned"]["entities"] == 3


def test_write_index_is_atomic_on_failure(isolated_store_config, monkeypatch):
    """Acceptance criterion #7: a failed/killed build must not corrupt or
    remove the previous creators.json."""
    root = isolated_store_config
    output_path = root / "videos" / "creators.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('{"schema_version": 1, "old": true}', encoding="utf-8")

    def _boom(self, target):
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr(Path, "rename", _boom)

    index = build_index(root / "videos" / "work")
    try:
        write_index(index, output_path)
    except OSError:
        pass

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"schema_version": 1, "old": True}


def test_check_reports_ok_when_index_matches_disk(isolated_store_config):
    root = isolated_store_config
    _meta(root, "t1", title="V1", uploader="A", uploader_id="@a")
    work_dir = root / "videos" / "work"
    output_path = root / "videos" / "creators.json"
    write_index(build_index(work_dir), output_path)

    ok, message = check_index(work_dir, output_path)
    assert ok is True
    assert message.startswith("OK:")


def test_check_reports_stale_when_disk_has_more_entities(isolated_store_config):
    root = isolated_store_config
    work_dir = root / "videos" / "work"
    output_path = root / "videos" / "creators.json"
    _meta(root, "t1", title="V1", uploader="A", uploader_id="@a")
    write_index(build_index(work_dir), output_path)

    _meta(root, "t2", title="V2", uploader="B", uploader_id="@b")  # not rebuilt

    ok, message = check_index(work_dir, output_path)
    assert ok is False
    assert "STALE" in message


def test_check_reports_stale_when_index_missing(isolated_store_config):
    root = isolated_store_config
    work_dir = root / "videos" / "work"
    _meta(root, "t1", title="V1", uploader="A", uploader_id="@a")

    ok, message = check_index(work_dir, root / "videos" / "creators.json")
    assert ok is False
    assert "STALE" in message
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd skills/research/learn-video && pytest tests/test_build_creator_index.py -v`
Expected: `ModuleNotFoundError: No module named 'build_creator_index'`.

- [ ] **Step 3: Write `build_creator_index.py`**

Create `skills/research/learn-video/scripts/build_creator_index.py`:

```python
#!/usr/bin/env python3
"""Builds <knowledgeRoot>/videos/creators.json — vdl's video entities grouped
by normalized uploader handle. Never reads registry.json: matching a handle
to "am I watching this person" is scholia's job at read time (judgment isn't
stored next to fact — see
docs/superpowers/specs/2026-09-15-video-creator-index-design.md §0, §3.3).

Usage:
  python3 build_creator_index.py build   # full rebuild, atomic write
  python3 build_creator_index.py check   # compare index vs disk, exit 1 if stale
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import store_config


def _normalize_handle(uploader_id: str) -> str:
    return uploader_id.lstrip("@").strip().lower()


def build_index(work_dir: Path) -> dict:
    creators: dict[str, dict] = {}
    unresolved: dict[str, dict] = {}
    scanned = 0

    for meta_path in sorted(work_dir.glob("*/meta.json")):
        task_id = meta_path.parent.name
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        scanned += 1

        video_entry = {
            "task_id": task_id,
            "title": meta.get("title", ""),
            "upload_date": meta.get("upload_date", ""),
            "duration": meta.get("duration", ""),
        }

        uploader_id = (meta.get("uploader_id") or "").strip()
        if uploader_id:
            key = _normalize_handle(uploader_id)
            entry = creators.setdefault(key, {
                "key": key,
                "display_name": meta.get("uploader") or key,
                "channel_id": meta.get("channel_id") or "",
                "uploader_url": meta.get("uploader_url") or "",
                "videos": [],
            })
            if not entry["channel_id"] and meta.get("channel_id"):
                entry["channel_id"] = meta["channel_id"]
            if not entry["uploader_url"] and meta.get("uploader_url"):
                entry["uploader_url"] = meta["uploader_url"]
            if meta.get("uploader"):
                entry["display_name"] = meta["uploader"]
            entry["videos"].append(video_entry)
        else:
            display_name = meta.get("uploader") or meta.get("title") or task_id
            entry = unresolved.setdefault(display_name, {
                "display_name": display_name,
                "task_ids": [],
            })
            entry["task_ids"].append(task_id)

    return {
        "schema_version": 1,
        "built_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "scanned": {"entities": scanned},
        "creators": sorted(creators.values(), key=lambda c: c["key"]),
        "unresolved": sorted(unresolved.values(), key=lambda u: u["display_name"]),
    }


def write_index(index: dict, output_path: Path) -> None:
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.rename(output_path)


def check_index(work_dir: Path, index_path: Path) -> tuple[bool, str]:
    disk_count = len(list(work_dir.glob("*/meta.json")))
    if not index_path.is_file():
        return False, f"STALE: 索引缺失（{index_path}），磁盘 {disk_count} 条"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    indexed_count = index.get("scanned", {}).get("entities", 0)
    if indexed_count != disk_count:
        return False, f"STALE: 索引 {indexed_count} 条 / 磁盘 {disk_count} 条"
    return True, f"OK: 索引 {indexed_count} 条，与磁盘一致"


def main():
    parser = argparse.ArgumentParser(description="构建/核对 learn-video 的 creator 索引")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("check")
    args = parser.parse_args()

    videos_dir = store_config.videos_dir()
    work_dir = videos_dir / "work"
    index_path = videos_dir / "creators.json"

    if args.command == "build":
        index = build_index(work_dir)
        write_index(index, index_path)
        print(
            f"已写入 {index_path}：{len(index['creators'])} 位 creator，"
            f"{len(index['unresolved'])} 组 unresolved，"
            f"共 {index['scanned']['entities']} 条实体"
        )
    elif args.command == "check":
        ok, message = check_index(work_dir, index_path)
        print(message)
        if not ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests again to confirm they pass**

Run: `cd skills/research/learn-video && pytest tests/test_build_creator_index.py -v`
Expected: all 8 tests pass.

- [ ] **Step 5: Run the full learn-video test suite to check for regressions**

Run: `cd skills/research/learn-video && pytest -v`
Expected: all tests pass (Task 1's `test_archive.py` + this task's `test_build_creator_index.py`).

- [ ] **Step 6: Commit**

```bash
git add skills/research/learn-video/scripts/build_creator_index.py skills/research/learn-video/tests/test_build_creator_index.py
git commit -m "feat(learn-video): add build_creator_index build/check subcommands"
```

---

### Task 3: Update `SKILL.md` — archive is now validate-only, wire in the index build

**Files:**
- Modify: `skills/research/learn-video/SKILL.md` (frontmatter `version`, §"获取结果" comment, §"归档到统一存储根", §"参考文件")

**Interfaces:**
- No code interface — this is documentation the executing agent (a future `learn-video` invocation) reads to know how to call `archive.py`/`build_creator_index.py` correctly.

- [ ] **Step 1: Bump the version**

In the frontmatter (line 3): `version: "1.8.2"` → `version: "1.9.0"` (minor bump — new script + a behavior change to an existing one, no removed public interface since `archive.py` was never called with positional args by anything outside this SKILL.md).

- [ ] **Step 2: Fix the stale comment in "获取结果"**

Find (around line 237):

```
├── meta.json                 # 归档步骤写入
```

Replace with:

```
├── meta.json                 # vdl 写入（fetch 步骤完成时）
```

- [ ] **Step 3: Rewrite "归档到统一存储根"**

Replace the whole section (currently lines 251-263):

```markdown
## 归档到统一存储根

vdl 的产物已经落在统一存储根里了（`WORK_ROOT` 指向 `<knowledgeRoot>/videos`），meta.json 也已经由 vdl 自己写好——本 skill 不再写它，只校验：

```bash
cd "$HOME/Projects/harveyz-skill/skills/research/learn-video"  # 或本 skill 安装后的实际目录
TASK_ID="<task_id>" python3 scripts/archive.py
```

成功输出两行 `VIDEO_DIR: <path>` 和 `META_PATH: <path>`。**若报错说缺统一存储契约必填字段**（`source_url`/`title`/`fetched_at`），说明 vdl 那次没有把任务跑到 `completed`，不要试图在这里补字段——回去确认 vdl 那边的任务状态，或联系维护者核对 vdl 版本。

校验通过后，顺手重建一次 creator 索引（零额外成本——流程本来就在跑脚本）：

```bash
python3 scripts/build_creator_index.py build
```

`meta.json` 是索引的唯一凭据（`find <knowledgeRoot> -name meta.json` 就是全量实体清单）；`creators.json` 是这份清单按 uploader 归好的第二层索引，不含 `registry.json` 的任何信息。
```

- [ ] **Step 4: Update the reference table**

Replace the `archive.py` row and add a new row (currently lines 278-281):

```markdown
| 文件 | 用途 |
|------|------|
| `scripts/store_config.py` | 读共享 `knowledgeRoot`（`~/.hskill/config.json`），四个入范围 skill 各存一份内容相同的副本 |
| `scripts/archive.py` | 校验 vdl 已写好的 `meta.json` 是否满足统一存储契约（`source_url`/`title`/`fetched_at`）；不写文件，不足则报错退出 |
| `scripts/build_creator_index.py` | 全量重算 `<knowledgeRoot>/videos/creators.json`（`build`），或核对索引是否与磁盘实体数一致（`check`）——不读 `registry.json` |
```

- [ ] **Step 5: Commit**

```bash
git add skills/research/learn-video/SKILL.md
git commit -m "docs(learn-video): document archive.py validation + build_creator_index"
```

---

### Task 4: Bump `skills-index.json`'s `contentHash`/`contentVersion`

**Files:**
- Modify: `skills-index.json` (the `research/learn-video` entry)

**Interfaces:** none — this is a registry-consistency step required by this repo's own publish rule (F8: hash must change whenever `version` changes, and vice versa — see `skills/mint/publish-skill/SKILL.md`).

- [ ] **Step 1: Compute the new content hash**

```bash
compute_content_hash() {
  sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' "$1" | sha256sum | cut -c1-16
}
compute_content_hash skills/research/learn-video/SKILL.md
```

Copy the printed 16-character hex string — this is your new `contentHash`.

- [ ] **Step 2: Update `skills-index.json`**

Find the `research/learn-video` entry (around line 56-61):

```json
    {
      "path": "research/learn-video",
      "bundle": "research",
      "installScope": "global",
      "contentHash": "f01282325e8af7b9",
      "contentVersion": "1.8.2"
    },
```

Replace `contentHash` with the value from Step 1, and `contentVersion` with `"1.9.0"`.

- [ ] **Step 3: Verify with the repo's own test suite**

Run: `npm test`
Expected: passes — this is the suite that checks SKILL.md format compliance and skills-index.json consistency (per this repo's `CLAUDE.md`).

- [ ] **Step 4: Commit**

```bash
git add skills-index.json
git commit -m "chore(skills): bump learn-video version and contentHash"
```
