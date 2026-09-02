# 统一存储契约 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `clip-url` / `learn-video` / `sync-xtimeline` / `sync-ytchannel` 四个 skill 不再各自持有存储根配置，统一从 `~/.hskill/config.json` 的 `knowledgeRoot` 字段解析落盘路径，并提供一次性迁移脚本把历史数据搬过去。

**Architecture:** 每个入范围 skill 携带一份内容相同的 `scripts/store_config.py`（读 `knowledgeRoot`，拼出 `articles_dir()` / `videos_dir()` / `feeds_dir(channel)`）。clip-url 的 `vault_config.py`、两个 sync skill 的 `config.py` 改为委托它；`roster_client.py` 交出 `data_dir()`。`learn-video` 新增第一段本地脚本（归档 vdl 产物 + 写 `meta.json`）。`scripts/migrate-store.sh` 一次性把历史数据从旧根搬到新根，dry-run 默认、`--apply` 才执行。

**Tech Stack:** Python 3（每个 skill 的 `scripts/` 独立运行，无跨 skill import）、bash（迁移脚本，`set -euo pipefail` 三段式）、pytest（各 skill `tests/` 目录自动被 `scripts/run-skill-tests.sh` 发现）、bats-core（仓库根 `tests/*.bats`，`npm test` 里 `bats tests/` 直接扫描，不递归）。

**Spec:** `docs/superpowers/specs/2026-09-01-unified-store-design.md`（唯一权威设计依据，八节）；交接文档 `docs/commute/2026-09-01-unified-store-handoff.md`（最小验收锚点、关键决定、范围铁律）。

## Global Constraints

- **只做矩阵里的四个 skill**：`clip-url`、`learn-video`、`sync-xtimeline`、`sync-ytchannel`。不碰 `learn-paper`/`fetch-paper`/`pdf-math-translate`/`learn-skill`/`survey-skillrepo`，不碰 `vdl`（另一个仓库），不碰任何 skill 的抓取契约/翻译流程/去重算法/游标语义。
- **不新增索引文件**（`index.jsonl` 之类）。`find <ROOT> -name meta.json` 就是全量清单。
- **不统一实体目录内部结构。** `Origin/`+`Translation/` 与 `transcript/`+`writing/` 的差异保留。
- **不为 Obsidian 保留兼容层**——软链、双写都不做。
- **`store_config.py` 四份内容完全相同**（clip-url / learn-video / sync-xtimeline / sync-ytchannel 各一份物理副本），这是仓库既定模式（`browser_fetch_locate.py` 已经这样做）。
- **`HSKILL_CONFIG` 环境变量**覆盖 `~/.hskill/config.json` 路径，供测试注入临时根；每次调用时读取（不在 import 时绑定），保证进程内 monkeypatch 生效。
- **不做目录创建在 `store_config.py` 里**——读路径与建目录分离，各 skill 在真正写文件时自己 `mkdir -p`。
- **迁移脚本禁止整目录 `mv` Obsidian vault**：只搬同时满足「目录名匹配 `^[0-9a-f]{8}$`」且「内含 `meta.json`」两个条件的子目录，其余一律列入"跳过"，绝不触碰。
- 分支 `feature/unified-store`（已从 `doc/unified-store-design` 拉出）。commit-msg 强制 Conventional Commits：`feat|fix|chore|docs|refactor|test|style|perf`（是 `docs` 不是 `doc`）。每个 Task 结束提交一次。
- Python 测试运行：`cd skills/<category>/<skill> && python3 -m pytest tests/ -q`。bats 测试运行：`bats tests/migrate-store.bats`（仓库根）。全量验证用 `npm test`。

---

## Task 1: `store_config.py` 规范实现（先在 clip-url 落地，作为其余三份副本的蓝本）

**Files:**
- Create: `skills/research/clip-url/scripts/store_config.py`
- Test: `skills/research/clip-url/tests/test_store_config.py`

**Interfaces:**
- Produces（后续所有 Task 依赖的公共接口，四份副本完全一致）：
  - `get_root() -> Path` — 读 `knowledgeRoot`；config 不存在抛 `FileNotFoundError`，缺字段抛 `KeyError`，异常信息含初始化引导语
  - `articles_dir() -> Path` — `get_root() / "articles"`
  - `videos_dir() -> Path` — `get_root() / "videos"`
  - `feeds_dir(channel: str) -> Path` — `get_root() / "feeds" / channel`
  - `main()` — CLI `check` 子命令：配置齐全打印 `OK: <root>`（stdout）exit 0；缺失打印 `MISSING: <reason>`（stderr）exit 1
  - 环境变量 `HSKILL_CONFIG` 覆盖默认 `~/.hskill/config.json` 路径

- [ ] **Step 1: 写 `scripts/store_config.py`**

```python
#!/usr/bin/env python3
"""统一存储根解析：读 ~/.hskill/config.json 的 knowledgeRoot 字段，为
clip-url / learn-video / sync-xtimeline / sync-ytchannel 四个 skill 提供
落盘路径。四份内容相同的副本——本仓库既定模式（browser_fetch_locate.py
就在三处各存一份）。

只做"读一个字符串再拼一层固定子目录名"，不做目录创建——各 skill 在真正
写文件时自己 mkdir -p，保持"读路径"与"建目录"分离。

支持 HSKILL_CONFIG 环境变量覆盖 config 路径，供测试注入临时根；每次调用
时读取（不在 import 时绑定），进程内 monkeypatch 才能生效。
"""
import json
import os
import sys
from pathlib import Path

_INIT_HINT = "抓取产物统一存到哪个目录？（直接回车使用默认：~/Documents/knowledge）"


def _config_path() -> Path:
    env_cfg = os.environ.get("HSKILL_CONFIG")
    return Path(env_cfg) if env_cfg else Path.home() / ".hskill" / "config.json"


def get_root() -> Path:
    config_path = _config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"{config_path} 不存在，请先完成初始化：{_INIT_HINT}")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if "knowledgeRoot" not in cfg:
        raise KeyError(f"{config_path} 缺少 knowledgeRoot 字段，请先完成初始化：{_INIT_HINT}")
    return Path(cfg["knowledgeRoot"])


def articles_dir() -> Path:
    return get_root() / "articles"


def videos_dir() -> Path:
    return get_root() / "videos"


def feeds_dir(channel: str) -> Path:
    return get_root() / "feeds" / channel


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        try:
            print(f"OK: {get_root()}")
        except (FileNotFoundError, KeyError) as e:
            print(f"MISSING: {e}", file=sys.stderr)
            sys.exit(1)
        return
    print("Usage: store_config.py check", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 写 `tests/test_store_config.py`**

```python
"""Unit tests for store_config.py — the shared knowledgeRoot resolver
copied identically into clip-url / learn-video / sync-xtimeline /
sync-ytchannel. Pure filesystem I/O against a fake config.json, never the
real ~/.hskill/config.json."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import store_config  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "store_config.py"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("HSKILL_CONFIG", str(config_path))
    return config_path


def _write(config_path: Path, **fields) -> None:
    config_path.write_text(json.dumps(fields), encoding="utf-8")


def test_get_root_raises_when_config_missing(isolated_config):
    with pytest.raises(FileNotFoundError):
        store_config.get_root()


def test_get_root_raises_when_knowledge_root_key_missing(isolated_config):
    _write(isolated_config, skillDir="/some/other/path")
    with pytest.raises(KeyError):
        store_config.get_root()


def test_get_root_reads_configured_value(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    assert store_config.get_root() == Path("/fake/knowledge")


def test_articles_dir(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    assert store_config.articles_dir() == Path("/fake/knowledge/articles")


def test_videos_dir(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    assert store_config.videos_dir() == Path("/fake/knowledge/videos")


def test_feeds_dir(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    assert store_config.feeds_dir("tweets") == Path("/fake/knowledge/feeds/tweets")
    assert store_config.feeds_dir("youtube") == Path("/fake/knowledge/feeds/youtube")


def test_hskill_config_env_overrides_default_path(tmp_path, monkeypatch):
    other_path = tmp_path / "other-config.json"
    other_path.write_text(json.dumps({"knowledgeRoot": "/other/root"}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_CONFIG", str(other_path))
    assert store_config.get_root() == Path("/other/root")


def test_cli_check_prints_ok_and_exits_zero_when_configured(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check"],
        env={**os.environ, "HSKILL_CONFIG": str(isolated_config)},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "OK: /fake/knowledge"


def test_cli_check_prints_missing_and_exits_one_when_config_absent(tmp_path):
    missing_path = tmp_path / "does-not-exist.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check"],
        env={**os.environ, "HSKILL_CONFIG": str(missing_path)},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    assert result.stderr.strip().startswith("MISSING:")
```

- [ ] **Step 3: 运行测试**

```bash
cd skills/research/clip-url && python3 -m pytest tests/test_store_config.py -v
```

Expected: 全部 PASS（9 项）。

- [ ] **Step 4: Commit**

```bash
git add skills/research/clip-url/scripts/store_config.py skills/research/clip-url/tests/test_store_config.py
git commit -m "feat(clip-url): add store_config.py for the unified knowledgeRoot"
```

---

## Task 2: 复制 `store_config.py` 到其余三个 skill

**Files:**
- Create: `skills/research/learn-video/scripts/store_config.py`（同时新建 `scripts/` 目录——learn-video 目前没有）
- Create: `skills/research/learn-video/tests/store_config` 测试见 Task 9（learn-video 的 `tests/` 目录一并在 Task 9 建立，含 conftest）
- Create: `skills/feed/sync-xtimeline/scripts/store_config.py`
- Test: `skills/feed/sync-xtimeline/tests/test_store_config.py`
- Create: `skills/feed/sync-ytchannel/scripts/store_config.py`
- Test: `skills/feed/sync-ytchannel/tests/test_store_config.py`

**Interfaces:**
- Consumes: Task 1 的 `store_config.py` / `test_store_config.py` 源文本（逐字节复制）
- Produces: 同 Task 1（三处独立副本，供 Task 5/7/9 委托调用）

- [ ] **Step 1: 复制到 sync-xtimeline 和 sync-ytchannel（scripts/ 已存在）**

```bash
cp skills/research/clip-url/scripts/store_config.py skills/feed/sync-xtimeline/scripts/store_config.py
cp skills/research/clip-url/scripts/store_config.py skills/feed/sync-ytchannel/scripts/store_config.py
cp skills/research/clip-url/tests/test_store_config.py skills/feed/sync-xtimeline/tests/test_store_config.py
cp skills/research/clip-url/tests/test_store_config.py skills/feed/sync-ytchannel/tests/test_store_config.py
```

- [ ] **Step 2: 新建 learn-video 的 scripts/ 目录并放入副本**

```bash
mkdir -p skills/research/learn-video/scripts
cp skills/research/clip-url/scripts/store_config.py skills/research/learn-video/scripts/store_config.py
```

（learn-video 的 `test_store_config.py` 放到 Task 9，因为那时才一并新建 `tests/conftest.py`。）

- [ ] **Step 3: 运行 xtimeline 和 ytchannel 的新测试**

```bash
cd skills/feed/sync-xtimeline && python3 -m pytest tests/test_store_config.py -v
cd ../sync-ytchannel && python3 -m pytest tests/test_store_config.py -v
```

Expected: 两处各 9 项 PASS（这两个 skill 目前没有 `conftest.py` 里会冲突的 autouse fixture 影响 `store_config` 的隔离——`test_store_config.py` 自带的 `isolated_config` fixture 独立生效）。

- [ ] **Step 4: Commit**

```bash
git add skills/research/learn-video/scripts/store_config.py \
        skills/feed/sync-xtimeline/scripts/store_config.py skills/feed/sync-xtimeline/tests/test_store_config.py \
        skills/feed/sync-ytchannel/scripts/store_config.py skills/feed/sync-ytchannel/tests/test_store_config.py
git commit -m "feat: copy store_config.py into learn-video / sync-xtimeline / sync-ytchannel"
```

---

## Task 3: clip-url — `vault_config.py` 委托 `store_config`

**Files:**
- Modify: `skills/research/clip-url/scripts/vault_config.py`
- Modify: `skills/research/clip-url/tests/conftest.py`
- Modify: `skills/research/clip-url/tests/test_vault_config.py`
- Modify: `skills/research/clip-url/tests/test_dedup_check.py`
- Modify: `skills/research/clip-url/tests/test_write_meta_and_separate.py`

**Interfaces:**
- Consumes: Task 1 的 `store_config.articles_dir() -> Path`
- Produces: `vault_config.get_vault_path() -> str`（不变的签名，内部改为委托）、`get_article_paths(url) -> dict`（不变，下游 `dedup_check.py`/`article_meta.py`/`write_meta_and_separate.py` 零改动）

- [ ] **Step 1: 改写 `vault_config.py`**

```python
#!/usr/bin/env python3
"""Article path resolution for clip-url. Delegates the storage root to
store_config.articles_dir() — VAULT_PATH (the old
~/.hskill/url-extract/config.json field) has retired; that config file
now only carries fixed_tags.txt's directory. See
docs/superpowers/specs/2026-09-01-unified-store-design.md §5.1.
"""
import hashlib
from pathlib import Path

import store_config


def get_vault_path() -> str:
    return str(store_config.articles_dir())


def get_url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:8]


def get_article_paths(url: str) -> dict:
    """origin_path/translation_path aren't included here — their filename
    is derived from the article's title (sanitize_filename(title) + ".md",
    matching extract-url's convention), which isn't known until after
    fetch_article extracts it. Callers get the real origin_path from
    fetch_article's response, and derive translation_path from it (same
    filename, Origin -> Translation)."""
    vault_path = get_vault_path()
    url_hash = get_url_hash(url)
    article_dir = Path(vault_path) / url_hash
    return {
        "article_dir": article_dir,
        "meta_path": article_dir / "meta.json",
    }
```

（原来的 `main()`/`check` CLI 一并删除——初始化检查改由 `store_config.py check` 承担，见 Task 4。）

- [ ] **Step 2: 改写 `tests/conftest.py`（隔离点从 VAULT_PATH 切到 knowledgeRoot）**

```python
"""Shared test isolation for clip-url: points store_config at a fake
config.json under tmp_path for every test in this directory (autouse),
so a test file that forgets to declare its own isolation still can't read
or write the real ~/.hskill/config.json. Does not write config content —
tests that need a valid knowledgeRoot write it themselves (building on
isolated_store_config); tests exercising a missing/invalid config leave
it absent."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def isolated_store_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("HSKILL_CONFIG", str(config_path))
    return config_path
