# browser-fetch-mcp Chrome Profile Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Chrome-profile detection into `browser-fetch-mcp` as reusable MCP tools, add a persisted default Chrome profile so the user is only asked once, and make `fetch_article` resolve that default automatically wherever it would otherwise need an explicitly-passed `chrome_profile` — without changing which sites use cookies at all.

**Architecture:** Three new MCP tools in `browser-fetch-mcp` (`list_chrome_profiles`, `get_default_chrome_profile`, `set_default_chrome_profile`) backed by a small JSON config file in the server's existing data dir. `fetch_article` resolves `chrome_profile or <persisted default>` once at the top of the function; every existing downstream decision (x.com's mandatory check, the other three sites' thin-retry gate) keeps reading that one resolved value, so per-site policy is untouched. `extract-url-mcp`'s `SKILL.md` and `detect_xcom_chrome_profile.py` are rewritten to call the new MCP tools instead of querying Chrome's cookie database directly, and the "ask the user" gate moves from "hostname is x.com" to "no default has ever been configured, regardless of URL."

**Tech Stack:** Python 3, MCP Python SDK (`mcp.server.MCPServer`, `mcp.client.stdio`), `pytest`, `sqlite3` (stdlib), Playwright (unchanged, only `fetch_article` callers change).

## Global Constraints

