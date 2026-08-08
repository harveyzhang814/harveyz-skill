# browser-fetch-mcp Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, installable MCP server (`tools/browser-fetch-mcp/`) that exposes one tool, `fetch_page`, which fetches a URL through a warm (process-lifetime) headless Playwright context, optionally injecting cookies decrypted from a local Chrome profile for authenticated fetches.

**Architecture:** A FastMCP server (`playwright.async_api`, required — the sync API cannot run inside FastMCP's event loop) keeps one persistent Playwright browser context per identity (`__anon__` for anonymous fetches, or a hash of the Chrome profile path for authenticated fetches), reusing it across tool calls instead of launching a fresh browser per call. Cookie extraction (Chrome's encrypted SQLite cookie DB → plaintext) is a separate, independently-testable pure function that the server calls before each authenticated fetch.

**Tech Stack:** Python 3.11+, `mcp` (FastMCP) SDK, `playwright` (async API), `pycookiecheat`, `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`), packaged with `hatchling` following the `tools/hub` / `tools/sync-agent` convention already in this repo.

## Global Constraints

- Package lives at `tools/browser-fetch-mcp/`, following the exact structure of `tools/hub/` and `tools/sync-agent/` (`pyproject.toml`, `tool.json`, `<name>.sh` wrapper, `<name>/` source, `tests/`).
- Do NOT modify `skills/research/extract-url/` or `skills/research/probe-session/` — Phase A ships the server standalone, no consumer migration (deferred to Phase B).
- Do NOT register this server in any platform's MCP client config (`~/.claude.json` `mcpServers`, etc.) — deferred to Phase B.
- Must use `playwright.async_api`, never `playwright.sync_api` — verified in the feasibility experiment that sync API raises inside FastMCP's event loop.
- `fetch_page` return shape is exactly `{html: str, title: str, status: int, cookies_injected: int}` — do not add fields (e.g. no `elapsed_seconds`); tests measure timing from the client side instead.
- `use_auth=True` with `chrome_profile=None` must raise (not silently fall back to anonymous) — see spec ambiguity fix in `docs/superpowers/specs/2026-08-08-browser-fetch-mcp-phase-a-design.md`.
- Never touch the user's real Chrome profile directory as a Playwright `launch_persistent_context` target — only read its `Cookies` file (via a copied temp file, matching `docs/explanation/chrome-profile-cookie-injection.md`'s existing security pattern). The server's own persistent contexts live under `BROWSER_FETCH_MCP_DATA_DIR` (default `~/.hskill/browser-fetch-mcp/contexts`), never inside the real Chrome profile.

---

### Task 1: Package scaffold + dev environment

**Files:**
- Create: `tools/browser-fetch-mcp/pyproject.toml`
- Create: `tools/browser-fetch-mcp/browser_fetch_mcp/__init__.py`

**Interfaces:**
- Produces: an importable `browser_fetch_mcp` package, dev venv at `tools/browser-fetch-mcp/.venv` with the package installed editable.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "browser-fetch-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.28.0",
    "playwright>=1.45",
    "pycookiecheat>=0.7",
]

