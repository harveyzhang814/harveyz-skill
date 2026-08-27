# browser-fetch CLI 化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `tools/browser-fetch-mcp` 的 MCP 传输层拆掉，改成独立 CLI；三个消费者 skill 的 wrapper 改 subprocess 调用；三者补齐四平台补丁；extract-url 归档。

**Architecture:** 核心业务逻辑从 `server.py` 原样剥到 `core.py`（去掉 `@mcp.tool()` 装饰器，函数体不动），新增 `cli.py` 作为唯一入口——argparse 子命令 → 调 core → 一行 compact JSON 打到 stdout。skill 侧的六个 wrapper 把 `stdio_client` + `call_tool` 换成 `subprocess.run` + `json.loads`，**函数签名和返回值不变**，上游调用者零改动。

**Tech Stack:** Python 3.11+，hatchling 打包，playwright async API，pycookiecheat，pytest（`asyncio_mode = "auto"`）。skill 侧 wrapper 跑在 ambient system Python，tool 跑在自己的 venv。

**Spec:** `docs/superpowers/specs/2026-08-27-browser-fetch-cli-design.md`

## Global Constraints

- 包名 `browser_fetch_mcp` → `browser_fetch`；tool 名 `browser-fetch-mcp` → `browser-fetch`。
- `pyproject.toml` 删除 `mcp>=2.0.0` 依赖。保留 `playwright>=1.45`、`pycookiecheat>=0.7`，`requires-python = ">=3.11"`。
- 环境变量改名：`BROWSER_FETCH_MCP_DATA_DIR` → `BROWSER_FETCH_DATA_DIR`；`BROWSER_FETCH_MCP_CHROME_BASE` → `BROWSER_FETCH_CHROME_BASE`。
- 数据目录：`~/.hskill/browser-fetch-mcp/` → `~/.hskill/browser-fetch/`，由 `browser-fetch.sh` 做一次性幂等 `mv`。
- 退出码契约：`0` 成功（stdout 为一行 compact JSON）；`2` 调用方用法错（core 抛 `ValueError`）；`1` 运行时失败（其他异常）。失败时 stdout 必须为空，错误消息走 stderr。
- 六个顶层子命令的参数名与返回 dict 字段**逐字沿用**原 MCP 工具，不重命名、不合并。
- 内部继续用 `playwright.async_api`，不改回 sync。CLI 入口用 `asyncio.run()` 包一层。
- 六个 wrapper 的对外函数签名与返回值不变。
- 平台补丁只做四个：`claude` / `codex` / `hermes` / `pi`。`codex` 和 `hermes` 是诚实占位，必须写明"未在该平台验证过，subagent 派发语法待补"。
- 配置目录 `~/.hskill/url-extract/` 保持原地不动，不迁移、不改名。

## File Structure

| 文件 | 职责 |
|---|---|
| `tools/browser-fetch/browser_fetch/core.py` | 八个业务函数，零 MCP 依赖。从 `server.py` 剥出，函数体不动 |
| `tools/browser-fetch/browser_fetch/cli.py` | argparse 子命令 → core → JSON stdout；退出码分档 |
| `tools/browser-fetch/browser_fetch/{config,cookies,extractors,images,markdown,pacing,pacing_log,profiles}.py` | 原样迁移，仅改包名 import |
| `tools/browser-fetch/browser-fetch.sh` | venv 自愈安装 + 一次性数据目录迁移 |
| `tools/browser-fetch/{pyproject.toml,tool.json}` | 打包与 hskill tool 注册 |
| `skills/*/*/scripts/browser_fetch_locate.py` | 定位 CLI 可执行文件（三个 skill 各一份副本） |
| `skills/research/clip-url/platforms/SKILL.{claude,codex,hermes,pi}.md` | subagent 派发语法，按平台 |

---

### Task 1: 建包骨架并把 core 从 server.py 剥出

**Files:**
- Create: `tools/browser-fetch/browser_fetch/__init__.py`
- Create: `tools/browser-fetch/browser_fetch/core.py`
- Create: `tools/browser-fetch/browser_fetch/{config,cookies,extractors,images,markdown,pacing,pacing_log,profiles}.py`（从旧包复制，改 import）
- Create: `tools/browser-fetch/pyproject.toml`
- Create: `tools/browser-fetch/tests/`（从旧包复制十份纯函数测试）
- Test: `tools/browser-fetch/tests/test_core_import.py`

**Interfaces:**
- Produces: `browser_fetch.core` 暴露八个 async 函数，签名逐字沿用原 MCP 工具——
  `fetch_page(url: str, use_auth: bool = False, chrome_profile: Optional[str] = None) -> dict`
  `get_default_chrome_profile() -> dict`
  `set_default_chrome_profile(profile_path: str) -> dict`
  `list_chrome_profiles(host_keys: list[str], cookie_names: list[str]) -> dict`
  `fetch_article(url: str, output_dir: str, chrome_profile: Optional[str] = None, output_format: Literal["path","json"] = "path") -> dict`
  `fetch_user_timeline(profile_url: str, chrome_profile: Optional[str] = None, max_tweets: int = 20) -> dict`
  `fetch_channel_videos(channel_url: str, chrome_profile: Optional[str] = None, max_videos: int = 30) -> dict`
  `evaluate_js(url: str, js_code: str, chrome_profile: Optional[str] = None) -> dict`

- [ ] **Step 1: 复制包内容到新目录**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
mkdir -p tools/browser-fetch/browser_fetch tools/browser-fetch/tests
cp tools/browser-fetch-mcp/browser_fetch_mcp/{__init__,config,cookies,extractors,images,markdown,pacing,pacing_log,profiles}.py \
   tools/browser-fetch/browser_fetch/
cp tools/browser-fetch-mcp/browser_fetch_mcp/server.py tools/browser-fetch/browser_fetch/core.py
cp tools/browser-fetch-mcp/tests/test_{config,cookies,extractors,extractors_timeline,extractors_youtube,images,markdown,pacing,pacing_log,profiles}.py \
   tools/browser-fetch/tests/
```

- [ ] **Step 2: 全包改 import 与环境变量名**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
grep -rl 'browser_fetch_mcp\|BROWSER_FETCH_MCP_' browser_fetch tests \
  | xargs sed -i '' -e 's/browser_fetch_mcp/browser_fetch/g' \
                    -e 's/BROWSER_FETCH_MCP_DATA_DIR/BROWSER_FETCH_DATA_DIR/g' \
                    -e 's/BROWSER_FETCH_MCP_CHROME_BASE/BROWSER_FETCH_CHROME_BASE/g'
```

- [ ] **Step 3: 从 core.py 去掉 MCP**

编辑 `tools/browser-fetch/browser_fetch/core.py`：

1. 删掉 `from mcp.server import MCPServer` 这一行。
2. 删掉 `mcp = MCPServer("browser-fetch-mcp")` 这一行。
3. 删掉全部八处 `@mcp.tool()` 装饰器（函数体一行不动）。
4. 把文件末尾的 `main()` 和 `if __name__ == "__main__":` 整块删掉：

```python
def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

5. 把 `_data_dir()` 里的默认路径改掉：

```python
def _data_dir() -> Path:
    override = os.environ.get("BROWSER_FETCH_DATA_DIR")
    base = (
        Path(override)
        if override
        else Path.home() / ".hskill" / "browser-fetch" / "contexts"
    )
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    base.chmod(0o700)
    return base
```

6. 把模块 docstring 首句的 "MCP server exposing" 改成 "Core fetch functions exposing"。

- [ ] **Step 4: 写 pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "browser-fetch"
version = "0.2.0"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.45",
    "pycookiecheat>=0.7",
]

[project.scripts]
browser-fetch = "browser_fetch.cli:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.hatch.build.targets.wheel]
packages = ["browser_fetch"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 5: 写失败测试——core 可以脱离 mcp 被 import**

Create `tools/browser-fetch/tests/test_core_import.py`:

```python
"""core 必须完全不依赖 mcp——这是整次改造的立足点，用断言钉住它。"""
import re
import subprocess
import sys
from pathlib import Path

TOOLS = (
    "fetch_page", "fetch_article", "fetch_user_timeline", "fetch_channel_videos",
    "evaluate_js", "list_chrome_profiles",
    "get_default_chrome_profile", "set_default_chrome_profile",
)

PROBE = """
import sys
sys.modules["mcp"] = None          # 让 `import mcp` 直接失败
import browser_fetch.core as c
missing = [n for n in {tools!r} if not hasattr(c, n)]
print("MISSING:" + ",".join(missing))
"""


