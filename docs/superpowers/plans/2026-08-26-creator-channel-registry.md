# 人与渠道名册（roster）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `sync-xtimeline` / `sync-ytchannel` 各自的 `watchlist.json` 抽成统一的 creator + channel 名册，由一个独立 CLI tool 持有，两个 sync skill 退化为纯执行器。

**Architecture:** 新增 `tools/roster`（普通 CLI tool，形态对齐 `tools/hub`，stdlib-only 无第三方依赖）持有三份数据的全部 I/O：`registry.json`（人与渠道定义）、`state.json`（游标与失败态）、`profiles/*.md`（画像）。CLI 按三个命令组划分，一组对应一份文件、对应一个消费者。新增 `manage-roster` skill 作人机入口；两个 sync skill 移除 `add`/`remove`/`list`，只保留 `run`（`sync-xtimeline` 另保留 `view`）。

**Tech Stack:** Python 3.11+ 标准库（`json` / `pathlib` / `argparse` / `re`）、pytest、hatchling、bats。

**Spec:** `docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md`

## Global Constraints

- **Python 版本下限 3.11**（对齐 `tools/hub/pyproject.toml` 的 `requires-python = ">=3.11"`）。
- **`roster` 包不得引入任何第三方运行时依赖。** 它只读写 JSON 和 Markdown，`pyproject.toml` 的 `dependencies` 必须是空列表。`hub` 依赖 typer/textual，这里刻意不跟。
- **`schema_version` 常量值为 `1`**，写进 `registry.json` 和 `state.json` 的顶层。
- **渠道主键是 `(platform, handle)`**，序列化成字符串键时格式固定为 `f"{platform}:{handle}"`。
- **`platform` 的取值只有两个**：`"x"`、`"youtube"`。
- **creator 的 `id` 创建后不可变**；`merge` 保留 `<id-a>` 的 `id`，`<id-b>` 的 `id` 落入 `aliases`。
- **画像的「观察」段只追加，不改写**；「当前判断」段允许重写。
- **删除操作永不删除画像文件**，只移入 `profiles/archived/`。
- **配置路径固定**：`~/.hskill/roster/config.json`，只含一个键 `DATA_DIR`。环境变量 `HSKILL_ROSTER_CONFIG` 覆盖之，且必须在**每次调用时**读取（不能在 import 时固化），否则测试无法在进程内重定向——`sync-ytchannel/scripts/config.py` 是正确示范，`sync-xtimeline/scripts/config.py` 用了 import 时固化的 `CONFIG_PATH`，是反面示范。
- **提交信息结尾追加**：`Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **分支**：全部工作在 `feature/creator-channel-registry` 上进行，不直接提交 `main` / `staging`。

## 写入权如何落地（对 spec 第 2.2 节的补充）

spec 用"文件边界"表达写入权。改由一个共享 tool 持有全部 I/O 之后，边界从"谁打开文件句柄"变成"**谁被允许调哪个命令组**"：

| 命令组 | 操作的文件 | 唯一允许的调用方 |
|---|---|---|
| `roster registry ...` | `registry.json` | `manage-roster` skill |
| `roster state ...` | `state.json` | `sync-xtimeline` / `sync-ytchannel` |
| `roster profile ...` | `profiles/*.md` | 认知层 skill（本计划不实现） |

这比字段级约定强（命令组在 SKILL.md 里是可 grep 的字面量），但比真正的文件句柄隔离弱。这是选"独立 tool"路线换来的代价，明确记在这里。

`roster registry list` 需要读 `state.json` 展示游标——**读跨组允许，写不允许**。

---

## File Structure

**新建：**

| 文件 | 职责 |
|---|---|
| `tools/roster/roster.sh` | launcher，dev 模式跑源码树 venv，装机模式跑 `~/.hskill/tools/roster/venv` |
| `tools/roster/pyproject.toml` | 包元数据，`dependencies = []` |
| `tools/roster/tool.json` | 安装元数据（`extraPaths` / `uninstallPaths` / `configPaths`） |
| `tools/roster/roster/config.py` | `DATA_DIR` 读写 |
| `tools/roster/roster/urls.py` | URL → `(platform, handle)`；`slugify` |
| `tools/roster/roster/registry.py` | `registry.json` 读写 + creator/channel CRUD + merge |
| `tools/roster/roster/state.py` | `state.json` 读写（游标、失败态） |
| `tools/roster/roster/profiles.py` | `profiles/*.md` 追加/归档/合并 |
| `tools/roster/roster/migrate.py` | 旧 `watchlist.json` 一次性迁移 |
| `tools/roster/roster/__main__.py` | argparse CLI，三个命令组 |
| `tools/roster/tests/*` | 上述模块的 pytest |
| `skills/research/manage-roster/SKILL.md` | 名册人机入口 |
| `skills/research/manage-roster/scripts/roster_locate.py` | 定位 `roster` launcher（对齐 `browser_fetch_mcp_locate.py`） |

**修改：**

| 文件 | 改什么 |
|---|---|
| `scripts/run-skill-tests.sh` | 用 pytest 跑 `skills/*/*/tests/`，并纳入 `tools/*/tests/` |
| `skills/research/sync-ytchannel/scripts/config.py` | `get_data_dir()` 改为向 `roster` 要 |
| `skills/research/sync-ytchannel/scripts/watchlist.py` | 拆：CRUD 删除，保留 `compute_update`，新增读 registry / 写 state |
| `skills/research/sync-ytchannel/scripts/sync_channels.py` | 改用新的读写入口；digest 落 `digests/youtube/` |
| `skills/research/sync-ytchannel/SKILL.md` | 移除 `add`/`remove`/`list` 三节，指向 `manage-roster` |
| `skills/research/sync-xtimeline/*` | 同上，平台为 `x`，digest 落 `digests/x/` |
| `skills-index.json` | 注册 `roster` tool 与 `manage-roster` skill |

---

## Task 0: 让 skill 与 tool 的 pytest 真正被执行

当前 `scripts/run-skill-tests.sh` 对 `skills/*/*/tests/*.py` 执行 `python3 <file>`。这些是 pytest 文件，直接执行只会 import 模块然后退出 0，**一个测试都不跑**。后续所有任务的验证步骤都依赖这个被修好。

**Files:**
- Modify: `scripts/run-skill-tests.sh:55-72`

**Interfaces:**
- Consumes: 无
- Produces: `npm test` 能真正执行 `skills/*/*/tests/` 与 `tools/*/tests/` 下的 pytest

- [ ] **Step 1: 先证明问题存在**

```bash
python3 skills/research/sync-ytchannel/tests/test_watchlist.py; echo "exit=$?"
```

Expected: 无任何输出，`exit=0`（16 个测试一个都没跑）。

```bash
cd skills/research/sync-ytchannel && python3 -m pytest tests/ -q; cd -
```

Expected: `16 passed`。两者对比即为 bug 的证据。

- [ ] **Step 2: 改 runner，改用 pytest 按目录跑**

把 `run-skill-tests.sh` 里 `_run_python` 与其 `while` 循环整段替换为：

```bash
_run_pytest_dir() {
  local dir="$1"
  found=$((found + 1))
  echo "── pytest: ${dir#"${REPO_ROOT}/"}"
  if (cd "$(dirname "${dir}")" && python3 -m pytest tests/ -q); then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
  fi
}

# skills/<category>/<skill>/tests/ 与 tools/<tool>/tests/，任一含 test_*.py 即视为 pytest 套件
while IFS= read -r -d '' tests_dir; do
  if compgen -G "${tests_dir}/test_*.py" > /dev/null; then
    _run_pytest_dir "${tests_dir}"
  fi
done < <(find "${REPO_ROOT}/skills" "${REPO_ROOT}/tools" \
           -type d -name tests \
           -not -path "*/.venv/*" -not -path "*/node_modules/*" \
           -print0 2>/dev/null | sort -z)
```

同时把文件顶部注释里的 `skills/*/*/tests/*.py → 用 python3 运行` 改为 `skills/*/*/tests/ 与 tools/*/tests/ → 用 pytest 按目录运行`。

`compgen` 需要 bash，脚本首行已经是 `#!/usr/bin/env bash`，无需改。

- [ ] **Step 3: 跑 runner，确认测试真的执行了**

```bash
bash scripts/run-skill-tests.sh 2>&1 | tail -20
```

Expected: 输出里出现 `── pytest: skills/research/sync-ytchannel` 和 `16 passed` 之类的真实计数，而不是静默通过。

- [ ] **Step 4: 跑全量测试确认没打破别的**

```bash
npm test
```

Expected: 全绿。若 `sync-xtimeline` 的 pytest 此时暴露出真实失败，**先停下报告，不要在本任务里顺手修**——那是被这个 bug 掩盖了多久的既有问题，需要单独决定怎么处理。

- [ ] **Step 5: Commit**

```bash
git add scripts/run-skill-tests.sh
git commit -m "fix(tests): skill 与 tool 的 pytest 改用 pytest 执行

run-skill-tests.sh 此前对 tests/*.py 执行 python3 <file>。这些是
pytest 文件，直接执行只 import 模块然后退出 0，一个测试都不跑，
npm test 一直把「没跑」报成「通过」。改为按 tests/ 目录调 pytest，
并把 tools/*/tests/ 一并纳入。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 1: roster tool 脚手架与配置

**Files:**
- Create: `tools/roster/pyproject.toml`, `tools/roster/tool.json`, `tools/roster/roster.sh`, `tools/roster/roster/__init__.py`, `tools/roster/roster/config.py`
- Test: `tools/roster/tests/conftest.py`, `tools/roster/tests/test_config.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `roster.config.get_config_path() -> Path`
  - `roster.config.get_data_dir() -> Path`（`DATA_DIR` 缺失时抛 `KeyError`，配置文件不存在时抛 `FileNotFoundError`）
  - `roster.config.set_config(key: str, value: str) -> None`
  - `roster.SCHEMA_VERSION: int = 1`
  - pytest fixture `data_dir`（`tmp_path` 下的隔离数据目录）

- [ ] **Step 1: 写失败的测试**

`tools/roster/tests/conftest.py`：

```python
"""Test isolation for roster:每个测试拿到 tmp_path 下的独立配置与数据目录，
绝不触碰真实的 ~/.hskill/roster/。config.get_config_path() 每次调用都读环境
变量（不在 import 时固化），所以设一次 env 同时覆盖进程内调用和子进程。"""
import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch) -> Path:
    d = tmp_path / "roster-data"
    cfg = tmp_path / "roster-config.json"
    cfg.write_text(json.dumps({"DATA_DIR": str(d)}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(cfg))
    return d
```

`tools/roster/tests/test_config.py`：

```python
import json

import pytest

from roster import SCHEMA_VERSION, config


def test_schema_version_is_one():
    assert SCHEMA_VERSION == 1


def test_get_data_dir_reads_configured_path(data_dir):
    assert config.get_data_dir() == data_dir


def test_get_config_path_follows_env_var_changed_after_import(tmp_path, monkeypatch):
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"DATA_DIR": "/tmp/elsewhere"}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(other))
    assert config.get_config_path() == other


def test_missing_config_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(tmp_path / "nope.json"))
    with pytest.raises(FileNotFoundError):
        config.get_data_dir()


def test_config_without_data_dir_raises(tmp_path, monkeypatch):
    cfg = tmp_path / "empty.json"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(cfg))
    with pytest.raises(KeyError):
        config.get_data_dir()


def test_set_config_creates_parent_dirs(tmp_path, monkeypatch):
    cfg = tmp_path / "deep" / "nested" / "config.json"
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(cfg))
    config.set_config("DATA_DIR", "/tmp/x")
    assert json.loads(cfg.read_text(encoding="utf-8"))["DATA_DIR"] == "/tmp/x"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_config.py -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'roster'`。

- [ ] **Step 3: 写最小实现**

`tools/roster/roster/__init__.py`：

```python
"""roster —— 人（creator）与渠道（channel）名册。

三份数据、三个消费者、三个 CLI 命令组：
  registry.json    人与渠道的定义   manage-roster skill
  state.json       游标与失败态     sync-* skill
  profiles/*.md    画像             认知层 skill

渠道数据可重建，画像不可重建。这条线决定了它们为什么分三份存。
"""

SCHEMA_VERSION = 1
```

`tools/roster/roster/config.py`：

```python
"""roster 的数据目录位置。

路径由用户提供，不给默认值：名册里的画像是要跟用户笔记同等对待的资产，
猜一个目录会把它悄悄埋在别处。配置文件自身的位置是固定的
（~/.hskill/roster/config.json），只有它指向的数据目录可配。

HSKILL_ROSTER_CONFIG 覆盖配置路径，且在每次调用时读取——测试要能在
进程内重定向，不能只对子进程生效。
"""
import json
import os
from pathlib import Path