[project.scripts]
browser-fetch-mcp = "browser_fetch_mcp.server:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.hatch.build.targets.wheel]
packages = ["browser_fetch_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Write `browser_fetch_mcp/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create dev venv and install editable**

Run:
```bash
cd tools/browser-fetch-mcp
python3 -m venv .venv
./.venv/bin/pip install -q -e ".[dev]"
./.venv/bin/python3 -m playwright install chromium
```
Expected: no errors. `playwright install chromium` may print download progress — that's expected on first run.

- [ ] **Step 4: Verify the package imports**

Run: `./.venv/bin/python3 -c "import browser_fetch_mcp; print(browser_fetch_mcp.__version__)"`
Expected: prints `0.1.0`

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch-mcp/pyproject.toml tools/browser-fetch-mcp/browser_fetch_mcp/__init__.py
git commit -m "chore(browser-fetch-mcp): scaffold package"
```

---

### Task 2: Cookie extraction module + unit tests

**Files:**
- Create: `tools/browser-fetch-mcp/browser_fetch_mcp/cookies.py`
- Test: `tools/browser-fetch-mcp/tests/test_cookies.py`

**Interfaces:**
- Produces: `extract_cookies(url: str, chrome_profile: str) -> dict[str, str]` — used by Task 4's `fetch_page`.

- [ ] **Step 1: Write the failing tests**

Create `tools/browser-fetch-mcp/tests/test_cookies.py`:

```python
from unittest.mock import patch

from browser_fetch_mcp.cookies import extract_cookies


def test_extract_cookies_missing_profile_returns_empty(tmp_path):
    missing_profile = tmp_path / "NoProfileHere"
    result = extract_cookies("https://example.com", str(missing_profile))
    assert result == {}


def test_extract_cookies_delegates_to_pycookiecheat(tmp_path):
    profile_dir = tmp_path / "Profile"
    profile_dir.mkdir()
    (profile_dir / "Cookies").write_bytes(b"fake-sqlite-bytes")

    with patch("browser_fetch_mcp.cookies.pycookiecheat.chrome_cookies") as mock_cc:
        mock_cc.return_value = {"session_id": "abc123"}
        result = extract_cookies("https://example.com", str(profile_dir))

    assert result == {"session_id": "abc123"}
    called_cookie_file = mock_cc.call_args.kwargs["cookie_file"]
    assert called_cookie_file != str(profile_dir / "Cookies")


def test_extract_cookies_empty_result_from_pycookiecheat(tmp_path):
    profile_dir = tmp_path / "Profile"
    profile_dir.mkdir()
    (profile_dir / "Cookies").write_bytes(b"fake-sqlite-bytes")

    with patch("browser_fetch_mcp.cookies.pycookiecheat.chrome_cookies") as mock_cc:
        mock_cc.return_value = {}
        result = extract_cookies("https://example.com", str(profile_dir))

    assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tools/browser-fetch-mcp && ./.venv/bin/pytest tests/test_cookies.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'browser_fetch_mcp.cookies'`

- [ ] **Step 3: Write `browser_fetch_mcp/cookies.py`**

```python
"""Chrome profile cookie extraction.

Mirrors docs/explanation/chrome-profile-cookie-injection.md's pattern:
copy the Cookies DB to a temp file first (Chrome holds an exclusive lock
on the original while running), then let pycookiecheat decrypt it. This
module only extracts plaintext cookies — injecting them into a browser
context happens in server.py, which owns the browser lifecycle.
"""
import os
import shutil
import tempfile
from pathlib import Path

import pycookiecheat


def extract_cookies(url: str, chrome_profile: str) -> dict[str, str]:
    """Return {cookie_name: plaintext_value} for `url`'s domain from the
    given Chrome profile.

    Returns {} if the profile has no Cookies file, or if pycookiecheat
    finds no matching cookies — this is a normal "not logged in" result,
    not an error condition, so it never raises for that case.
    """
    cookies_src = Path(chrome_profile) / "Cookies"
    if not cookies_src.exists():
        return {}

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        shutil.copy2(cookies_src, tmp_path)
        return pycookiecheat.chrome_cookies(url, cookie_file=tmp_path) or {}
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/browser-fetch-mcp && ./.venv/bin/pytest tests/test_cookies.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/cookies.py tools/browser-fetch-mcp/tests/test_cookies.py
git commit -m "feat(browser-fetch-mcp): add cookie extraction module"
```

---

### Task 3: FastMCP server — anonymous fetch_page + e2e test

**Files:**
- Create: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`
- Test: `tools/browser-fetch-mcp/tests/test_server.py`

**Interfaces:**
- Consumes: nothing from Task 2 yet (auth wiring is Task 4).
- Produces: `fetch_page(url: str, use_auth: bool = False, chrome_profile: str | None = None) -> dict` MCP tool; `main()` entry point running `mcp.run(transport="stdio")`; module-level `mcp = FastMCP("browser-fetch-mcp")`.

- [ ] **Step 1: Write the failing e2e test**

Create `tools/browser-fetch-mcp/tests/test_server.py`:

```python
import json
import os
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_MODULE = "browser_fetch_mcp.server"


def _server_params(data_dir: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command="python3",
        args=["-m", SERVER_MODULE],
        env={**os.environ, "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir)},
    )


async def _call_fetch_page(session, **kwargs):
    result = await session.call_tool("fetch_page", kwargs)
    if result.isError:
        return result, None
    payload = result.structuredContent or json.loads(result.content[0].text)
    return result, payload


async def test_fetch_page_anonymous(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_page(session, url="https://example.com")
            assert payload["title"] == "Example Domain"
            assert payload["status"] == 200
            assert payload["cookies_injected"] == 0


async def test_fetch_page_warm_reuse_is_faster(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            start = time.monotonic()
            await _call_fetch_page(session, url="https://example.com")
            first_call = time.monotonic() - start

            start = time.monotonic()
            await _call_fetch_page(session, url="https://example.com")
            second_call = time.monotonic() - start

            assert second_call < first_call / 2
```

Note: these tests need real network access to `https://example.com` — this matches the feasibility experiment's methodology and is expected to work in the same environment the experiment ran in.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tools/browser-fetch-mcp && ./.venv/bin/pytest tests/test_server.py -v`
Expected: FAIL — connection/spawn error, no `browser_fetch_mcp.server` module yet

- [ ] **Step 3: Write `browser_fetch_mcp/server.py`**

```python
"""FastMCP server exposing fetch_page: a warm-context headless browser
fetch tool. Auth (Chrome cookie injection) is wired in Task 4."""
import hashlib
import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, BrowserContext

mcp = FastMCP("browser-fetch-mcp")

ANON_KEY = "__anon__"

_state = {"playwright": None, "contexts": {}}


def _data_dir() -> Path:
    override = os.environ.get("BROWSER_FETCH_MCP_DATA_DIR")
    base = (
        Path(override)
        if override
        else Path.home() / ".hskill" / "tools" / "browser-fetch-mcp" / "contexts"
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


async def _get_context(key: str) -> BrowserContext:
    if key not in _state["contexts"]:
        if _state["playwright"] is None:
            _state["playwright"] = await async_playwright().start()
        profile_dir = _data_dir() / key
        profile_dir.mkdir(parents=True, exist_ok=True)
        _state["contexts"][key] = await _state["playwright"].chromium.launch_persistent_context(
            str(profile_dir), headless=True
        )
    return _state["contexts"][key]


@mcp.tool()
async def fetch_page(url: str, use_auth: bool = False, chrome_profile: Optional[str] = None) -> dict:
    """Fetch a URL with a warm headless-browser context.

    use_auth/chrome_profile are accepted here for interface stability but
    not yet implemented — Task 4 adds cookie injection.
    """
    ctx = await _get_context(ANON_KEY)
    page = await ctx.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        html = await page.content()
        status = response.status if response else 0
    finally:
        await page.close()

    return {
        "html": html,
        "title": title,
        "status": status,
        "cookies_injected": 0,
    }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/browser-fetch-mcp && ./.venv/bin/pytest tests/test_server.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py tools/browser-fetch-mcp/tests/test_server.py
git commit -m "feat(browser-fetch-mcp): anonymous fetch_page MCP tool"
```

---

### Task 4: Wire `use_auth` + `chrome_profile` into fetch_page

**Files:**
- Modify: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py` (replace `fetch_page` function body, add `_profile_key` helper)
- Modify: `tools/browser-fetch-mcp/tests/test_server.py` (add one test)

**Interfaces:**
- Consumes: `extract_cookies(url: str, chrome_profile: str) -> dict[str, str]` from Task 2's `browser_fetch_mcp.cookies`.
- Produces: `fetch_page` now honors `use_auth`/`chrome_profile`; `cookies_injected` in the return dict reflects real injection counts.

- [ ] **Step 1: Write the failing test**

Add to `tools/browser-fetch-mcp/tests/test_server.py`:

```python
async def test_fetch_page_use_auth_requires_chrome_profile(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_page(session, url="https://example.com", use_auth=True)
            assert result.isError is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/browser-fetch-mcp && ./.venv/bin/pytest tests/test_server.py -v -k use_auth`
Expected: FAIL — current `fetch_page` ignores `use_auth` entirely, never raises, so `result.isError` is `False`

- [ ] **Step 3: Modify `server.py`**

Add the import and a profile-key helper near the top (after the existing imports):

```python
from urllib.parse import urlparse

from browser_fetch_mcp.cookies import extract_cookies
```

```python
def _profile_key(chrome_profile: str) -> str:
    return hashlib.sha256(chrome_profile.encode("utf-8")).hexdigest()[:16]
```

Replace the `fetch_page` function body:

```python
@mcp.tool()
async def fetch_page(url: str, use_auth: bool = False, chrome_profile: Optional[str] = None) -> dict:
    """Fetch a URL with a warm headless-browser context, optionally
    injecting cookies decrypted from a local Chrome profile.

    Raises ValueError if use_auth=True and chrome_profile is not given —
    this never silently degrades to an anonymous fetch, so callers can't
    mistake an anonymous result for an authenticated one.
    """
    if use_auth and not chrome_profile:
        raise ValueError("chrome_profile is required when use_auth=True")

    key = _profile_key(chrome_profile) if use_auth else ANON_KEY
    ctx = await _get_context(key)

    cookies_injected = 0
    if use_auth:
        cookies_dict = extract_cookies(url, chrome_profile)
        if cookies_dict:
            netloc_parts = urlparse(url).netloc.split(".")
            domain = (
                "." + ".".join(netloc_parts[-2:])
                if len(netloc_parts) >= 2
                else urlparse(url).netloc
            )
            pw_cookies = [
                {"name": k, "value": v, "domain": domain, "path": "/", "secure": True}
                for k, v in cookies_dict.items()
            ]
            await ctx.add_cookies(pw_cookies)
            cookies_injected = len(pw_cookies)

    page = await ctx.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        html = await page.content()
        status = response.status if response else 0
    finally:
        await page.close()

    return {
        "html": html,
        "title": title,
        "status": status,
        "cookies_injected": cookies_injected,
    }
```

- [ ] **Step 4: Run full test suite to verify it passes**

Run: `cd tools/browser-fetch-mcp && ./.venv/bin/pytest tests/ -v`
Expected: 6 passed (3 from test_cookies.py + 3 from test_server.py)

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py tools/browser-fetch-mcp/tests/test_server.py
git commit -m "feat(browser-fetch-mcp): wire cookie injection into fetch_page"
```

---

### Task 5: Packaging plumbing + final verification

**Files:**
- Create: `tools/browser-fetch-mcp/tool.json`
- Create: `tools/browser-fetch-mcp/browser-fetch-mcp.sh`

**Interfaces:**
- Produces: an hskill-registrable tool manifest and a self-bootstrapping wrapper script, matching `tools/hub/tool.json` and `tools/hub/hub.sh`.

- [ ] **Step 1: Write `tool.json`**

```json
{
  "name": "browser-fetch-mcp",
  "version": "0.1.0",
  "description": "Shared MCP server for authenticated headless browser fetches (warm Playwright context, Chrome cookie injection)",
  "extraPaths": ["browser_fetch_mcp", "pyproject.toml"],
  "uninstallPaths": ["~/.hskill/tools/browser-fetch-mcp/venv", "~/.hskill/tools/browser-fetch-mcp"],
  "configPaths": ["~/.hskill/tools/browser-fetch-mcp"]
}
```

- [ ] **Step 2: Write `browser-fetch-mcp.sh`**

```bash
#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect dev mode: script is running from the source tree
if [ -d "${SCRIPT_DIR}/browser_fetch_mcp" ] && [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
  DEV_VENV="${SCRIPT_DIR}/.venv"
  if [ ! -x "${DEV_VENV}/bin/browser-fetch-mcp" ]; then
    python3 -m venv "${DEV_VENV}"
    "${DEV_VENV}/bin/pip" install -q -e "${SCRIPT_DIR}"
  fi
  exec "${DEV_VENV}/bin/browser-fetch-mcp" "$@"
fi

VENV_DIR="${HOME}/.hskill/tools/browser-fetch-mcp/venv"
INSTALL_DIR="${HOME}/.hskill/tools/browser-fetch-mcp"
HASH_FILE="${VENV_DIR}/.installed_hash"

_hash_source() {
  find "${INSTALL_DIR}" -type f \( -name "*.py" -o -name "*.toml" -o -name "*.json" \) \
    ! -path "*/__pycache__/*" ! -path "*/venv/*" \
    | sort | xargs sha256sum 2>/dev/null | sha256sum | awk '{print $1}'
}

CURRENT_HASH=$(_hash_source)

if [ ! -x "${VENV_DIR}/bin/browser-fetch-mcp" ] || [ "$(cat "${HASH_FILE}" 2>/dev/null)" != "${CURRENT_HASH}" ]; then
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install -q --upgrade "${INSTALL_DIR}"
  echo "${CURRENT_HASH}" > "${HASH_FILE}"
fi

exec "${VENV_DIR}/bin/browser-fetch-mcp" "$@"
```

- [ ] **Step 3: Make the wrapper executable**

Run: `chmod +x tools/browser-fetch-mcp/browser-fetch-mcp.sh`

- [ ] **Step 4: Verify the wrapper boots the server (dev-mode path)**

Run:
```bash
cd tools/browser-fetch-mcp
timeout 5 ./browser-fetch-mcp.sh < /dev/null > /tmp/browser-fetch-mcp-boot.log 2>&1 || true
cat /tmp/browser-fetch-mcp-boot.log
```
Expected: no Python tracebacks in the log (the process starts, waits on stdio for an MCP client, and gets killed by `timeout` after 5s — that's the expected shutdown path for this manual check, not a test assertion). If `pyproject.toml`/`browser_fetch_mcp/` aren't picked up correctly this step will show an import error instead — fix before proceeding.

- [ ] **Step 5: Run the full test suite one final time**

Run: `cd tools/browser-fetch-mcp && ./.venv/bin/pytest tests/ -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add tools/browser-fetch-mcp/tool.json tools/browser-fetch-mcp/browser-fetch-mcp.sh
git commit -m "chore(browser-fetch-mcp): add tool.json and wrapper script"
```