def test_core_imports_without_mcp_and_exposes_all_eight_functions():
    r = subprocess.run(
        [sys.executable, "-c", PROBE.format(tools=TOOLS)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "MISSING:"


def test_core_source_has_no_mcp_imports_or_decorators():
    """只查真正的依赖形式。docstring 里引用旧设计文档名
    （…browser-fetch-mcp-xcom-extraction-design.md）是允许的，
    用整词匹配避免误报。"""
    src = (Path(__file__).resolve().parents[1] / "browser_fetch" / "core.py").read_text("utf-8")
    assert not re.search(r"^\s*(import mcp|from mcp)\b", src, re.M)
    assert "@mcp.tool" not in src
    assert "MCPServer" not in src
```

- [ ] **Step 6: 建 venv 并跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
python3 -m venv .venv && .venv/bin/pip install -q -e ".[dev]" && .venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest tests/test_core_import.py -v
```

Expected: FAIL（`cli` 模块还不存在导致 `pip install -e` 报错，或 core 仍含 mcp 引用）

- [ ] **Step 7: 建最小 cli.py 占位让包能安装**

Create `tools/browser-fetch/browser_fetch/cli.py`:

```python
"""CLI entry point — 子命令在后续 task 中逐个接上。"""


def main():
    raise SystemExit("not implemented yet")
```

- [ ] **Step 8: 跑全部测试确认通过**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/pip install -q -e ".[dev]"
.venv/bin/python -m pytest tests/ -v
```

Expected: PASS（十份纯函数测试 + 两个 core import 测试全绿）

- [ ] **Step 9: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add tools/browser-fetch
git commit -m "feat(browser-fetch): 剥出无 MCP 依赖的 core 包"
```

---

### Task 2: cli.py 骨架与 profile 子命令组

先做不需要浏览器的三个子命令，把 argparse 骨架、JSON 输出、退出码分档一次钉死。

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/cli.py`
- Test: `tools/browser-fetch/tests/test_cli.py`

**Interfaces:**
- Consumes: `browser_fetch.core` 的八个函数（Task 1）
- Produces: `browser_fetch.cli.main(argv: Optional[list[str]] = None) -> int`；`browser_fetch.cli.build_parser() -> argparse.ArgumentParser`

- [ ] **Step 1: 写失败测试**

Create `tools/browser-fetch/tests/test_cli.py`:

```python
import json
import subprocess
import sys

CLI = [sys.executable, "-m", "browser_fetch.cli"]


def run(args, data_dir, stdin=None):
    return subprocess.run(
        CLI + args, capture_output=True, text=True, input=stdin,
        env={"PATH": "/usr/bin:/bin", "HOME": str(data_dir),
             "BROWSER_FETCH_DATA_DIR": str(data_dir)},
    )


def test_profile_get_returns_null_when_unset(tmp_path):
    r = run(["profile", "get"], tmp_path)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"profile_path": None}


def test_profile_set_then_get_round_trips(tmp_path):
    p = tmp_path / "SomeProfile"
    p.mkdir()
    r = run(["profile", "set", str(p)], tmp_path)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"ok": True}

    r = run(["profile", "get"], tmp_path)
    assert json.loads(r.stdout)["profile_path"] == str(p)


def test_profile_set_rejects_missing_path_with_exit_2(tmp_path):
    r = run(["profile", "set", str(tmp_path / "Nope")], tmp_path)
    assert r.returncode == 2
    assert r.stdout == ""
    assert "not a directory" in r.stderr


def test_profile_list_reports_profiles(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    (chrome_base / "Default").mkdir(parents=True)
    r = subprocess.run(
        CLI + ["profile", "list", "--host-key", ".x.com", "--cookie-name", "auth_token"],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
             "BROWSER_FETCH_DATA_DIR": str(tmp_path),
             "BROWSER_FETCH_CHROME_BASE": str(chrome_base)},
    )
    assert r.returncode == 0, r.stderr
    profiles = json.loads(r.stdout)["profiles"]
    assert len(profiles) == 1
    assert profiles[0]["looks_logged_in"] is False


def test_stdout_is_single_line_compact_json(tmp_path):
    r = run(["profile", "get"], tmp_path)
    assert r.stdout.count("\n") == 1
    assert ", " not in r.stdout  # compact separators
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/python -m pytest tests/test_cli.py -v
```

Expected: FAIL with "not implemented yet"

- [ ] **Step 3: 实现 cli.py 骨架 + profile 子命令**

Replace `tools/browser-fetch/browser_fetch/cli.py`:

```python
"""browser-fetch CLI —— 六个顶层子命令，stdout 一行 compact JSON。

退出码：0 成功；2 调用方用法错（core 抛 ValueError）；1 运行时失败。
失败时 stdout 保持空，消息走 stderr。
"""
import argparse
import asyncio
import json
import sys

from browser_fetch import core


def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="browser-fetch")
    sub = parser.add_subparsers(dest="command", required=True)

    p_profile = sub.add_parser("profile", help="持久化的默认 Chrome profile")
    psub = p_profile.add_subparsers(dest="profile_command", required=True)

    p_get = psub.add_parser("get")
    p_get.set_defaults(handler=lambda a: core.get_default_chrome_profile())

    p_set = psub.add_parser("set")
    p_set.add_argument("path")
    p_set.set_defaults(handler=lambda a: core.set_default_chrome_profile(a.path))

    p_list = psub.add_parser("list")
    p_list.add_argument("--host-key", action="append", default=[], dest="host_keys")
    p_list.add_argument("--cookie-name", action="append", default=[], dest="cookie_names")
    p_list.set_defaults(handler=lambda a: core.list_chrome_profiles(a.host_keys, a.cookie_names))

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(args.handler(args))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1
    _emit(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/python -m pytest tests/test_cli.py -v
```

Expected: PASS（5 passed）

- [ ] **Step 5: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add tools/browser-fetch
git commit -m "feat(browser-fetch): cli 骨架与 profile 子命令组"
```

---

### Task 3: page 与 eval 子命令

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/cli.py`
- Test: `tools/browser-fetch/tests/test_cli_page_eval.py`

**Interfaces:**
- Consumes: `browser_fetch.cli.build_parser`（Task 2）、`core.fetch_page`、`core.evaluate_js`
- Produces: 子命令 `page`、`eval`；`eval` 的 JS 源可来自 `--js-file <path>` 或 stdin

- [ ] **Step 1: 写失败测试**

Create `tools/browser-fetch/tests/test_cli_page_eval.py`:

```python
"""真网络、真浏览器，不 mock——与仓库既有测试风格一致。"""
import json
import subprocess
import sys

CLI = [sys.executable, "-m", "browser_fetch.cli"]


def run(args, tmp_path, stdin=None):
    return subprocess.run(
        CLI + args, capture_output=True, text=True, input=stdin,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
             "BROWSER_FETCH_DATA_DIR": str(tmp_path / "data")},
    )


def test_page_anonymous_fetch(tmp_path):
    r = run(["page", "https://example.com"], tmp_path)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["title"] == "Example Domain"
    assert payload["status"] == 200
    assert payload["cookies_injected"] == 0


def test_page_auth_without_profile_exits_2(tmp_path):
    r = run(["page", "https://example.com", "--auth"], tmp_path)
    assert r.returncode == 2
    assert r.stdout == ""
    assert "chrome_profile is required" in r.stderr


def test_page_auth_with_empty_profile_injects_nothing(tmp_path):
    empty = tmp_path / "EmptyProfile"
    empty.mkdir()
    r = run(["page", "https://example.com", "--auth", "--chrome-profile", str(empty)], tmp_path)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["cookies_injected"] == 0
    assert payload["status"] == 200


def test_eval_reads_js_from_file(tmp_path):
    js = tmp_path / "probe.js"
    js.write_text("() => document.title", encoding="utf-8")
    r = run(["eval", "https://example.com", "--js-file", str(js)], tmp_path)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["result"] == "Example Domain"


def test_eval_reads_js_from_stdin(tmp_path):
    r = run(["eval", "https://example.com", "--js-file", "-"], tmp_path,
            stdin="() => document.title")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["result"] == "Example Domain"


def test_eval_rejects_non_http_scheme_with_exit_2(tmp_path):
    js = tmp_path / "probe.js"
    js.write_text("() => 1", encoding="utf-8")
    r = run(["eval", "file:///etc/passwd", "--js-file", str(js)], tmp_path)
    assert r.returncode == 2
    assert r.stdout == ""
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/python -m pytest tests/test_cli_page_eval.py -v
```

Expected: FAIL with "invalid choice: 'page'"

- [ ] **Step 3: 加两个子命令**

在 `build_parser()` 的 `return parser` 之前插入：

```python
    p_page = sub.add_parser("page", help="抓原始 HTML")
    p_page.add_argument("url")
    p_page.add_argument("--auth", action="store_true")
    p_page.add_argument("--chrome-profile", default=None)
    p_page.set_defaults(handler=lambda a: core.fetch_page(a.url, a.auth, a.chrome_profile))

    p_eval = sub.add_parser("eval", help="在页面上执行 JS（调试用）")
    p_eval.add_argument("url")
    p_eval.add_argument("--js-file", required=True, help="JS 源文件路径，'-' 表示读 stdin")
    p_eval.add_argument("--chrome-profile", default=None)
    p_eval.set_defaults(handler=lambda a: core.evaluate_js(a.url, _read_js(a.js_file), a.chrome_profile))