- Persisted config lives at `<data-dir>/config.json`, where `<data-dir>` is exactly what `_data_dir()` in `tools/browser-fetch-mcp/browser_fetch_mcp/server.py` already resolves (respects `BROWSER_FETCH_MCP_DATA_DIR` for test isolation — never introduce a second env var for this).
- `list_chrome_profiles(host_keys: list[str], cookie_names: list[str])` is existence-only — it must never decrypt cookie values (that stays `extract_cookies`'s job in `cookies.py`).
- `fetch_article` resolves `effective_chrome_profile = chrome_profile or config.get_default_chrome_profile(_data_dir())` exactly once, at the top of the function, immediately after the URL-scheme check. Every other line in `fetch_article` that currently reads the `chrome_profile` parameter must read `effective_chrome_profile` instead — no other conditional logic changes. x.com's mandatory-profile error and the other three sites' thin-retry-only-if-profile-present gate must behave bit-for-bit as they do today, just fed the resolved value.
- One global default profile — no per-site defaults, no data model that implies more than one.
- `skills/research/extract-url/` (the original, real skill) is not touched by this plan.
- x.com's cookie-name matching stays exactly `host_keys=[".x.com", ".twitter.com"]`, `cookie_names=["auth_token", "ct0", "twid"]` — same values as today's `detect_xcom_chrome_profile.py`, just passed as parameters instead of hardcoded.
- All new tests that touch config read/write or Chrome-profile scanning MUST set `BROWSER_FETCH_MCP_DATA_DIR` (and, for scanning, `BROWSER_FETCH_MCP_CHROME_BASE`) to an isolated `tmp_path` — never let a test read or write the real user's `~/.hskill/browser-fetch-mcp/` or real Chrome profile directory.

---

### Task 1: Persisted default-profile config (`config.py` + `get_default_chrome_profile`/`set_default_chrome_profile` MCP tools)

**Files:**
- Create: `tools/browser-fetch-mcp/browser_fetch_mcp/config.py`
- Create: `tools/browser-fetch-mcp/tests/test_config.py`
- Modify: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`
- Modify: `tools/browser-fetch-mcp/tests/test_server.py`

**Interfaces:**
- Produces: `config.get_default_chrome_profile(data_dir: Path) -> Optional[str]`, `config.set_default_chrome_profile(data_dir: Path, profile_path: str) -> None` — plain functions taking `data_dir` explicitly (no import of `server._data_dir` inside `config.py`, to avoid a circular import since `server.py` imports `config`).
- Produces: two new `@mcp.tool()` functions in `server.py`, `get_default_chrome_profile() -> dict` (returns `{"profile_path": str | None}`) and `set_default_chrome_profile(profile_path: str) -> dict` (returns `{"ok": True}`, raises `ValueError` if `profile_path` doesn't exist or isn't a directory).
- Consumes: nothing from other tasks.

- [ ] **Step 1: Write the failing unit tests for `config.py`**

Create `tools/browser-fetch-mcp/tests/test_config.py`:

```python
"""Unit tests for config.py's persisted-default-profile read/write —
pure filesystem I/O, no MCP protocol involved."""
from pathlib import Path

from browser_fetch_mcp import config


def test_get_default_chrome_profile_returns_none_when_unconfigured(tmp_path):
    assert config.get_default_chrome_profile(tmp_path) is None


def test_set_then_get_round_trips(tmp_path):
    config.set_default_chrome_profile(tmp_path, "/Users/x/Chrome/Default")
    assert config.get_default_chrome_profile(tmp_path) == "/Users/x/Chrome/Default"


def test_set_overwrites_previous_value(tmp_path):
    config.set_default_chrome_profile(tmp_path, "/first/path")
    config.set_default_chrome_profile(tmp_path, "/second/path")
    assert config.get_default_chrome_profile(tmp_path) == "/second/path"


def test_config_file_written_at_expected_location(tmp_path):
    config.set_default_chrome_profile(tmp_path, "/some/path")
    assert (tmp_path / "config.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'browser_fetch_mcp.config'` (or `ImportError`).

- [ ] **Step 3: Implement `config.py`**

Create `tools/browser-fetch-mcp/browser_fetch_mcp/config.py`:

```python
"""Persisted default Chrome profile — a single JSON file in the server's
data dir, {"default_chrome_profile": "<path>"}. Read/write here is pure
I/O; the caller (server.py) owns resolving `data_dir` (BROWSER_FETCH_MCP_DATA_DIR
override for tests) and validating the path before calling set().
"""
import json
from pathlib import Path
from typing import Optional


def _config_file(data_dir: Path) -> Path:
    return data_dir / "config.json"


def get_default_chrome_profile(data_dir: Path) -> Optional[str]:
    path = _config_file(data_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("default_chrome_profile")


def set_default_chrome_profile(data_dir: Path, profile_path: str) -> None:
    path = _config_file(data_dir)
    path.write_text(json.dumps({"default_chrome_profile": profile_path}), encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/test_config.py -v`
Expected: 4 passed.

- [ ] **Step 5: Add the two MCP tools to `server.py`**

In `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`, add the import alongside the existing ones (after the `from browser_fetch_mcp.images import download_images` line):

```python
from browser_fetch_mcp import config
```

Add these two tools immediately after the existing `fetch_page` tool (before `fetch_article`):

```python
@mcp.tool()
async def get_default_chrome_profile() -> dict:
    """Read the persisted default Chrome profile, set via
    set_default_chrome_profile. Returns {"profile_path": None} if no
    default has ever been configured."""
    return {"profile_path": config.get_default_chrome_profile(_data_dir())}


@mcp.tool()
async def set_default_chrome_profile(profile_path: str) -> dict:
    """Persist profile_path as the default Chrome profile fetch_article
    uses whenever a caller omits chrome_profile. Raises ValueError if
    profile_path does not exist or is not a directory — never silently
    accepts a bad path."""
    path = Path(profile_path)
    if not path.is_dir():
        raise ValueError(
            f"chrome_profile path does not exist or is not a directory: {profile_path}"
        )
    config.set_default_chrome_profile(_data_dir(), profile_path)
    return {"ok": True}
```

- [ ] **Step 6: Write the failing MCP-protocol tests**

Append to `tools/browser-fetch-mcp/tests/test_server.py`:

```python
async def test_get_default_chrome_profile_returns_none_initially(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_default_chrome_profile", {})
            payload = result.structured_content or json.loads(result.content[0].text)
            assert payload["profile_path"] is None


async def test_set_default_chrome_profile_then_get_round_trips(tmp_path):
    profile_dir = tmp_path / "SomeChromeProfile"
    profile_dir.mkdir()
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            set_result = await session.call_tool(
                "set_default_chrome_profile", {"profile_path": str(profile_dir)}
            )
            assert set_result.is_error is not True

            get_result = await session.call_tool("get_default_chrome_profile", {})
            payload = get_result.structured_content or json.loads(get_result.content[0].text)
            assert payload["profile_path"] == str(profile_dir)


async def test_set_default_chrome_profile_rejects_nonexistent_path(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "set_default_chrome_profile", {"profile_path": str(tmp_path / "DoesNotExist")}
            )
            assert result.is_error is True
```

Note: `test_server.py` already imports `json`, `stdio_client`, `ClientSession`, and defines `_server_params(tmp_path)` — reuse them, don't redefine.

- [ ] **Step 7: Run tests to verify they fail then pass**

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/test_server.py -v -k "default_chrome_profile"`
Expected first (before Step 5, if run out of order): FAIL — tool not found. After Step 5: 3 passed.

Run the full server test suite to confirm no regressions:
Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/ -v`
Expected: all passing (existing tests plus the new 7).

- [ ] **Step 8: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/config.py \
        tools/browser-fetch-mcp/browser_fetch_mcp/server.py \
        tools/browser-fetch-mcp/tests/test_config.py \
        tools/browser-fetch-mcp/tests/test_server.py
git commit -m "feat(browser-fetch-mcp): add persisted default chrome profile"
```

---

### Task 2: `list_chrome_profiles` MCP tool (generalized profile discovery)

**Files:**
- Create: `tools/browser-fetch-mcp/browser_fetch_mcp/profiles.py`
- Create: `tools/browser-fetch-mcp/tests/test_profiles.py`
- Modify: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`
- Modify: `tools/browser-fetch-mcp/tests/test_server.py`

**Interfaces:**
- Produces: `profiles.list_chrome_profiles(host_keys: list[str], cookie_names: list[str]) -> list[dict]`, where each dict is `{"profile_path": str, "account_email": str, "matched_cookie_names": list[str], "looks_logged_in": bool}`. `looks_logged_in` is `True` iff at least one of `cookie_names` was found among the cookies matched by `host_keys` (same "any overlap" semantics as today's `detect_xcom_chrome_profile.py`, not "all present").
- Produces: one new `@mcp.tool()` function in `server.py`, `list_chrome_profiles(host_keys: list[str], cookie_names: list[str]) -> dict` (returns `{"profiles": [...]}`).
- Consumes: nothing from Task 1 (independent).

- [ ] **Step 1: Write the failing unit tests**

Create `tools/browser-fetch-mcp/tests/test_profiles.py`:

```python
"""Unit tests for profiles.py's Chrome profile discovery — uses
BROWSER_FETCH_MCP_CHROME_BASE to point at a fake profile directory tree
instead of touching a real Chrome install. Existence-only: no cookie
value is ever decrypted here, only cookie *names* are checked."""
import os
import sqlite3
from pathlib import Path

from browser_fetch_mcp.profiles import list_chrome_profiles

HOST_KEYS = [".x.com", ".twitter.com"]
COOKIE_NAMES = ["auth_token", "ct0", "twid"]


def _make_cookies_db(path: Path, rows):
    """rows: list of (name, host_key) tuples"""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cookies (name TEXT, host_key TEXT)")
    conn.executemany("INSERT INTO cookies (name, host_key) VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


def test_no_chrome_dir_returns_empty_list(tmp_path, monkeypatch):
    nonexistent = tmp_path / "NoChromeHere"
    monkeypatch.setenv("BROWSER_FETCH_MCP_CHROME_BASE", str(nonexistent))
    assert list_chrome_profiles(HOST_KEYS, COOKIE_NAMES) == []


def test_profile_with_no_cookies_db_is_listed_but_not_logged_in(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    (chrome_base / "Default").mkdir(parents=True)
    monkeypatch.setenv("BROWSER_FETCH_MCP_CHROME_BASE", str(chrome_base))

    result = list_chrome_profiles(HOST_KEYS, COOKIE_NAMES)
    assert len(result) == 1
    assert result[0]["matched_cookie_names"] == []
    assert result[0]["looks_logged_in"] is False


def test_profile_with_auth_cookies_is_marked_logged_in(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    _make_cookies_db(
        default_dir / "Cookies",
        [("auth_token", ".x.com"), ("ct0", ".x.com"), ("some_other_cookie", ".example.com")],
    )
    monkeypatch.setenv("BROWSER_FETCH_MCP_CHROME_BASE", str(chrome_base))

    result = list_chrome_profiles(HOST_KEYS, COOKIE_NAMES)
    assert len(result) == 1
    assert result[0]["profile_path"] == str(default_dir)
    assert set(result[0]["matched_cookie_names"]) == {"auth_token", "ct0"}
    assert result[0]["looks_logged_in"] is True
    assert "some_other_cookie" not in result[0]["matched_cookie_names"]


def test_profile_with_unrelated_cookies_only_is_not_logged_in(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    _make_cookies_db(
        default_dir / "Cookies",
        [("session_id", ".x.com")],  # present but not one of cookie_names
    )
    monkeypatch.setenv("BROWSER_FETCH_MCP_CHROME_BASE", str(chrome_base))

    result = list_chrome_profiles(HOST_KEYS, COOKIE_NAMES)
    assert result[0]["matched_cookie_names"] == ["session_id"]
    assert result[0]["looks_logged_in"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/test_profiles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'browser_fetch_mcp.profiles'`.

- [ ] **Step 3: Implement `profiles.py`**

Create `tools/browser-fetch-mcp/browser_fetch_mcp/profiles.py`:

```python
"""Chrome profile discovery — lists local Chrome profiles and checks,
by cookie NAME only (no decryption), whether each looks logged into a
caller-supplied set of hosts. Generalizes extract-url-mcp's original
detect_xcom_chrome_profile.py (which hardcoded X.com's host_keys and
cookie names) into parameters, so other consumers can reuse it for a
different site later.
"""
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


def _chrome_base() -> Path:
    override = os.environ.get("BROWSER_FETCH_MCP_CHROME_BASE")
    return (
        Path(override)
        if override
        else Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    )


def _profile_email(profile_dir: Path) -> str:
    prefs = profile_dir / "Preferences"
    try:
        data = json.loads(prefs.read_text(errors="ignore"))
        accounts = data.get("account_info", [])
        if accounts:
            return accounts[0].get("email", "")
        return data.get("user_name", "")
    except Exception:
        return ""


def _matching_cookie_names(profile_dir: Path, host_keys: list[str]) -> set[str]:
    cookies_db = profile_dir / "Cookies"
    if not cookies_db.exists():
        return set()

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        shutil.copy2(cookies_db, tmp_path)
        conn = sqlite3.connect(tmp_path)
        try:
            cur = conn.cursor()
            placeholders = ",".join("?" * len(host_keys))
            cur.execute(
                f"SELECT DISTINCT name FROM cookies WHERE host_key IN ({placeholders})",
                host_keys,
            )
            return {row[0] for row in cur.fetchall()}
        finally:
            conn.close()
    except Exception:
        return set()
    finally:
        os.unlink(tmp_path)


def list_chrome_profiles(host_keys: list[str], cookie_names: list[str]) -> list[dict]:
    """Scan local Chrome profiles, returning one dict per profile:
    {"profile_path", "account_email", "matched_cookie_names", "looks_logged_in"}.

    looks_logged_in is True iff ANY of cookie_names was found among the
    cookies matched by host_keys in that profile — same "any match"
    semantics as the script this generalizes. Existence-only: cookie
    values are never decrypted here.
    """
    chrome_base = _chrome_base()
    if not chrome_base.exists():
        return []

    profile_dirs = sorted(
        (
            d
            for d in chrome_base.iterdir()
            if d.is_dir() and (d.name == "Default" or d.name.startswith("Profile"))
        ),
        key=lambda d: (d.name != "Default", d.name),
    )

    required = set(cookie_names)
    results = []
    for profile_dir in profile_dirs:
        found = _matching_cookie_names(profile_dir, host_keys)
        results.append(
            {
                "profile_path": str(profile_dir),
                "account_email": _profile_email(profile_dir),
                "matched_cookie_names": sorted(found),
                "looks_logged_in": bool(required & found),
            }
        )
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/test_profiles.py -v`
Expected: 4 passed.

- [ ] **Step 5: Add the MCP tool to `server.py`**

In `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`, add the import alongside the others:

```python
from browser_fetch_mcp.profiles import list_chrome_profiles as _list_chrome_profiles
```

Add this tool after `set_default_chrome_profile` (before `fetch_article`):

```python
@mcp.tool()
async def list_chrome_profiles(host_keys: list[str], cookie_names: list[str]) -> dict:
    """List local Chrome profiles and, for each, which of cookie_names
    exist for the given host_keys (existence-only, never decrypted).
    Returns {"profiles": [{"profile_path", "account_email",
    "matched_cookie_names", "looks_logged_in"}, ...]}. Callers decide
    which profile to recommend/use — this tool never picks one."""
    profiles = await asyncio.to_thread(_list_chrome_profiles, host_keys, cookie_names)
    return {"profiles": profiles}
```

- [ ] **Step 6: Write the failing MCP-protocol test**

Append to `tools/browser-fetch-mcp/tests/test_server.py`:

```python
async def test_list_chrome_profiles_via_mcp_protocol(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    monkeypatch.setenv("BROWSER_FETCH_MCP_CHROME_BASE", str(chrome_base))

    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "list_chrome_profiles",
                {"host_keys": [".x.com"], "cookie_names": ["auth_token"]},
            )
            payload = result.structured_content or json.loads(result.content[0].text)
            assert len(payload["profiles"]) == 1
            assert payload["profiles"][0]["profile_path"] == str(default_dir)
            assert payload["profiles"][0]["looks_logged_in"] is False
```

Note: `monkeypatch.setenv` affects the test process, not the subprocess `stdio_client` spawns — `_server_params` builds the subprocess `env` from `os.environ` at call time, so setting the env var via `monkeypatch.setenv` *before* calling `_server_params(tmp_path)` is what makes it visible to the spawned server. Keep that ordering.

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/test_server.py -v -k "list_chrome_profiles"`
Expected: 1 passed.

Run the full server test suite to confirm no regressions:
Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/ -v`
Expected: all passing.

- [ ] **Step 8: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/profiles.py \
        tools/browser-fetch-mcp/browser_fetch_mcp/server.py \
        tools/browser-fetch-mcp/tests/test_profiles.py \
        tools/browser-fetch-mcp/tests/test_server.py
git commit -m "feat(browser-fetch-mcp): add list_chrome_profiles MCP tool"
```

---

### Task 3: `fetch_article` resolves the persisted default at its existing per-site decision points

**Files:**
- Modify: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py:172-302` (the `fetch_article` function)
- Modify: `tools/browser-fetch-mcp/tests/test_fetch_article.py`

**Interfaces:**
- Consumes: `config.get_default_chrome_profile(data_dir)` from Task 1.
- Produces: no new public interface — `fetch_article`'s signature is unchanged (`chrome_profile: Optional[str] = None` stays optional); only its internal resolution of that parameter changes.

- [ ] **Step 1: Write the failing tests**

Append to `tools/browser-fetch-mcp/tests/test_fetch_article.py`:

```python
async def _set_default_chrome_profile(session, profile_dir: Path):
    result = await session.call_tool(
        "set_default_chrome_profile", {"profile_path": str(profile_dir)}
    )
    assert result.is_error is not True


async def test_fetch_article_x_dot_com_falls_back_to_persisted_default(tmp_path):
    """No chrome_profile passed, but a default is configured — fetch_article
    must get PAST the 'chrome_profile is required' check and reach the
    auth-cookie check instead (which then fails for this empty profile,
    proving resolution happened rather than an early required-param error)."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _set_default_chrome_profile(session, default_profile)

            result, _ = await _call_fetch_article(
                session,
                url="https://x.com/someuser/status/123",
                output_dir=str(output_dir),
            )
    assert result.is_error is True
    assert "No x.com session cookies" in result.content[0].text
    assert "is required" not in result.content[0].text


async def test_fetch_article_explicit_chrome_profile_wins_over_configured_default(tmp_path):
    """An explicitly-passed chrome_profile must be used as-is, never
    overridden by a configured default."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    explicit_profile = tmp_path / "ExplicitProfile"
    explicit_profile.mkdir()
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _set_default_chrome_profile(session, default_profile)

            result, _ = await _call_fetch_article(
                session,
                url="https://x.com/someuser/status/123",
                output_dir=str(output_dir),
                chrome_profile=str(explicit_profile),
            )
    assert result.is_error is True
    assert f"No x.com session cookies in {explicit_profile}" in result.content[0].text


async def test_fetch_article_thin_retry_uses_persisted_default_when_omitted(tmp_path):
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _set_default_chrome_profile(session, default_profile)

            _, payload = await _call_fetch_article(
                session,
                url="https://example.com",
                output_dir=str(output_dir),
            )
    assert payload["thin_retry_used"] is True
    assert payload["cookies_injected"] == 0


async def test_fetch_article_non_thin_result_ignores_configured_default(tmp_path):
    """A configured default must NOT force cookie use on content that
    isn't thin — the per-site opportunistic-retry policy is unchanged."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _set_default_chrome_profile(session, default_profile)

            _, payload = await _call_fetch_article(
                session,
                url="https://en.wikipedia.org/wiki/Model_Context_Protocol",
                output_dir=str(output_dir),
            )
    assert payload["thin_retry_used"] is False
    assert payload["cookies_injected"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/test_fetch_article.py -v -k "default"`
Expected: FAIL — `test_fetch_article_x_dot_com_falls_back_to_persisted_default` fails because today's code still raises "chrome_profile is required" (the default is never consulted); the thin-retry test fails because `thin_retry_used` stays `False` (today's code only retries when `chrome_profile` was explicitly passed).

- [ ] **Step 3: Implement the resolution point in `fetch_article`**

In `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`, inside `fetch_article`, immediately after the existing URL-scheme validation block:

```python
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(f"Rejected URL with scheme '{parsed_url.scheme}' — only http/https allowed")

    effective_chrome_profile = chrome_profile or config.get_default_chrome_profile(_data_dir())

    site = dispatch_site(url)
```

Then, in the rest of the function, replace every remaining use of the bare `chrome_profile` parameter with `effective_chrome_profile`:

- `if site == "xcom": if not chrome_profile:` → `if not effective_chrome_profile:`
- `cookies_dict = await asyncio.to_thread(extract_cookies, "https://x.com", chrome_profile)` → `..., effective_chrome_profile)`
- `f"No x.com session cookies in {chrome_profile} — "` → `f"No x.com session cookies in {effective_chrome_profile} — "`
- `if chrome_profile and is_thin(result):` → `if effective_chrome_profile and is_thin(result):`
- `auth_key = _profile_key(chrome_profile)` → `auth_key = _profile_key(effective_chrome_profile)`
- `cookies_dict = extract_cookies(url, chrome_profile)` (inside the `else` branch's thin-retry block) → `extract_cookies(url, effective_chrome_profile)`

Do not change the function's parameter name or default (`chrome_profile: Optional[str] = None` stays as-is) — only the body's variable usage changes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/test_fetch_article.py -v`
Expected: all passing, including the 4 new tests and all pre-existing ones (in particular `test_fetch_article_x_dot_com_without_chrome_profile_is_rejected` must still pass unchanged — no default is configured in that test's isolated `tmp_path`, so `effective_chrome_profile` resolves to `None` and the same error fires).

Run the full server test suite to confirm no regressions:
Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/ -v`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py \
        tools/browser-fetch-mcp/tests/test_fetch_article.py
git commit -m "feat(browser-fetch-mcp): fetch_article resolves persisted default chrome_profile"
```

---

### Task 4: `extract-url-mcp` — replace local Chrome-DB detection with MCP calls, simplify the setup gate

**Files:**
- Modify: `skills/research/extract-url-mcp/scripts/detect_xcom_chrome_profile.py` (rewritten from sqlite-querying script to MCP-client script)
- Create: `skills/research/extract-url-mcp/scripts/chrome_profile_config.py`
- Modify: `skills/research/extract-url-mcp/tests/test_detect_xcom_chrome_profile.py` (rewritten for the MCP-backed script)
- Create: `skills/research/extract-url-mcp/tests/test_chrome_profile_config.py`
- Modify: `skills/research/extract-url-mcp/SKILL.md`

**Interfaces:**
- Consumes: the `list_chrome_profiles`, `get_default_chrome_profile`, `set_default_chrome_profile` MCP tools from Tasks 1–2 (via the same `stdio_client`/`ClientSession` pattern `mcp_fetch_client.py` already uses, including its `isError`/`structuredContent` camelCase note — this environment runs mcp 1.28.1).
- Produces: `detect_xcom_chrome_profile.py`'s CLI output contract is preserved (`RECOMMENDED_PROFILE: <path>` or `RECOMMENDED_PROFILE: (none found)`, plus the comparison table) so `SKILL.md`'s existing instruction to "show the full output" keeps working. `chrome_profile_config.py`'s CLI contract: `get` prints `CONFIGURED: <path>` or `NOT_CONFIGURED`; `set <path>` prints `OK` on success or an error message to stderr and exits 1 on failure.

- [ ] **Step 1: Write the failing tests for the rewritten `detect_xcom_chrome_profile.py`**

Replace the contents of `skills/research/extract-url-mcp/tests/test_detect_xcom_chrome_profile.py`:

```python
"""Tests for the MCP-backed detect_xcom_chrome_profile.py — real
browser-fetch-mcp subprocess, real MCP stdio protocol, fixture Chrome
profile dirs via BROWSER_FETCH_MCP_CHROME_BASE (never touches a real
Chrome install).

Run: python3 -m pytest skills/research/extract-url-mcp/tests/ -v
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "detect_xcom_chrome_profile.py"


def _make_cookies_db(path: Path, rows):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cookies (name TEXT, host_key TEXT)")
    conn.executemany("INSERT INTO cookies (name, host_key) VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


def _run(chrome_base: Path, data_dir: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={
            **os.environ,
            "BROWSER_FETCH_MCP_CHROME_BASE": str(chrome_base),
            "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir),
        },
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_no_chrome_dir_reports_none_found(tmp_path):
    output = _run(tmp_path / "NoChromeHere", tmp_path / "data")
    assert "RECOMMENDED_PROFILE: (none found)" in output


def test_profile_with_no_cookies_db_reports_none_found(tmp_path):
    chrome_base = tmp_path / "Chrome"
    (chrome_base / "Default").mkdir(parents=True)
    output = _run(chrome_base, tmp_path / "data")
    assert "(no X.com cookies)" in output
    assert "RECOMMENDED_PROFILE: (none found)" in output


def test_profile_with_auth_cookies_is_recommended(tmp_path):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    _make_cookies_db(
        default_dir / "Cookies",
        [("auth_token", ".x.com"), ("ct0", ".x.com"), ("some_other_cookie", ".example.com")],
    )
    output = _run(chrome_base, tmp_path / "data")
    assert "auth_token" in output
    assert "looks logged in" in output
    assert f"RECOMMENDED_PROFILE: {default_dir}" in output
    assert "some_other_cookie" not in output


def test_profile_with_unrelated_cookies_only_is_not_recommended(tmp_path):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    _make_cookies_db(
        default_dir / "Cookies",
        [("session_id", ".x.com")],
    )
    output = _run(chrome_base, tmp_path / "data")
    assert "session_id" in output
    assert "looks logged in" not in output
    assert "RECOMMENDED_PROFILE: (none found)" in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest skills/research/extract-url-mcp/tests/test_detect_xcom_chrome_profile.py -v`
Expected: FAIL (or unreliably pass/fail depending on the machine's real Chrome install) — today's script reads `EXTRACT_URL_MCP_CHROME_BASE`, not `BROWSER_FETCH_MCP_DATA_DIR`/`BROWSER_FETCH_MCP_CHROME_BASE`, and queries sqlite directly instead of going through MCP. Since the new tests only set the new env vars, today's script ignores them entirely and falls through to scanning the real `~/Library/Application Support/Google/Chrome` path instead of the test's fixture dir — non-deterministic against these fixture-based assertions. Proceed to Step 3's rewrite regardless of the exact failure observed.

- [ ] **Step 3: Rewrite `detect_xcom_chrome_profile.py` to call the MCP tools**

Replace the contents of `skills/research/extract-url-mcp/scripts/detect_xcom_chrome_profile.py`:

```python
#!/usr/bin/env python3
"""
Detect which Chrome profile(s) are logged into X.com (Twitter), via
browser-fetch-mcp's list_chrome_profiles MCP tool — no direct sqlite
access here anymore; the cookie-scanning logic now lives in
tools/browser-fetch-mcp/browser_fetch_mcp/profiles.py.

Usage: python3 detect_xcom_chrome_profile.py
Prints a human-readable comparison table, then one line:
  RECOMMENDED_PROFILE: <path>
or, if no profile has any of the known auth cookies:
  RECOMMENDED_PROFILE: (none found)

This script only reports candidates — it never picks one automatically
for a caller. Detection and use MUST stay separated: whoever calls this
script must show the result to a human and get explicit confirmation
before persisting a profile via chrome_profile_config.py.

NOTE ON mcp SDK VERSION: see mcp_fetch_client.py's docstring — this
script runs under the ambient system Python (mcp 1.28.1, camelCase
isError/structuredContent), same as mcp_fetch_client.py.
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BROWSER_FETCH_MCP_SH = (
    Path(__file__).resolve().parents[4] / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
)

HOST_KEYS = [".x.com", ".twitter.com"]
COOKIE_NAMES = ["auth_token", "ct0", "twid"]


async def _list_profiles() -> list[dict]:
    server_params = StdioServerParameters(command=str(BROWSER_FETCH_MCP_SH), args=[])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "list_chrome_profiles", {"host_keys": HOST_KEYS, "cookie_names": COOKIE_NAMES}
            )
            if result.isError:
                raise RuntimeError(f"list_chrome_profiles failed: {result.content[0].text}")
            payload = result.structuredContent or json.loads(result.content[0].text)
            return payload["profiles"]


def main():
    profiles = asyncio.run(_list_profiles())

    if not profiles:
        print("No Chrome profiles found.")
        print("RECOMMENDED_PROFILE: (none found)")
        return

    print(f"{'Profile':<50} {'Account':<38} {'X.com cookies found'}")
    print("-" * 110)

    recommended = None
    for p in profiles:
        email = p["account_email"] or "(not logged into Google)"
        names = p["matched_cookie_names"]
        status = ", ".join(names) if names else "(no X.com cookies)"
        marker = " <-- looks logged in" if p["looks_logged_in"] else ""
        print(f"{p['profile_path']:<50} {email:<38} {status}{marker}")
        if p["looks_logged_in"] and recommended is None:
            recommended = p["profile_path"]

    print()
    if recommended:
        print(f"RECOMMENDED_PROFILE: {recommended}")
    else:
        print("RECOMMENDED_PROFILE: (none found)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest skills/research/extract-url-mcp/tests/test_detect_xcom_chrome_profile.py -v`
Expected: 4 passed.

- [ ] **Step 5: Write the failing tests for the new `chrome_profile_config.py`**

Create `skills/research/extract-url-mcp/tests/test_chrome_profile_config.py`:

```python
"""Tests for chrome_profile_config.py — real browser-fetch-mcp
subprocess, real MCP stdio protocol, BROWSER_FETCH_MCP_DATA_DIR pointed
at an isolated tmp_path (never touches the real ~/.hskill config).

Run: python3 -m pytest skills/research/extract-url-mcp/tests/ -v
"""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "chrome_profile_config.py"


def _run(args: list[str], data_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={**os.environ, "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir)},
        capture_output=True, text=True, timeout=30,
    )


def test_get_reports_not_configured_initially(tmp_path):
    result = _run(["get"], tmp_path / "data")
    assert result.returncode == 0, result.stderr
    assert "NOT_CONFIGURED" in result.stdout


def test_set_then_get_reports_configured(tmp_path):
    data_dir = tmp_path / "data"
    profile_dir = tmp_path / "SomeProfile"
    profile_dir.mkdir()

    set_result = _run(["set", str(profile_dir)], data_dir)
    assert set_result.returncode == 0, set_result.stderr
    assert "OK" in set_result.stdout

    get_result = _run(["get"], data_dir)
    assert f"CONFIGURED: {profile_dir}" in get_result.stdout


def test_set_rejects_nonexistent_path(tmp_path):
    data_dir = tmp_path / "data"
    result = _run(["set", str(tmp_path / "DoesNotExist")], data_dir)
    assert result.returncode == 1
    assert result.stderr.strip() != ""
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `python3 -m pytest skills/research/extract-url-mcp/tests/test_chrome_profile_config.py -v`
Expected: FAIL with `FileNotFoundError` (script doesn't exist yet).

- [ ] **Step 7: Implement `chrome_profile_config.py`**

Create `skills/research/extract-url-mcp/scripts/chrome_profile_config.py`:

```python
#!/usr/bin/env python3
"""Thin MCP-client CLI for reading/writing browser-fetch-mcp's persisted
default Chrome profile (get_default_chrome_profile / set_default_chrome_profile
tools). Written from scratch, same stdio_client pattern as mcp_fetch_client.py
and detect_xcom_chrome_profile.py.

Usage:
  python3 chrome_profile_config.py get
  python3 chrome_profile_config.py set <profile_path>

get prints "CONFIGURED: <path>" or "NOT_CONFIGURED".
set prints "OK" on success; on failure, prints the error to stderr and
exits 1 (e.g. profile_path doesn't exist or isn't a directory).
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BROWSER_FETCH_MCP_SH = (
    Path(__file__).resolve().parents[4] / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
)


async def _get() -> str:
    server_params = StdioServerParameters(command=str(BROWSER_FETCH_MCP_SH), args=[])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_default_chrome_profile", {})
            if result.isError:
                raise RuntimeError(f"get_default_chrome_profile failed: {result.content[0].text}")
            payload = result.structuredContent or json.loads(result.content[0].text)
            profile_path = payload["profile_path"]
            return f"CONFIGURED: {profile_path}" if profile_path else "NOT_CONFIGURED"


async def _set(profile_path: str) -> str:
    server_params = StdioServerParameters(command=str(BROWSER_FETCH_MCP_SH), args=[])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "set_default_chrome_profile", {"profile_path": profile_path}
            )
            if result.isError:
                raise RuntimeError(f"set_default_chrome_profile failed: {result.content[0].text}")
            return "OK"


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("get", "set"):
        print("Usage: chrome_profile_config.py get | set <profile_path>", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "get":
        print(asyncio.run(_get()))
        return

    if len(sys.argv) < 3:
        print("Usage: chrome_profile_config.py set <profile_path>", file=sys.stderr)
        sys.exit(1)

    try:
        print(asyncio.run(_set(sys.argv[2])))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python3 -m pytest skills/research/extract-url-mcp/tests/test_chrome_profile_config.py -v`
Expected: 3 passed.

Run the full extract-url-mcp test suite to confirm no regressions:
Run: `python3 -m pytest skills/research/extract-url-mcp/tests/ -v`
Expected: all passing.

- [ ] **Step 9: Rewrite `SKILL.md`'s step 2 and simplify step 3**

In `skills/research/extract-url-mcp/SKILL.md`, replace the entire "步骤 2" section (currently the hostname-gated detect-and-ask flow) with:

```markdown
### 步骤 2：确认默认 chrome_profile（首次使用时设置一次，之后不再询问）

运行 `python3 SkillDir/scripts/chrome_profile_config.py get`。

- 若输出 `CONFIGURED: <path>`：已经配置过默认 profile，跳过下面的检测和提问，直接进入步骤 3。
- 若输出 `NOT_CONFIGURED`（不论当前 URL 是什么网站，只要还没配置过就会命中这一分支）：
  1. 运行 `python3 SkillDir/scripts/detect_xcom_chrome_profile.py`，把完整输出（对比表 + `RECOMMENDED_PROFILE:` 那行）原样展示给用户。
  2. 向用户提问：把推荐的 profile 设为以后的默认值？或输入一个替代路径？也可以选择这次先不设置。
  3. 若用户提供了 profile 路径（推荐的或自己输入的）：运行 `python3 SkillDir/scripts/chrome_profile_config.py set <path>` 持久化。此后所有网站的抓取都不会再触发这个设置流程。
  4. 若用户选择不设置：不持久化任何值，本次继续（x.com 的 URL 会在 Subagent 1 里因为 browser-fetch-mcp 的 `fetch_article` 报错而失败——x.com 没有匿名抓取选项；非 x.com 的 URL 正常匿名抓取，不受影响）。

**不允许**：跳过展示直接把探测到的 profile 设为默认值——必须等用户明确回答，且只有用户确认后才能调用 `chrome_profile_config.py set`。
```

Then update "步骤 3"（派发 Subagent 1）— remove the reference to a per-call `chrome_profile` decision (that decision no longer varies by URL; `fetch_article` resolves the persisted default itself when nothing is passed). Replace the existing 步骤 3 paragraph with:

```markdown
### 步骤 3：派发 Subagent 1（MCP 抓取）

读取 `references/subagent1-fetch-prompt.md`，将其中 `<URL>` 替换为 url_safe，`<OUTPUT_DIR>` 替换为一个输出目录（没有正式的 VAULT_PATH 配置流程，调用方直接指定一个测试目录，不写真实 Obsidian Vault），`<CHROME_PROFILE>` 替换为空（不留任何字符）——browser-fetch-mcp 的 `fetch_article` 会自己解析已持久化的默认 chrome_profile，不需要这里显式传值，按当前平台的 subagent 派发机制派发。
```

Renumber the remaining steps (old 步骤 4/5/6 stay as 步骤 4/5/6 — only the content of 步骤 2 and 步骤 3 changed, not the count), and update the frontmatter version and description:

```yaml
version: "0.4.0"
description: "Stage 4 validation build — NOT for real use. Fetches a URL through browser-fetch-mcp's fetch_article (site-aware extraction: generic/wechat/arxiv/xcom, with image download and a persisted default chrome_profile), tags, translates, and saves origin + translation. Proves the MCP-based fetch path — including MCP-side chrome-profile detection and persistence — works end to end inside a two-subagent flow shaped like extract-url."
```

Update the reference table at the bottom of `SKILL.md` to add the new script and adjust the description of `detect_xcom_chrome_profile.py`:

```markdown
| `scripts/mcp_fetch_client.py` | 核心脚本：真实 MCP client，调用 browser-fetch-mcp 的 `fetch_article` |
| `scripts/detect_xcom_chrome_profile.py` | 通过 browser-fetch-mcp 的 `list_chrome_profiles` MCP 工具检测哪些 Chrome profile 登录了 x.com，仅供用户确认用，不自动使用检测结果 |
| `scripts/chrome_profile_config.py` | 读写 browser-fetch-mcp 持久化的默认 chrome_profile（`get`/`set` 子命令） |
```

- [ ] **Step 10: Run the full test suite one more time**

Run: `python3 -m pytest skills/research/extract-url-mcp/tests/ -v`
Expected: all passing.

Run: `cd tools/browser-fetch-mcp && python3 -m pytest tests/ -v`
Expected: all passing.

Run: `npm test` (from repo root)
Expected: all passing (hskill CLI tests + custom skill tests, including `skills/research/extract-url-mcp`'s suite).

- [ ] **Step 11: Commit**

```bash
git add skills/research/extract-url-mcp/scripts/detect_xcom_chrome_profile.py \
        skills/research/extract-url-mcp/scripts/chrome_profile_config.py \
        skills/research/extract-url-mcp/tests/test_detect_xcom_chrome_profile.py \
        skills/research/extract-url-mcp/tests/test_chrome_profile_config.py \
        skills/research/extract-url-mcp/SKILL.md
git commit -m "feat(extract-url-mcp): use MCP-side chrome profile detection + persisted default"
```