```

- [ ] **Step 3: 改写 `tests/test_vault_config.py`**

```python
"""Unit tests for vault_config.py — pure delegation to store_config for
the storage root; own logic only covers md5 hashing and path
composition."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from vault_config import get_article_paths, get_url_hash, get_vault_path  # noqa: E402


def _write_root(isolated_store_config, root: Path) -> None:
    isolated_store_config.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")


def test_get_vault_path_delegates_to_store_config(isolated_store_config, tmp_path):
    root = tmp_path / "knowledge"
    _write_root(isolated_store_config, root)
    assert get_vault_path() == str(root / "articles")


def test_get_url_hash_matches_md5_first_8_chars():
    url = "https://example.com/article"
    expected = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    assert get_url_hash(url) == expected


def test_get_article_paths_layout(isolated_store_config, tmp_path):
    root = tmp_path / "knowledge"
    _write_root(isolated_store_config, root)
    url = "https://example.com/article"
    paths = get_article_paths(url)
    url_hash = get_url_hash(url)
    assert paths["article_dir"] == root / "articles" / url_hash
    assert paths["meta_path"] == root / "articles" / url_hash / "meta.json"
```

（原先针对 `~/.hskill/url-extract/config.json` 缺失/缺字段消息里要不要提 "clip-url"/"extract-url" 的测试一并删除——那是 `vault_config.py` 自己直接读配置文件时代的行为；现在异常从 `store_config.get_root()` 抛出，消息内容已经在 Task 1 的 `test_store_config.py` 里覆盖过，这里不重复断言。）

- [ ] **Step 4: 改写 `tests/test_dedup_check.py` 里的 fixture**

把文件顶部的

```python
@pytest.fixture(autouse=True)
def valid_vault_config(isolated_vault_config):
    vault_path = isolated_vault_config.parent / "vault"
    isolated_vault_config.write_text(json.dumps({"VAULT_PATH": str(vault_path)}), encoding="utf-8")
```

改为

```python
@pytest.fixture(autouse=True)
def valid_store_config(isolated_store_config, tmp_path):
    root = tmp_path / "knowledge"
    isolated_store_config.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")
```

其余测试函数体不变（都只调用 `is_already_fetched` / `get_article_paths`，跟 fixture 内容无关）。

- [ ] **Step 5: 改写 `tests/test_write_meta_and_separate.py` 里的同名 fixture**

把

```python
@pytest.fixture(autouse=True)
def valid_vault_config(isolated_vault_config, tmp_path, monkeypatch):
    vault_path = isolated_vault_config.parent / "vault"
    isolated_vault_config.write_text(json.dumps({"VAULT_PATH": str(vault_path)}), encoding="utf-8")
    fixed_tags_path = tmp_path / "fixed_tags.txt"
    fixed_tags_path.write_text("ai\n", encoding="utf-8")
    monkeypatch.setenv("FIXED_TAGS_PATH", str(fixed_tags_path))
```

改为

```python
@pytest.fixture(autouse=True)
def valid_store_config(isolated_store_config, tmp_path, monkeypatch):
    root = tmp_path / "knowledge"
    isolated_store_config.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")
    fixed_tags_path = tmp_path / "fixed_tags.txt"
    fixed_tags_path.write_text("ai\n", encoding="utf-8")
    monkeypatch.setenv("FIXED_TAGS_PATH", str(fixed_tags_path))
```

测试体内 `vault_config.get_article_paths(url)["article_dir"]` 等调用不变。

- [ ] **Step 6: 运行 clip-url 全部测试**

```bash
cd skills/research/clip-url && python3 -m pytest tests/ -q
```

Expected: 全绿。若有遗漏的 `isolated_vault_config`/`HSKILL_EXTRACT_URL_CONFIG` 残留引用导致失败，按报错定位并按上面同样的改法修掉（`article_meta.py`/`dedup_check.py`/`write_meta_and_separate.py` 三个生产脚本本身不需要改，只有测试 fixture 需要跟着 conftest 改名）。

- [ ] **Step 7: Commit**

```bash
git add skills/research/clip-url/scripts/vault_config.py skills/research/clip-url/tests/
git commit -m "refactor(clip-url): vault_config delegates storage root to store_config"
```

---

## Task 4: clip-url — SKILL.md 初始化 / 边界 / 参考文件更新

**Files:**
- Modify: `skills/research/clip-url/SKILL.md`

**Interfaces:**
- Consumes: Task 1 的 `store_config.py check` CLI 输出格式（`OK:`/`MISSING:`）

- [ ] **Step 1: 替换「② 检查共享配置」小节（第 29-35 行）**

old:
```
**② 检查共享配置**

运行 `python3 scripts/vault_config.py check`。若报缺失，引导用户提供 Obsidian Vault
绝对路径。写入前先确保目录存在（`mkdir -p ~/.hskill/url-extract/`），再写入
`~/.hskill/url-extract/config.json` 的 `VAULT_PATH` 字段，并在同目录创建空的
`fixed_tags.txt`。配置目录名 `url-extract` 是历史遗留，clip-url 沿用同一份
配置，以便与历史抓取记录互相去重。
```

new:
```
**② 检查共享配置**

运行 `python3 scripts/store_config.py check`。若输出 `MISSING:`，询问用户"抓取产物
统一存到哪个目录？（直接回车使用默认：`~/Documents/knowledge`）"，将回答展开为绝对
路径，写入 `~/.hskill/config.json` 的 `knowledgeRoot` 字段（文件不存在则新建；若已
存在 `skillDir` 等其他字段，只增改 `knowledgeRoot`，不覆盖）。再确保
`~/.hskill/url-extract/` 目录存在（`mkdir -p ~/.hskill/url-extract/`）并在其中创建
空的 `fixed_tags.txt`（若不存在）——这份历史目录现在只承载固定词表，文章存储路径
已改由 `knowledgeRoot` 统一解析，不再读取其中的 `VAULT_PATH` 字段。
```

- [ ] **Step 2: 替换「步骤 2.5」小节（第 80-92 行）**

old:
```
### 步骤 2.5：确认共享配置存在（VAULT_PATH / 固定词表）

```python
import subprocess
result = subprocess.run(
    ['python3', '-c',
     'import sys; sys.path.insert(0, "scripts"); import vault_config; print(vault_config.get_vault_path())'],
    capture_output=True, text=True
)
```

- 若 `result.returncode != 0`（`config.json` 不存在，或存在但缺 `VAULT_PATH` 字段）：向用户报告"共享配置缺失，请先完成本文档「初始化」小节的 ② 检查共享配置，再回来使用本 skill"，流程终止。
- 若 `result.returncode == 0`：再检查 `~/.hskill/url-extract/fixed_tags.txt` 是否存在：
```

new:
```
### 步骤 2.5：确认共享配置存在（knowledgeRoot / 固定词表）

```bash
python3 scripts/store_config.py check
```

- 若输出 `MISSING:`（`~/.hskill/config.json` 不存在，或存在但缺 `knowledgeRoot` 字段）：向用户报告"共享配置缺失，请先完成本文档「初始化」小节的 ② 检查共享配置，再回来使用本 skill"，流程终止。
- 若输出 `OK: <root>`：再检查 `~/.hskill/url-extract/fixed_tags.txt` 是否存在：
```

（该小节剩余的 `ls ... fixed_tags.txt` 代码块与提示文案不变。）

- [ ] **Step 3: 替换步骤 3 里提到 VAULT_PATH 的一句**

old（第 100 行内）：
```
文章存储目录由 Subagent 1 内部通过共享的 VAULT_PATH 自动计算，不再需要这里传参。
```

new：
```
文章存储目录由 Subagent 1 内部通过共享的 knowledgeRoot 自动计算，不再需要这里传参。
```

- [ ] **Step 4: 替换「边界」小节里的存储布局描述（第 170 行）**

old:
```
沿用与已归档的 extract-url 相同的存储布局与去重索引，因此历史抓取记录仍然有效：URL 去重和固定标签词表读同一份 `~/.hskill/url-extract/config.json`（`VAULT_PATH`）和 `fixed_tags.txt`；抓取产出的原文文件名沿用同一命名规则，按标题命名（`Origin/<标题>.md`，Translation 沿用同一文件名），两者共存于同一个 `<hash8>/` 目录下，去重判定只看 `meta.json` 的 `source_url`，不受文件名影响——历史抓取记录与新抓取的文章互相认得出"已抓取"。
```

new:
```
文章统一落在 `<knowledgeRoot>/articles/<hash8>/` 下（`knowledgeRoot` 见 `~/.hskill/config.json`，由 `store_config.py` 解析）；固定标签词表仍读 `~/.hskill/url-extract/fixed_tags.txt`（这是这份历史配置目录唯一保留的用途，`VAULT_PATH` 字段已退休，不再读取）。抓取产出的原文文件名按标题命名（`Origin/<标题>.md`，Translation 沿用同一文件名），两者共存于同一个 `<hash8>/` 目录下，去重判定只看 `meta.json` 的 `source_url`，不受文件名影响。历史抓取记录（原 Obsidian vault 下的数据）需要先跑 `bash scripts/migrate-store.sh --apply`（仓库根）搬过来，才能被新根下的去重判定认出。
```

- [ ] **Step 5: 替换「参考文件」表格里 `vault_config.py` 那一行，并新增 `store_config.py` 一行（第 180-182 行附近）**

old（第 182 行）：
```
| `scripts/vault_config.py` | 读共享 `VAULT_PATH`（`~/.hskill/url-extract/config.json`），计算文章路径 |
```

new（插入在 `browser_fetch_cli.py` 行之后，`vault_config.py` 行之前，新增一行；`vault_config.py` 行本身改写）：
```
| `scripts/store_config.py` | 读共享 `knowledgeRoot`（`~/.hskill/config.json`），四个入范围 skill 各存一份内容相同的副本 |
| `scripts/vault_config.py` | 委托 `store_config.articles_dir()` 计算文章路径；`fixed_tags.txt` 仍读 `~/.hskill/url-extract/` |
```

- [ ] **Step 6: 更新 frontmatter 版本号**

把第 3 行 `version: "0.8.1"` 改为 `version: "0.9.0"`（存储落点是用户可见的行为变更，minor bump）。

- [ ] **Step 7: Commit**

```bash
git add skills/research/clip-url/SKILL.md
git commit -m "docs(clip-url): SKILL.md init/boundary/reference sections follow knowledgeRoot"
```

---

## Task 5: sync-xtimeline — `config.py` 委托 `store_config`，`roster_client.py` 交出 `data_dir()`，四个调用点改路径

**Files:**
- Modify: `skills/feed/sync-xtimeline/scripts/config.py`
- Modify: `skills/feed/sync-xtimeline/scripts/roster_client.py`
- Modify: `skills/feed/sync-xtimeline/scripts/archive_tweets.py:25`
- Modify: `skills/feed/sync-xtimeline/scripts/render_digest.py:85`
- Modify: `skills/feed/sync-xtimeline/tests/conftest.py`
- Modify: `skills/feed/sync-xtimeline/tests/test_archive_tweets.py`
- Modify: `skills/feed/sync-xtimeline/tests/test_render_digest.py`

**Interfaces:**
- Consumes: Task 1 的 `store_config.feeds_dir("tweets") -> Path`
- Produces: `config.get_data_dir() -> Path`（语义变化：直接返回渠道目录 `<ROOT>/feeds/tweets`，不再是共用根）

- [ ] **Step 1: 改写 `config.py`**

```python
#!/usr/bin/env python3
"""sync-xtimeline 的数据目录：通过 store_config 向统一存储根要 tweets 渠道
目录（<ROOT>/feeds/tweets）。刻意在调用时才向 store_config 取值（而不是
import 时绑定函数对象），这样测试能在进程内重定向。
"""
from pathlib import Path

import store_config


def get_data_dir() -> Path:
    return store_config.feeds_dir("tweets")
```

- [ ] **Step 2: 从 `roster_client.py` 删除 `data_dir()`**

删除第 28-29 行：
```python
def data_dir() -> Path:
    return Path(_run("data-dir"))


```
（保留 `channels()` / `get_cursor()` / `set_cursor()` / `set_error()` 四个函数不动；文件顶部 `from pathlib import Path` 的 import 若删除 `data_dir()` 后仍被其他函数用到（`get_cursor`/`set_cursor` 签名里没用到 `Path`，检查一下——若 `Path` 不再被引用则一并删除该 import；若仍有引用则保留）。

- [ ] **Step 3: `archive_tweets.py:25` 去掉中间的 `"tweets"` 段**

old:
```python
def _archive_path(handle: str) -> Path:
    return Path(get_data_dir()) / "tweets" / "creators" / f"{handle}.json"
```

new:
```python
def _archive_path(handle: str) -> Path:
    return Path(get_data_dir()) / "creators" / f"{handle}.json"
```

- [ ] **Step 4: `render_digest.py:85` 同样去掉中间段**

old:
```python
    digests_dir = Path(get_data_dir()) / "tweets" / "digest"
```

new:
```python
    digests_dir = Path(get_data_dir()) / "digest"
```

- [ ] **Step 5: 改写 `tests/conftest.py`**

```python
"""sync-xtimeline 的测试隔离：config.get_data_dir() 通过 store_config 向
统一存储根要 tweets 渠道目录（<ROOT>/feeds/tweets）。用 HSKILL_CONFIG 指向
一份临时 config.json 完成隔离——进程内、子进程两种场景都靠这一个环境变量，
不需要再对 roster_client 打 monkeypatch（config.py 不再经它取路径）。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