```

在 `_emit` 下方加辅助函数：

```python
def _read_js(js_file: str) -> str:
    """JS 走文件或 stdin，不走 argv——自优化 subagent 迭代的是多行 JS，
    塞进命令行参数是引号地狱。"""
    if js_file == "-":
        return sys.stdin.read()
    with open(js_file, encoding="utf-8") as f:
        return f.read()
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/python -m pytest tests/test_cli_page_eval.py -v
```

Expected: PASS（6 passed）

- [ ] **Step 5: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add tools/browser-fetch
git commit -m "feat(browser-fetch): page 与 eval 子命令"
```

---

### Task 4: article / timeline / channel 子命令

**Files:**
- Modify: `tools/browser-fetch/browser_fetch/cli.py`
- Test: `tools/browser-fetch/tests/test_cli_fetch.py`

**Interfaces:**
- Consumes: `build_parser`（Task 2）、`core.fetch_article`、`core.fetch_user_timeline`、`core.fetch_channel_videos`
- Produces: 子命令 `article`、`timeline`、`channel`

- [ ] **Step 1: 写失败测试**

Create `tools/browser-fetch/tests/test_cli_fetch.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

CLI = [sys.executable, "-m", "browser_fetch.cli"]


def run(args, tmp_path):
    return subprocess.run(
        CLI + args, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
             "BROWSER_FETCH_DATA_DIR": str(tmp_path / "data")},
    )


def test_article_default_format_writes_file_and_returns_path(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    r = run(["article", "https://example.com", "--out", str(out)], tmp_path)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert "blocks" not in payload
    origin = Path(payload["origin_path"])
    assert origin.exists()
    assert origin.parent.name == "Origin"
    assert payload["title"] == "Example Domain"


def test_article_json_format_returns_blocks_and_writes_nothing(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    r = run(["article", "https://example.com", "--out", str(out), "--format", "json"], tmp_path)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert isinstance(payload["blocks"], list)
    assert "origin_path" not in payload
    assert not (out / "Origin").exists()


def test_article_xcom_without_profile_exits_2(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    r = run(["article", "https://x.com/someone/status/1", "--out", str(out)], tmp_path)
    assert r.returncode == 2
    assert r.stdout == ""


def test_timeline_without_profile_exits_2(tmp_path):
    r = run(["timeline", "https://x.com/someone"], tmp_path)
    assert r.returncode == 2
    assert r.stdout == ""


def test_channel_lists_videos(tmp_path):
    r = run(["channel", "https://www.youtube.com/@YouTube", "--max", "5"], tmp_path)
    assert r.returncode == 0, r.stderr
    videos = json.loads(r.stdout)["videos"]
    assert len(videos) <= 5
    assert all("title" in v and "url" in v for v in videos)
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/python -m pytest tests/test_cli_fetch.py -v
```

Expected: FAIL with "invalid choice: 'article'"

- [ ] **Step 3: 加三个子命令**

在 `build_parser()` 的 `return parser` 之前插入：

```python
    p_article = sub.add_parser("article", help="站点感知的结构化文章抽取")
    p_article.add_argument("url")
    p_article.add_argument("--out", required=True, dest="output_dir")
    p_article.add_argument("--chrome-profile", default=None)
    p_article.add_argument("--format", choices=("path", "json"), default="path",
                           dest="output_format")
    p_article.set_defaults(handler=lambda a: core.fetch_article(
        a.url, a.output_dir, a.chrome_profile, a.output_format))

    p_timeline = sub.add_parser("timeline", help="X.com 账号时间线批量列表")
    p_timeline.add_argument("profile_url")
    p_timeline.add_argument("--max", type=int, default=20, dest="max_tweets")
    p_timeline.add_argument("--chrome-profile", default=None)
    p_timeline.set_defaults(handler=lambda a: core.fetch_user_timeline(
        a.profile_url, a.chrome_profile, a.max_tweets))

    p_channel = sub.add_parser("channel", help="YouTube 频道最新上传列表")
    p_channel.add_argument("channel_url")
    p_channel.add_argument("--max", type=int, default=30, dest="max_videos")
    p_channel.add_argument("--chrome-profile", default=None)
    p_channel.set_defaults(handler=lambda a: core.fetch_channel_videos(
        a.channel_url, a.chrome_profile, a.max_videos))
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/python -m pytest tests/test_cli_fetch.py -v
```

Expected: PASS（5 passed）

- [ ] **Step 5: 跑全量确认没打破前面的**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add tools/browser-fetch
git commit -m "feat(browser-fetch): article/timeline/channel 子命令"
```

---

### Task 5: 启动器、tool 注册与数据目录迁移

**Files:**
- Create: `tools/browser-fetch/browser-fetch.sh`
- Create: `tools/browser-fetch/tool.json`
- Modify: `skills-index.json`（`tools[]` 与 `toolBundleMeta`）
- Modify: `package.json`（`files[]`）
- Test: `tools/browser-fetch/tests/test_data_dir_migration.py`

**Interfaces:**
- Produces: 可执行文件 `browser-fetch`（dev 模式从源码树、installed 模式从 `~/.hskill/tools/browser-fetch/venv`）；数据目录 `~/.hskill/browser-fetch/`

- [ ] **Step 1: 写失败测试——迁移必须幂等且不覆盖**

Create `tools/browser-fetch/tests/test_data_dir_migration.py`:

```python
"""数据目录迁移跑在 browser-fetch.sh 里（登录态实际落盘在 contexts/ 下，
迁移失败的表现是静默退回未登录，所以必须钉死三种情形）。"""
import subprocess
from pathlib import Path

SH = Path(__file__).resolve().parents[1] / "browser-fetch.sh"


def _run_migration_only(home: Path):
    """只跑脚本里的迁移函数，不进 venv 安装分支。"""
    return subprocess.run(
        ["bash", "-c", f'source "{SH}" --migrate-only'],
        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": str(home)},
    )


def test_migrates_old_dir_when_new_absent(tmp_path):
    old = tmp_path / ".hskill" / "browser-fetch-mcp" / "contexts" / "abc123"
    old.mkdir(parents=True)
    (old / "marker").write_text("x", encoding="utf-8")

    _run_migration_only(tmp_path)

    assert (tmp_path / ".hskill" / "browser-fetch" / "contexts" / "abc123" / "marker").exists()
    assert not (tmp_path / ".hskill" / "browser-fetch-mcp").exists()


def test_is_idempotent_when_old_absent(tmp_path):
    (tmp_path / ".hskill" / "browser-fetch" / "contexts").mkdir(parents=True)
    r = _run_migration_only(tmp_path)
    assert r.returncode == 0
    assert (tmp_path / ".hskill" / "browser-fetch" / "contexts").exists()


def test_does_not_clobber_existing_new_dir(tmp_path):
    old = tmp_path / ".hskill" / "browser-fetch-mcp" / "contexts"
    new = tmp_path / ".hskill" / "browser-fetch" / "contexts"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (new / "keep").write_text("keep", encoding="utf-8")

    _run_migration_only(tmp_path)

    assert (new / "keep").exists()
    assert old.exists()  # 新目录已存在时不动老目录，交给人处理
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/python -m pytest tests/test_data_dir_migration.py -v
```

Expected: FAIL（`browser-fetch.sh` 不存在）

- [ ] **Step 3: 写 browser-fetch.sh**

Create `tools/browser-fetch/browser-fetch.sh`（照抄 `tools/hub/hub.sh` 的 dev/installed 双模式惯例，加迁移函数）:

```bash
#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 一次性数据目录迁移：browser-fetch-mcp -> browser-fetch。
# contexts/ 下是 Playwright persistent context，站点登录态实际落盘在这里；
# 不迁移的表现是静默退回未登录，不报错。新目录已存在时不动老目录。
_migrate_data_dir() {
  local old="${HOME}/.hskill/browser-fetch-mcp"
  local new="${HOME}/.hskill/browser-fetch"
  if [ -d "${old}" ] && [ ! -d "${new}" ]; then
    mv "${old}" "${new}"
    echo "browser-fetch: 已迁移数据目录 ${old} -> ${new}" >&2
  fi
}

_migrate_data_dir

# 测试钩子：只跑迁移，不进安装分支
if [ "$1" = "--migrate-only" ]; then
  return 0 2>/dev/null || exit 0
fi