def get_config_path() -> Path:
    override = os.environ.get("HSKILL_ROSTER_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".hskill" / "roster" / "config.json"


def get_config() -> dict:
    path = get_config_path()
    if not path.exists():
        raise FileNotFoundError(
            f"roster 配置文件不存在：{path}\n首次使用请先完成初始化，设置 DATA_DIR。"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def get_data_dir() -> Path:
    cfg = get_config()
    if "DATA_DIR" not in cfg:
        raise KeyError("config.json 缺少 DATA_DIR，请重新初始化。")
    return Path(cfg["DATA_DIR"]).expanduser()


def set_config(key: str, value: str) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg: dict = {}
    if path.exists():
        cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg[key] = value
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
```

`tools/roster/pyproject.toml`：

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "roster"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
roster = "roster.__main__:main"

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.hatch.build.targets.wheel]
packages = ["roster"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`tools/roster/tool.json`：

```json
{
  "name": "roster",
  "version": "0.1.0",
  "description": "Creator + channel roster — shared watchlist, cursors and profiles for the sync-* skills",
  "extraPaths": ["roster", "pyproject.toml"],
  "uninstallPaths": ["~/.hskill/tools/roster/venv", "~/.hskill/tools/roster"],
  "configPaths": ["~/.hskill/roster"]
}
```

注意 `uninstallPaths` **不含** `DATA_DIR`——那里躺着不可重建的画像，卸载 tool 不该碰它。`configPaths` 只覆盖 `~/.hskill/roster`（里面只有指向 `DATA_DIR` 的 `config.json`）。

`tools/roster/roster.sh`（照抄 `tools/hub/hub.sh`，把 `hub` 换成 `roster`）：

```bash
#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect dev mode: script is running from the source tree
if [ -d "${SCRIPT_DIR}/roster" ] && [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
  DEV_VENV="${SCRIPT_DIR}/.venv"
  if [ ! -x "${DEV_VENV}/bin/roster" ]; then
    python3 -m venv "${DEV_VENV}"
    "${DEV_VENV}/bin/pip" install -q -e "${SCRIPT_DIR}"
  fi
  exec "${DEV_VENV}/bin/roster" "$@"
fi

VENV_DIR="${HOME}/.hskill/tools/roster/venv"
INSTALL_DIR="${HOME}/.hskill/tools/roster"
HASH_FILE="${VENV_DIR}/.installed_hash"

_hash_source() {
  find "${INSTALL_DIR}" -type f \( -name "*.py" -o -name "*.toml" -o -name "*.json" \) \
    ! -path "*/__pycache__/*" ! -path "*/venv/*" \
    | sort | xargs sha256sum 2>/dev/null | sha256sum | awk '{print $1}'
}

CURRENT_HASH=$(_hash_source)

if [ ! -x "${VENV_DIR}/bin/roster" ] || [ "$(cat "${HASH_FILE}" 2>/dev/null)" != "${CURRENT_HASH}" ]; then
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install -q --upgrade "${INSTALL_DIR}"
  echo "${CURRENT_HASH}" > "${HASH_FILE}"
fi

exec "${VENV_DIR}/bin/roster" "$@"
```

```bash
chmod +x tools/roster/roster.sh
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/ -q
```

Expected: `6 passed`。

`roster` 包尚无 `__main__.py`，`pyproject.toml` 的 `[project.scripts]` 指向它——本步骤不安装包，pytest 靠 rootdir 下的包目录直接 import，不受影响。Task 7 补齐 `__main__.py`。

- [ ] **Step 5: Commit**

```bash
git add tools/roster
git commit -m "feat(roster): tool 脚手架与 DATA_DIR 配置

stdlib-only，无第三方运行时依赖。uninstallPaths 刻意不含 DATA_DIR，
那里存着不可重建的画像。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: URL 解析与 slug 生成

**Files:**
- Create: `tools/roster/roster/urls.py`
- Test: `tools/roster/tests/test_urls.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `roster.urls.parse_channel_url(url: str) -> tuple[str, str]` → `(platform, handle)`，platform 取值 `"x"` 或 `"youtube"`；无法识别时抛 `ValueError`
  - `roster.urls.slugify(text: str) -> str`
  - `roster.urls.channel_key(platform: str, handle: str) -> str` → `f"{platform}:{handle}"`

YouTube 分支的正则直接取自 `skills/research/sync-ytchannel/scripts/watchlist.py:24-26`，行为必须保持一致（`/watch?v=` 这类单视频链接要拒绝）。X 分支是新写的：profile URL 形如 `https://x.com/<handle>` 或 `https://twitter.com/<handle>`，`handle` 是最后一段路径。

- [ ] **Step 1: 写失败的测试**

`tools/roster/tests/test_urls.py`：

```python
import pytest

from roster import urls


@pytest.mark.parametrize("url,expected", [
    ("https://youtube.com/@AndrejKarpathy", ("youtube", "AndrejKarpathy")),
    ("https://www.youtube.com/@AndrejKarpathy/videos", ("youtube", "AndrejKarpathy")),
    ("https://m.youtube.com/channel/UCabc123", ("youtube", "UCabc123")),
    ("https://youtube.com/c/somename", ("youtube", "somename")),
    ("https://youtube.com/user/olduser", ("youtube", "olduser")),
    ("https://x.com/karpathy", ("x", "karpathy")),
    ("https://x.com/@karpathy", ("x", "karpathy")),
    ("https://twitter.com/karpathy", ("x", "karpathy")),
    ("https://x.com/karpathy/", ("x", "karpathy")),
])
def test_parse_channel_url(url, expected):
    assert urls.parse_channel_url(url) == expected


@pytest.mark.parametrize("url", [
    "https://youtube.com/watch?v=abc123",
    "https://example.com/karpathy",
    "not a url",
    "https://x.com/",
])
def test_parse_channel_url_rejects(url):
    with pytest.raises(ValueError):
        urls.parse_channel_url(url)


@pytest.mark.parametrize("text,expected", [
    ("AndrejKarpathy", "andrejkarpathy"),
    ("Andrej Karpathy", "andrej-karpathy"),
    ("Two Minute Papers!", "two-minute-papers"),
    ("__weird__name__", "weird-name"),
])
def test_slugify(text, expected):
    assert urls.slugify(text) == expected


def test_channel_key():
    assert urls.channel_key("x", "karpathy") == "x:karpathy"
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_urls.py -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'roster.urls'`。

- [ ] **Step 3: 写最小实现**

`tools/roster/roster/urls.py`：

```python
"""URL → (platform, handle)，以及 creator id 用的 slug。

YouTube 的正则原样取自 sync-ytchannel/scripts/watchlist.py，行为要保持一致：
/watch?v= 这类单视频链接必须拒绝——名册收的是渠道，不是单条物料。
"""
import re

_YOUTUBE_RE = re.compile(
    r"^https?://(?:www\.|m\.)?youtube\.com/(?:(@[^/?#]+)|(?:channel|c|user)/([^/?#]+))(?:/[^/?#]*)?/?(?:[?#].*)?$"
)
_X_RE = re.compile(
    r"^https?://(?:www\.)?(?:x|twitter)\.com/@?([A-Za-z0-9_]+)/?(?:[?#].*)?$"
)


def parse_channel_url(url: str) -> tuple[str, str]:
    url = url.strip()

    match = _YOUTUBE_RE.match(url)
    if match:
        at_handle, path_id = match.groups()
        return "youtube", (at_handle[1:] if at_handle else path_id)

    match = _X_RE.match(url)
    if match:
        return "x", match.group(1)

    raise ValueError(f"不是可识别的渠道 URL：{url}")


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    if not slug:
        raise ValueError(f"无法从 {text!r} 生成 slug")
    return slug


def channel_key(platform: str, handle: str) -> str:
    return f"{platform}:{handle}"
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/test_urls.py -q
```

Expected: `18 passed`。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/urls.py tools/roster/tests/test_urls.py
git commit -m "feat(roster): URL 解析与 slug 生成

YouTube 正则沿用 sync-ytchannel 既有行为（拒绝单视频链接），
X 分支新增。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: registry.json 读写与 creator/channel CRUD

**Files:**
- Create: `tools/roster/roster/registry.py`
- Test: `tools/roster/tests/test_registry.py`

**Interfaces:**
- Consumes: `roster.SCHEMA_VERSION`、`roster.urls.parse_channel_url`、`roster.urls.slugify`
- Produces:
  - `load(data_dir: Path) -> dict` — 文件不存在时返回 `{"schema_version": 1, "creators": []}`
  - `save(data_dir: Path, reg: dict) -> None`
  - `find_creator(reg: dict, creator_id: str) -> dict | None` — `id` 或 `aliases` 命中均可
  - `find_channel(reg: dict, platform: str, handle: str) -> tuple[dict, dict] | None` — 返回 `(creator, channel)`
  - `add_channel(reg: dict, url: str, today: str) -> tuple[str, bool]` — 返回 `(creator_id, created_placeholder)`；渠道已存在时抛 `ValueError`
  - `channels_for_platform(reg: dict, platform: str) -> list[dict]` — 每项为 `{"creator_id", "platform", "handle", "url"}`
  - `remove_creator(reg: dict, creator_id: str) -> dict` — 返回被摘掉的 creator；不存在时抛 `ValueError`
  - `remove_channel(reg: dict, platform: str, handle: str) -> None` — 不存在时抛 `ValueError`

`add_channel` 自动建占位 creator：`id = slugify(handle)`、`display_name = handle`、`placeholder = True`。若该 slug 已被占用（不同平台同名 handle 属于不同人），追加 `-2`、`-3` 直到不冲突。

- [ ] **Step 1: 写失败的测试**

`tools/roster/tests/test_registry.py`：

```python
import json

import pytest

from roster import SCHEMA_VERSION, registry

TODAY = "2026-08-26"


def test_load_missing_file_returns_empty(data_dir):
    reg = registry.load(data_dir)
    assert reg == {"schema_version": SCHEMA_VERSION, "creators": []}


def test_save_then_load_roundtrip(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.save(data_dir, reg)
    assert registry.load(data_dir) == reg


def test_save_creates_parent_dir(data_dir):
    registry.save(data_dir, registry.load(data_dir))
    assert (data_dir / "registry.json").exists()


def test_add_channel_creates_placeholder_creator(data_dir):
    reg = registry.load(data_dir)
    creator_id, created = registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    assert (creator_id, created) == ("karpathy", True)
    creator = registry.find_creator(reg, "karpathy")
    assert creator["display_name"] == "karpathy"
    assert creator["placeholder"] is True
    assert creator["added_at"] == TODAY
    assert creator["aliases"] == []
    assert creator["channels"] == [
        {"platform": "x", "handle": "karpathy", "url": "https://x.com/karpathy"}
    ]


def test_add_second_channel_for_same_handle_on_other_platform_makes_second_creator(data_dir):
    """同名 handle 跨平台不代表同一个人——不自动合并，交给 merge。"""
    reg = registry.load(data_dir)
    a, _ = registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    b, _ = registry.add_channel(reg, "https://youtube.com/@karpathy", TODAY)
    assert a == "karpathy"
    assert b == "karpathy-2"
    assert len(reg["creators"]) == 2


def test_add_duplicate_channel_raises(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    with pytest.raises(ValueError, match="已在名册"):
        registry.add_channel(reg, "https://x.com/karpathy", TODAY)


def test_add_channel_rejects_bad_url(data_dir):
    reg = registry.load(data_dir)
    with pytest.raises(ValueError):
        registry.add_channel(reg, "https://youtube.com/watch?v=abc", TODAY)


def test_find_channel_returns_creator_and_channel(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    creator, channel = registry.find_channel(reg, "x", "karpathy")
    assert creator["id"] == "karpathy"
    assert channel["handle"] == "karpathy"


def test_find_channel_missing_returns_none(data_dir):
    assert registry.find_channel(registry.load(data_dir), "x", "nobody") is None


def test_find_creator_matches_alias(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.find_creator(reg, "karpathy")["aliases"].append("old-id")
    assert registry.find_creator(reg, "old-id")["id"] == "karpathy"


def test_channels_for_platform_filters_and_carries_creator_id(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.add_channel(reg, "https://youtube.com/@TwoMinutePapers", TODAY)
    assert registry.channels_for_platform(reg, "x") == [
        {"creator_id": "karpathy", "platform": "x",
         "handle": "karpathy", "url": "https://x.com/karpathy"}
    ]
    assert len(registry.channels_for_platform(reg, "youtube")) == 1


def test_channels_for_platform_empty(data_dir):
    assert registry.channels_for_platform(registry.load(data_dir), "x") == []


def test_remove_channel_leaves_creator_behind(data_dir):
    """人可以暂时没有渠道——认识但还没订阅。删渠道不连带删人。"""
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.remove_channel(reg, "x", "karpathy")
    assert registry.find_creator(reg, "karpathy")["channels"] == []


def test_remove_channel_missing_raises(data_dir):
    with pytest.raises(ValueError):
        registry.remove_channel(registry.load(data_dir), "x", "nobody")


def test_remove_creator_returns_it_and_drops_channels(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    removed = registry.remove_creator(reg, "karpathy")
    assert removed["id"] == "karpathy"
    assert reg["creators"] == []


def test_remove_creator_missing_raises(data_dir):
    with pytest.raises(ValueError):
        registry.remove_creator(registry.load(data_dir), "nobody")


def test_saved_json_is_readable_utf8(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.find_creator(reg, "karpathy")["display_name"] = "安德烈"
    registry.save(data_dir, reg)
    raw = (data_dir / "registry.json").read_text(encoding="utf-8")
    assert "安德烈" in raw          # 不是 \uXXXX 转义
    assert json.loads(raw)["schema_version"] == SCHEMA_VERSION
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_registry.py -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'roster.registry'`。

- [ ] **Step 3: 写最小实现**

`tools/roster/roster/registry.py`：

```python
"""registry.json —— 人（creator）与渠道（channel）的定义。

唯一写入方是 manage-roster skill（经 `roster registry` 命令组）。抓取层
只读这里、只写 state.json。

归属关系嵌套表达：渠道存在哪个 creator 的 channels 里，就属于谁。不另存
creator_id 外键——一份归属关系只有一个真值来源。
"""
from pathlib import Path

from . import SCHEMA_VERSION
from .urls import parse_channel_url, slugify


def _path(data_dir: Path) -> Path:
    return Path(data_dir) / "registry.json"


def load(data_dir: Path) -> dict:
    import json

    path = _path(data_dir)
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "creators": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(data_dir: Path, reg: dict) -> None:
    import json

    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def find_creator(reg: dict, creator_id: str) -> dict | None:
    for c in reg["creators"]:
        if c["id"] == creator_id or creator_id in c.get("aliases", []):
            return c
    return None


def find_channel(reg: dict, platform: str, handle: str) -> tuple[dict, dict] | None:
    for c in reg["creators"]:
        for ch in c["channels"]:
            if ch["platform"] == platform and ch["handle"] == handle:
                return c, ch
    return None


def _free_slug(reg: dict, base: str) -> str:
    """同名 handle 跨平台不代表同一个人，所以撞了就编号，不合并。
    真是同一个人由用户跑 merge 决定——那是判断，不是解析。"""
    if find_creator(reg, base) is None:
        return base
    n = 2
    while find_creator(reg, f"{base}-{n}") is not None:
        n += 1
    return f"{base}-{n}"


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
        "channels": [{"platform": platform, "handle": handle, "url": url}],
    })
    return creator_id, True


def channels_for_platform(reg: dict, platform: str) -> list[dict]:
    out = []
    for c in reg["creators"]:
        for ch in c["channels"]:
            if ch["platform"] == platform:
                out.append({"creator_id": c["id"], **ch})
    return out


def remove_creator(reg: dict, creator_id: str) -> dict:
    creator = find_creator(reg, creator_id)
    if creator is None:
        raise ValueError(f"名册里没有 {creator_id}")
    reg["creators"].remove(creator)
    return creator


def remove_channel(reg: dict, platform: str, handle: str) -> None:
    found = find_channel(reg, platform, handle)
    if found is None:
        raise ValueError(f"名册里没有 {platform}:{handle}")
    creator, channel = found
    creator["channels"].remove(channel)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/test_registry.py -q
```

Expected: `17 passed`。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/registry.py tools/roster/tests/test_registry.py
git commit -m "feat(roster): registry.json 读写与 creator/channel CRUD

归属关系用嵌套表达，不存 creator_id 外键。同名 handle 跨平台自动编号
而非合并——判断谁是同一个人交给 merge。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: creator 的 merge 与 rename

**Files:**
- Modify: `tools/roster/roster/registry.py`
- Test: `tools/roster/tests/test_registry_merge.py`

**Interfaces:**
- Consumes: Task 3 的 `find_creator`
- Produces:
  - `rename_creator(reg: dict, creator_id: str, display_name: str) -> None` — 顺带清 `placeholder` 标记
  - `merge_creators(reg: dict, id_a: str, id_b: str) -> None` — 保留 `id_a` 的 `id` 与 `display_name`；`id_b` 的 `id` 与其 `aliases` 并入 `id_a` 的 `aliases`；渠道追加；`placeholder` 取两者的与（任一为 False 则结果为 False）

**画像文件的归并不在这里** —— `registry.py` 不碰 `profiles/`。CLI 层（Task 7）负责在 `merge` 时依次调 `registry.merge_creators` 和 `profiles.merge`。

- [ ] **Step 1: 写失败的测试**

`tools/roster/tests/test_registry_merge.py`：

```python
import pytest

from roster import registry

TODAY = "2026-08-26"


def _two_creators(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.add_channel(reg, "https://youtube.com/@AndrejKarpathy", TODAY)
    return reg


def test_rename_sets_name_and_clears_placeholder(data_dir):
    reg = _two_creators(data_dir)
    registry.rename_creator(reg, "karpathy", "Andrej Karpathy")
    creator = registry.find_creator(reg, "karpathy")
    assert creator["display_name"] == "Andrej Karpathy"
    assert creator["placeholder"] is False
    assert creator["id"] == "karpathy"          # id 不可变


def test_rename_missing_raises(data_dir):
    with pytest.raises(ValueError):
        registry.rename_creator(registry.load(data_dir), "nobody", "X")


def test_merge_keeps_first_id_and_name(data_dir):
    reg = _two_creators(data_dir)
    registry.rename_creator(reg, "karpathy", "Andrej Karpathy")
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    assert len(reg["creators"]) == 1
    merged = reg["creators"][0]
    assert merged["id"] == "karpathy"
    assert merged["display_name"] == "Andrej Karpathy"


def test_merge_puts_second_id_into_aliases(data_dir):
    reg = _two_creators(data_dir)
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    assert "andrejkarpathy" in registry.find_creator(reg, "karpathy")["aliases"]


def test_merged_old_id_still_resolves(data_dir):
    """旧 id 落进 aliases 的意义就在这里——外部引用不失效。"""
    reg = _two_creators(data_dir)
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    assert registry.find_creator(reg, "andrejkarpathy")["id"] == "karpathy"


def test_merge_combines_channels(data_dir):
    reg = _two_creators(data_dir)
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    merged = registry.find_creator(reg, "karpathy")
    assert {(c["platform"], c["handle"]) for c in merged["channels"]} == {
        ("x", "karpathy"), ("youtube", "AndrejKarpathy")
    }


def test_merge_carries_over_second_aliases(data_dir):
    reg = _two_creators(data_dir)
    registry.find_creator(reg, "andrejkarpathy")["aliases"].append("ancient-id")
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    aliases = registry.find_creator(reg, "karpathy")["aliases"]
    assert set(aliases) == {"andrejkarpathy", "ancient-id"}


def test_merge_clears_placeholder_if_either_is_confirmed(data_dir):
    reg = _two_creators(data_dir)
    registry.rename_creator(reg, "andrejkarpathy", "Andrej Karpathy")
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    assert registry.find_creator(reg, "karpathy")["placeholder"] is False


def test_merge_into_self_raises(data_dir):
    reg = _two_creators(data_dir)
    with pytest.raises(ValueError, match="不能合并到自己"):
        registry.merge_creators(reg, "karpathy", "karpathy")


def test_merge_missing_raises(data_dir):
    reg = _two_creators(data_dir)
    with pytest.raises(ValueError):
        registry.merge_creators(reg, "karpathy", "nobody")
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_registry_merge.py -q
```

Expected: FAIL，`AttributeError: module 'roster.registry' has no attribute 'rename_creator'`。

- [ ] **Step 3: 写最小实现**

在 `tools/roster/roster/registry.py` 末尾追加：

```python
def rename_creator(reg: dict, creator_id: str, display_name: str) -> None:
    creator = find_creator(reg, creator_id)
    if creator is None:
        raise ValueError(f"名册里没有 {creator_id}")
    creator["display_name"] = display_name
    creator["placeholder"] = False


def merge_creators(reg: dict, id_a: str, id_b: str) -> None:
    """b 并入 a。a 的 id 和 display_name 胜出，b 的 id 落进 a 的 aliases，
    这样外部对 b 的旧引用仍然解析得到。"""
    a = find_creator(reg, id_a)
    b = find_creator(reg, id_b)
    if a is None:
        raise ValueError(f"名册里没有 {id_a}")
    if b is None:
        raise ValueError(f"名册里没有 {id_b}")
    if a is b:
        raise ValueError("不能合并到自己")

    for alias in [b["id"], *b.get("aliases", [])]:
        if alias not in a["aliases"]:
            a["aliases"].append(alias)
    a["channels"].extend(b["channels"])
    a["placeholder"] = a["placeholder"] and b["placeholder"]
    reg["creators"].remove(b)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/ -q
```

Expected: `51 passed`（前三个任务 6 + 18 + 17，本任务 10）。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/registry.py tools/roster/tests/test_registry_merge.py
git commit -m "feat(roster): creator 的 merge 与 rename

merge 保留 id-a，id-b 落入 aliases 以保旧引用可解析。画像归并不在
registry 层，由 CLI 编排。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: state.json —— 游标与失败态

**Files:**
- Create: `tools/roster/roster/state.py`
- Test: `tools/roster/tests/test_state.py`

**Interfaces:**
- Consumes: `roster.SCHEMA_VERSION`、`roster.urls.channel_key`
- Produces:
  - `load(data_dir: Path) -> dict` — 缺失时返回 `{"schema_version": 1, "channels": {}}`
  - `save(data_dir: Path, st: dict) -> None`
  - `get_cursor(st: dict, platform: str, handle: str) -> dict | None` — 返回 `{"type", "value"}`，从未抓过则 `None`
  - `set_cursor(st: dict, platform: str, handle: str, cursor_type: str, value, run_time: str) -> None` — 顺带清空 `last_error`
  - `set_error(st: dict, platform: str, handle: str, error: str, run_time: str) -> None` — **不动游标**
  - `drop_channel(st: dict, platform: str, handle: str) -> None` — 渠道不在 state 里时静默返回

`cursor_type` 只有两个合法值：`"last_seen_id"`（X）、`"seen_urls"`（YouTube）。传别的抛 `ValueError`。游标语义刻意不统一——X 的 snowflake id 可比大小，YouTube 的 video id 不透明，强行统一会逼 X 退化成 URL 集合。

- [ ] **Step 1: 写失败的测试**

`tools/roster/tests/test_state.py`：

```python
import pytest

from roster import SCHEMA_VERSION, state

RUN = "2026-08-26T09:14:00+08:00"


def test_load_missing_returns_empty(data_dir):
    assert state.load(data_dir) == {"schema_version": SCHEMA_VERSION, "channels": {}}


def test_roundtrip(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1876543210987654321", RUN)
    state.save(data_dir, st)
    assert state.load(data_dir) == st


def test_get_cursor_before_first_fetch_is_none(data_dir):
    assert state.get_cursor(state.load(data_dir), "x", "karpathy") is None


def test_set_and_get_last_seen_id(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "123", RUN)
    assert state.get_cursor(st, "x", "karpathy") == {"type": "last_seen_id", "value": "123"}


def test_set_and_get_seen_urls(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "youtube", "AK", "seen_urls", ["https://a", "https://b"], RUN)
    assert state.get_cursor(st, "youtube", "AK") == {
        "type": "seen_urls", "value": ["https://a", "https://b"]
    }


def test_channels_are_keyed_by_platform_and_handle(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1", RUN)
    assert "x:karpathy" in st["channels"]


def test_same_handle_on_two_platforms_does_not_collide(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "same", "last_seen_id", "1", RUN)
    state.set_cursor(st, "youtube", "same", "seen_urls", ["u"], RUN)
    assert state.get_cursor(st, "x", "same")["value"] == "1"
    assert state.get_cursor(st, "youtube", "same")["value"] == ["u"]


def test_set_cursor_rejects_unknown_type(data_dir):
    with pytest.raises(ValueError, match="未知的游标类型"):
        state.set_cursor(state.load(data_dir), "x", "k", "whatever", "1", RUN)


def test_set_cursor_records_run_time(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1", RUN)
    assert st["channels"]["x:karpathy"]["last_run"] == RUN


def test_set_error_leaves_cursor_untouched(data_dir):
    """抓取失败不该让游标倒退——那会导致下一次重报一批旧物料。"""
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "123", RUN)
    state.set_error(st, "x", "karpathy", "timed out", "2026-08-27T09:00:00+08:00")
    assert state.get_cursor(st, "x", "karpathy")["value"] == "123"
    assert st["channels"]["x:karpathy"]["last_error"] == "timed out"


def test_set_error_on_never_fetched_channel(data_dir):
    st = state.load(data_dir)
    state.set_error(st, "x", "nobody", "boom", RUN)
    assert state.get_cursor(st, "x", "nobody") is None
    assert st["channels"]["x:nobody"]["last_error"] == "boom"


def test_successful_set_cursor_clears_previous_error(data_dir):
    st = state.load(data_dir)
    state.set_error(st, "x", "karpathy", "timed out", RUN)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1", RUN)
    assert st["channels"]["x:karpathy"]["last_error"] is None


def test_drop_channel(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1", RUN)
    state.drop_channel(st, "x", "karpathy")
    assert st["channels"] == {}


def test_drop_missing_channel_is_silent(data_dir):
    state.drop_channel(state.load(data_dir), "x", "nobody")
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_state.py -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'roster.state'`。

- [ ] **Step 3: 写最小实现**

`tools/roster/roster/state.py`：

```python
"""state.json —— 每个渠道的游标、上次运行时间、上次失败原因。

唯一写入方是抓取层（sync-* 经 `roster state` 命令组）。这份数据可重建：
删掉重跑最坏是刷一次基线、漏报一批，没有永久损失。

游标语义按平台各存各的，刻意不统一：X 的 snowflake id 单调递增可比大小，
YouTube 的 video id 不透明只能判「见过没有」。统一会逼 X 退化成 URL 集合，
白丢一个更省的表示。
"""
import json
from pathlib import Path

from . import SCHEMA_VERSION
from .urls import channel_key

CURSOR_TYPES = ("last_seen_id", "seen_urls")


def _path(data_dir: Path) -> Path:
    return Path(data_dir) / "state.json"


def load(data_dir: Path) -> dict:
    path = _path(data_dir)
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "channels": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save(data_dir: Path, st: dict) -> None:
    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


def _entry(st: dict, platform: str, handle: str) -> dict:
    key = channel_key(platform, handle)
    return st["channels"].setdefault(
        key, {"cursor": None, "last_run": None, "last_error": None}
    )


def get_cursor(st: dict, platform: str, handle: str) -> dict | None:
    entry = st["channels"].get(channel_key(platform, handle))
    return entry["cursor"] if entry else None


def set_cursor(st: dict, platform: str, handle: str,
               cursor_type: str, value, run_time: str) -> None:
    if cursor_type not in CURSOR_TYPES:
        raise ValueError(f"未知的游标类型：{cursor_type}")
    entry = _entry(st, platform, handle)
    entry["cursor"] = {"type": cursor_type, "value": value}
    entry["last_run"] = run_time
    entry["last_error"] = None


def set_error(st: dict, platform: str, handle: str, error: str, run_time: str) -> None:
    """失败不动游标。让它倒退会导致下一次重报一批旧物料。"""
    entry = _entry(st, platform, handle)
    entry["last_run"] = run_time
    entry["last_error"] = error


def drop_channel(st: dict, platform: str, handle: str) -> None:
    st["channels"].pop(channel_key(platform, handle), None)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/test_state.py -q
```

Expected: `14 passed`。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/state.py tools/roster/tests/test_state.py
git commit -m "feat(roster): state.json 游标与失败态

游标语义按平台各存各的，不强行统一。抓取失败只记 last_error，不动游标。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: profiles/*.md —— 画像的追加、归档与归并

**Files:**
- Create: `tools/roster/roster/profiles.py`
- Test: `tools/roster/tests/test_profiles.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `profile_path(data_dir: Path, creator_id: str) -> Path` → `<data_dir>/profiles/<creator_id>.md`
  - `read(data_dir: Path, creator_id: str) -> str | None`
  - `append_observation(data_dir: Path, creator_id: str, date: str, source: str, body: str) -> None` — 文件不存在则创建；新观察插在「观察」段**最前**（倒序）；**绝不改动已有观察**
  - `set_summary(data_dir: Path, creator_id: str, text: str, updated_at: str) -> None` — 只重写「当前判断」段
  - `archive(data_dir: Path, creator_id: str) -> Path | None` — 移到 `profiles/archived/<creator_id>.md`；无画像时返回 `None`
  - `merge(data_dir: Path, id_a: str, id_b: str, updated_at: str) -> None` — 两份观察按日期倒序归并进 `id_a`，`id_b` 的文件归档，`id_a` 的「当前判断」置空

这是全套数据里唯一不可重建的部分。**「观察」只追加，「当前判断」可重写**——后者能从前者重算，前者不能。

文件格式（每条观察的标题行格式固定，解析器依赖它）：

```markdown
---
creator_id: andrej-karpathy
updated_at: 2026-08-26
---

## 当前判断

（空或一段可重算的摘要）

## 观察

### 2026-08-26 · 依据：sync-xtimeline 本次 12 条推文

正文

### 2026-08-19 · 依据：sync-ytchannel 3 个新视频标题

正文
```

- [ ] **Step 1: 写失败的测试**

`tools/roster/tests/test_profiles.py`：

```python
from roster import profiles

D1, D2, D3 = "2026-08-19", "2026-08-26", "2026-09-02"


def test_read_missing_returns_none(data_dir):
    assert profiles.read(data_dir, "nobody") is None


def test_append_creates_file_with_frontmatter(data_dir):
    profiles.append_observation(data_dir, "karpathy", D2, "sync-xtimeline 12 条推文", "写得很密")
    text = profiles.read(data_dir, "karpathy")
    assert text.startswith("---\n")
    assert "creator_id: karpathy" in text
    assert f"updated_at: {D2}" in text
    assert "## 当前判断" in text
    assert "## 观察" in text
    assert "### 2026-08-26 · 依据：sync-xtimeline 12 条推文" in text
    assert "写得很密" in text


def test_profile_path_is_under_profiles_dir(data_dir):
    assert profiles.profile_path(data_dir, "karpathy") == data_dir / "profiles" / "karpathy.md"


def test_second_append_goes_on_top(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "旧观察")
    profiles.append_observation(data_dir, "k", D2, "晚", "新观察")
    text = profiles.read(data_dir, "k")
    assert text.index("新观察") < text.index("旧观察")


def test_append_never_rewrites_existing_observations(data_dir):
    """这是整个设计里唯一不可重建的数据，追加不能碰旧条目。"""
    profiles.append_observation(data_dir, "k", D1, "早", "旧观察原文")
    before = profiles.read(data_dir, "k")
    profiles.append_observation(data_dir, "k", D2, "晚", "新观察")
    after = profiles.read(data_dir, "k")
    assert "### 2026-08-19 · 依据：早\n\n旧观察原文" in before
    assert "### 2026-08-19 · 依据：早\n\n旧观察原文" in after


def test_append_bumps_updated_at(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "a")
    profiles.append_observation(data_dir, "k", D2, "晚", "b")
    assert f"updated_at: {D2}" in profiles.read(data_dir, "k")


def test_set_summary_replaces_only_summary(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "观察正文")
    profiles.set_summary(data_dir, "k", "他擅长把复杂的东西讲简单", D2)
    text = profiles.read(data_dir, "k")
    assert "他擅长把复杂的东西讲简单" in text
    assert "观察正文" in text


def test_set_summary_twice_does_not_accumulate(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "观察")
    profiles.set_summary(data_dir, "k", "第一版判断", D2)
    profiles.set_summary(data_dir, "k", "第二版判断", D3)
    text = profiles.read(data_dir, "k")
    assert "第一版判断" not in text
    assert "第二版判断" in text


def test_set_summary_on_missing_profile_creates_it(data_dir):
    profiles.set_summary(data_dir, "k", "判断", D2)
    assert "判断" in profiles.read(data_dir, "k")


def test_archive_moves_file_and_leaves_original_gone(data_dir):
    profiles.append_observation(data_dir, "k", D1, "早", "观察")
    dest = profiles.archive(data_dir, "k")
    assert dest == data_dir / "profiles" / "archived" / "k.md"
    assert dest.exists()
    assert profiles.read(data_dir, "k") is None
    assert "观察" in dest.read_text(encoding="utf-8")


def test_archive_missing_returns_none(data_dir):
    assert profiles.archive(data_dir, "nobody") is None


def test_archive_twice_does_not_clobber(data_dir):
    """取关又重关又取关时，第一份归档不能被第二份盖掉。"""
    profiles.append_observation(data_dir, "k", D1, "早", "第一轮观察")
    profiles.archive(data_dir, "k")
    profiles.append_observation(data_dir, "k", D2, "晚", "第二轮观察")
    second = profiles.archive(data_dir, "k")
    assert second == data_dir / "profiles" / "archived" / "k-2.md"
    first = data_dir / "profiles" / "archived" / "k.md"
    assert "第一轮观察" in first.read_text(encoding="utf-8")


def test_merge_combines_observations_newest_first(data_dir):
    profiles.append_observation(data_dir, "a", D1, "a 源", "a 的旧观察")
    profiles.append_observation(data_dir, "b", D3, "b 源", "b 的新观察")
    profiles.merge(data_dir, "a", "b", D3)
    text = profiles.read(data_dir, "a")
    assert text.index("b 的新观察") < text.index("a 的旧观察")


def test_merge_clears_summary(data_dir):
    """两个人的判断合并之后，旧摘要不再成立，置空等重算。"""
    profiles.append_observation(data_dir, "a", D1, "源", "观察")
    profiles.set_summary(data_dir, "a", "旧判断", D2)
    profiles.append_observation(data_dir, "b", D2, "源", "观察 b")
    profiles.merge(data_dir, "a", "b", D3)
    assert "旧判断" not in profiles.read(data_dir, "a")


def test_merge_archives_b(data_dir):
    profiles.append_observation(data_dir, "a", D1, "源", "观察 a")
    profiles.append_observation(data_dir, "b", D2, "源", "观察 b")
    profiles.merge(data_dir, "a", "b", D3)
    assert profiles.read(data_dir, "b") is None
    assert (data_dir / "profiles" / "archived" / "b.md").exists()


def test_merge_when_b_has_no_profile_is_noop(data_dir):
    profiles.append_observation(data_dir, "a", D1, "源", "观察 a")
    profiles.merge(data_dir, "a", "b", D3)
    assert "观察 a" in profiles.read(data_dir, "a")


def test_merge_when_a_has_no_profile_adopts_b(data_dir):
    profiles.append_observation(data_dir, "b", D2, "源", "观察 b")
    profiles.merge(data_dir, "a", "b", D3)
    assert "观察 b" in profiles.read(data_dir, "a")
    assert "creator_id: a" in profiles.read(data_dir, "a")
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_profiles.py -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'roster.profiles'`。

- [ ] **Step 3: 写最小实现**

`tools/roster/roster/profiles.py`：

```python
"""profiles/<creator-id>.md —— 人的画像。

全套数据里唯一不可重建的部分。「观察」段只追加不改写；「当前判断」段可以
重写，因为它能从观察重算。删除操作一律归档而非删除——一个日常动作不该能
永久销毁这份数据。

每条观察带日期和依据来源：三个月后看到「他擅长 X」，得能判断这是基于 40 条
推文写的，还是基于 3 个视频标题猜的。
"""
import re
from pathlib import Path

_OBS_RE = re.compile(r"^### (\d{4}-\d{2}-\d{2}) · 依据：(.*)$")


def _profiles_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "profiles"


def profile_path(data_dir: Path, creator_id: str) -> Path:
    return _profiles_dir(data_dir) / f"{creator_id}.md"


def read(data_dir: Path, creator_id: str) -> str | None:
    path = profile_path(data_dir, creator_id)
    return path.read_text(encoding="utf-8") if path.exists() else None


def _parse(text: str | None) -> tuple[str, list[dict]]:
    """→ (当前判断正文, [{date, source, body}, ...])。解析失败不抛异常：
    宁可把整段当成摘要保留，也不能因为用户手改过格式就丢掉观察。"""
    if not text:
        return "", []

    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    summary_part, _, obs_part = body.partition("## 观察")
    summary = summary_part.replace("## 当前判断", "", 1).strip()

    observations: list[dict] = []
    current: dict | None = None
    for line in obs_part.splitlines():
        match = _OBS_RE.match(line)
        if match:
            current = {"date": match.group(1), "source": match.group(2), "body": ""}
            observations.append(current)
        elif current is not None:
            current["body"] += line + "\n"
    for obs in observations:
        obs["body"] = obs["body"].strip()
    return summary, observations


def _render(creator_id: str, updated_at: str, summary: str, observations: list[dict]) -> str:
    parts = [
        "---",
        f"creator_id: {creator_id}",
        f"updated_at: {updated_at}",
        "---",
        "",
        "## 当前判断",
        "",
        summary,
        "",
        "## 观察",
        "",
    ]
    for obs in observations:
        parts += [f"### {obs['date']} · 依据：{obs['source']}", "", obs["body"], ""]
    return "\n".join(parts).rstrip() + "\n"


def _write(data_dir: Path, creator_id: str, updated_at: str,
           summary: str, observations: list[dict]) -> None:
    path = profile_path(data_dir, creator_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render(creator_id, updated_at, summary, observations), encoding="utf-8")


def append_observation(data_dir: Path, creator_id: str, date: str,
                       source: str, body: str) -> None:
    summary, observations = _parse(read(data_dir, creator_id))
    observations.insert(0, {"date": date, "source": source, "body": body.strip()})
    _write(data_dir, creator_id, date, summary, observations)


def set_summary(data_dir: Path, creator_id: str, text: str, updated_at: str) -> None:
    _, observations = _parse(read(data_dir, creator_id))
    _write(data_dir, creator_id, updated_at, text.strip(), observations)


def archive(data_dir: Path, creator_id: str) -> Path | None:
    src = profile_path(data_dir, creator_id)
    if not src.exists():
        return None
    archived = _profiles_dir(data_dir) / "archived"
    archived.mkdir(parents=True, exist_ok=True)

    dest = archived / f"{creator_id}.md"
    n = 2
    while dest.exists():           # 早先归档的那份不能被盖掉
        dest = archived / f"{creator_id}-{n}.md"
        n += 1
    src.rename(dest)
    return dest


def merge(data_dir: Path, id_a: str, id_b: str, updated_at: str) -> None:
    _, obs_a = _parse(read(data_dir, id_a))
    _, obs_b = _parse(read(data_dir, id_b))
    if not obs_b:
        return
    merged = sorted(obs_a + obs_b, key=lambda o: o["date"], reverse=True)
    _write(data_dir, id_a, updated_at, "", merged)   # 摘要置空，等重算
    archive(data_dir, id_b)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/test_profiles.py -q
```

Expected: `17 passed`。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/profiles.py tools/roster/tests/test_profiles.py
git commit -m "feat(roster): 画像的追加、归档与归并

观察只追加不改写，当前判断可重写。删除一律归档，归档同名不覆盖。
解析失败不抛异常——宁可整段当摘要留着，也不能因为手改过格式丢观察。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: CLI 入口

**Files:**
- Create: `tools/roster/roster/__main__.py`
- Test: `tools/roster/tests/test_cli.py`

**Interfaces:**
- Consumes: Task 1-6 全部模块
- Produces: `roster.__main__.main(argv: list[str] | None = None) -> int`

命令组与写入权一一对应（见计划开头的表）：

| 命令 | 输出 |
|---|---|
| `roster init <DATA_DIR>` | `OK <path>` |
| `roster data-dir` | `<path>`（sync-* 靠它定位 digests 目录） |
| `roster registry add <url>` | `OK <creator_id> <platform>:<handle>` |
| `roster registry remove <creator_id>` | `OK removed <id>, profile archived at <path>` 或 `OK removed <id>, no profile` |
| `roster registry remove <platform>:<handle>` | `OK removed <platform>:<handle>` |
| `roster registry rename <id> <display_name>` | `OK` |
| `roster registry merge <id-a> <id-b>` | `OK merged <id-b> into <id-a>` |
| `roster registry list` | 每行 `<id>  <display_name>  [placeholder]`，其下每渠道一行 `  <platform>:<handle>  cursor=<...>  err=<...>`；空名册输出 `EMPTY` |
| `roster registry channels --platform <p>` | 一行 JSON 数组（机器读，给 sync-*） |
| `roster state get <platform>:<handle>` | 一行 JSON（`null` 表示从未抓过） |
| `roster state set <platform>:<handle> --type <t> --value-json <j> --run-time <ts>` | `OK` |
| `roster state fail <platform>:<handle> --error <msg> --run-time <ts>` | `OK` |
| `roster profile append <id> --date <d> --source <s> --body <text>` | `OK <path>` |
| `roster profile summary <id> --text <t> --updated-at <d>` | `OK <path>` |
| `roster profile show <id>` | 画像全文，或 `EMPTY` |

错误一律写 stderr、退出码 1。**读跨组允许（`registry list` 读 state），写不允许。**

`--value-json` 收 JSON 而非裸字符串：`seen_urls` 的值是数组，`last_seen_id` 是字符串，用 JSON 才能无歧义地表达两者。

- [ ] **Step 1: 写失败的测试**

`tools/roster/tests/test_cli.py`：

```python
import json

import pytest

from roster.__main__ import main

RUN = "2026-08-26T09:14:00+08:00"


def _run(capsys, *argv) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out.strip(), captured.err.strip()


def test_registry_add(data_dir, capsys):
    code, out, _ = _run(capsys, "registry", "add", "https://x.com/karpathy")
    assert code == 0
    assert out == "OK karpathy x:karpathy"


def test_registry_add_persists_to_disk(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    reg = json.loads((data_dir / "registry.json").read_text(encoding="utf-8"))
    assert reg["creators"][0]["id"] == "karpathy"


def test_registry_add_bad_url_exits_1(data_dir, capsys):
    code, _, err = _run(capsys, "registry", "add", "https://example.com/x")
    assert code == 1
    assert "不是可识别的渠道 URL" in err


def test_registry_add_duplicate_exits_1(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    code, _, err = _run(capsys, "registry", "add", "https://x.com/karpathy")
    assert code == 1
    assert "已在名册" in err


def test_registry_list_empty(data_dir, capsys):
    code, out, _ = _run(capsys, "registry", "list")
    assert (code, out) == (0, "EMPTY")


def test_registry_list_shows_placeholder_and_channel(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _, out, _ = _run(capsys, "registry", "list")
    assert "karpathy" in out
    assert "placeholder" in out
    assert "x:karpathy" in out


def test_registry_list_shows_cursor_from_state(data_dir, capsys):
    """list 跨组读 state 是允许的——读跨组可以，写不行。"""
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "state", "set", "x:karpathy",
         "--type", "last_seen_id", "--value-json", '"123"', "--run-time", RUN)
    _, out, _ = _run(capsys, "registry", "list")
    assert "123" in out


def test_registry_channels_outputs_json(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "registry", "add", "https://youtube.com/@AK")
    code, out, _ = _run(capsys, "registry", "channels", "--platform", "x")
    assert code == 0
    assert json.loads(out) == [{
        "creator_id": "karpathy", "platform": "x",
        "handle": "karpathy", "url": "https://x.com/karpathy",
    }]


def test_registry_channels_empty_is_empty_json_array(data_dir, capsys):
    _, out, _ = _run(capsys, "registry", "channels", "--platform", "x")
    assert json.loads(out) == []


def test_registry_rename(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    code, out, _ = _run(capsys, "registry", "rename", "karpathy", "Andrej Karpathy")
    assert (code, out) == (0, "OK")
    _, listing, _ = _run(capsys, "registry", "list")
    assert "Andrej Karpathy" in listing
    assert "placeholder" not in listing


def test_registry_merge_combines_and_reports(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "registry", "add", "https://youtube.com/@AndrejKarpathy")
    code, out, _ = _run(capsys, "registry", "merge", "karpathy", "andrejkarpathy")
    assert code == 0
    assert out == "OK merged andrejkarpathy into karpathy"
    _, listing, _ = _run(capsys, "registry", "list")
    assert "x:karpathy" in listing and "youtube:AndrejKarpathy" in listing


def test_registry_merge_also_merges_profiles(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "registry", "add", "https://youtube.com/@AndrejKarpathy")
    _run(capsys, "profile", "append", "andrejkarpathy",
         "--date", "2026-08-26", "--source", "视频标题", "--body", "b 的观察")
    _run(capsys, "registry", "merge", "karpathy", "andrejkarpathy")
    _, out, _ = _run(capsys, "profile", "show", "karpathy")
    assert "b 的观察" in out


def test_registry_remove_creator_archives_profile(data_dir, capsys):
    """删人绝不删画像——那是唯一不可重建的数据。"""
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "profile", "append", "karpathy",
         "--date", "2026-08-26", "--source", "推文", "--body", "宝贵的观察")
    code, out, _ = _run(capsys, "registry", "remove", "karpathy")
    assert code == 0
    assert "archived" in out
    archived = data_dir / "profiles" / "archived" / "karpathy.md"
    assert "宝贵的观察" in archived.read_text(encoding="utf-8")


def test_registry_remove_creator_drops_its_state(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    _run(capsys, "state", "set", "x:karpathy",
         "--type", "last_seen_id", "--value-json", '"123"', "--run-time", RUN)
    _run(capsys, "registry", "remove", "karpathy")
    _, out, _ = _run(capsys, "state", "get", "x:karpathy")
    assert json.loads(out) is None


def test_registry_remove_channel_only(data_dir, capsys):
    _run(capsys, "registry", "add", "https://x.com/karpathy")
    code, out, _ = _run(capsys, "registry", "remove", "x:karpathy")
    assert (code, out) == (0, "OK removed x:karpathy")
    _, listing, _ = _run(capsys, "registry", "list")
    assert "karpathy" in listing          # 人还在
    assert "x:karpathy" not in listing    # 渠道没了


def test_state_get_before_first_fetch_is_null(data_dir, capsys):
    code, out, _ = _run(capsys, "state", "get", "x:karpathy")
    assert (code, json.loads(out)) == (0, None)


def test_state_set_and_get_seen_urls(data_dir, capsys):
    _run(capsys, "state", "set", "youtube:AK", "--type", "seen_urls",
         "--value-json", '["https://a","https://b"]', "--run-time", RUN)
    _, out, _ = _run(capsys, "state", "get", "youtube:AK")
    assert json.loads(out) == {"type": "seen_urls", "value": ["https://a", "https://b"]}


def test_state_set_rejects_bad_type(data_dir, capsys):
    code, _, err = _run(capsys, "state", "set", "x:k", "--type", "nope",
                        "--value-json", '"1"', "--run-time", RUN)
    assert code == 1
    assert "未知的游标类型" in err


def test_state_fail_keeps_cursor(data_dir, capsys):
    _run(capsys, "state", "set", "x:k", "--type", "last_seen_id",
         "--value-json", '"123"', "--run-time", RUN)
    _run(capsys, "state", "fail", "x:k", "--error", "timed out", "--run-time", RUN)
    _, out, _ = _run(capsys, "state", "get", "x:k")
    assert json.loads(out)["value"] == "123"


def test_profile_append_and_show(data_dir, capsys):
    code, out, _ = _run(capsys, "profile", "append", "karpathy",
                        "--date", "2026-08-26", "--source", "12 条推文", "--body", "观察正文")
    assert code == 0
    assert out.startswith("OK ")
    _, shown, _ = _run(capsys, "profile", "show", "karpathy")
    assert "观察正文" in shown
    assert "依据：12 条推文" in shown


def test_profile_show_missing_is_empty(data_dir, capsys):
    code, out, _ = _run(capsys, "profile", "show", "nobody")
    assert (code, out) == (0, "EMPTY")


def test_profile_summary_replaces(data_dir, capsys):
    _run(capsys, "profile", "summary", "k", "--text", "第一版", "--updated-at", "2026-08-26")
    _run(capsys, "profile", "summary", "k", "--text", "第二版", "--updated-at", "2026-08-27")
    _, out, _ = _run(capsys, "profile", "show", "k")
    assert "第二版" in out and "第一版" not in out


def test_init_writes_config(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "fresh-config.json"
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(cfg))
    target = tmp_path / "my-data"
    code, out, _ = _run(capsys, "init", str(target))
    assert code == 0
    assert str(target) in out
    assert json.loads(cfg.read_text(encoding="utf-8"))["DATA_DIR"] == str(target)


def test_data_dir_prints_configured_path(data_dir, capsys):
    code, out, _ = _run(capsys, "data-dir")
    assert (code, out) == (0, str(data_dir))


def test_bad_channel_ref_exits_1(data_dir, capsys):
    code, _, err = _run(capsys, "state", "get", "no-colon-here")
    assert code == 1
    assert "platform:handle" in err
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_cli.py -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'roster.__main__'`。

- [ ] **Step 3: 写最小实现**

`tools/roster/roster/__main__.py`：

```python
"""roster CLI —— 三个命令组，一组对应一份文件、对应一个消费者：

  roster registry ...   registry.json    manage-roster skill
  roster state ...      state.json       sync-* skill
  roster profile ...    profiles/*.md    认知层 skill

读跨组允许（registry list 要读 state 展示游标），写不允许。
"""
import argparse
import json
import sys
from datetime import date

from . import config, profiles, registry, state
from .urls import parse_channel_url


def _split_ref(ref: str) -> tuple[str, str]:
    if ":" not in ref:
        raise ValueError(f"渠道引用格式应为 platform:handle，收到：{ref}")
    platform, _, handle = ref.partition(":")
    if not platform or not handle:
        raise ValueError(f"渠道引用格式应为 platform:handle，收到：{ref}")
    return platform, handle


def _cmd_init(args) -> int:
    config.set_config("DATA_DIR", args.data_dir)
    print(f"OK {args.data_dir}")
    return 0


def _cmd_data_dir(args) -> int:
    print(config.get_data_dir())
    return 0


def _cmd_registry_add(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)
    creator_id, _ = registry.add_channel(reg, args.url, date.today().isoformat())
    registry.save(data_dir, reg)
    platform, handle = parse_channel_url(args.url)
    print(f"OK {creator_id} {platform}:{handle}")
    return 0


def _cmd_registry_remove(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)

    if ":" in args.ref:
        platform, handle = _split_ref(args.ref)
        registry.remove_channel(reg, platform, handle)
        registry.save(data_dir, reg)
        st = state.load(data_dir)
        state.drop_channel(st, platform, handle)
        state.save(data_dir, st)
        print(f"OK removed {platform}:{handle}")
        return 0

    creator = registry.remove_creator(reg, args.ref)
    registry.save(data_dir, reg)
    st = state.load(data_dir)
    for channel in creator["channels"]:
        state.drop_channel(st, channel["platform"], channel["handle"])
    state.save(data_dir, st)
    archived = profiles.archive(data_dir, creator["id"])
    suffix = f"profile archived at {archived}" if archived else "no profile"
    print(f"OK removed {creator['id']}, {suffix}")
    return 0


def _cmd_registry_rename(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)
    registry.rename_creator(reg, args.creator_id, args.display_name)
    registry.save(data_dir, reg)
    print("OK")
    return 0


def _cmd_registry_merge(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)
    registry.merge_creators(reg, args.id_a, args.id_b)
    registry.save(data_dir, reg)
    profiles.merge(data_dir, args.id_a, args.id_b, date.today().isoformat())
    print(f"OK merged {args.id_b} into {args.id_a}")
    return 0


def _cmd_registry_list(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)
    if not reg["creators"]:
        print("EMPTY")
        return 0

    st = state.load(data_dir)
    for creator in reg["creators"]:
        mark = "  [placeholder]" if creator["placeholder"] else ""
        print(f"{creator['id']}  {creator['display_name']}{mark}")
        for channel in creator["channels"]:
            key = f"{channel['platform']}:{channel['handle']}"
            entry = st["channels"].get(key) or {}
            cursor = entry.get("cursor")
            if cursor is None:
                shown = "(none)"
            elif cursor["type"] == "seen_urls":
                shown = f"{len(cursor['value'])} urls"
            else:
                shown = str(cursor["value"])
            err = entry.get("last_error")
            tail = f"  err={err}" if err else ""
            print(f"  {key}  cursor={shown}{tail}")
    return 0


def _cmd_registry_channels(args) -> int:
    reg = registry.load(config.get_data_dir())
    print(json.dumps(registry.channels_for_platform(reg, args.platform), ensure_ascii=False))
    return 0


def _cmd_state_get(args) -> int:
    platform, handle = _split_ref(args.ref)
    st = state.load(config.get_data_dir())
    print(json.dumps(state.get_cursor(st, platform, handle), ensure_ascii=False))
    return 0


def _cmd_state_set(args) -> int:
    platform, handle = _split_ref(args.ref)
    data_dir = config.get_data_dir()
    st = state.load(data_dir)
    state.set_cursor(st, platform, handle, args.type,
                     json.loads(args.value_json), args.run_time)
    state.save(data_dir, st)
    print("OK")
    return 0


def _cmd_state_fail(args) -> int:
    platform, handle = _split_ref(args.ref)
    data_dir = config.get_data_dir()
    st = state.load(data_dir)
    state.set_error(st, platform, handle, args.error, args.run_time)
    state.save(data_dir, st)
    print("OK")
    return 0


def _cmd_profile_append(args) -> int:
    data_dir = config.get_data_dir()
    profiles.append_observation(data_dir, args.creator_id, args.date, args.source, args.body)
    print(f"OK {profiles.profile_path(data_dir, args.creator_id)}")
    return 0


def _cmd_profile_summary(args) -> int:
    data_dir = config.get_data_dir()
    profiles.set_summary(data_dir, args.creator_id, args.text, args.updated_at)
    print(f"OK {profiles.profile_path(data_dir, args.creator_id)}")
    return 0


def _cmd_profile_show(args) -> int:
    text = profiles.read(config.get_data_dir(), args.creator_id)
    print(text.rstrip() if text else "EMPTY")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="roster")
    groups = parser.add_subparsers(dest="group", required=True)

    p_init = groups.add_parser("init", help="设置数据目录")
    p_init.add_argument("data_dir")
    p_init.set_defaults(func=_cmd_init)

    groups.add_parser("data-dir", help="打印数据目录").set_defaults(func=_cmd_data_dir)

    reg_sub = groups.add_parser("registry", help="人与渠道的定义").add_subparsers(
        dest="action", required=True)

    p = reg_sub.add_parser("add"); p.add_argument("url"); p.set_defaults(func=_cmd_registry_add)
    p = reg_sub.add_parser("remove"); p.add_argument("ref"); p.set_defaults(func=_cmd_registry_remove)
    p = reg_sub.add_parser("rename")
    p.add_argument("creator_id"); p.add_argument("display_name")
    p.set_defaults(func=_cmd_registry_rename)
    p = reg_sub.add_parser("merge")
    p.add_argument("id_a"); p.add_argument("id_b"); p.set_defaults(func=_cmd_registry_merge)
    p = reg_sub.add_parser("list"); p.set_defaults(func=_cmd_registry_list)
    p = reg_sub.add_parser("channels")
    p.add_argument("--platform", required=True); p.set_defaults(func=_cmd_registry_channels)

    state_sub = groups.add_parser("state", help="游标与失败态").add_subparsers(
        dest="action", required=True)

    p = state_sub.add_parser("get"); p.add_argument("ref"); p.set_defaults(func=_cmd_state_get)
    p = state_sub.add_parser("set")
    p.add_argument("ref")
    p.add_argument("--type", required=True)
    p.add_argument("--value-json", required=True, dest="value_json")
    p.add_argument("--run-time", required=True, dest="run_time")
    p.set_defaults(func=_cmd_state_set)
    p = state_sub.add_parser("fail")
    p.add_argument("ref")
    p.add_argument("--error", required=True)
    p.add_argument("--run-time", required=True, dest="run_time")
    p.set_defaults(func=_cmd_state_fail)

    prof_sub = groups.add_parser("profile", help="画像").add_subparsers(
        dest="action", required=True)

    p = prof_sub.add_parser("append")
    p.add_argument("creator_id")
    p.add_argument("--date", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--body", required=True)
    p.set_defaults(func=_cmd_profile_append)
    p = prof_sub.add_parser("summary")
    p.add_argument("creator_id")
    p.add_argument("--text", required=True)
    p.add_argument("--updated-at", required=True, dest="updated_at")
    p.set_defaults(func=_cmd_profile_summary)
    p = prof_sub.add_parser("show")
    p.add_argument("creator_id"); p.set_defaults(func=_cmd_profile_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/ -q
```

Expected: 全绿，`test_cli.py` 25 passed。

- [ ] **Step 5: 手动跑一次真 CLI**

```bash
cd tools/roster
HSKILL_ROSTER_CONFIG=/tmp/roster-smoke.json ./roster.sh init /tmp/roster-smoke-data
HSKILL_ROSTER_CONFIG=/tmp/roster-smoke.json ./roster.sh registry add https://x.com/karpathy
HSKILL_ROSTER_CONFIG=/tmp/roster-smoke.json ./roster.sh registry list
rm -rf /tmp/roster-smoke.json /tmp/roster-smoke-data
```

Expected: 依次输出 `OK /tmp/roster-smoke-data`、`OK karpathy x:karpathy`、两行 listing。这一步验证 `roster.sh` 的 dev 模式 venv 能建起来、`[project.scripts]` 入口正确——pytest 是直接 import 包的，绕过了这条路径。

- [ ] **Step 6: Commit**

```bash
git add tools/roster/roster/__main__.py tools/roster/tests/test_cli.py
git commit -m "feat(roster): CLI 三个命令组

registry / state / profile 各对应一份文件、一个消费者。读跨组允许，
写不允许。删人归档画像、连带清理 state。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: 旧 watchlist 的一次性迁移

**Files:**
- Create: `tools/roster/roster/migrate.py`
- Modify: `tools/roster/roster/__main__.py`（挂 `roster migrate` 子命令）
- Test: `tools/roster/tests/test_migrate.py`

**Interfaces:**
- Consumes: `registry`、`state`、`urls`
- Produces:
  - `migrate.from_watchlists(data_dir: Path, x_watchlist: list[dict] | None, yt_watchlist: list[dict] | None, today: str, run_time: str) -> dict` — 返回 `{"creators": <新增人数>, "channels": <新增渠道数>, "cursors": <迁移游标数>}`
  - CLI：`roster migrate [--from-xtimeline <path>] [--from-ytchannel <path>]` → `OK creators=N channels=M cursors=K`

旧格式：

| 来源 | 字段 | 去向 |
|---|---|---|
| sync-xtimeline `watchlist.json` | `{handle, profile_url, last_seen_tweet_id}` | creator（`placeholder: true`）+ channel `x:<handle>` + cursor `last_seen_id` |
| sync-ytchannel `watchlist.json` | `{handle, channel_url, seen_urls}` | creator（同上）+ channel `youtube:<handle>` + cursor `seen_urls` |

游标为 `None` 的条目**不写 state**——那表示从未成功抓取过，下次运行应当照常建基线。

迁移后每个 handle 各自成一个人，同一个人的 X 和 YouTube 需要用户跑 `roster registry merge` 合并。这一步无法自动化：判断"这两个 handle 是同一个人"正是 spec 第 1.2 节说的判断类信息。

**迁移是一次性的**：跑完之后不要再跑第二次。重复跑会因为渠道已存在而抛错并停在半路，所以实现里对"渠道已存在"做跳过处理，让重复执行是安全的（幂等）。

- [ ] **Step 1: 写失败的测试**

`tools/roster/tests/test_migrate.py`：

```python
import json

from roster import migrate, registry, state

TODAY = "2026-08-26"
RUN = "2026-08-26T09:14:00+08:00"

X_OLD = [
    {"handle": "karpathy", "profile_url": "https://x.com/karpathy",
     "last_seen_tweet_id": "1876543210987654321"},
    {"handle": "newbie", "profile_url": "https://x.com/newbie",
     "last_seen_tweet_id": None},
]
YT_OLD = [
    {"handle": "AndrejKarpathy", "channel_url": "https://youtube.com/@AndrejKarpathy",
     "seen_urls": ["https://youtu.be/a", "https://youtu.be/b"]},
    {"handle": "FreshChannel", "channel_url": "https://youtube.com/@FreshChannel",
     "seen_urls": None},
]


def test_migrate_counts(data_dir):
    result = migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    assert result == {"creators": 4, "channels": 4, "cursors": 2}


def test_migrate_creates_placeholder_creators(data_dir):
    migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    reg = registry.load(data_dir)
    assert len(reg["creators"]) == 4
    assert all(c["placeholder"] for c in reg["creators"])


def test_migrate_maps_x_cursor_to_last_seen_id(data_dir):
    migrate.from_watchlists(data_dir, X_OLD, None, TODAY, RUN)
    st = state.load(data_dir)
    assert state.get_cursor(st, "x", "karpathy") == {
        "type": "last_seen_id", "value": "1876543210987654321"
    }


def test_migrate_maps_yt_cursor_to_seen_urls(data_dir):
    migrate.from_watchlists(data_dir, None, YT_OLD, TODAY, RUN)
    st = state.load(data_dir)
    assert state.get_cursor(st, "youtube", "AndrejKarpathy") == {
        "type": "seen_urls", "value": ["https://youtu.be/a", "https://youtu.be/b"]
    }


def test_migrate_skips_null_cursors(data_dir):
    """游标为 None 表示从未成功抓过，下次运行应照常建基线。"""
    migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    st = state.load(data_dir)
    assert state.get_cursor(st, "x", "newbie") is None
    assert state.get_cursor(st, "youtube", "FreshChannel") is None


def test_migrate_does_not_guess_identity_across_platforms(data_dir):
    """karpathy 和 AndrejKarpathy 是同一个人，但迁移不猜——交给用户 merge。"""
    migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    reg = registry.load(data_dir)
    ids = {c["id"] for c in reg["creators"]}
    assert "karpathy" in ids and "andrejkarpathy" in ids


def test_migrate_is_idempotent(data_dir):
    migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    second = migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    assert second == {"creators": 0, "channels": 0, "cursors": 0}
    assert len(registry.load(data_dir)["creators"]) == 4


def test_migrate_with_both_none_is_noop(data_dir):
    assert migrate.from_watchlists(data_dir, None, None, TODAY, RUN) == {
        "creators": 0, "channels": 0, "cursors": 0
    }


def test_cli_migrate(data_dir, tmp_path, capsys):
    from roster.__main__ import main

    x_file = tmp_path / "x-watchlist.json"
    x_file.write_text(json.dumps(X_OLD), encoding="utf-8")
    yt_file = tmp_path / "yt-watchlist.json"
    yt_file.write_text(json.dumps(YT_OLD), encoding="utf-8")

    code = main(["migrate", "--from-xtimeline", str(x_file), "--from-ytchannel", str(yt_file)])
    out = capsys.readouterr().out.strip()
    assert code == 0
    assert out == "OK creators=4 channels=4 cursors=2"


def test_cli_migrate_missing_file_exits_1(data_dir, tmp_path, capsys):
    from roster.__main__ import main

    code = main(["migrate", "--from-xtimeline", str(tmp_path / "nope.json")])
    assert code == 1
    assert "nope.json" in capsys.readouterr().err
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd tools/roster && python3 -m pytest tests/test_migrate.py -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'roster.migrate'`。

- [ ] **Step 3: 写最小实现**

`tools/roster/roster/migrate.py`：

```python
"""把 sync-xtimeline / sync-ytchannel 各自的 watchlist.json 迁进名册。

一次性动作，但做成幂等的：已存在的渠道跳过，不抛错。重复执行不该把人卡在
半路。

不猜跨平台身份——karpathy 和 AndrejKarpathy 是同一个人这件事，是判断，
由用户跑 registry merge 决定。
"""
from pathlib import Path

from . import registry, state

_SOURCES = (
    # (旧字段名: url, 旧字段名: cursor, platform, cursor_type)
    ("profile_url", "last_seen_tweet_id", "x", "last_seen_id"),
    ("channel_url", "seen_urls", "youtube", "seen_urls"),
)


def from_watchlists(data_dir: Path, x_watchlist: list[dict] | None,
                    yt_watchlist: list[dict] | None,
                    today: str, run_time: str) -> dict:
    reg = registry.load(data_dir)
    st = state.load(data_dir)
    counts = {"creators": 0, "channels": 0, "cursors": 0}

    for entries, (url_field, cursor_field, platform, cursor_type) in zip(
            (x_watchlist, yt_watchlist), _SOURCES):
        for entry in entries or []:
            handle = entry["handle"]
            if registry.find_channel(reg, platform, handle) is not None:
                continue

            registry.add_channel(reg, entry[url_field], today)
            counts["creators"] += 1
            counts["channels"] += 1

            cursor_value = entry.get(cursor_field)
            if cursor_value is not None:
                state.set_cursor(st, platform, handle, cursor_type, cursor_value, run_time)
                counts["cursors"] += 1

    registry.save(data_dir, reg)
    state.save(data_dir, st)
    return counts
```

在 `tools/roster/roster/__main__.py` 里补上处理函数（放在 `_cmd_init` 之后）：

```python
def _cmd_migrate(args) -> int:
    from . import migrate

    def _read(path: str | None) -> list[dict] | None:
        if path is None:
            return None
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"找不到旧 watchlist：{path}")
        return json.loads(p.read_text(encoding="utf-8"))

    data_dir = config.get_data_dir()
    result = migrate.from_watchlists(
        data_dir,
        _read(args.from_xtimeline),
        _read(args.from_ytchannel),
        date.today().isoformat(),
        datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    print(f"OK creators={result['creators']} channels={result['channels']} "
          f"cursors={result['cursors']}")
    return 0
```

在 `__main__.py` 顶部补两个 import：

```python
from datetime import date, datetime
from pathlib import Path
```

（原来是 `from datetime import date`，改成上面这两行。）

在 `_build_parser()` 里 `p_init.set_defaults(...)` 之后挂上：

```python
    p_mig = groups.add_parser("migrate", help="从旧 watchlist.json 迁移（一次性，幂等）")
    p_mig.add_argument("--from-xtimeline", dest="from_xtimeline", default=None)
    p_mig.add_argument("--from-ytchannel", dest="from_ytchannel", default=None)
    p_mig.set_defaults(func=_cmd_migrate)
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd tools/roster && python3 -m pytest tests/ -q
```

Expected: 全绿。

- [ ] **Step 5: Commit**

```bash
git add tools/roster/roster/migrate.py tools/roster/roster/__main__.py tools/roster/tests/test_migrate.py
git commit -m "feat(roster): 旧 watchlist 迁移，幂等

游标为 None 的条目不写 state，下次运行照常建基线。不猜跨平台身份，
合并交给用户跑 registry merge。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 9: 把 roster 注册进 skills-index.json 并验证安装

**Files:**
- Modify: `skills-index.json`（`toolBundleMeta` 与 `tools[]`）
- Test: `tests/install.bats`

**Interfaces:**
- Consumes: Task 1 的 `tools/roster/tool.json`
- Produces: `hskill install --tool roster` 可用；`~/.local/bin/roster` 落地

`skills-index.json` 是 npm 打包与安装的唯一真值来源，不在里面的东西会被排除。

- [ ] **Step 1: 写失败的测试**

在 `tests/install.bats` 末尾追加：

```bash
@test "install --tool: roster lands a launcher and its package" {
  _install --tool roster --force
  [ -x "${MOCK_HOME}/.local/bin/roster" ]
  [ -f "${MOCK_HOME}/.hskill/tools/roster.json" ]
  [ -d "${MOCK_HOME}/.hskill/tools/roster/roster" ]
  [ -f "${MOCK_HOME}/.hskill/tools/roster/pyproject.toml" ]
}

@test "install --tool: roster does not declare DATA_DIR as an uninstall path" {
  # 画像不可重建，卸载 tool 绝不能把它带走
  run grep -c "DATA_DIR" tools/roster/tool.json
  [ "$status" -ne 0 ]
}
```

- [ ] **Step 2: 跑测试确认失败**

```bash
bats tests/install.bats -f roster
```

Expected: 第一个测试 FAIL（`roster` 不在索引里，装不上）；第二个应当已经通过。

- [ ] **Step 3: 注册到索引**

在 `skills-index.json` 的 `toolBundleMeta` 里给 `research-tools` 的描述补上 roster：

```json
"research-tools": "研究抓取后端（browser-fetch-mcp — clip-url/extract-url 共用的认证浏览器抓取 MCP server；roster — sync-* 共用的人与渠道名册）"
```

在 `tools[]` 数组末尾追加：

```json
    {
      "name": "roster",
      "path": "tools/roster",
      "bundle": "research-tools"
    }
```

- [ ] **Step 4: 跑测试确认通过**

```bash
bats tests/install.bats -f roster
npm test
```

Expected: 两个 roster 测试通过，全量测试全绿。

- [ ] **Step 5: Commit**

```bash
git add skills-index.json tests/install.bats
git commit -m "feat(roster): 注册进 skills-index.json

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: manage-roster skill

**Files:**
- Create: `skills/research/manage-roster/SKILL.md`, `skills/research/manage-roster/scripts/roster_locate.py`, `skills/research/manage-roster/tests/test_roster_locate.py`
- Modify: `skills-index.json`（`skills[]` 与 `bundleMeta.research`）

**Interfaces:**
- Consumes: `roster` CLI 的 `init` / `registry` / `migrate` 命令组
- Produces:
  - `roster_locate.find_roster() -> str`（找不到时抛 `FileNotFoundError`）
  - `python3 scripts/roster_locate.py` → `FOUND: <path>` / `NOT_FOUND: <error>`（exit 1）

`roster_locate.py` 与 `browser_fetch_mcp_locate.py` 同构：dev 模式从仓库 checkout 里找，装机模式找 `~/.local/bin/roster`。

**这个 skill 只调 `registry` 命令组**（外加一次性的 `init` / `migrate`）。它不碰 `state`、不碰 `profile`——那是抓取层和认知层的写入权。

- [ ] **Step 1: 写失败的测试**

`skills/research/manage-roster/tests/test_roster_locate.py`：

```python
"""roster_locate 的两种布局：仓库 checkout 内 / hskill 装机后。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import roster_locate


def test_finds_launcher_in_repo_checkout():
    """本测试就跑在 checkout 里，dev 路径必须命中真实文件。"""
    found = Path(roster_locate.find_roster())
    assert found.name == "roster.sh"
    assert found.exists()


def test_raises_when_nothing_found(monkeypatch, tmp_path):
    monkeypatch.setattr(roster_locate, "_dev_path", lambda: tmp_path / "nope.sh")
    monkeypatch.setattr(roster_locate.shutil, "which", lambda _: None)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    with pytest.raises(FileNotFoundError, match="roster"):
        roster_locate.find_roster()
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd skills/research/manage-roster && python3 -m pytest tests/ -q
```

Expected: FAIL，`ModuleNotFoundError: No module named 'roster_locate'`。

- [ ] **Step 3: 写实现**

`skills/research/manage-roster/scripts/roster_locate.py`：

```python
"""定位 roster launcher（跟 browser_fetch_mcp_locate.py 同款，独立副本）。

两种布局：
- Dev 模式：本 skill 跑在 harveyz-skill 的 checkout 里，
  tools/roster/roster.sh 在 scripts/ 上面四层。
- 装机模式：经 hskill install 装到 ~/.claude/skills 等处，roster 作为 tool
  单独安装，launcher 落在 ~/.local/bin/roster。
"""
import shutil
import sys
from pathlib import Path


def _dev_path() -> Path:
    return Path(__file__).resolve().parents[4] / "tools" / "roster" / "roster.sh"


def find_roster() -> str:
    dev = _dev_path()
    if dev.exists():
        return str(dev)

    on_path = shutil.which("roster")
    if on_path:
        return on_path

    installed = Path.home() / ".local" / "bin" / "roster"
    if installed.exists():
        return str(installed)

    raise FileNotFoundError(
        "roster launcher 未找到。请在 harveyz-skill 的 checkout 里运行本 skill，"
        "或运行 `hskill install --tool roster`。"
    )


def main():
    try:
        print(f"FOUND: {find_roster()}")
    except FileNotFoundError as e:
        print(f"NOT_FOUND: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

`skills/research/manage-roster/SKILL.md`：

````markdown
---
name: manage-roster
version: "0.1.0"
description: "Maintain the roster of watched creators and their channels — the shared watchlist behind sync-xtimeline and sync-ytchannel. Add a channel URL, merge two handles that turn out to be the same person, rename a placeholder, view the roster with cursor state. Trigger phrases: '/manage-roster add <url>', '/manage-roster list', '/manage-roster merge <a> <b>', '/manage-roster rename <id> <name>', '/manage-roster remove <id>', 'watch this X account', 'watch this YouTube channel', 'who am I following'. Does not fetch anything — running an incremental fetch is sync-xtimeline / sync-ytchannel; writing a creator's profile is the cognition layer."
user_invocable: true
---

# manage-roster

维护"关注了哪些人、每个人有哪些渠道"这份名册。抓取本身不归它管——`sync-xtimeline` 和 `sync-ytchannel` 从这份名册读渠道列表去抓。

**渠道必属于一个人。** 机构号、聚合频道也当人处理。`add` 会自动建一个占位人（名字先用 handle 顶着），之后用 `merge` 把"这俩 handle 其实是同一个人"合起来。

**这个 skill 只写 `registry.json`。** 游标归抓取层写，画像归认知层写，它一概不碰。

## 初始化（run first）

```bash
python3 scripts/roster_locate.py
```

若输出 `NOT_FOUND: <error>`（exit 1），向用户报告"roster tool 未安装：{error}"，流程终止。

若输出 `FOUND: <path>`，检查配置：

```bash
ls ~/.hskill/roster/config.json 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

**若 `NOT_FOUND`：**

1. 询问用户名册数据要存在哪个目录（`DATA_DIR`，必须由用户手动提供，不得猜测）。可建议默认值 `~/.hskill/roster`。提醒用户：这个目录里的画像文件是累积出来的、删了长不回来，值得跟笔记一样对待（`registry.json` 和 `state.json` 都可重建，画像不能）。
2. 运行 `<roster_path> init <DATA_DIR>`。

**若用户此前用过 sync-xtimeline / sync-ytchannel**，初始化后问一次是否迁移旧关注列表：

```bash
<roster_path> migrate \
  --from-xtimeline "$(python3 -c "import json,pathlib;print(pathlib.Path(json.loads((pathlib.Path.home()/'.hskill/sync-xtimeline/config.json').read_text())['DATA_DIR']).expanduser()/'watchlist.json')")" \
  --from-ytchannel "$(python3 -c "import json,pathlib;print(pathlib.Path(json.loads((pathlib.Path.home()/'.hskill/sync-ytchannel/config.json').read_text())['DATA_DIR']).expanduser()/'watchlist.json')")"
```

任一旧配置不存在就省掉对应的参数。迁移是幂等的，重复跑安全。迁移后告诉用户：每个 handle 现在各自是一个人，同一个人的 X 和 YouTube 需要用 `merge` 合并，并主动列出名字相近的候选对给用户确认——**不要自己替用户合并**。

## 用法

`<roster>` 指 `roster_locate.py` 输出的路径。

| 用户说 | 运行 | 报告 |
|---|---|---|
| `add <url>` | `<roster> registry add <url>` | `OK <id> <platform>:<handle>` → 告知已加入，并提示这是占位人、可用 `rename` 填正式名字 |
| `list` | `<roster> registry list` | 原样展示。`EMPTY` 表示还没关注任何人 |
| `merge <a> <b>` | `<roster> registry merge <a> <b>` | `OK merged b into a` → 告知 b 的 id 已进 aliases，旧引用仍可查到 |
| `rename <id> <name>` | `<roster> registry rename <id> <name>` | `OK` |
| `remove <id>` | `<roster> registry remove <id>` | 输出里带画像归档路径时，**必须把这个路径转告用户**——画像没被删，只是移走了 |
| `remove <platform>:<handle>` | `<roster> registry remove <platform>:<handle>` | `OK removed ...`。人还留着 |

所有失败原样把 stderr 报给用户，不要自行改写或重试。

## 边界

不抓取、不翻译、不写画像、不进 Obsidian。跑一次增量抓取走 [sync-xtimeline](../sync-xtimeline/) 或 [sync-ytchannel](../sync-ytchannel/)。单条物料入库走 [clip-url](../clip-url/)，单个视频精读走 [learn-video](../learn-video/)。

设计文档：`docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md`。

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/roster_locate.py` | 定位 roster launcher（跟 `browser_fetch_mcp_locate.py` 同款，独立副本） |
````

- [ ] **Step 4: 跑测试确认通过**

```bash
cd skills/research/manage-roster && python3 -m pytest tests/ -q
```

Expected: `2 passed`。

- [ ] **Step 5: 注册到索引并校验 SKILL.md 格式**

在 `skills-index.json` 的 `skills[]` 里追加：

```json
    {
      "path": "research/manage-roster",
      "bundle": "research",
      "installScope": "project"
    }
```

并把 `bundleMeta.research` 的描述末尾补上 `+ manage-roster`。

```bash
npm test
```

Expected: 全绿。`npm test` 含所有 skill 的 SKILL.md 格式校验，会检查 frontmatter 字段、semver、name 与目录名一致。

- [ ] **Step 6: Commit**

```bash
git add skills/research/manage-roster skills-index.json
git commit -m "feat(manage-roster): 名册的人机入口

只写 registry.json。游标归抓取层，画像归认知层。remove 时必须把画像
归档路径转告用户。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 11: 改造 sync-ytchannel 为纯执行器

**Files:**
- Create: `skills/research/sync-ytchannel/scripts/roster_locate.py`（复制自 Task 10，改一处路径层数说明）, `skills/research/sync-ytchannel/scripts/roster_client.py`
- Rename: `skills/research/sync-ytchannel/scripts/watchlist.py` → `scripts/cursor.py`（只保留 `compute_update`），`tests/test_watchlist.py` → `tests/test_cursor.py`
- Modify: `skills/research/sync-ytchannel/scripts/config.py`, `scripts/sync_channels.py`, `SKILL.md`, `tests/conftest.py`, `tests/test_sync_channels.py`
- Delete: 无（`digest.py` / `mcp_channel_client.py` / `browser_fetch_mcp_locate.py` 原样保留）

**Interfaces:**
- Consumes: `roster registry channels --platform youtube`、`roster state get/set/fail`、`roster data-dir`
- Produces:
  - `cursor.compute_update(seen_urls: list[str] | None, videos: list[dict]) -> tuple[str, dict | None]` — 签名从吃 `entry` 改成吃游标值本身
  - `roster_client.channels() -> list[dict]`、`get_cursor(handle) -> list[str] | None`、`set_cursor(handle, seen_urls, run_time) -> None`、`set_error(handle, error, run_time) -> None`、`data_dir() -> Path`

**行为契约不变**：`run` 无交互、输出 `EMPTY` 或 `WRITTEN: <path>`、**写盘成功才推进游标**。digest 落点从 `<DATA_DIR>/digests/` 改为 `<DATA_DIR>/digests/youtube/`（两个 skill 共用 DATA_DIR 后，同一天两份 digest 会撞文件名）。

- [ ] **Step 1: 写失败的测试**

`skills/research/sync-ytchannel/tests/test_cursor.py`（由 `test_watchlist.py` 改写而来——删掉所有 CRUD 测试，`compute_update` 的测试改成传游标值）：

```python
"""compute_update 是纯函数：吃「上次见过的 URL 列表」和「刚抓到的视频列表」，
吐「这次该报什么、该存什么」。不碰磁盘、不碰网络。

游标是 URL 集合而不是单个 last_seen id：X 的 snowflake id 按时间递增可以
比大小，YouTube 的 video id 不透明，只能判断「见过没有」。
"""
import cursor


def _video(url: str, title: str = "t") -> dict:
    return {"url": url, "title": title}


def test_no_videos_reports_nothing():
    assert cursor.compute_update(None, []) == ("none", None)


def test_first_fetch_establishes_baseline():
    """首次抓取记录全部但一条不报——否则会把整个历史片库倒进摘要。"""
    videos = [_video("https://a"), _video("https://b")]
    kind, data = cursor.compute_update(None, videos)
    assert kind == "baseline"
    assert data == {"count": 2, "seen_urls": ["https://a", "https://b"]}


def test_nothing_new_reports_none():
    assert cursor.compute_update(["https://a"], [_video("https://a")]) == ("none", None)


def test_new_video_is_reported():
    kind, data = cursor.compute_update(["https://a"], [_video("https://b"), _video("https://a")])
    assert kind == "new"
    assert data["videos"] == [_video("https://b")]
    assert data["seen_urls"] == ["https://b", "https://a"]


def test_reordered_grid_does_not_produce_false_positives():
    """频道页会置顶/重排，顺序变了不代表有新视频——集合判定不受影响。"""
    seen = ["https://a", "https://b"]
    assert cursor.compute_update(seen, [_video("https://b"), _video("https://a")]) == ("none", None)


def test_empty_seen_list_is_not_treated_as_first_fetch():
    """空列表（抓到过但一个视频都没有）和 None（从没抓过）语义不同。"""
    kind, data = cursor.compute_update([], [_video("https://a")])
    assert kind == "new"
    assert data["seen_urls"] == ["https://a"]
```

`skills/research/sync-ytchannel/tests/test_roster_client.py`：

```python
"""roster_client 把 roster CLI 的输出翻成 Python 值。用假的 launcher
（一个打印固定输出的 shell 脚本）驱动，不依赖真的装了 roster。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import roster_client


@pytest.fixture
def fake_roster(tmp_path, monkeypatch):
    """造一个假 launcher，把每次调用的参数记进 argv.log，按预设脚本回话。"""
    script = tmp_path / "fake-roster"
    script.write_text(
        '#!/usr/bin/env bash\n'
        'echo "$@" >> "$FAKE_ROSTER_LOG"\n'
        'cat "$FAKE_ROSTER_OUT"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setattr(roster_client, "_launcher", lambda: str(script))
    monkeypatch.setenv("FAKE_ROSTER_LOG", str(tmp_path / "argv.log"))
    monkeypatch.setenv("FAKE_ROSTER_OUT", str(tmp_path / "out.txt"))
    return tmp_path


def _reply(fake_roster, text: str) -> None:
    (fake_roster / "out.txt").write_text(text, encoding="utf-8")


def _argv(fake_roster) -> str:
    return (fake_roster / "argv.log").read_text(encoding="utf-8")


def test_channels_parses_json_and_asks_for_youtube(fake_roster):
    _reply(fake_roster, '[{"creator_id":"ak","platform":"youtube",'
                        '"handle":"AK","url":"https://youtube.com/@AK"}]\n')
    assert roster_client.channels() == [{
        "creator_id": "ak", "platform": "youtube",
        "handle": "AK", "url": "https://youtube.com/@AK",
    }]
    assert "registry channels --platform youtube" in _argv(fake_roster)


def test_channels_empty(fake_roster):
    _reply(fake_roster, "[]\n")
    assert roster_client.channels() == []


def test_get_cursor_null_means_never_fetched(fake_roster):
    _reply(fake_roster, "null\n")
    assert roster_client.get_cursor("AK") is None


def test_get_cursor_unwraps_seen_urls(fake_roster):
    _reply(fake_roster, '{"type":"seen_urls","value":["https://a"]}\n')
    assert roster_client.get_cursor("AK") == ["https://a"]


def test_set_cursor_sends_seen_urls_type(fake_roster):
    _reply(fake_roster, "OK\n")
    roster_client.set_cursor("AK", ["https://a"], "2026-08-26T09:00:00+08:00")
    argv = _argv(fake_roster)
    assert "state set youtube:AK" in argv
    assert "--type seen_urls" in argv


def test_set_error_sends_fail(fake_roster):
    _reply(fake_roster, "OK\n")
    roster_client.set_error("AK", "timed out", "2026-08-26T09:00:00+08:00")
    assert "state fail youtube:AK" in _argv(fake_roster)


def test_nonzero_exit_raises(fake_roster, tmp_path, monkeypatch):
    failing = tmp_path / "failing-roster"
    failing.write_text('#!/usr/bin/env bash\necho "boom" >&2\nexit 1\n', encoding="utf-8")
    failing.chmod(0o755)
    monkeypatch.setattr(roster_client, "_launcher", lambda: str(failing))
    with pytest.raises(RuntimeError, match="boom"):
        roster_client.channels()
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd skills/research/sync-ytchannel && python3 -m pytest tests/test_cursor.py tests/test_roster_client.py -q
```

Expected: FAIL，两个 `ModuleNotFoundError`（`cursor`、`roster_client`）。

- [ ] **Step 3: 写实现**

**3a.** 把 `scripts/watchlist.py` 重命名为 `scripts/cursor.py`，只保留 `compute_update` 并改签名；删除 `tests/test_watchlist.py`：

```bash
git mv skills/research/sync-ytchannel/scripts/watchlist.py skills/research/sync-ytchannel/scripts/cursor.py
git rm skills/research/sync-ytchannel/tests/test_watchlist.py
```

`scripts/cursor.py` 全文替换为：

```python
#!/usr/bin/env python3
"""sync-ytchannel 的增量判定，纯函数：不碰磁盘、不碰网络。关注列表现在归
roster 名册管（见 roster_client.py），这里只剩「拿游标和新抓的列表算差集」。

游标是 URL 集合而不是单个 last_seen id：X 的 snowflake tweet id 按时间
递增可以比大小，YouTube 的 video id 不透明，只能判断「见过没有」。
"""


def compute_update(seen_urls: list[str] | None, videos: list[dict]) -> tuple[str, dict | None]:
    """给定该频道已报告过的 URL 列表和刚抓到的视频（最新在前，
    fetch_channel_videos 的契约），决定本次报什么、存什么。

    seen_urls 为 None 只出现在首次成功抓取之前；那一次建立基线（全部记录、
    一条不报），而不是把整个历史片库倒进摘要。空列表跟 None 不同——那表示
    抓到过但当时一个视频都没有。
    """
    if not videos:
        return "none", None

    fetched_urls = [v["url"] for v in videos]
    if seen_urls is None:
        return "baseline", {"count": len(videos), "seen_urls": fetched_urls}

    seen_set = set(seen_urls)
    new = [v for v in videos if v["url"] not in seen_set]
    if not new:
        return "none", None
    return "new", {"videos": new, "seen_urls": [v["url"] for v in new] + seen_urls}
```

**3b.** 复制 locate 脚本：

```bash
cp skills/research/manage-roster/scripts/roster_locate.py \
   skills/research/sync-ytchannel/scripts/roster_locate.py
```

**3c.** `scripts/roster_client.py`：

```python
#!/usr/bin/env python3
"""sync-ytchannel 与 roster 名册之间的桥。

只调两个命令组：`registry channels`（读渠道列表）和 `state`（读写游标）。
**绝不调 `registry add/remove/merge/rename`**——registry.json 的写入权
归 manage-roster，这里只读。画像同理，归认知层。
"""
import json
import subprocess
from pathlib import Path

from roster_locate import find_roster

PLATFORM = "youtube"


def _launcher() -> str:
    return find_roster()


def _run(*args: str) -> str:
    result = subprocess.run(
        [_launcher(), *args], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"roster {' '.join(args)} 失败：{result.stderr.strip()}")
    return result.stdout.strip()


def data_dir() -> Path:
    return Path(_run("data-dir"))


def channels() -> list[dict]:
    return json.loads(_run("registry", "channels", "--platform", PLATFORM))


def get_cursor(handle: str) -> list[str] | None:
    cursor = json.loads(_run("state", "get", f"{PLATFORM}:{handle}"))
    return cursor["value"] if cursor else None


def set_cursor(handle: str, seen_urls: list[str], run_time: str) -> None:
    _run("state", "set", f"{PLATFORM}:{handle}",
         "--type", "seen_urls",
         "--value-json", json.dumps(seen_urls, ensure_ascii=False),
         "--run-time", run_time)


def set_error(handle: str, error: str, run_time: str) -> None:
    _run("state", "fail", f"{PLATFORM}:{handle}", "--error", error, "--run-time", run_time)
```

**3d.** `scripts/config.py` 全文替换（DATA_DIR 不再自己持有）：

```python
#!/usr/bin/env python3
"""sync-ytchannel 的数据目录。

名册化之后这个 skill 不再持有自己的 DATA_DIR——它和 sync-xtimeline 共用
roster 名册那一个，向 roster 要。保留这个模块只是为了让其余脚本的
import 不用改。旧的 ~/.hskill/sync-ytchannel/config.json 在迁移后作废，
但不自动删除。
"""
from pathlib import Path

from roster_client import data_dir as _roster_data_dir


def get_data_dir() -> Path:
    return _roster_data_dir()
```

**3e.** `scripts/sync_channels.py` 的三处改动：

把 import 段的 `import watchlist` 换成：

```python
import cursor as cursor_mod
import roster_client
```

`_collect` 的循环体改为（`entry["channel_url"]` 变成 `channel["url"]`，游标从 roster 取，失败写 roster）：

```python
async def _collect(chrome_profile: Optional[str]) -> tuple[dict, list[tuple[str, list[str]]]]:
    run_time = datetime.now(timezone.utc).isoformat()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}
    pending_cursors: list[tuple[str, list[str]]] = []

    for channel in roster_client.channels():
        handle = channel["handle"]
        try:
            videos = await fetch_channel_videos(channel["url"], chrome_profile)
            kind, data = cursor_mod.compute_update(roster_client.get_cursor(handle), videos)
            if kind == "none":
                continue
            if kind == "baseline":
                baselines[handle] = data["count"]
            elif kind == "new":
                new[handle] = data["videos"]
            pending_cursors.append((handle, data["seen_urls"]))
        except Exception as e:
            failures[handle] = str(e)
            roster_client.set_error(handle, str(e), run_time)
            continue

    report = {
        "run_time": run_time,
        "new": new,
        "baselines": baselines,
        "failures": failures,
    }
    return report, pending_cursors
```

`write_digest` 的落点加平台子目录：

```python
def write_digest(report: dict) -> Path:
    digests_dir = get_data_dir() / "digests" / "youtube"
    digests_dir.mkdir(parents=True, exist_ok=True)
    run_time = datetime.fromisoformat(report["run_time"])
    digest_path = digests_dir / f"{run_time.strftime('%Y%m%dT%H%M%S')}--digest.md"
    digest_path.write_text(digest.render_digest(report), encoding="utf-8")
    return digest_path
```

`main()` 里推进游标那两行：

```python
    digest_path = write_digest(report)
    for handle, seen_urls in pending_cursors:
        roster_client.set_cursor(handle, seen_urls, report["run_time"])
    print(f"WRITTEN: {digest_path}")
```

**写盘成功才推进游标**这个顺序不能动——digest 没落盘的话，它本该报告的视频要留到下次再报。

**3f.** `tests/conftest.py`：删掉整个 `isolated_data_dir` fixture 和 `HSKILL_SYNC_YTCHANNEL_CONFIG` 相关代码，只保留 `sys.path` 注入：

```python
"""sync-ytchannel 的测试隔离。名册化之后本 skill 不再持有自己的
DATA_DIR（改为向 roster 要），所以这里不再需要伪造配置文件——需要隔离
roster 的测试自己 monkeypatch roster_client。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
```

**3g.** `tests/test_config.py` 删除（它测的是已经不存在的配置持有逻辑）：

```bash
git rm skills/research/sync-ytchannel/tests/test_config.py
```

**3h.** `tests/test_sync_channels.py` 里所有对 `watchlist` 的 monkeypatch 改为对 `roster_client` 的：把 `watchlist.load_watchlist` 换成 `roster_client.channels`（返回 `[{"creator_id","platform","handle","url"}]`），`watchlist.set_seen_urls` 换成 `roster_client.set_cursor`，并给 `roster_client.get_cursor` 打桩返回对应的游标值。断言 digest 落在 `digests/youtube/` 下。

- [ ] **Step 4: 跑测试确认通过**

```bash
cd skills/research/sync-ytchannel && python3 -m pytest tests/ -q
```

Expected: 全绿。若 `test_sync_channels.py` 因为 3h 改得不完整而红，按报错逐个补桩——**不要为了让它绿而放宽断言**。

- [ ] **Step 5: 改 SKILL.md**

- 删掉「用法」下的 `add / remove / list` 整节，四个子命令的列表改成两条：`/sync-ytchannel run`、（无）。
- 在开头加一句：「关注哪些频道由 [manage-roster](../manage-roster/) 维护；本 skill 只负责跑一次增量抓取。」
- 「初始化」一节改为：先跑 `python3 scripts/roster_locate.py`，`NOT_FOUND` 则报告并终止；不再有自己的 `config.json` 初始化流程。
- 「边界」一节里「跟 sync-xtimeline 是同一套架构的两个独立实例，互不共享数据」这句已经不成立——改成「跟 sync-xtimeline 共用同一份 roster 名册和同一个数据目录，digest 各落各的平台子目录」。
- 「参考文件」表：`watchlist.py` 那行换成 `cursor.py`（纯函数增量判定）与 `roster_client.py`（读名册、读写游标），补 `roster_locate.py` 一行。
- frontmatter `version` 从 `"0.1.0"` 提到 `"0.2.0"`（子命令删减是破坏性变更）。
- description 里删掉 `'/sync-ytchannel add <channel_url>'`、`'/sync-ytchannel list'`、`'/sync-ytchannel remove <handle>'` 三个触发短语，补一句 `Adding or removing a watched channel is manage-roster, not this skill.`

- [ ] **Step 6: 全量测试并提交**

```bash
npm test
```

Expected: 全绿。

```bash
git add skills/research/sync-ytchannel
git commit -m "refactor(sync-ytchannel): 退化为纯执行器，关注列表交给 roster

watchlist.py 拆成 cursor.py（纯函数增量判定）与 roster_client.py
（读名册、读写游标）。add/remove/list 迁到 manage-roster。digest 落
digests/youtube/，避免与 sync-xtimeline 共用 DATA_DIR 后撞名。

写盘成功才推进游标的顺序不变。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 12: 改造 sync-xtimeline 为纯执行器

**Files:**
- Create: `skills/research/sync-xtimeline/scripts/roster_locate.py`, `scripts/roster_client.py`
- Rename: `scripts/watchlist.py` → `scripts/cursor.py`，`tests/test_watchlist.py` → `tests/test_cursor.py`
- Modify: `scripts/config.py`, `scripts/fetch_new_tweets.py`, `scripts/render_digest.py`, `SKILL.md`, `tests/conftest.py`, `tests/test_fetch_new_tweets.py`, `tests/test_render_digest.py`
- Delete: `tests/test_config.py`

**Interfaces:**
- Consumes: `roster registry channels --platform x`、`roster state get/set/fail`、`roster data-dir`
- Produces:
  - `cursor.compute_update(last_seen_tweet_id: str | None, tweets: list[dict]) -> tuple[str, dict | None]`
  - `roster_client.channels() / get_cursor(handle) / set_cursor(handle, tweet_id, run_time) / set_error(handle, error, run_time) / data_dir()`，`PLATFORM = "x"`

结构与 Task 11 完全平行，四处不同：平台是 `x`；游标类型是 `last_seen_id`（值是字符串）；`fetch_new_tweets.py` 是**抓完就推进游标**（不像 YT 那样等 digest 落盘）——这个既有行为**保持不变**，本次不改；digest 落 `digests/x/`。

`tweets/<handle>.json` 归档路径不变（`archive_tweets.py` / `render_view.py` 不用改，它们只用 `get_data_dir()`，而 `get_data_dir()` 现在指向共享目录）。

- [ ] **Step 1: 写失败的测试**

`skills/research/sync-xtimeline/tests/test_cursor.py`（从 `test_watchlist.py` 改写，删掉 CRUD 测试）：

```python
"""compute_update 是纯函数：吃「上次见过的 tweet id」和「刚抓到的推文」，
吐「这次该报什么、游标推到哪」。不碰磁盘、不碰网络。

游标能用单个 id 是因为 X 的 snowflake tweet id 按时间单调递增，可以比大小。
YouTube 那边的 video id 不透明，所以那边用的是 URL 集合。
"""
import cursor


def _tweet(tweet_id: str) -> dict:
    return {"tweet_id": tweet_id, "text": "t"}


def test_no_tweets_reports_nothing():
    assert cursor.compute_update(None, []) == ("none", None)


def test_first_fetch_establishes_baseline():
    tweets = [_tweet("300"), _tweet("200")]
    kind, data = cursor.compute_update(None, tweets)
    assert kind == "baseline"
    assert data == {"count": 2, "last_seen_tweet_id": "300"}


def test_nothing_newer_reports_none():
    assert cursor.compute_update("300", [_tweet("300"), _tweet("200")]) == ("none", None)


def test_newer_tweets_are_reported():
    kind, data = cursor.compute_update("200", [_tweet("400"), _tweet("300"), _tweet("200")])
    assert kind == "new"
    assert [t["tweet_id"] for t in data["tweets"]] == ["400", "300"]
    assert data["last_seen_tweet_id"] == "400"


def test_ids_compare_numerically_not_lexically():
    """snowflake id 位数会变，字符串比较会把 "9" 判成大于 "10"。"""
    kind, data = cursor.compute_update("9", [_tweet("10")])
    assert kind == "new"
    assert data["last_seen_tweet_id"] == "10"
```

`skills/research/sync-xtimeline/tests/test_roster_client.py`：与 Task 11 的同名文件结构相同，`fake_roster` fixture 逐字照抄，断言换成 X 侧：

```python
def test_channels_asks_for_x(fake_roster):
    _reply(fake_roster, '[{"creator_id":"k","platform":"x",'
                        '"handle":"karpathy","url":"https://x.com/karpathy"}]\n')
    assert roster_client.channels()[0]["handle"] == "karpathy"
    assert "registry channels --platform x" in _argv(fake_roster)


def test_get_cursor_unwraps_last_seen_id(fake_roster):
    _reply(fake_roster, '{"type":"last_seen_id","value":"123"}\n')
    assert roster_client.get_cursor("karpathy") == "123"


def test_get_cursor_null_means_never_fetched(fake_roster):
    _reply(fake_roster, "null\n")
    assert roster_client.get_cursor("karpathy") is None


def test_set_cursor_sends_last_seen_id_type(fake_roster):
    _reply(fake_roster, "OK\n")
    roster_client.set_cursor("karpathy", "123", "2026-08-26T09:00:00+08:00")
    argv = _argv(fake_roster)
    assert "state set x:karpathy" in argv
    assert "--type last_seen_id" in argv


def test_set_error_sends_fail(fake_roster):
    _reply(fake_roster, "OK\n")
    roster_client.set_error("karpathy", "timed out", "2026-08-26T09:00:00+08:00")
    assert "state fail x:karpathy" in _argv(fake_roster)
```

（文件开头的 import 段、`fake_roster` / `_reply` / `_argv` 三个 helper 与 Task 11 的 `test_roster_client.py` 完全一致，逐字复制过来。）

- [ ] **Step 2: 跑测试确认失败**

```bash
cd skills/research/sync-xtimeline && python3 -m pytest tests/test_cursor.py tests/test_roster_client.py -q
```

Expected: FAIL，两个 `ModuleNotFoundError`。

- [ ] **Step 3: 写实现**

**3a.** 重命名并改写 `cursor.py`：

```bash
git mv skills/research/sync-xtimeline/scripts/watchlist.py skills/research/sync-xtimeline/scripts/cursor.py
git rm skills/research/sync-xtimeline/tests/test_watchlist.py skills/research/sync-xtimeline/tests/test_config.py
```

`scripts/cursor.py` 全文替换为：

```python
#!/usr/bin/env python3
"""sync-xtimeline 的增量判定，纯函数：不碰磁盘、不碰网络。关注列表现在归
roster 名册管（见 roster_client.py），这里只剩「拿游标和新抓的推文算差集」。

游标能用单个 id，是因为 X 的 snowflake tweet id 按时间单调递增可以比大小。
YouTube 的 video id 不透明，那边用的是 URL 集合。
"""


def compute_update(last_seen_tweet_id: str | None,
                   tweets: list[dict]) -> tuple[str, dict | None]:
    """给定该账号的游标和刚抓到的推文（最新在前，fetch_user_timeline 的
    契约），决定本次报什么、游标推到哪。

    游标为 None 只出现在首次成功抓取之前；那一次建立基线（记下最新 id、
    一条不报），而不是把整条历史时间线倒进摘要。
    """
    if not tweets:
        return "none", None
    if last_seen_tweet_id is None:
        return "baseline", {"count": len(tweets), "last_seen_tweet_id": tweets[0]["tweet_id"]}

    last_seen = int(last_seen_tweet_id)
    newer = [t for t in tweets if int(t["tweet_id"]) > last_seen]
    if not newer:
        return "none", None
    return "new", {"tweets": newer, "last_seen_tweet_id": newer[0]["tweet_id"]}
```

**3b.** 复制 locate 脚本：

```bash
cp skills/research/manage-roster/scripts/roster_locate.py \
   skills/research/sync-xtimeline/scripts/roster_locate.py
```

**3c.** `scripts/roster_client.py`：与 Task 11 的同名文件逐字相同，只改三处——模块 docstring 里的 skill 名、`PLATFORM = "x"`、以及游标读写：

```python
#!/usr/bin/env python3
"""sync-xtimeline 与 roster 名册之间的桥。

只调两个命令组：`registry channels`（读渠道列表）和 `state`（读写游标）。
**绝不调 `registry add/remove/merge/rename`**——registry.json 的写入权
归 manage-roster，这里只读。画像同理，归认知层。
"""
import json
import subprocess
from pathlib import Path

from roster_locate import find_roster

PLATFORM = "x"


def _launcher() -> str:
    return find_roster()


def _run(*args: str) -> str:
    result = subprocess.run([_launcher(), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"roster {' '.join(args)} 失败：{result.stderr.strip()}")
    return result.stdout.strip()


def data_dir() -> Path:
    return Path(_run("data-dir"))


def channels() -> list[dict]:
    return json.loads(_run("registry", "channels", "--platform", PLATFORM))


def get_cursor(handle: str) -> str | None:
    cursor = json.loads(_run("state", "get", f"{PLATFORM}:{handle}"))
    return cursor["value"] if cursor else None


def set_cursor(handle: str, tweet_id: str, run_time: str) -> None:
    _run("state", "set", f"{PLATFORM}:{handle}",
         "--type", "last_seen_id",
         "--value-json", json.dumps(tweet_id),
         "--run-time", run_time)


def set_error(handle: str, error: str, run_time: str) -> None:
    _run("state", "fail", f"{PLATFORM}:{handle}", "--error", error, "--run-time", run_time)
```

**3d.** `scripts/config.py` 全文替换：

```python
#!/usr/bin/env python3
"""sync-xtimeline 的数据目录。

名册化之后这个 skill 不再持有自己的 DATA_DIR——它和 sync-ytchannel 共用
roster 名册那一个，向 roster 要。保留这个模块只是为了让 archive_tweets.py
和 render_view.py 的 import 不用改。旧的
~/.hskill/sync-xtimeline/config.json 在迁移后作废，但不自动删除。
"""
from pathlib import Path

from roster_client import data_dir as _roster_data_dir


def get_data_dir() -> Path:
    return _roster_data_dir()
```

注意原来的 `config.py` 有一个 import 时固化的 `CONFIG_PATH` 常量，`tests/conftest.py` 里 monkeypatch 了它——这两处一起消失。

**3e.** `scripts/fetch_new_tweets.py`：`import watchlist` 换成 `import cursor as cursor_mod` 与 `import roster_client`，`run()` 的循环体改为：

```python
async def run(chrome_profile: Optional[str]) -> dict:
    run_time = datetime.now(timezone.utc).isoformat()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}

    for channel in roster_client.channels():
        handle = channel["handle"]
        try:
            tweets = await fetch_timeline(_timeline_url(channel["url"]), chrome_profile)
            kind, data = cursor_mod.compute_update(roster_client.get_cursor(handle), tweets)
            if kind == "none":
                continue
            if kind == "baseline":
                baselines[handle] = data["count"]
            elif kind == "new":
                new[handle] = data["tweets"]
            roster_client.set_cursor(handle, data["last_seen_tweet_id"], run_time)
        except Exception as e:
            failures[handle] = str(e)
            roster_client.set_error(handle, str(e), run_time)
            continue

    return {
        "run_time": run_time,
        "new": new,
        "baselines": baselines,
        "failures": failures,
    }
```

**3f.** `scripts/render_digest.py`：digest 落点加平台子目录。找到写 `DATA_DIR/digests` 的那处，改为 `get_data_dir() / "digests" / "x"`。

**3g.** `tests/conftest.py` 全文替换：

```python
"""sync-xtimeline 的测试隔离。名册化之后本 skill 不再持有自己的 DATA_DIR
（改为向 roster 要），所以不再需要伪造配置文件——需要隔离的测试自己
monkeypatch roster_client。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
```

**3h.** `tests/test_fetch_new_tweets.py`：把对 `watchlist` 的 monkeypatch 改成对 `roster_client` 的（`channels` 返回渠道字典列表、`get_cursor` 返回游标字符串或 `None`、`set_cursor` / `set_error` 记调用）。

**3i.** `tests/test_render_digest.py` 与 `tests/test_archive_tweets.py` / `tests/test_render_view.py`：这三个原先依赖 conftest 的 `isolated_sync_xtimeline_data_dir` fixture 提供 `DATA_DIR`。改为在各自文件里 monkeypatch `config.get_data_dir` 返回 `tmp_path`。断言路径里 digest 改成 `digests/x/`。

- [ ] **Step 4: 跑测试确认通过**

```bash
cd skills/research/sync-xtimeline && python3 -m pytest tests/ -q
```

Expected: 全绿。

- [ ] **Step 5: 改 SKILL.md**

与 Task 11 的 Step 5 相同的六处改动，另加两处 X 特有的：

- 「用法」的五个子命令删到两个：`/sync-xtimeline run`、`/sync-xtimeline view`。
- `run` 流程第 2 步里描述 `fetch_new_tweets.py` 输出的那段保持原样（report 结构没变）。
- frontmatter `version` 从 `"0.2.0"` 提到 `"0.3.0"`。
- description 删掉 add/list/remove 三个触发短语，补 `Adding or removing a watched account is manage-roster, not this skill.`
- 「边界」里补一句：跟 sync-ytchannel 共用同一份 roster 名册和数据目录，digest 各落各的平台子目录。

- [ ] **Step 6: 全量测试并提交**

```bash
npm test
```

```bash
git add skills/research/sync-xtimeline
git commit -m "refactor(sync-xtimeline): 退化为纯执行器，关注列表交给 roster

watchlist.py 拆成 cursor.py 与 roster_client.py。add/remove/list 迁到
manage-roster。digest 落 digests/x/。抓完即推进游标的既有顺序不变。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 13: 端到端手工验收与收尾

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: 全部前序任务
- Produces: 可合并的分支

自动化测试全都用假 launcher / 假 MCP 打桩，**没有任何一条真的从 roster 走到平台再回来**。这一步是唯一的端到端证据。

- [ ] **Step 1: 全量自动化测试**

```bash
npm test
```

Expected: 全绿。特别确认输出里出现 `pytest: tools/roster`、`pytest: skills/research/manage-roster`、`pytest: skills/research/sync-xtimeline`、`pytest: skills/research/sync-ytchannel` 四行真实计数——Task 0 修的就是这个，如果这里还是静默通过，说明 Task 0 没生效。

- [ ] **Step 2: 在隔离目录里跑一次真流程**

```bash
export HSKILL_ROSTER_CONFIG=/tmp/roster-e2e.json
R=tools/roster/roster.sh

$R init /tmp/roster-e2e-data
$R registry add https://x.com/karpathy
$R registry add https://youtube.com/@AndrejKarpathy
$R registry merge karpathy andrejkarpathy
$R registry rename karpathy "Andrej Karpathy"
$R registry list
```

Expected: `list` 输出一个人、两个渠道、两个 `cursor=(none)`，且不带 `[placeholder]` 标记。

- [ ] **Step 3: 真抓一次（需要 browser-fetch-mcp 已配好 chrome_profile）**

```bash
cd skills/research/sync-ytchannel && python3 scripts/roster_locate.py && python3 scripts/sync_channels.py
cd ../sync-xtimeline && python3 scripts/roster_locate.py && python3 scripts/fetch_new_tweets.py | head -c 400
```

Expected: YT 侧输出 `WRITTEN: /tmp/roster-e2e-data/digests/youtube/...`（首次是建基线）；X 侧输出一行 JSON。

若 X 侧所有账号都 `failures`，是 `chrome_profile` 没配——不是本次改动的问题，按 SKILL.md 里既有的提示处理。

- [ ] **Step 4: 验证游标真的落进了 state.json**

```bash
cat /tmp/roster-e2e-data/state.json
```

Expected: 两个渠道各有一条，`cursor.type` 分别是 `seen_urls` 和 `last_seen_id`，`last_error` 为 `null`。

- [ ] **Step 5: 验证删人不删画像**

```bash
$R profile append karpathy --date 2026-08-26 --source "端到端验收" --body "这段必须活下来"
$R registry remove karpathy
grep -r "这段必须活下来" /tmp/roster-e2e-data/profiles/archived/
```

Expected: grep 命中。这是整个设计那条主线的最终验收——不可重建的数据，一个日常删除操作动不了它。

- [ ] **Step 6: 清理并写 CHANGELOG**

```bash
unset HSKILL_ROSTER_CONFIG
rm -rf /tmp/roster-e2e.json /tmp/roster-e2e-data
```

在 `CHANGELOG.md` 顶部按既有格式加一条，说明：新增 `roster` tool 与 `manage-roster` skill；`sync-xtimeline` / `sync-ytchannel` 移除 `add`/`remove`/`list` 子命令（破坏性变更），关注列表迁到 `manage-roster`；升级路径是运行 `manage-roster` 的初始化流程完成迁移。

- [ ] **Step 7: Commit 并合并**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): roster 名册与两个 sync skill 的破坏性变更

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"

git checkout staging
git merge --no-ff feature/creator-channel-registry
```

---

## 计划自查

**Spec 覆盖对照：**

| Spec 小节 | 落在哪个任务 |
|---|---|
| 1.1 / 1.2 渠道可重建、画像不可重建 | Task 5（state 可重建）、Task 6（画像只追加不删）、Task 13 Step 5（验收） |
| 1.3 渠道必属于一个人 | Task 3 `add_channel` 自动建占位人；无孤儿渠道路径 |
| 1.4 主键与 handle 可变缺陷 | Task 2 `slugify`、Task 3 `_free_slug`；handle 可变的代价已在 spec 记录，本次不缓解 |
| 2.1 / 2.2 三层与写入权 | 计划开头的命令组表；Task 7 CLI 分组；Task 11/12 的 `roster_client` docstring 明写"绝不调 registry 写命令" |
| 3.1 registry.json | Task 3 / Task 4 |
| 3.2 state.json | Task 5 |
| 3.3 profiles/*.md | Task 6 |
| 4 独立 CLI tool，不合并进 browser-fetch-mcp | Task 1（`tool.json` 不含 DATA_DIR）、Task 9（安装测试断言这一点） |
| 5.1 manage-roster 五个子命令 | Task 7 CLI + Task 10 SKILL.md |
| 5.2 sync-* 退化为纯执行器 | Task 11 / Task 12 |
| 6 迁移 | Task 8 + Task 10 初始化流程里的迁移分支 |
| 7 边界（不调度、不做认知层实现） | 全程未出现；`profile` 命令组只提供写入原语，无任何调用方 |

**已知未覆盖：** spec 第 5.1 节说 `list` 要把 `placeholder` 标出来——Task 7 的 `_cmd_registry_list` 实现了，`test_registry_list_shows_placeholder_and_channel` 覆盖了。spec 提到"取关又重关会捡回旧画像，list 需要提示这种情况"——**本计划没实现这个提示**，因为 `remove` 已改为归档（画像不会留在原地被捡回），提示的前提不成立。这是 spec 与实现的一处偏离，故意的。