HSKILL_CONFIG_ENV = "HSKILL_CONFIG"


def write_config(config_path: Path, root: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch) -> Path:
    config_path = tmp_path / "config.json"
    root = tmp_path / "knowledge-root"
    write_config(config_path, root)
    monkeypatch.setenv(HSKILL_CONFIG_ENV, str(config_path))
    return root / "feeds" / "tweets"
```

- [ ] **Step 6: 改写 `tests/test_archive_tweets.py` 的 `_run` 与 CLI 测试**

把

```python
def _run(report: dict, data_dir: Path) -> subprocess.CompletedProcess:
    config_path = data_dir.parent / "config.json"
    write_config(config_path, data_dir)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(report),
        env={**os.environ, "HSKILL_ROSTER_CONFIG": str(config_path)},
        capture_output=True, text=True, timeout=10,
    )
```

改为

```python
def _run(report: dict, root: Path) -> subprocess.CompletedProcess:
    config_path = root.parent / "config.json"
    write_config(config_path, root)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(report),
        env={**os.environ, "HSKILL_CONFIG": str(config_path)},
        capture_output=True, text=True, timeout=10,
    )
```

把

```python
def test_cli_archives_report_from_stdin(tmp_path):
    data_dir = tmp_path / "data"
    report = {"run_time": "t", "new": {"alice": [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1"}]}}
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    saved = json.loads((data_dir / "tweets" / "creators" / "alice.json").read_text(encoding="utf-8"))
    assert saved == report["new"]["alice"]
```

改为

```python
def test_cli_archives_report_from_stdin(tmp_path):
    root = tmp_path / "knowledge"
    report = {"run_time": "t", "new": {"alice": [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1"}]}}
    result = _run(report, root)
    assert result.returncode == 0, result.stderr
    saved = json.loads((root / "feeds" / "tweets" / "creators" / "alice.json").read_text(encoding="utf-8"))
    assert saved == report["new"]["alice"]
```

其余测试函数（直接调用 `archive_tweets()`/`_archive_path()`/`advance_cursors()` 的那些）不用改——它们依赖 conftest 的 autouse fixture，行为不变。

- [ ] **Step 7: 改写 `tests/test_render_digest.py` 的 `_run` 与三个 CLI 测试**

`_run` 的改法同 Step 6（`data_dir` 参数改名 `root`，`HSKILL_ROSTER_CONFIG` 改 `HSKILL_CONFIG`）。

把

```python
def test_cli_empty_report_prints_empty_and_writes_no_file(tmp_path):
    data_dir = tmp_path / "data"
    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {}, "failures": {}}
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EMPTY"
    assert not (data_dir / "tweets" / "digest").exists()
```

改为

```python
def test_cli_empty_report_prints_empty_and_writes_no_file(tmp_path):
    root = tmp_path / "knowledge"
    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {}, "failures": {}}
    result = _run(report, root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EMPTY"
    assert not (root / "feeds" / "tweets" / "digest").exists()
```

把

```python
def test_cli_nonempty_report_writes_timestamped_file(tmp_path):
    data_dir = tmp_path / "data"
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {}, "baselines": {"carol": 3}, "failures": {},
    }
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.exists()
    assert written_path.name == "digest-20260815T090000.md"
    assert "@carol" in written_path.read_text(encoding="utf-8")


def test_cli_digest_lands_under_the_platform_subdirectory(tmp_path):
    """两个 sync skill 共用同一个 DATA_DIR，渠道各有自己的子目录。"""
    data_dir = tmp_path / "data"
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {}, "baselines": {"carol": 3}, "failures": {},
    }
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.parent == data_dir / "tweets" / "digest"
```

改为

```python
def test_cli_nonempty_report_writes_timestamped_file(tmp_path):
    root = tmp_path / "knowledge"
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {}, "baselines": {"carol": 3}, "failures": {},
    }
    result = _run(report, root)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.exists()
    assert written_path.name == "digest-20260815T090000.md"
    assert "@carol" in written_path.read_text(encoding="utf-8")


def test_cli_digest_lands_under_the_feeds_subdirectory(tmp_path):
    """两个 sync skill 共用同一份 knowledgeRoot 配置，渠道各有自己的子目录。"""
    root = tmp_path / "knowledge"
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {}, "baselines": {"carol": 3}, "failures": {},
    }
    result = _run(report, root)
    assert result.returncode == 0, result.stderr
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.parent == root / "feeds" / "tweets" / "digest"
```

- [ ] **Step 8: 运行 sync-xtimeline 全部测试**

```bash
cd skills/feed/sync-xtimeline && python3 -m pytest tests/ -q
```

Expected: 全绿。`test_roster_client.py`/`test_cursor.py`/`test_fetch_new_tweets.py`/`test_mcp_timeline_client.py`/`test_browser_fetch_locate.py` 不涉及 `get_data_dir`，不需要改动，应保持原样通过。

- [ ] **Step 9: Commit**

```bash
git add skills/feed/sync-xtimeline/scripts/config.py skills/feed/sync-xtimeline/scripts/roster_client.py \
        skills/feed/sync-xtimeline/scripts/archive_tweets.py skills/feed/sync-xtimeline/scripts/render_digest.py \
        skills/feed/sync-xtimeline/tests/
git commit -m "refactor(sync-xtimeline): config.get_data_dir delegates to store_config, drop roster data_dir()"
```

---

## Task 6: sync-xtimeline — SKILL.md 更新

**Files:**
- Modify: `skills/feed/sync-xtimeline/SKILL.md`

- [ ] **Step 1: 「② 检查 roster 名册」小节末尾（第 33 行）新增一句知识根检查**

old:
```
所有产物（`tweets/digest/`、`tweets/creators/<handle>.json`）落在名册的数据目录下的 `tweets/` 子目录里，跟 sync-ytchannel 共用同一个 `DATA_DIR`（各自渠道各占一个顶层子目录）。
```

new:
```
所有产物（`digest/`、`creators/<handle>.json`）落在统一存储根下的 `feeds/tweets/` 子目录里（`<knowledgeRoot>/feeds/tweets/`），跟 sync-ytchannel 共用同一份 `knowledgeRoot` 配置（各自渠道各占 `feeds/` 下一个子目录）。运行 `python3 scripts/store_config.py check`，若输出 `MISSING:`，询问用户"抓取产物统一存到哪个目录？（直接回车使用默认：`~/Documents/knowledge`）"，写入 `~/.hskill/config.json` 的 `knowledgeRoot` 字段（若已有 `skillDir` 等字段，只增改 `knowledgeRoot`）。
```

- [ ] **Step 2: 「用法」小节里读历史归档的路径提示（第 42 行）**

old:
```
`add` / `remove` / `list` 已迁到 [manage-creators](../manage-creators/)。查看归档过的历史推文，直接读 `DATA_DIR/tweets/creators/<handle>.json`（外部应用读，不是本 skill 的职责）。
```

new:
```
`add` / `remove` / `list` 已迁到 [manage-creators](../manage-creators/)。查看归档过的历史推文，直接读 `<knowledgeRoot>/feeds/tweets/creators/<handle>.json`（外部应用读，不是本 skill 的职责）。
```

- [ ] **Step 3: run 步骤 4/5 里的路径提示（第 53-54 行）**

old（第 53 行片段）：`非空时写入 DATA_DIR/tweets/digest/digest-<TS>.md`
new：`非空时写入 <knowledgeRoot>/feeds/tweets/digest/digest-<TS>.md`

old（第 54 行片段）：`把本次新推文累加进 tweets/creators/<handle>.json`
new：`把本次新推文累加进 <knowledgeRoot>/feeds/tweets/creators/<handle>.json`

- [ ] **Step 4: 「边界」小节（第 61 行）**

old:
```
跟 [sync-ytchannel](../sync-ytchannel/) 共用同一份 roster 名册和同一个数据目录，各渠道各占一个顶层子目录（本 skill 落 `tweets/`）。
```

new:
```
跟 [sync-ytchannel](../sync-ytchannel/) 共用同一份 roster 名册（游标/渠道列表）和同一份 `knowledgeRoot` 配置，各渠道在 `feeds/` 下各占一个子目录（本 skill 落 `feeds/tweets/`）。历史归档（原 roster `DATA_DIR/tweets/`）需要先跑 `bash scripts/migrate-store.sh --apply`（仓库根）搬过来。
```

- [ ] **Step 5: 「参考文件」表格（第 67-77 行）**

在 `platforms/` 行之后插入一行，`config.py` 行改写，`render_digest.py`/`archive_tweets.py` 两行的路径描述改写：

old（第 68、76、77 行）：
```
| `scripts/config.py` | 数据目录：运行时向 roster 要，本 skill 不再自持 `DATA_DIR` |
...
| `scripts/render_digest.py` | `run` 子命令的第二阶段：把翻译后的报告渲染成 Markdown，非空时写入 `DATA_DIR/tweets/digest/` |
| `scripts/archive_tweets.py` | `run` 子命令的第三阶段、本轮的提交点：把新推文按博主累加进 `DATA_DIR/tweets/creators/<handle>.json`（按 tweet_id 去重），然后推进游标 |
```

new:
```
| `scripts/store_config.py` | 读共享 `knowledgeRoot`（`~/.hskill/config.json`），四个入范围 skill 各存一份内容相同的副本 |
| `scripts/config.py` | 数据目录：运行时向 `store_config` 要 `feeds/tweets`，本 skill 不再自持 `DATA_DIR` |
...
| `scripts/render_digest.py` | `run` 子命令的第二阶段：把翻译后的报告渲染成 Markdown，非空时写入 `<knowledgeRoot>/feeds/tweets/digest/` |
| `scripts/archive_tweets.py` | `run` 子命令的第三阶段、本轮的提交点：把新推文按博主累加进 `<knowledgeRoot>/feeds/tweets/creators/<handle>.json`（按 tweet_id 去重），然后推进游标 |
```

- [ ] **Step 6: 更新 frontmatter 版本号**

把第 3 行 `version: "0.7.1"` 改为 `version: "0.8.0"`。

- [ ] **Step 7: Commit**

```bash
git add skills/feed/sync-xtimeline/SKILL.md
git commit -m "docs(sync-xtimeline): SKILL.md follows knowledgeRoot / feeds layout"
```

---

## Task 7: sync-ytchannel — `config.py` 委托、`roster_client.py` 交出 `data_dir()`、四个调用点、测试隔离重做

**Files:**
- Modify: `skills/feed/sync-ytchannel/scripts/config.py`
- Modify: `skills/feed/sync-ytchannel/scripts/roster_client.py`
- Modify: `skills/feed/sync-ytchannel/scripts/archive_videos.py:25`
- Modify: `skills/feed/sync-ytchannel/scripts/digest.py:67`
- Modify: `skills/feed/sync-ytchannel/tests/conftest.py`
- Modify: `skills/feed/sync-ytchannel/tests/test_archive_videos.py`
- Modify: `skills/feed/sync-ytchannel/tests/test_digest.py`
- Modify: `skills/feed/sync-ytchannel/tests/test_fetch_new_videos.py`

**Interfaces:**
- Consumes: Task 1 的 `store_config.feeds_dir("youtube") -> Path`
- Produces: `config.get_data_dir() -> Path`（同 Task 5，返回渠道目录）

- [ ] **Step 1: 改写 `config.py`**

```python
#!/usr/bin/env python3
"""sync-ytchannel 的数据目录：通过 store_config 向统一存储根要 youtube 渠道
目录（<ROOT>/feeds/youtube）——sync-xtimeline 的 youtube 对应实现。刻意在
调用时才向 store_config 取值（而不是 import 时绑定函数对象），这样测试能
在进程内重定向。
"""
from pathlib import Path

import store_config


def get_data_dir() -> Path:
    return store_config.feeds_dir("youtube")
```

- [ ] **Step 2: 从 `roster_client.py` 删除 `data_dir()`**（同 Task 5 Step 2 的做法，删第 28-29 行，检查 `Path` import 是否仍被引用）

- [ ] **Step 3: `archive_videos.py:25` 去掉中间段**

old:
```python
def _archive_path(handle: str) -> Path:
    return Path(get_data_dir()) / "youtube" / "creators" / f"{handle}.json"
```

new:
```python
def _archive_path(handle: str) -> Path:
    return Path(get_data_dir()) / "creators" / f"{handle}.json"
```

- [ ] **Step 4: `digest.py:67` 去掉中间段**

old:
```python
    digests_dir = Path(get_data_dir()) / "youtube" / "digest"
```

new:
```python
    digests_dir = Path(get_data_dir()) / "digest"
```

- [ ] **Step 5: 改写 `tests/conftest.py`（原来没有 autouse fixture，改成跟 sync-xtimeline 对称）**

```python
"""sync-ytchannel 的测试隔离：config.get_data_dir() 通过 store_config 向
统一存储根要 youtube 渠道目录（<ROOT>/feeds/youtube）。用 HSKILL_CONFIG 指向
一份临时 config.json 完成隔离，镜像 sync-xtimeline 的同名 fixture/helper。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

HSKILL_CONFIG_ENV = "HSKILL_CONFIG"


def write_config(config_path: Path, root: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch) -> Path:
    config_path = tmp_path / "config.json"
    root = tmp_path / "knowledge-root"
    write_config(config_path, root)
    monkeypatch.setenv(HSKILL_CONFIG_ENV, str(config_path))
    return root / "feeds" / "youtube"
```

- [ ] **Step 6: 改写 `tests/test_archive_videos.py`——删掉每个测试里的 `roster_client.data_dir` monkeypatch，`_run` 改用 `HSKILL_CONFIG`**

把文件里每一处

```python
    import roster_client
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
```

删除（这些测试函数不再需要 `tmp_path`/`monkeypatch` 参数里跟 `data_dir` 相关的部分——若某测试的参数列表因此不再用到 `monkeypatch`，把 `monkeypatch` 参数一并从函数签名删掉；`tmp_path` 若也不再被函数体使用，一并删掉）。

`test_archive_path_is_under_youtube_creators` 改为使用 conftest 的 `isolated_data_dir` fixture 取期望值：

old:
```python
def test_archive_path_is_under_youtube_creators(tmp_path, monkeypatch):
    import roster_client
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
    assert _archive_path("a") == tmp_path / "youtube" / "creators" / "a.json"
```

new:
```python
def test_archive_path_is_under_creators(isolated_data_dir):
    assert _archive_path("a") == isolated_data_dir / "creators" / "a.json"
```

`_run` 与 `test_cli_archives_report_from_stdin` 按 Task 5 Step 6 同样的模式改（`data_dir` 参数改名 `root`，`HSKILL_ROSTER_CONFIG` 改 `HSKILL_CONFIG`，断言路径改成 `root / "feeds" / "youtube" / "creators" / "a.json"`）。

- [ ] **Step 7: 改写 `tests/test_digest.py` 的 `_run` 与两个 CLI 测试**

把
```python
from conftest import ROSTER_CONFIG_ENV, write_config
```
改为
```python
from conftest import HSKILL_CONFIG_ENV, write_config
```

`_run` 里 `env={**os.environ, ROSTER_CONFIG_ENV: str(config_path)}` 改为 `env={**os.environ, HSKILL_CONFIG_ENV: str(config_path)}`，`data_dir` 参数改名 `root`（同 Task 5 Step 7 模式）。

`test_cli_empty_report_prints_empty_and_writes_no_file` 里 `assert not (data_dir / "youtube" / "digest").exists()` 改为 `assert not (root / "feeds" / "youtube" / "digest").exists()`。

`test_cli_nonempty_report_writes_timestamped_file` 里 `assert written_path.parent == data_dir / "youtube" / "digest"` 改为 `assert written_path.parent == root / "feeds" / "youtube" / "digest"`。

- [ ] **Step 8: 改写 `tests/test_fetch_new_videos.py`——`fake_roster` 去掉 `data_dir` monkeypatch，`_pending_path` 去掉中间段**

把 `fake_roster` fixture 里这一行删掉：
```python
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
```

把
```python
def _pending_path() -> Path:
    return get_data_dir() / "youtube" / "pending.json"
```
改为
```python
def _pending_path() -> Path:
    return get_data_dir() / "pending.json"
```

（`get_data_dir()` 现在通过 conftest 新增的 autouse `isolated_data_dir` fixture 隔离，不需要这个测试文件自己再管 `HSKILL_CONFIG`。）

- [ ] **Step 9: 运行 sync-ytchannel 全部测试，修掉剩余报错**

```bash
cd skills/feed/sync-ytchannel && python3 -m pytest tests/ -q
```

Expected: 全绿。若还有测试因为 `roster_client.data_dir` 被删除而 `AttributeError`（比如某处忘了改的 monkeypatch），按报错逐个定位删除/替换，模式同 Step 6-8。

- [ ] **Step 10: Commit**

```bash
git add skills/feed/sync-ytchannel/scripts/config.py skills/feed/sync-ytchannel/scripts/roster_client.py \
        skills/feed/sync-ytchannel/scripts/archive_videos.py skills/feed/sync-ytchannel/scripts/digest.py \
        skills/feed/sync-ytchannel/tests/
git commit -m "refactor(sync-ytchannel): config.get_data_dir delegates to store_config, drop roster data_dir()"
```

---

## Task 8: sync-ytchannel — SKILL.md 更新

**Files:**
- Modify: `skills/feed/sync-ytchannel/SKILL.md`

**Interfaces:**
- Consumes: 无（纯文档）

对照 Task 6 对 sync-xtimeline SKILL.md 的六处编辑，在 sync-ytchannel/SKILL.md 里做对称改动（`tweets`→`youtube`，`@handle`→`@handle` 不变，`sync-ytchannel`↔`sync-xtimeline` 互指不变）：

- [ ] **Step 1**：「② 检查 roster 名册」小节末尾（对应第 33 行）替换为：
```
所有产物（`digest/`、`creators/<handle>.json`）落在统一存储根下的 `feeds/youtube/` 子目录里（`<knowledgeRoot>/feeds/youtube/`），跟 sync-xtimeline 共用同一份 `knowledgeRoot` 配置（各自渠道各占 `feeds/` 下一个子目录）。运行 `python3 scripts/store_config.py check`，若输出 `MISSING:`，询问用户"抓取产物统一存到哪个目录？（直接回车使用默认：`~/Documents/knowledge`）"，写入 `~/.hskill/config.json` 的 `knowledgeRoot` 字段（若已有 `skillDir` 等字段，只增改 `knowledgeRoot`）。
```

- [ ] **Step 2**：「用法」小节里的历史归档路径提示（对应第 42 行），`DATA_DIR/youtube/creators/<handle>.json` 改为 `<knowledgeRoot>/feeds/youtube/creators/<handle>.json`。

- [ ] **Step 3**：run 步骤里 `DATA_DIR/youtube/digest/` 改为 `<knowledgeRoot>/feeds/youtube/digest/`，`youtube/creators/<handle>.json` 改为 `<knowledgeRoot>/feeds/youtube/creators/<handle>.json`。

- [ ] **Step 4**：「边界」小节，同 Task 6 Step 4 的措辞，`tweets/`↔`youtube/` 对调，加上迁移脚本提示句。

- [ ] **Step 5**：「参考文件」表格，`platforms/` 行后插入 `scripts/store_config.py` 行（文案同 Task 6 Step 5），`config.py`/`digest.py`/`archive_videos.py` 三行路径描述改成 `<knowledgeRoot>/feeds/youtube/...`。

- [ ] **Step 6**：frontmatter `version: "0.6.1"` 改为 `version: "0.7.0"`。

- [ ] **Step 7: Commit**

```bash
git add skills/feed/sync-ytchannel/SKILL.md
git commit -m "docs(sync-ytchannel): SKILL.md follows knowledgeRoot / feeds layout"
```

---

## Task 9: learn-video — 归档脚本 + 测试 + 工作流更新

**Files:**
- Create: `skills/research/learn-video/tests/conftest.py`
- Create: `skills/research/learn-video/tests/test_store_config.py`（复制 Task 1 的测试文件）
- Create: `skills/research/learn-video/scripts/archive.py`
- Create: `skills/research/learn-video/tests/test_archive.py`
- Modify: `skills/research/learn-video/SKILL.md`

**Interfaces:**
- Consumes: Task 2 已放好的 `skills/research/learn-video/scripts/store_config.py` 里的 `videos_dir() -> Path`
- Produces: `archive.archive(task_id, source_url, title, transcript_path, article_path, summary_path, fetched_at=None) -> dict`（键：`video_dir`/`meta_path`/`transcript_path`/`article_path`/`summary_path`，均为 `Path`）；CLI `main()` 读环境变量 `TASK_ID`/`SOURCE_URL`/`TITLE`/`TRANSCRIPT_PATH`/`ARTICLE_PATH`/`SUMMARY_PATH`/`FETCHED_AT`(可选)，打印 `VIDEO_DIR: <path>` 和 `META_PATH: <path>`

- [ ] **Step 1: 新建 `tests/conftest.py`**

```python
"""Shared test isolation for learn-video: points store_config at a fake
config.json under tmp_path for every test in this directory (autouse),
so a test file that forgets to declare its own isolation still can't
read or write the real ~/.hskill/config.json."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def isolated_store_config(tmp_path, monkeypatch) -> Path:
    config_path = tmp_path / "config.json"
    root = tmp_path / "knowledge"
    config_path.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_CONFIG", str(config_path))
    return root
```

- [ ] **Step 2: 复制 Task 1 的 `test_store_config.py`**

```bash
cp skills/research/clip-url/tests/test_store_config.py skills/research/learn-video/tests/test_store_config.py
```

（这份测试自带独立的 `isolated_config` fixture，跟 Step 1 新增的 conftest `isolated_store_config` fixture 并存不冲突——各自用不同的 `tmp_path`/`monkeypatch` 组合，pytest 允许同名参数不同 fixture 共存于不同测试文件。）

- [ ] **Step 3: 写 `scripts/archive.py`**

```python
#!/usr/bin/env python3
"""Archives learn-video's vdl output into the unified storage root: copies
the three vdl-produced files into <ROOT>/videos/<task_id>/ and writes
meta.json. Copies, never moves — vdl's own work/<task_id>/ must stay in
place for `vdl rerun` to keep working. Same task_id rerun overwrites in
place (shutil.copyfile always overwrites the destination), so this is
idempotent.

Parameters via environment variables:
  TASK_ID          - vdl's task_id (this skill's entity primary key)
  SOURCE_URL        - the video URL the user gave
  TITLE             - video title
  TRANSCRIPT_PATH   - vdl's transcript/original.md path
  ARTICLE_PATH      - vdl's writing/article.md path
  SUMMARY_PATH      - vdl's writing/summary.md path
  FETCHED_AT        - (optional) override date, defaults to today (UTC+8)
"""
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

import store_config


def archive(task_id: str, source_url: str, title: str,
            transcript_path: str, article_path: str, summary_path: str,
            fetched_at: str | None = None) -> dict:
    video_dir = store_config.videos_dir() / task_id
    (video_dir / "transcript").mkdir(parents=True, exist_ok=True)
    (video_dir / "writing").mkdir(parents=True, exist_ok=True)

    dest_transcript = video_dir / "transcript" / "original.md"
    dest_article = video_dir / "writing" / "article.md"
    dest_summary = video_dir / "writing" / "summary.md"
    shutil.copyfile(transcript_path, dest_transcript)
    shutil.copyfile(article_path, dest_article)
    shutil.copyfile(summary_path, dest_summary)

    meta_path = video_dir / "meta.json"
    meta = {
        "source_url": source_url,
        "title": title,
        "fetched_at": fetched_at or datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "video_dir": video_dir,
        "meta_path": meta_path,
        "transcript_path": dest_transcript,
        "article_path": dest_article,
        "summary_path": dest_summary,
    }


def main():
    result = archive(
        task_id=os.environ["TASK_ID"],
        source_url=os.environ["SOURCE_URL"],
        title=os.environ["TITLE"],
        transcript_path=os.environ["TRANSCRIPT_PATH"],
        article_path=os.environ["ARTICLE_PATH"],
        summary_path=os.environ["SUMMARY_PATH"],
        fetched_at=os.environ.get("FETCHED_AT"),
    )
    print(f"VIDEO_DIR: {result['video_dir']}")
    print(f"META_PATH: {result['meta_path']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 写 `tests/test_archive.py`**

```python
"""Unit tests for archive.py — learn-video's first piece of local logic:
copying vdl's output into <ROOT>/videos/<task_id>/ and writing meta.json."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from archive import archive  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "archive.py"


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_archive_copies_three_files_and_writes_meta(tmp_path, isolated_store_config):
    transcript = _write(tmp_path / "work" / "t1" / "transcript" / "original.md", "raw transcript")
    article = _write(tmp_path / "work" / "t1" / "writing" / "article.md", "article body")
    summary = _write(tmp_path / "work" / "t1" / "writing" / "summary.md", "summary body")

    result = archive("t1", "https://youtube.com/watch?v=t1", "My Video",
                      str(transcript), str(article), str(summary),
                      fetched_at="2026-09-01")

    assert result["video_dir"] == isolated_store_config / "videos" / "t1"
    assert result["transcript_path"].read_text(encoding="utf-8") == "raw transcript"
    assert result["article_path"].read_text(encoding="utf-8") == "article body"
    assert result["summary_path"].read_text(encoding="utf-8") == "summary body"

    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert meta == {
        "source_url": "https://youtube.com/watch?v=t1",
        "title": "My Video",
        "fetched_at": "2026-09-01",
    }


def test_archive_layout_matches_spec_directory_structure(tmp_path, isolated_store_config):
    transcript = _write(tmp_path / "work" / "t1" / "transcript" / "original.md", "x")
    article = _write(tmp_path / "work" / "t1" / "writing" / "article.md", "x")
    summary = _write(tmp_path / "work" / "t1" / "writing" / "summary.md", "x")

    result = archive("t1", "u", "T", str(transcript), str(article), str(summary))

    assert result["transcript_path"] == isolated_store_config / "videos" / "t1" / "transcript" / "original.md"
    assert result["article_path"] == isolated_store_config / "videos" / "t1" / "writing" / "article.md"
    assert result["summary_path"] == isolated_store_config / "videos" / "t1" / "writing" / "summary.md"


def test_archive_is_idempotent_for_same_task_id(tmp_path, isolated_store_config):
    transcript = _write(tmp_path / "work" / "t1" / "transcript" / "original.md", "v1")
    article = _write(tmp_path / "work" / "t1" / "writing" / "article.md", "v1")
    summary = _write(tmp_path / "work" / "t1" / "writing" / "summary.md", "v1")
    archive("t1", "u", "T", str(transcript), str(article), str(summary), fetched_at="2026-09-01")

    transcript.write_text("v2", encoding="utf-8")
    result = archive("t1", "u", "T2", str(transcript), str(article), str(summary), fetched_at="2026-09-02")

    assert result["transcript_path"].read_text(encoding="utf-8") == "v2"
    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert meta["title"] == "T2"
    assert meta["fetched_at"] == "2026-09-02"


def test_cli_prints_video_dir_and_meta_path(tmp_path, isolated_store_config, monkeypatch):
    transcript = _write(tmp_path / "transcript.md", "x")
    article = _write(tmp_path / "article.md", "x")
    summary = _write(tmp_path / "summary.md", "x")
    env = {
        **os.environ,
        "TASK_ID": "t1", "SOURCE_URL": "u", "TITLE": "T",
        "TRANSCRIPT_PATH": str(transcript), "ARTICLE_PATH": str(article), "SUMMARY_PATH": str(summary),
        "FETCHED_AT": "2026-09-01",
        "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"],
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    expected_dir = isolated_store_config / "videos" / "t1"
    assert f"VIDEO_DIR: {expected_dir}" in result.stdout
    assert f"META_PATH: {expected_dir / 'meta.json'}" in result.stdout
```

- [ ] **Step 5: 运行 learn-video 测试**

```bash
cd skills/research/learn-video && python3 -m pytest tests/ -q
```

Expected: 全绿（`test_store_config.py` 9 项 + `test_archive.py` 4 项）。

- [ ] **Step 6: 更新 `SKILL.md`——新增初始化检查 + 归档步骤 + 参考文件**

在「前置：确认 vdl 可用」小节之后插入新小节：

```
---

## 前置：检查统一存储根

运行 `python3 scripts/store_config.py check`。若输出 `MISSING:`，询问用户"抓取产物统一存到哪个目录？（直接回车使用默认：`~/Documents/knowledge`）"，将回答展开为绝对路径，写入 `~/.hskill/config.json` 的 `knowledgeRoot` 字段（文件不存在则新建；若已存在 `skillDir` 等其他字段，只增改 `knowledgeRoot`，不覆盖）。
```

在「向用户报告」小节之前、「获取结果」小节之后插入新小节：

```
---

## 归档到统一存储根

拿到「进度汇报与完成判定」返回的 `transcript`/`article`/`summary` 三个路径后，在向用户报告之前先归档：

```bash
cd "$HOME/Projects/harveyz-skill/skills/research/learn-video"  # 或本 skill 安装后的实际目录
TASK_ID="<task_id>" SOURCE_URL="<URL>" TITLE="<视频标题>" \
TRANSCRIPT_PATH="<transcript 路径>" ARTICLE_PATH="<article 路径>" SUMMARY_PATH="<summary 路径>" \
python3 scripts/archive.py
```

输出两行 `VIDEO_DIR: <path>` 和 `META_PATH: <path>`。同一个 `task_id` 重复归档时覆盖，幂等——`rerun`/更换 focus 之后重新归档不会产生重复目录。

**复制而非移动**：`vdl` 侧的 `work/<task_id>/` 保持不变，`vdl rerun` 需要它还在。归档只是把三个文件的副本放进 `<knowledgeRoot>/videos/<task_id>/`。

归档完成后，「向用户报告」小节里的"产物路径"改为报告 `VIDEO_DIR` 打印出的路径，不再是 `work/<task_id>/...`。
```

- [ ] **Step 7: 新增「参考文件」小节（learn-video 之前没有这个小节）**

在文件末尾（「向用户报告」小节之后）追加：

```

---

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/store_config.py` | 读共享 `knowledgeRoot`（`~/.hskill/config.json`），四个入范围 skill 各存一份内容相同的副本 |
| `scripts/archive.py` | 把 vdl 产物复制进 `<knowledgeRoot>/videos/<task_id>/` 并写 `meta.json`，同 `task_id` 重跑幂等 |
```

- [ ] **Step 8: 更新 frontmatter 版本号**

把 `version: "1.6.1"` 改为 `version: "1.7.0"`。

- [ ] **Step 9: Commit**

```bash
git add skills/research/learn-video/scripts/store_config.py skills/research/learn-video/scripts/archive.py \
        skills/research/learn-video/tests/ skills/research/learn-video/SKILL.md
git commit -m "feat(learn-video): archive vdl output into the unified storage root"
```

---

## Task 10: `scripts/migrate-store.sh` + bats 测试

**Files:**
- Create: `scripts/migrate-store.sh`
- Create: `tests/migrate-store.bats`

**Interfaces:**
- Consumes: `~/.hskill/config.json`（`knowledgeRoot`）、`~/.hskill/url-extract/config.json`（`VAULT_PATH`，只读，不写）、`~/.hskill/roster/config.json`（`DATA_DIR`，只读，不写）——三者路径均可用 `HSKILL_CONFIG`/`HSKILL_EXTRACT_URL_CONFIG`/`HSKILL_ROSTER_CONFIG` 环境变量覆盖（跟对应 Python 模块用同一套环境变量名，供测试和用户手动指定）
- Produces: 无代码接口，纯 CLI（stdout 打印计划或执行结果，exit 0 表示脚本本身跑完，不代表"有东西可搬"）

- [ ] **Step 1: 写 `scripts/migrate-store.sh`**

```bash
#!/usr/bin/env bash
# migrate-store.sh — one-time migration into the unified storage root.
#
# Moves three things into <ROOT> (~/.hskill/config.json's knowledgeRoot):
#   <VAULT_PATH>/<hash8>/     -> <ROOT>/articles/<hash8>/   (clip-url)
#   <DATA_DIR>/tweets/        -> <ROOT>/feeds/tweets/        (sync-xtimeline)
#   <DATA_DIR>/youtube/       -> <ROOT>/feeds/youtube/       (sync-ytchannel)
#
# Default: dry-run, prints the plan, no filesystem side effects.
# --apply: actually moves files. Idempotent — safe to rerun.
#
# clip-url's VAULT_PATH is the user's Obsidian vault root and is NEVER
# mv'd wholesale — only subdirectories whose name matches ^[0-9a-f]{8}$
# AND contain a meta.json are moved; everything else (including
# hand-written notes) is left untouched and printed under "跳过".
#
# Usage: bash scripts/migrate-store.sh [--apply]

set -euo pipefail

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[2m· %s\033[0m\n"  "$*"; }
warn() { printf "\033[33m⚠\033[0m %s\n" "$*"; }

_json_get() {
  # _json_get <config-path> <key> — prints the value, exits 1 if the file
  # or key is missing (caller wraps with `|| true` under set -e).
  local path="$1" key="$2"
  [[ -f "$path" ]] || return 1
  python3 -c "
import json, sys
try:
    cfg = json.load(open(sys.argv[1], encoding='utf-8'))
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(1)
value = cfg.get(sys.argv[2])
if value is None:
    sys.exit(1)
print(value)
" "$path" "$key"
}

STORE_CONFIG="${HSKILL_CONFIG:-$HOME/.hskill/config.json}"
VAULT_CONFIG="${HSKILL_EXTRACT_URL_CONFIG:-$HOME/.hskill/url-extract/config.json}"
ROSTER_CONFIG="${HSKILL_ROSTER_CONFIG:-$HOME/.hskill/roster/config.json}"

ROOT="$(_json_get "$STORE_CONFIG" knowledgeRoot || true)"
if [[ -z "$ROOT" ]]; then
  warn "统一存储根未配置（$STORE_CONFIG 缺少 knowledgeRoot），无法迁移。请先跑任一入范围 skill 完成初始化。"
  exit 1
fi

echo ""
echo "统一存储契约迁移"
echo "─────────────────"
if [[ "$APPLY" -eq 1 ]]; then
  info "模式：--apply（将实际搬移文件）"
else
  info "模式：dry-run（只打印计划，不产生任何副作用；加 --apply 执行）"
fi
info "目标根：$ROOT"
echo ""

_move_dir() {
  # _move_dir <src> <dst> <label>
  local src="$1" dst="$2" label="$3"
  if [[ ! -d "$src" ]]; then
    info "$label：源目录不存在，跳过（$src）"
    return
  fi
  if [[ -d "$dst" ]]; then
    warn "$label：目标已存在，跳过（$dst）——如需重搬，先手动处理目标目录"
    return
  fi
  if [[ "$APPLY" -eq 1 ]]; then
    mkdir -p "$(dirname "$dst")"
    mv "$src" "$dst"
    ok "$label：$src → $dst"
  else
    info "$label：将搬 $src → $dst"
  fi
}

# ── clip-url: 只搬 <hash8>/ 且含 meta.json 的子目录 ─────────────────────
VAULT_PATH="$(_json_get "$VAULT_CONFIG" VAULT_PATH || true)"
echo "clip-url（VAULT_PATH → $ROOT/articles/）"
if [[ -z "$VAULT_PATH" ]]; then
  info "未配置 VAULT_PATH（$VAULT_CONFIG），跳过这一项"
elif [[ ! -d "$VAULT_PATH" ]]; then
  info "VAULT_PATH 不存在（$VAULT_PATH），跳过这一项"
else
  moved_any=0
  for entry in "$VAULT_PATH"/*/; do
    [[ -d "$entry" ]] || continue
    name="$(basename "$entry")"
    dst="$ROOT/articles/$name"
    if [[ "$name" =~ ^[0-9a-f]{8}$ && -f "${entry}meta.json" ]]; then
      moved_any=1
      if [[ -d "$dst" ]]; then
        warn "  跳过：$name（目标已存在：$dst）"
        continue
      fi
      if [[ "$APPLY" -eq 1 ]]; then
        mkdir -p "$ROOT/articles"
        mv "$entry" "$dst"
        ok "  $name → $dst"
      else
        info "  将搬：$name"
      fi
    else
      info "  跳过：$name（非 8 位十六进制目录名，或无 meta.json）"
    fi
  done
  [[ "$moved_any" -eq 0 ]] && info "  没有可搬的文章目录"
fi
echo ""

# ── sync-xtimeline / sync-ytchannel: 整段 tweets/ youtube/ 搬走 ────────
DATA_DIR="$(_json_get "$ROSTER_CONFIG" DATA_DIR || true)"
echo "sync-xtimeline（DATA_DIR/tweets → $ROOT/feeds/tweets）"
if [[ -z "$DATA_DIR" ]]; then
  info "未配置 roster DATA_DIR（$ROSTER_CONFIG），跳过这一项"
else
  _move_dir "$DATA_DIR/tweets" "$ROOT/feeds/tweets" "sync-xtimeline"
fi
echo ""

echo "sync-ytchannel（DATA_DIR/youtube → $ROOT/feeds/youtube）"
if [[ -z "$DATA_DIR" ]]; then
  info "未配置 roster DATA_DIR（$ROSTER_CONFIG），跳过这一项"
else
  _move_dir "$DATA_DIR/youtube" "$ROOT/feeds/youtube" "sync-ytchannel"
fi
echo ""

if [[ "$APPLY" -ne 1 ]]; then
  info "以上只是计划，未产生任何文件系统改动。加 --apply 执行。"
fi
```

- [ ] **Step 2: 赋可执行权限**

```bash
chmod +x scripts/migrate-store.sh
```

- [ ] **Step 3: 写 `tests/migrate-store.bats`**

```bash
#!/usr/bin/env bats
# Tests for scripts/migrate-store.sh — the one-time migration into the
# unified storage root. Every test runs against a temp fixture, never the
# real ~/.hskill/ configs or a real Obsidian vault.

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/migrate-store.sh"

setup() {
  TEST_DIR="$(mktemp -d)"
  export HSKILL_CONFIG="${TEST_DIR}/hskill-config.json"
  export HSKILL_EXTRACT_URL_CONFIG="${TEST_DIR}/vault-config.json"
  export HSKILL_ROSTER_CONFIG="${TEST_DIR}/roster-config.json"
  ROOT="${TEST_DIR}/knowledge"
  VAULT="${TEST_DIR}/vault"
  DATA_DIR="${TEST_DIR}/roster-data"
  cat > "$HSKILL_CONFIG" <<CFG
{"knowledgeRoot": "${ROOT}"}
CFG
}

teardown() {
  rm -rf "${TEST_DIR}"
}

_write_vault_config() {
  cat > "$HSKILL_EXTRACT_URL_CONFIG" <<CFG
{"VAULT_PATH": "${VAULT}"}
CFG
}

_write_roster_config() {
  cat > "$HSKILL_ROSTER_CONFIG" <<CFG
{"DATA_DIR": "${DATA_DIR}"}
CFG
}

@test "dry-run: hash8 dir with meta.json listed under 将搬, non-hash dir under 跳过" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${VAULT}/我的笔记"
  echo "hi" > "${VAULT}/我的笔记/note.md"

  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"将搬：deadbeef"* ]]
  [[ "$output" == *"跳过：我的笔记"* ]]
}

@test "dry-run: produces no filesystem side effects" {
  _write_vault_config
  _write_roster_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${DATA_DIR}/tweets" "${DATA_DIR}/youtube"

  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -e "${ROOT}" ]
  [ -d "${VAULT}/deadbeef" ]
  [ -d "${DATA_DIR}/tweets" ]
  [ -d "${DATA_DIR}/youtube" ]
}

@test "--apply: moves matching hash8 dirs into ROOT/articles, leaves non-matching alone" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"
  mkdir -p "${VAULT}/我的笔记"
  echo "hi" > "${VAULT}/我的笔记/note.md"

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [ -d "${ROOT}/articles/deadbeef" ]
  [ -f "${ROOT}/articles/deadbeef/meta.json" ]
  [ -d "${VAULT}/我的笔记" ]
  [ ! -e "${VAULT}/deadbeef" ]
}

@test "--apply: moves DATA_DIR/tweets and DATA_DIR/youtube into ROOT/feeds" {
  _write_roster_config
  mkdir -p "${DATA_DIR}/tweets/creators" "${DATA_DIR}/youtube/creators"
  echo '[]' > "${DATA_DIR}/tweets/creators/alice.json"

  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [ -f "${ROOT}/feeds/tweets/creators/alice.json" ]
  [ -d "${ROOT}/feeds/youtube" ]
  [ ! -e "${DATA_DIR}/tweets" ]
  [ ! -e "${DATA_DIR}/youtube" ]
}

@test "--apply: rerunning is idempotent" {
  _write_vault_config
  mkdir -p "${VAULT}/deadbeef"
  echo '{}' > "${VAULT}/deadbeef/meta.json"

  bash "$SCRIPT" --apply
  run bash "$SCRIPT" --apply
  [ "$status" -eq 0 ]
  [ -d "${ROOT}/articles/deadbeef" ]
}
```

- [ ] **Step 4: 运行 bats 测试**

```bash
bats tests/migrate-store.bats
```

Expected: 5 项全 PASS。

- [ ] **Step 5: 手动实跑验证（交接文档标注的最高风险项，不只靠单测）**

```bash
TMP="$(mktemp -d)"
export HSKILL_CONFIG="$TMP/hskill-config.json"
export HSKILL_EXTRACT_URL_CONFIG="$TMP/vault-config.json"
export HSKILL_ROSTER_CONFIG="$TMP/roster-config.json"
echo "{\"knowledgeRoot\": \"$TMP/knowledge\"}" > "$HSKILL_CONFIG"
echo "{\"VAULT_PATH\": \"$TMP/vault\"}" > "$HSKILL_EXTRACT_URL_CONFIG"
mkdir -p "$TMP/vault/deadbeef" "$TMP/vault/我的笔记"
echo '{}' > "$TMP/vault/deadbeef/meta.json"
echo 'hi' > "$TMP/vault/我的笔记/note.md"
bash scripts/migrate-store.sh          # dry-run，确认输出里 deadbeef 在"将搬"、我的笔记 在"跳过"
bash scripts/migrate-store.sh --apply  # 实际搬
ls "$TMP/knowledge/articles/deadbeef/meta.json"   # 应存在
ls "$TMP/vault/我的笔记/note.md"                   # 应仍在原地，未被碰
rm -rf "$TMP"
```

- [ ] **Step 6: Commit**

```bash
git add scripts/migrate-store.sh tests/migrate-store.bats
git commit -m "feat: add migrate-store.sh for one-time migration into the unified storage root"
```

---

## Task 11: `skills-index.json` — 四个 skill 的 `contentHash`/`contentVersion` 更新

**Files:**
- Modify: `skills-index.json`

**Interfaces:**
- Consumes: `publish-skill` skill 定义的 F8 hash 算法（`skills/mint/publish-skill/SKILL.md`）：`sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' SKILL.md | sha256sum | cut -c1-16`

- [ ] **Step 1: 为四个已改动的 `SKILL.md` 各算一次新 hash**

```bash
compute_content_hash() {
  sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' "$1" | shasum -a 256 | cut -c1-16
}
compute_content_hash skills/research/clip-url/SKILL.md
compute_content_hash skills/research/learn-video/SKILL.md
compute_content_hash skills/feed/sync-xtimeline/SKILL.md
compute_content_hash skills/feed/sync-ytchannel/SKILL.md
```

（`shasum -a 256` 是 macOS 自带命令，等价于 Linux 的 `sha256sum`；两者都行，用当前环境有的那个。）

- [ ] **Step 2: 用 Edit 工具把四条结果写回 `skills-index.json`**

四个条目当前状态（Task 4/6/8/9 已把 version 分别 bump 到 `0.9.0`/`0.8.0`/`0.7.0`/`1.7.0`）：

```json
{"path": "research/learn-video", "bundle": "research", "installScope": "global", "contentHash": "bbd4d47bb386e182", "contentVersion": "1.6.1"}
{"path": "research/clip-url", "bundle": "research", "installScope": "project", "contentHash": "588dc9194f846fa8", "contentVersion": "0.8.1"}
{"path": "feed/sync-xtimeline", "bundle": "feed", "installScope": "project", "contentHash": "23fc4c422fbb66ba", "contentVersion": "0.7.1"}
{"path": "feed/sync-ytchannel", "bundle": "feed", "installScope": "project", "contentHash": "1fc93a9bf01e4167", "contentVersion": "0.6.1"}
```

把每条的 `contentHash` 替换成 Step 1 算出的值，`contentVersion` 替换成新 version（`0.9.0`/`0.8.0`/`0.7.0`/`1.7.0`）。用 `Edit` 工具按 `path` 字段定位每条 JSON 对象做字符串替换（`old_string` 用整行 JSON，`new_string` 换新的 hash/version）。

- [ ] **Step 3: 验证 JSON 仍合法**

```bash
python3 -c "import json; json.load(open('skills-index.json'))" && echo "VALID JSON"
```

Expected: `VALID JSON`。

- [ ] **Step 4: Commit**

```bash
git add skills-index.json
git commit -m "chore: bump contentHash/contentVersion for the four unified-store skills"
```

---

## Task 12: 全量验证（对照交接文档的七条最小验收锚点）

**Files:** 无新增/修改，纯验证。

**Interfaces:** 无。

- [ ] **Step 1: `npm test` 全绿（锚点 1）**

```bash
npm test
```

Expected: exit 0，`bats tests/`（含新增的 `migrate-store.bats`）、`scripts/run-skill-tests.sh`（含四个 skill 的新/改测试）、`node --test` 三段全部通过。

- [ ] **Step 2: 四份 `store_config.py` 的 `check` 行为（锚点 2）**

```bash
for f in skills/research/clip-url skills/research/learn-video skills/feed/sync-xtimeline skills/feed/sync-ytchannel; do
  echo "== $f =="
  test -f "$f/scripts/store_config.py" && echo "file exists" || echo "MISSING FILE"
  HSKILL_CONFIG=/tmp/does-not-exist-$$.json python3 "$f/scripts/store_config.py" check
  echo "exit=$?"
done
```

Expected: 四处都 `file exists`，且 `check` 在缺失配置时输出以 `MISSING:` 开头的信息、`exit=1`。再各自配一份真实临时 `HSKILL_CONFIG` 验证 `OK: <绝对路径>` + `exit=0` 的分支。

- [ ] **Step 3: VAULT_PATH 不再被代码读取（锚点 3）**

```bash
grep -rn "VAULT_PATH" skills/research/clip-url/
```

Expected: 命中项全部落在注释 / `.md` 文档 / 迁移路径说明里（`vault_config.py` 的 docstring、`SKILL.md` 的历史/迁移提示），不再有任何一行是"读取 `VAULT_PATH` 字段并据此拼产物路径"的可执行代码。

- [ ] **Step 4: 四个调用点全部改完（锚点 4）**

```bash
grep -n 'get_data_dir() / "tweets"\|get_data_dir() / "youtube"' skills/feed/ -r
```

Expected: 无结果（含测试文件——Task 7 Step 8 已经把 `test_fetch_new_videos.py` 里唯一的残留调用点也改掉了）。

- [ ] **Step 5: `roster_client.py` 只删了 `data_dir()`（锚点 5）**

```bash
grep -n "def data_dir" skills/feed/sync-xtimeline/scripts/roster_client.py skills/feed/sync-ytchannel/scripts/roster_client.py
grep -n "def channels\|def get_cursor\|def set_cursor\|def set_error" skills/feed/sync-xtimeline/scripts/roster_client.py
grep -n "def channels\|def get_cursor\|def set_cursor\|def set_error" skills/feed/sync-ytchannel/scripts/roster_client.py
```

Expected: 第一条无结果；后两条各命中 4 处。

- [ ] **Step 6: `migrate-store.sh` dry-run 无副作用 + fixture 分类正确（锚点 6，已在 Task 10 Step 4/5 验证过，这里重跑一次确认没有回归）**

```bash
bats tests/migrate-store.bats
```

Expected: 全 PASS。

- [ ] **Step 7: `skills-index.json` 四条记录已更新（锚点 7）**

```bash
python3 -c "
import json
d = json.load(open('skills-index.json'))
expected_versions = {
    'research/clip-url': '0.9.0',
    'research/learn-video': '1.7.0',
    'feed/sync-xtimeline': '0.8.0',
    'feed/sync-ytchannel': '0.7.0',
}
for s in d['skills']:
    if s['path'] in expected_versions:
        assert s['contentVersion'] == expected_versions[s['path']], s
        print(s['path'], 'OK', s['contentHash'], s['contentVersion'])
"
```

Expected: 四行 `OK`，无 AssertionError。

- [ ] **Step 8: 把验收结果记录进交接文档**

在 `docs/commute/2026-09-01-unified-store-handoff.md` 的「最小验收锚点」小节末尾追加一个「接手方自测」小节，逐条记录 Step 1-7 的 pass/fail（不要覆盖或删除已有的 author 冷读核对小节），并把文档顶部的状态从「执行中」改为「待验收」。

```bash
git add docs/commute/2026-09-01-unified-store-handoff.md
git commit -m "docs(commute): record self-test results, mark handoff as pending acceptance"
```

- [ ] **Step 9: 通知用户**

七条锚点自测通过后，告知用户可以进入 `handoff` 技能的 `accept` 阶段验收（不要自己把状态改成「已验收」——按 handoff 规则，那一步只能由原 session 判定后写）。