# Dev 模式：从源码树运行
if [ -d "${SCRIPT_DIR}/browser_fetch" ] && [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
  DEV_VENV="${SCRIPT_DIR}/.venv"
  if [ ! -x "${DEV_VENV}/bin/browser-fetch" ]; then
    python3 -m venv "${DEV_VENV}"
    "${DEV_VENV}/bin/pip" install -q -e "${SCRIPT_DIR}"
    "${DEV_VENV}/bin/python3" -m playwright install chromium
  fi
  exec "${DEV_VENV}/bin/browser-fetch" "$@"
fi

VENV_DIR="${HOME}/.hskill/tools/browser-fetch/venv"
INSTALL_DIR="${HOME}/.hskill/tools/browser-fetch"
HASH_FILE="${VENV_DIR}/.installed_hash"

_hash_source() {
  find "${INSTALL_DIR}" -type f \( -name "*.py" -o -name "*.toml" -o -name "*.json" \) \
    ! -path "*/__pycache__/*" ! -path "*/venv/*" \
    | sort | xargs sha256sum 2>/dev/null | sha256sum | awk '{print $1}'
}

CURRENT_HASH=$(_hash_source)

if [ ! -x "${VENV_DIR}/bin/browser-fetch" ] || [ "$(cat "${HASH_FILE}" 2>/dev/null)" != "${CURRENT_HASH}" ]; then
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install -q --upgrade "${INSTALL_DIR}"
  "${VENV_DIR}/bin/python3" -m playwright install chromium
  echo "${CURRENT_HASH}" > "${HASH_FILE}"
fi

exec "${VENV_DIR}/bin/browser-fetch" "$@"
```

- [ ] **Step 4: 写 tool.json**

Create `tools/browser-fetch/tool.json`:

```json
{
  "name": "browser-fetch",
  "version": "0.2.0",
  "description": "Shared CLI for authenticated headless browser fetches (Chrome cookie injection, site-aware article/timeline/channel extraction)",
  "extraPaths": ["browser_fetch", "pyproject.toml"],
  "uninstallPaths": ["~/.hskill/tools/browser-fetch/venv", "~/.hskill/tools/browser-fetch"],
  "configPaths": ["~/.hskill/browser-fetch"]
}
```

- [ ] **Step 5: 注册到 skills-index.json 与 package.json**

在 `skills-index.json` 的 `tools[]` 里，把 `browser-fetch-mcp` 那一项替换为（**保留** `browser-fetch-mcp` 旧项直到 Task 10 删旧目录，此处先新增）：

```json
{ "name": "browser-fetch", "path": "tools/browser-fetch", "bundle": "research-tools" }
```

在 `package.json` 的 `files[]` 里新增 `"tools/browser-fetch/"`（同样先不删旧项）。

- [ ] **Step 6: 跑测试确认通过**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
chmod +x browser-fetch.sh
.venv/bin/python -m pytest tests/test_data_dir_migration.py -v
```

Expected: PASS（3 passed）

- [ ] **Step 7: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add tools/browser-fetch skills-index.json package.json
git commit -m "feat(browser-fetch): 启动器、tool 注册与数据目录迁移"
```

---

### Task 6: 五份集成测试改成 CLI 驱动

**Files:**
- Create: `tools/browser-fetch/tests/test_evaluate_js.py`（从旧包迁移改写）
- Create: `tools/browser-fetch/tests/test_fetch_article.py`（同上）
- Create: `tools/browser-fetch/tests/test_fetch_user_timeline.py`（同上）
- Create: `tools/browser-fetch/tests/test_fetch_channel_videos.py`（同上）
- Create: `tools/browser-fetch/tests/conftest.py`

**Interfaces:**
- Consumes: 六个顶层子命令（Task 2-4）
- Produces: `conftest.py` 的 `run_cli` fixture，供四份集成测试共用

注：旧包的 `test_server.py` 只测 `fetch_page` 和 profile 三件事，已被 Task 2/3 的 `test_cli.py` + `test_cli_page_eval.py` 完整覆盖，**不迁移，直接丢弃**。

- [ ] **Step 1: 写共享 fixture**

Create `tools/browser-fetch/tests/conftest.py`:

```python
"""集成测试统一通过真实 CLI 进程驱动——与旧包用 stdio_client 驱动 MCP server
一一对应，断言内容不变，换的只是驱动方式。"""
import json
import subprocess
import sys

import pytest


@pytest.fixture
def run_cli(tmp_path):
    def _run(*args, stdin=None, extra_env=None):
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "BROWSER_FETCH_DATA_DIR": str(tmp_path / "data"),
        }
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, "-m", "browser_fetch.cli", *args],
            capture_output=True, text=True, input=stdin, env=env,
        )
        payload = json.loads(proc.stdout) if proc.returncode == 0 else None
        return proc, payload
    return _run
```

- [ ] **Step 2: 迁移四份集成测试**

对旧包 `tests/test_{evaluate_js,fetch_article,fetch_user_timeline,fetch_channel_videos}.py` 逐份改写。机械替换规则：

| 旧（MCP 驱动） | 新（CLI 驱动） |
|---|---|
| `async with stdio_client(...) as (read, write):` + `async with ClientSession(...)` + `await session.initialize()` | 删除整个嵌套块，函数改为同步 `def` |
| `result = await session.call_tool("fetch_article", {"url": u, "output_dir": d})` | `proc, payload = run_cli("article", u, "--out", d)` |
| `result = await session.call_tool("evaluate_js", {"url": u, "js_code": js})` | 把 js 写进 `tmp_path/"probe.js"`，再 `run_cli("eval", u, "--js-file", str(js_file))` |
| `result = await session.call_tool("fetch_user_timeline", {"profile_url": p, "max_tweets": n})` | `run_cli("timeline", p, "--max", str(n))` |
| `result = await session.call_tool("fetch_channel_videos", {"channel_url": c, "max_videos": n})` | `run_cli("channel", c, "--max", str(n))` |
| `result.is_error is True` | `proc.returncode == 2`（原 `ValueError` 场景）或 `== 1`（运行时失败场景） |
| `payload = result.structured_content or json.loads(result.content[0].text)` | 直接用 fixture 返回的 `payload` |
| `env={..., "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir)}` | fixture 已处理，删掉 |

**判断 `is_error` 该映射成 2 还是 1 的依据**：翻 `core.py` 里对应函数，抛的是 `ValueError` → 2，其他 → 1。已知的 `ValueError` 场景：`fetch_page` 的 `use_auth` 无 profile、`fetch_article`/`evaluate_js` 的 URL scheme 非 http/https、`fetch_article`/`fetch_user_timeline` 的 x.com 无 profile。

其余断言（字段名、字段值、blocks 结构、图片下载结果）**逐字保留**。

- [ ] **Step 3: 跑全量测试**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/browser-fetch
.venv/bin/python -m pytest tests/ -v
```

Expected: PASS（全部通过；网络相关用例耗时较长属正常）

- [ ] **Step 4: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add tools/browser-fetch/tests
git commit -m "test(browser-fetch): 集成测试改由 CLI 驱动"
```

---

### Task 7: clip-url 四个 wrapper 迁移

clip-url 排在三个 skill 的第一个，因为它的四个 wrapper 覆盖了全部八个业务函数，能最早暴露 CLI 接口面的问题。

**Files:**
- Create: `skills/research/clip-url/scripts/browser_fetch_locate.py`
- Create: `skills/research/clip-url/scripts/browser_fetch_cli.py`
- Delete: `skills/research/clip-url/scripts/browser_fetch_mcp_locate.py`
- Modify: `skills/research/clip-url/scripts/{mcp_fetch_client,mcp_debug_client,chrome_profile_config,detect_xcom_chrome_profile}.py`
- Modify: `skills/research/clip-url/tests/test_browser_fetch_mcp_locate.py` → 改名 `test_browser_fetch_locate.py`
- Modify: `skills/research/clip-url/tests/test_{mcp_fetch_client,mcp_debug_client,chrome_profile_config,detect_xcom_chrome_profile}.py`
- Modify: `skills/research/clip-url/SKILL.md`

**Interfaces:**
- Consumes: `browser-fetch` 可执行文件（Task 5）
- Produces: `browser_fetch_locate.find_browser_fetch() -> str`；`browser_fetch_cli.call(*args: str) -> dict`（Task 8/9 逐字复制这两个模块）；四个 wrapper 的公开函数签名与返回值**不变**——
  `mcp_fetch_client.fetch_and_report(url, chrome_profile=None) -> dict`（`origin_path` 为 `Path`）
  `mcp_fetch_client.fetch_and_save(url, chrome_profile=None) -> Path`
  `mcp_debug_client.call_fetch_page(url, use_auth=False, chrome_profile=None) -> dict`
  `mcp_debug_client.call_evaluate_js(url, js_code, chrome_profile=None) -> dict`

注：这四个模块名里的 `mcp_` 前缀**本次不改**——改名会波及 SKILL.md、references/ 里的 subagent prompt 模板和四份测试，与"改动关在 wrapper 内部"的约束冲突。模块 docstring 里注明前缀是历史遗留。

- [ ] **Step 1: 写 locate 模块的失败测试**

Rename `tests/test_browser_fetch_mcp_locate.py` → `tests/test_browser_fetch_locate.py`，内容改为：

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_fetch_locate  # noqa: E402


def test_finds_dev_launcher_in_repo_checkout():
    found = browser_fetch_locate.find_browser_fetch()
    assert Path(found).name == "browser-fetch.sh"
    assert Path(found).exists()


def test_raises_when_nothing_found(monkeypatch, tmp_path):
    monkeypatch.setattr(browser_fetch_locate, "_dev_path", lambda: tmp_path / "nope.sh")
    monkeypatch.setattr(browser_fetch_locate.shutil, "which", lambda _: None)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    with pytest.raises(FileNotFoundError, match="browser-fetch"):
        browser_fetch_locate.find_browser_fetch()
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/research/clip-url/tests/test_browser_fetch_locate.py -v
```

Expected: FAIL with "No module named 'browser_fetch_locate'"

- [ ] **Step 3: 写 locate 模块**

Create `skills/research/clip-url/scripts/browser_fetch_locate.py`（删掉旧的 `browser_fetch_mcp_locate.py`）:

```python
"""Locates the browser-fetch launcher for clip-url's client scripts.

Two supported layouts:
- Dev mode: this skill runs from inside a harveyz-skill git checkout, where
  tools/browser-fetch/browser-fetch.sh sits four directories above scripts/.
- Installed mode: this skill was installed via `hskill install` (to
  ~/.claude/skills, ~/.pi/agent/skills, etc.), and browser-fetch was
  separately installed as a tool — its launcher lands at
  ~/.local/bin/browser-fetch (see tools/browser-fetch/tool.json).
"""
import shutil
import sys
from pathlib import Path


def _dev_path() -> Path:
    return Path(__file__).resolve().parents[4] / "tools" / "browser-fetch" / "browser-fetch.sh"


def find_browser_fetch() -> str:
    dev_path = _dev_path()
    if dev_path.exists():
        return str(dev_path)

    on_path = shutil.which("browser-fetch")
    if on_path:
        return on_path

    installed_path = Path.home() / ".local" / "bin" / "browser-fetch"
    if installed_path.exists():
        return str(installed_path)

    raise FileNotFoundError(
        "browser-fetch launcher not found. Run clip-url from a harveyz-skill "
        "git checkout, or run `hskill install` and select the browser-fetch tool."
    )


def main():
    """CLI preflight check for SKILL.md: prints FOUND/NOT_FOUND instead of
    letting the FileNotFoundError surface as a raw traceback."""
    try:
        print(f"FOUND: {find_browser_fetch()}")
    except FileNotFoundError as e:
        print(f"NOT_FOUND: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试确认通过**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/research/clip-url/tests/test_browser_fetch_locate.py -v
```

Expected: PASS（2 passed）

- [ ] **Step 5: 写共享的 CLI 调用辅助模块**

Create `skills/research/clip-url/scripts/browser_fetch_cli.py`:

```python
"""四个 client 脚本共用的 browser-fetch CLI 调用层。

替代原先各自展开的 stdio_client + ClientSession 样板。CLI 退出码：
0 成功（stdout 一行 JSON）、2 调用方用法错、1 运行时失败——两种失败在
Python 侧统一抬成 RuntimeError，保持各 client 原有的异常契约不变。
"""
import json
import os
import subprocess

from browser_fetch_locate import find_browser_fetch

BROWSER_FETCH = find_browser_fetch()


def call(*args: str) -> dict:
    proc = subprocess.run(
        [BROWSER_FETCH, *args],
        capture_output=True, text=True, env=dict(os.environ),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"browser-fetch exited {proc.returncode}")
    return json.loads(proc.stdout)
```

- [ ] **Step 6: 改写四个 client 脚本**

`mcp_fetch_client.py` —— 删掉 `asyncio`/`mcp` 相关 import 和 `BROWSER_FETCH_MCP_SH`，把 `fetch_and_report` 改成同步：

```python
import sys
from pathlib import Path
from typing import Optional

import browser_fetch_cli
import vault_config


def fetch_and_report(url: str, chrome_profile: Optional[str] = None) -> dict:
    article_dir = vault_config.get_article_paths(url)["article_dir"]
    args = ["article", url, "--out", str(article_dir), "--format", "path"]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    payload = browser_fetch_cli.call(*args)
    payload["origin_path"] = Path(payload["origin_path"])
    return payload


def fetch_and_save(url: str, chrome_profile: Optional[str] = None) -> Path:
    return fetch_and_report(url, chrome_profile)["origin_path"]
```

`main()` 保留原有九行输出格式不变，但简化异常处理——不再有 `BaseExceptionGroup` 包裹问题：

```python
def main():
    if len(sys.argv) < 2:
        print("Usage: mcp_fetch_client.py <url> [chrome_profile]", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    chrome_profile = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    try:
        payload = fetch_and_report(url, chrome_profile)
    except Exception as e:
        # 只打裸消息，不加 "ERROR:" 前缀——subagent1-fetch-prompt.md 自己会加
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"ORIGIN_PATH: {payload['origin_path']}")
    print(f"TITLE: {payload['title']}")
    print(f"SITE: {payload['site']}")
    print(f"BLOCK_COUNT: {payload['block_count']}")
    print(f"CHAR_COUNT: {payload['char_count']}")
    print(f"CODE_BLOCK_COUNT: {payload['code_block_count']}")
    print(f"IMAGE_COUNT: {payload['image_count']}")
    print(f"CONTENT_THIN: {payload['content_thin']}")
    print(f"THIN_RETRY_USED: {payload['thin_retry_used']}")
```

`mcp_debug_client.py` —— 两个函数改成同步，JS 走临时文件：

```python
import tempfile
from pathlib import Path
from typing import Optional

import browser_fetch_cli


def call_fetch_page(url: str, use_auth: bool = False, chrome_profile: Optional[str] = None) -> dict:
    args = ["page", url]
    if use_auth:
        args.append("--auth")
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    return browser_fetch_cli.call(*args)


def call_evaluate_js(url: str, js_code: str, chrome_profile: Optional[str] = None) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js_code)
        js_path = f.name
    try:
        args = ["eval", url, "--js-file", js_path]
        if chrome_profile:
            args += ["--chrome-profile", chrome_profile]
        return browser_fetch_cli.call(*args)
    finally:
        Path(js_path).unlink(missing_ok=True)
```

`chrome_profile_config.py` —— `_get` / `_set` 改成同步，去掉 `asyncio.run`：

```python
def _get() -> str:
    payload = browser_fetch_cli.call("profile", "get")
    profile_path = payload["profile_path"]
    return f"CONFIGURED: {profile_path}" if profile_path else "NOT_CONFIGURED"


def _set(profile_path: str) -> str:
    browser_fetch_cli.call("profile", "set", profile_path)
    return "OK"
```

`main()` 里把 `asyncio.run(_get())` 改成 `_get()`、`asyncio.run(_set(...))` 改成 `_set(...)`，删掉 `asyncio` import。`_prompted_marker_path` / `get_prompted` / `mark_prompted` 三个本地函数一行不动。

`detect_xcom_chrome_profile.py` —— `_list_profiles` 改成同步：

```python
def _list_profiles() -> list[dict]:
    args = ["profile", "list"]
    for h in HOST_KEYS:
        args += ["--host-key", h]
    for c in COOKIE_NAMES:
        args += ["--cookie-name", c]
    return browser_fetch_cli.call(*args)["profiles"]
```

`main()` 里 `asyncio.run(_list_profiles())` 改成 `_list_profiles()`，删掉 `asyncio` import。表格渲染逻辑一行不动。

- [ ] **Step 7: 更新四份测试**

把 `test_mcp_fetch_client.py`、`test_mcp_debug_client.py`、`test_chrome_profile_config.py`、`test_detect_xcom_chrome_profile.py` 里：

- `asyncio.run(fetch_and_save(...))` → `fetch_and_save(...)`，删掉 `import asyncio`
- fixture 里 `monkeypatch.setenv("BROWSER_FETCH_MCP_DATA_DIR", ...)` → `"BROWSER_FETCH_DATA_DIR"`
- 断言内容全部保留

- [ ] **Step 8: 跑 clip-url 全部测试**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/research/clip-url/tests/ -v
```

Expected: PASS

- [ ] **Step 9: 更新 SKILL.md 里的引用**

`skills/research/clip-url/SKILL.md` 中：

- 第 10 行的 `[browser-fetch-mcp](../../../tools/browser-fetch-mcp/)` → `[browser-fetch](../../../tools/browser-fetch/)`，"抓取（MCP，经 fetch_article ...）" → "抓取（CLI，经 browser-fetch article ...）"
- 全文 `browser-fetch-mcp` → `browser-fetch`
- 脚本清单表里 `browser_fetch_mcp_locate.py` → `browser_fetch_locate.py`，并新增一行 `browser_fetch_cli.py`｜`browser-fetch CLI 调用层，四个 client 共用`
- preflight 步骤里的错误文案 `hskill install --tool browser-fetch-mcp` → `hskill install --tool browser-fetch`
- 提到 `list_chrome_profiles` / `fetch_page` / `evaluate_js` 等 "MCP 工具" 处，改成对应子命令名

- [ ] **Step 10: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add skills/research/clip-url
git commit -m "refactor(clip-url): wrapper 改调 browser-fetch CLI"
```

---

### Task 8: sync-xtimeline wrapper 迁移

**Files:**
- Create: `skills/feed/sync-xtimeline/scripts/browser_fetch_locate.py`
- Create: `skills/feed/sync-xtimeline/scripts/browser_fetch_cli.py`
- Delete: `skills/feed/sync-xtimeline/scripts/browser_fetch_mcp_locate.py`
- Modify: `skills/feed/sync-xtimeline/scripts/mcp_timeline_client.py`
- Modify: `skills/feed/sync-xtimeline/tests/test_browser_fetch_mcp_locate.py` → 改名 `test_browser_fetch_locate.py`
- Modify: `skills/feed/sync-xtimeline/tests/test_mcp_timeline_client.py`
- Modify: `skills/feed/sync-xtimeline/SKILL.md`

**Interfaces:**
- Consumes: `browser-fetch` 可执行文件（Task 5）
- Produces: `mcp_timeline_client.fetch_timeline(profile_url, chrome_profile=None, max_tweets=20) -> list[dict]`——**签名与返回值不变**，`fetch_new_tweets.py` 零改动

注：`fetch_timeline` 原本是 `async def`，`fetch_new_tweets.py` 用 `await` 调用它并跑在 `asyncio.run(run(...))` 里。**保持 `async def` 不变**，函数体内改为调同步 CLI——这样上游一行不用改。

- [ ] **Step 1: 复制两个共享模块**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
cp skills/research/clip-url/scripts/browser_fetch_locate.py skills/feed/sync-xtimeline/scripts/
cp skills/research/clip-url/scripts/browser_fetch_cli.py skills/feed/sync-xtimeline/scripts/
rm skills/feed/sync-xtimeline/scripts/browser_fetch_mcp_locate.py
git mv skills/feed/sync-xtimeline/tests/test_browser_fetch_mcp_locate.py \
       skills/feed/sync-xtimeline/tests/test_browser_fetch_locate.py
```

把复制过来的 `browser_fetch_locate.py` docstring 里的 "clip-url" 改成 "sync-xtimeline"，`find_browser_fetch` 的报错文案同理。

- [ ] **Step 2: 改写失败测试**

`skills/feed/sync-xtimeline/tests/test_mcp_timeline_client.py` 里，把驱动方式改为断言 CLI 参数拼装正确（这个 skill 的测试可以 mock，因为真抓取需要登录态）：

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_fetch_cli  # noqa: E402
import mcp_timeline_client  # noqa: E402


def test_fetch_timeline_builds_cli_args(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"tweets": [{"tweet_id": "1"}]}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    import asyncio
    tweets = asyncio.run(mcp_timeline_client.fetch_timeline(
        "https://x.com/someone", chrome_profile="/tmp/P", max_tweets=5))

    assert tweets == [{"tweet_id": "1"}]
    assert seen["args"] == (
        "timeline", "https://x.com/someone", "--max", "5", "--chrome-profile", "/tmp/P")


def test_fetch_timeline_omits_profile_when_absent(monkeypatch):
    seen = {}
    monkeypatch.setattr(browser_fetch_cli, "call",
                        lambda *a: (seen.update(args=a), {"tweets": []})[1])
    import asyncio
    asyncio.run(mcp_timeline_client.fetch_timeline("https://x.com/someone"))
    assert "--chrome-profile" not in seen["args"]


def test_fetch_timeline_propagates_cli_failure(monkeypatch):
    def boom(*args):
        raise RuntimeError("timeline failed: cookie 失效")
    monkeypatch.setattr(browser_fetch_cli, "call", boom)
    import asyncio
    with pytest.raises(RuntimeError, match="cookie 失效"):
        asyncio.run(mcp_timeline_client.fetch_timeline("https://x.com/someone"))
```

- [ ] **Step 3: 跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/feed/sync-xtimeline/tests/test_mcp_timeline_client.py -v
```

Expected: FAIL（`mcp_timeline_client` 仍 import `mcp`）

- [ ] **Step 4: 改写 mcp_timeline_client.py**

整份替换为：

```python
#!/usr/bin/env python3
"""browser-fetch CLI wrapper for the `timeline` subcommand. 模块名的 mcp_
前缀是历史遗留（本 skill 早期通过 MCP 调用），保留是为了不波及 SKILL.md
和上游 fetch_new_tweets.py。

保持 async def：fetch_new_tweets.py 在 asyncio.run() 里 await 它，
签名不变，上游零改动。
"""
from typing import Optional

import browser_fetch_cli


async def fetch_timeline(
    profile_url: str, chrome_profile: Optional[str] = None, max_tweets: int = 20
) -> list[dict]:
    args = ["timeline", profile_url, "--max", str(max_tweets)]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    return browser_fetch_cli.call(*args)["tweets"]
```

- [ ] **Step 5: 跑 sync-xtimeline 全部测试**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/feed/sync-xtimeline/tests/ -v
```

Expected: PASS

- [ ] **Step 6: 更新 SKILL.md**

`skills/feed/sync-xtimeline/SKILL.md` 第 37 行的 preflight 步骤：`browser_fetch_mcp_locate.py` → `browser_fetch_locate.py`，错误文案里 `browser-fetch-mcp 未安装` → `browser-fetch 未安装`、`hskill install --tool browser-fetch-mcp` → `hskill install --tool browser-fetch`。第 44 行提到的 `set_default_chrome_profile` MCP 工具 → `browser-fetch profile set <path>`。第 66 行脚本清单里"调用 browser-fetch-mcp 的 `fetch_user_timeline` MCP 工具" → "调用 browser-fetch 的 `timeline` 子命令"。

- [ ] **Step 7: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add skills/feed/sync-xtimeline
git commit -m "refactor(sync-xtimeline): wrapper 改调 browser-fetch CLI"
```

---

### Task 9: sync-ytchannel wrapper 迁移并补上缺失的测试

`mcp_channel_client.py` 目前没有任何测试——本 task 顺带补上。

**Files:**
- Create: `skills/feed/sync-ytchannel/scripts/browser_fetch_locate.py`
- Create: `skills/feed/sync-ytchannel/scripts/browser_fetch_cli.py`
- Create: `skills/feed/sync-ytchannel/tests/test_mcp_channel_client.py`
- Create: `skills/feed/sync-ytchannel/tests/test_browser_fetch_locate.py`
- Delete: `skills/feed/sync-ytchannel/scripts/browser_fetch_mcp_locate.py`
- Modify: `skills/feed/sync-ytchannel/scripts/mcp_channel_client.py`
- Modify: `skills/feed/sync-ytchannel/SKILL.md`

**Interfaces:**
- Consumes: `browser-fetch` 可执行文件（Task 5）
- Produces: `mcp_channel_client.fetch_channel_videos(channel_url, chrome_profile=None, max_videos=30) -> list[dict]`——签名与返回值不变，`sync_channels.py` 零改动

- [ ] **Step 1: 复制两个共享模块**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
cp skills/research/clip-url/scripts/browser_fetch_locate.py skills/feed/sync-ytchannel/scripts/
cp skills/research/clip-url/scripts/browser_fetch_cli.py skills/feed/sync-ytchannel/scripts/
rm skills/feed/sync-ytchannel/scripts/browser_fetch_mcp_locate.py
```

把 docstring 里的 "clip-url" 改成 "sync-ytchannel"。

- [ ] **Step 2: 写失败测试**

Create `skills/feed/sync-ytchannel/tests/test_mcp_channel_client.py`:

```python
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_fetch_cli  # noqa: E402
import mcp_channel_client  # noqa: E402


def test_fetch_channel_videos_builds_cli_args(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"videos": [{"title": "T", "url": "https://youtu.be/x"}]}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    videos = asyncio.run(mcp_channel_client.fetch_channel_videos(
        "https://www.youtube.com/@x", chrome_profile="/tmp/P", max_videos=7))

    assert videos == [{"title": "T", "url": "https://youtu.be/x"}]
    assert seen["args"] == (
        "channel", "https://www.youtube.com/@x", "--max", "7", "--chrome-profile", "/tmp/P")


def test_fetch_channel_videos_omits_profile_when_absent(monkeypatch):
    seen = {}
    monkeypatch.setattr(browser_fetch_cli, "call",
                        lambda *a: (seen.update(args=a), {"videos": []})[1])
    asyncio.run(mcp_channel_client.fetch_channel_videos("https://www.youtube.com/@x"))
    assert "--chrome-profile" not in seen["args"]


def test_fetch_channel_videos_propagates_cli_failure(monkeypatch):
    def boom(*args):
        raise RuntimeError("channel failed: 频道不存在")
    monkeypatch.setattr(browser_fetch_cli, "call", boom)
    with pytest.raises(RuntimeError, match="频道不存在"):
        asyncio.run(mcp_channel_client.fetch_channel_videos("https://www.youtube.com/@x"))
```

Create `skills/feed/sync-ytchannel/tests/test_browser_fetch_locate.py`——内容与 Task 7 Step 1 的同名文件逐字相同。

- [ ] **Step 3: 跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/feed/sync-ytchannel/tests/test_mcp_channel_client.py -v
```

Expected: FAIL（`mcp_channel_client` 仍 import `mcp`）

- [ ] **Step 4: 改写 mcp_channel_client.py**

整份替换为：

```python
#!/usr/bin/env python3
"""browser-fetch CLI wrapper for the `channel` subcommand. 模块名的 mcp_
前缀是历史遗留，保留是为了不波及 SKILL.md 和上游 sync_channels.py。

保持 async def：sync_channels.py 在 asyncio.run() 里 await 它。
"""
from typing import Optional

import browser_fetch_cli


async def fetch_channel_videos(
    channel_url: str, chrome_profile: Optional[str] = None, max_videos: int = 30
) -> list[dict]:
    args = ["channel", channel_url, "--max", str(max_videos)]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    return browser_fetch_cli.call(*args)["videos"]
```

- [ ] **Step 5: 跑 sync-ytchannel 全部测试**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/feed/sync-ytchannel/tests/ -v
```

Expected: PASS

- [ ] **Step 6: 更新 SKILL.md**

`skills/feed/sync-ytchannel/SKILL.md` 第 34 行 preflight：`browser_fetch_mcp_locate.py` → `browser_fetch_locate.py`，错误文案两处 `browser-fetch-mcp` → `browser-fetch`。第 61 行脚本清单里"调用 browser-fetch-mcp 的 `fetch_channel_videos` MCP 工具（解析逻辑全在 MCP 侧）" → "调用 browser-fetch 的 `channel` 子命令（解析逻辑全在 CLI 侧）"。

- [ ] **Step 7: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add skills/feed/sync-ytchannel
git commit -m "refactor(sync-ytchannel): wrapper 改调 browser-fetch CLI，补上缺失测试"
```

---

### Task 10: 删除旧 MCP tool 并清理注册

**前置门槛：Task 7/8/9 三个 skill 的测试必须全绿。** 提前删会让回退失去参照。

**Files:**
- Delete: `tools/browser-fetch-mcp/`
- Modify: `skills-index.json`（移除 `browser-fetch-mcp` 项；更新 `toolBundleMeta.research-tools`）
- Modify: `package.json`（`files[]` 移除 `tools/browser-fetch-mcp/`）

- [ ] **Step 1: 确认三个 skill 全绿**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/research/clip-url/tests/ skills/feed/sync-xtimeline/tests/ skills/feed/sync-ytchannel/tests/ -v
```

Expected: PASS。**任何一条红都必须停下修复，不得继续本 task。**

- [ ] **Step 2: 确认仓库里已无 browser-fetch-mcp 引用（旧目录自身除外）**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
grep -rn "browser-fetch-mcp\|browser_fetch_mcp" --include="*.py" --include="*.md" --include="*.json" --include="*.sh" . \
  | grep -v "^./tools/browser-fetch-mcp/" \
  | grep -v "^./docs/"
```

Expected: 无输出（`docs/` 下的历史设计文档保留原名，属正常）

- [ ] **Step 3: 删除旧目录并清理注册**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git rm -r --quiet tools/browser-fetch-mcp
```

`skills-index.json`：删掉 `tools[]` 里 `"name": "browser-fetch-mcp"` 那一项；把 `toolBundleMeta.research-tools` 改为：

```json
"research-tools": "研究抓取后端（browser-fetch — clip-url/sync-* 共用的认证浏览器抓取 CLI；roster — sync-* 共用的人与渠道名册）"
```

`package.json`：从 `files[]` 删掉 `"tools/browser-fetch-mcp/"`。

- [ ] **Step 4: 清理旧安装产物**

```bash
rm -f ~/.local/bin/browser-fetch-mcp
rm -rf ~/.hskill/tools/browser-fetch-mcp ~/.hskill/tools/browser-fetch-mcp.json
```

注：`~/.hskill/browser-fetch-mcp/`（数据目录）**不要手删**——它由 `browser-fetch.sh` 的迁移逻辑负责搬到新名字。若此时已迁移完成，该目录本就不存在。

- [ ] **Step 5: 跑仓库统一测试**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
npm test
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add -A tools skills-index.json package.json
git commit -m "chore(browser-fetch): 删除旧 MCP tool 与注册项"
```

---

### Task 11: clip-url 平台补丁与自有初始化流程

本 task 同时解掉归档制造的断头路——`vault_config.py` 的报错指向即将不存在的 extract-url。

**Files:**
- Create: `skills/research/clip-url/platforms/SKILL.{claude,codex,hermes,pi}.md`
- Modify: `skills/research/clip-url/scripts/vault_config.py`
- Modify: `skills/research/clip-url/SKILL.md`
- Modify: `skills/research/clip-url/tests/test_vault_config.py`

**Interfaces:**
- Produces: `platforms/` 四份补丁；clip-url 自有的 VAULT_PATH 初始化流程

- [ ] **Step 1: 抢救 extract-url 的补丁**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
mkdir -p skills/research/clip-url/platforms
cp skills/research/extract-url/platforms/SKILL.claude.md skills/research/clip-url/platforms/
cp skills/research/extract-url/platforms/SKILL.pi.md skills/research/clip-url/platforms/
```

- [ ] **Step 2: 改写 claude 与 pi 两份补丁**

两份都做同样三处改动：

1. 标题 `# url-extract — X 补丁` → `# clip-url — X 补丁`
2. **删掉整个「② 网页内容获取」小节**——CLI 自带 Playwright 和 cookie 注入，不再需要平台的 `web_fetch` 或 `curl`。Pi 那份里"无内置抓取工具、用 curl 兜底"和"若结果内容单薄…会自动改用 Playwright"两段一并删除。
3. 「③ 变量来源」小节改为只讲 `SKILL_DIR`：

```markdown
## ② 变量来源

`VAULT_PATH` 和固定词表由 Python 脚本在运行时从 `~/.hskill/url-extract/config.json`
读取，**无需 Agent 传参**（目录名 `url-extract` 是历史遗留，clip-url 沿用同一份配置，
以便两者抓过的文章互相去重）。默认 Chrome profile 由 browser-fetch 侧持久化，
调用方不传。

`SKILL_DIR` 为本平台固定值，在 subagent 任务代码中直接使用此路径字符串：
```

claude 那份填 `$HOME/.claude/skills/clip-url`，pi 那份填 `$HOME/.pi/agent/skills/clip-url`。

原「① Subagent 派发」小节**逐字保留**——claude 的 `sessions_spawn` 语法和 pi 的 `subagent({ agent: "worker", task: "<任务内容>" })`（含"必须同时提供 agent 和 task，只传 task 会报错 `Provide exactly one mode`"这句）是全仓库唯一的多平台派发资产。

- [ ] **Step 3: 写两份诚实占位补丁**

Create `skills/research/clip-url/platforms/SKILL.codex.md`:

```markdown
# clip-url — Codex 补丁

适用平台：Codex

> **⚠️ 未验证。** 本补丁从未在 Codex 上实际运行过，下方 subagent 派发语法尚未确认。
> Agent 读到本行时，必须先告知用户「clip-url 在 Codex 平台未验证，subagent 派发
> 语法待补」，再询问是否继续，不要直接尝试派发。

---

## ① Subagent 派发

**待补。** 需要在 Codex 上实际运行一次，记录可用的 subagent 派发调用语法后填入此处。

## ② 变量来源

`VAULT_PATH` 和固定词表由 Python 脚本在运行时从 `~/.hskill/url-extract/config.json`
读取，**无需 Agent 传参**。默认 Chrome profile 由 browser-fetch 侧持久化，调用方不传。

`SKILL_DIR` 为 Codex 安装本 skill 的目录（即包含 `scripts/` 的那一级），在 subagent
任务代码中直接使用该路径字符串。
```

Create `skills/research/clip-url/platforms/SKILL.hermes.md`——内容与上面逐字相同，把三处 `Codex` 替换为 `Hermes`。

- [ ] **Step 4: SKILL.md 增加平台补丁加载步骤**

在 `skills/research/clip-url/SKILL.md` 的「执行流程」之前插入：

```markdown
## 初始化（run first）

**① 加载平台补丁**

根据当前执行平台，读取对应补丁文件，了解**补丁①**（Subagent 派发）与**补丁②**（变量来源）的具体语法：

| 平台 | 补丁文件 |
|------|----------|
| Claude Code | `platforms/SKILL.claude.md` |
| Codex | `platforms/SKILL.codex.md` |
| Hermes | `platforms/SKILL.hermes.md` |
| Pi | `platforms/SKILL.pi.md` |

若补丁文件顶部带「⚠️ 未验证」标注，必须先按该标注要求告知用户，再决定是否继续。

以下流程中凡标注「**补丁①**」处，均使用对应平台补丁中定义的调用语法替换。
```

并把正文里三处"按当前平台的 subagent 派发机制派发"改为"按**补丁①**派发"。

- [ ] **Step 5: 写失败测试——vault_config 报错不再指向 extract-url**

在 `skills/research/clip-url/tests/test_vault_config.py` 追加：

```python
def test_missing_config_error_points_at_clip_url_not_extract_url(isolated_vault_config):
    import vault_config
    with pytest.raises(FileNotFoundError) as e:
        vault_config.get_vault_path()
    msg = str(e.value)
    assert "extract-url" not in msg
    assert "clip-url" in msg


def test_missing_vault_path_key_error_points_at_clip_url(isolated_vault_config):
    import json
    import vault_config
    isolated_vault_config.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(KeyError) as e:
        vault_config.get_vault_path()
    assert "extract-url" not in str(e.value)
```

- [ ] **Step 6: 跑测试确认失败**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/research/clip-url/tests/test_vault_config.py -v
```

Expected: FAIL（报错文案仍写着 extract-url）

- [ ] **Step 7: 改 vault_config.py 报错文案**

把两处文案改为：

```python
            "请先完成 clip-url 初始化（配置 VAULT_PATH 和固定词表）——"
            "见 SKILL.md「初始化」小节。"
```

```python
    if "VAULT_PATH" not in cfg:
        raise KeyError(
            f"{config_path} 缺少 VAULT_PATH，请重新完成 clip-url 初始化。"
        )
```

同时更新模块 docstring：把 "that extract-url writes" 改为 "由 clip-url 初始化写入（目录名 url-extract 为历史遗留）"。

- [ ] **Step 8: SKILL.md 增加 VAULT_PATH 初始化小节**

在「初始化（run first）」下追加：

```markdown
**② 检查共享配置**

运行 `python3 scripts/vault_config.py check`。若报缺失，引导用户提供 Obsidian Vault
绝对路径，写入 `~/.hskill/url-extract/config.json` 的 `VAULT_PATH` 字段，并在同目录
创建空的 `fixed_tags.txt`。配置目录名 `url-extract` 是历史遗留，clip-url 沿用同一份
配置，以便与历史抓取记录互相去重。
```

在 `vault_config.py` 末尾加对应的 `check` 入口：

```python
def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        try:
            print(f"OK: {get_vault_path()}")
        except (FileNotFoundError, KeyError) as e:
            print(f"MISSING: {e}", file=sys.stderr)
            sys.exit(1)
        return
    print("Usage: vault_config.py check", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 9: 跑测试确认通过**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -m pytest skills/research/clip-url/tests/ -v
```

Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add skills/research/clip-url
git commit -m "feat(clip-url): 四平台补丁与自有初始化流程"
```

---

### Task 12: 两个 sync skill 的平台补丁

这两个 skill 不派发 subagent（sync-ytchannel 零次提及；sync-xtimeline 明确写着"不派发 subagent"），补丁①对它们为空，补丁只需交代 `SKILL_DIR` 与验证状态。

**Files:**
- Create: `skills/feed/sync-xtimeline/platforms/SKILL.{claude,codex,hermes,pi}.md`
- Create: `skills/feed/sync-ytchannel/platforms/SKILL.{claude,codex,hermes,pi}.md`
- Modify: `skills/feed/sync-xtimeline/SKILL.md`
- Modify: `skills/feed/sync-ytchannel/SKILL.md`

- [ ] **Step 1: 写 sync-xtimeline 的四份补丁**

Create `skills/feed/sync-xtimeline/platforms/SKILL.claude.md`:

```markdown
# sync-xtimeline — Claude Code 补丁

适用平台：Claude Code

---

## ① Subagent 派发

**本 skill 不派发 subagent。** 全部步骤为 `python3 scripts/*.py` 直接调用，
推文翻译在主对话内完成（纯文本翻译不需要隔离）。本小节存在只为与其他
skill 的补丁结构对齐。

## ② 变量来源

名册与游标由 `roster` tool 持有，脚本自行定位，无需 Agent 传参。默认
Chrome profile 由 browser-fetch 侧持久化，与 clip-url 共用同一份配置。

`SKILL_DIR` 为 Claude Code 平台固定值：`$HOME/.claude/skills/sync-xtimeline`
```

`SKILL.pi.md` 逐字相同，把平台名改为 Pi、`SKILL_DIR` 改为 `$HOME/.pi/agent/skills/sync-xtimeline`。

`SKILL.codex.md` 与 `SKILL.hermes.md` 逐字相同（平台名相应替换），但在标题下方插入：

```markdown
> **⚠️ 未在本平台实测。** 本 skill 全程只调用 `python3 scripts/*.py` 与
> `browser-fetch` CLI，理论上平台无关，但从未在本平台实际运行过。首次运行
> 若出现异常，请回报以便补充本补丁。
```

`SKILL_DIR` 分别写"Codex/Hermes 安装本 skill 的目录（即包含 `scripts/` 的那一级）"。

- [ ] **Step 2: 写 sync-ytchannel 的四份补丁**

与 Step 1 逐字相同，把全部 `sync-xtimeline` 替换为 `sync-ytchannel`，并把 `① Subagent 派发` 小节正文改为：

```markdown
**本 skill 不派发 subagent。** 全部步骤为 `python3 scripts/*.py` 直接调用
（视频标题不翻译）。本小节存在只为与其他 skill 的补丁结构对齐。
```

`SKILL_DIR` 相应改为各平台下的 `sync-ytchannel` 路径。

- [ ] **Step 3: 两份 SKILL.md 增加补丁加载步骤**

在两个 SKILL.md 的流程正文之前各插入：

```markdown
## 初始化（run first）

根据当前执行平台读取对应补丁：Claude Code → `platforms/SKILL.claude.md`；
Codex → `platforms/SKILL.codex.md`；Hermes → `platforms/SKILL.hermes.md`；
Pi → `platforms/SKILL.pi.md`。若补丁顶部带「⚠️ 未在本平台实测」标注，
先告知用户再继续。
```

- [ ] **Step 4: 跑仓库统一测试**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
npm test
```

Expected: PASS（SKILL.md 格式校验通过）

- [ ] **Step 5: Commit**

```bash
git add skills/feed/sync-xtimeline skills/feed/sync-ytchannel
git commit -m "feat(sync-*): 四平台补丁"
```

---

### Task 13: 归档 extract-url

**前置门槛：Task 11 必须已完成**——`platforms/` 补丁已抢救到 clip-url，且 clip-url 有了自己的初始化流程。否则唯一的多平台派发资产和用户的初始化路径会同时断掉。

**Files:**
- Move: `skills/research/extract-url/` → `skills/archived/extract-url/`
- Modify: `skills-index.json`（`skills[]` 移除该项）
- Modify: `package.json`（`files[]` 移除 `skills/research/extract-url/`）

- [ ] **Step 1: 确认抢救已完成**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
ls skills/research/clip-url/platforms/
grep -c "subagent({ agent" skills/research/clip-url/platforms/SKILL.pi.md
python3 -m pytest skills/research/clip-url/tests/ -q
```

Expected: 四个补丁文件都在；Pi 补丁里的派发语法计数 ≥ 1；测试全绿。**任何一条不满足就停下，回到 Task 11。**

- [ ] **Step 2: 用 archive-skill 归档**

调用仓库的 `archive-skill` skill 归档 `extract-url`。它负责：移到 `skills/archived/`、从 `skills-index.json` 的 `skills[]` 摘除、重新生成打包配置。

若需手工执行：

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
mkdir -p skills/archived
git mv skills/research/extract-url skills/archived/extract-url
```

然后从 `skills-index.json` 的 `skills[]` 删掉 `{"path": "research/extract-url", "bundle": "research"}` 那一项，从 `package.json` 的 `files[]` 删掉 `"skills/research/extract-url/"`。

- [ ] **Step 3: 确认配置目录未被动过**

```bash
ls -la ~/.hskill/url-extract/
```

Expected: 目录仍在，`config.json` 与 `fixed_tags.txt` 完好。**归档不删用户数据。**

- [ ] **Step 4: 确认没有活跃 skill 还引用 extract-url**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
grep -rn "extract-url" skills/ --include="*.md" --include="*.py" | grep -v "^skills/archived/"
```

Expected: 只剩 clip-url 里注明"目录名 url-extract 为历史遗留"的那几处说明性文字，无功能性依赖。

- [ ] **Step 5: 跑全量测试**

```bash
npm test
python3 -m pytest skills/research/clip-url/tests/ skills/feed/sync-xtimeline/tests/ skills/feed/sync-ytchannel/tests/ -q
cd tools/browser-fetch && .venv/bin/python -m pytest tests/ -q
```

Expected: 全绿

- [ ] **Step 6: Commit**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add -A skills skills-index.json package.json
git commit -m "chore(extract-url): 归档，逻辑由 clip-url 承接"
```
