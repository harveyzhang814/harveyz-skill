# sync-agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-part sync tool — a `hskill sync` CLI that manages the Syncthing daemon lifecycle and initial setup, plus a `/sync-agent` Skill that lets Agent manage folders/devices at runtime via the Syncthing REST API.

**Architecture:** The hskill tool (`tools/sync-agent/`) is a Python + Typer package following the same pattern as `tools/hub/`. It reads `~/.hskill/sync-agent/config.json` as its source of truth, writes runtime state to `~/.hskill/sync-agent/state.json`, and configures Syncthing via its REST API. The Skill (`skills/meta/sync-agent/SKILL.md`) reads `state.json` for the API key, operates Syncthing entirely via `curl` REST calls, and writes config changes back to `config.json`.

**Tech Stack:** Python 3.11+, Typer 0.12+, hatchling (build), pytest (tests), Syncthing v2.x REST API, launchd (macOS autostart), bash (shell entry script + Skill curl calls).

## Global Constraints

- Python ≥ 3.11 (same as hub)
- Syncthing v2.x REST API at `http://127.0.0.1:8384`
- Config: `~/.hskill/sync-agent/config.json` — source of truth, user-editable
- State: `~/.hskill/sync-agent/state.json` — auto-generated, never hand-edited
- Tool name: `sync` (invoked as `hskill sync <subcommand>`)
- launchd plist: `~/Library/LaunchAgents/com.harveyz.syncthing.plist`
- Syncthing log: `~/.hskill/sync-agent/syncthing.log`
- `hskill sync status` shows API key as first 4 chars + `****` (never plaintext)
- All REST failures print HTTP status + response body; no silent failures
- Skill does NOT start/stop the daemon — only reports an error if it's not running

---

## File Map

**Create:**
- `tools/sync-agent/tool.json` — hskill tool metadata
- `tools/sync-agent/sync_agent.sh` — shell entry script (mirrors hub.sh pattern)
- `tools/sync-agent/pyproject.toml` — Python package config
- `tools/sync-agent/sync_agent/__init__.py` — package init
- `tools/sync-agent/sync_agent/__main__.py` — entry point
- `tools/sync-agent/sync_agent/config.py` — read/write `config.json` and `state.json`
- `tools/sync-agent/sync_agent/syncthing.py` — Syncthing REST API client
- `tools/sync-agent/sync_agent/launchd.py` — launchd plist install/uninstall
- `tools/sync-agent/sync_agent/cli.py` — Typer app: `start`, `stop`, `status`, `setup`
- `tools/sync-agent/tests/__init__.py`
- `tools/sync-agent/tests/test_config.py`
- `tools/sync-agent/tests/test_syncthing.py`
- `tools/sync-agent/tests/test_cli.py`
- `skills/meta/sync-agent/SKILL.md` — Agent skill

**Modify:**
- `skills-index.json` — register the new skill

---

## Task 1: Project Scaffold

**Files:**
- Create: `tools/sync-agent/tool.json`
- Create: `tools/sync-agent/sync_agent.sh`
- Create: `tools/sync-agent/pyproject.toml`
- Create: `tools/sync-agent/sync_agent/__init__.py`
- Create: `tools/sync-agent/sync_agent/__main__.py`
- Create: `tools/sync-agent/tests/__init__.py`

**Interfaces:**
- Produces: `hskill sync --help` runs without error

- [ ] **Step 1: Create `tool.json`**

```json
{
  "name": "sync",
  "version": "1.0.0",
  "description": "Syncthing daemon lifecycle and initial folder/device setup",
  "extraPaths": ["sync_agent", "pyproject.toml"],
  "uninstallPaths": ["~/.hskill/tools/sync-agent/venv", "~/.hskill/tools/sync-agent"],
  "configPaths": ["~/.hskill/sync-agent"]
}
```

- [ ] **Step 2: Create `sync_agent.sh`** (entry script, mirrors hub.sh)

```bash
#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "${SCRIPT_DIR}/sync_agent" ] && [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
  DEV_VENV="${SCRIPT_DIR}/.venv"
  if [ ! -x "${DEV_VENV}/bin/sync-agent" ]; then
    python3 -m venv "${DEV_VENV}"
    "${DEV_VENV}/bin/pip" install -q -e "${SCRIPT_DIR}"
  fi
  exec "${DEV_VENV}/bin/sync-agent" "$@"
fi

VENV_DIR="${HOME}/.hskill/tools/sync-agent/venv"
INSTALL_DIR="${HOME}/.hskill/tools/sync-agent"
HASH_FILE="${VENV_DIR}/.installed_hash"

_hash_source() {
  find "${INSTALL_DIR}" -type f \( -name "*.py" -o -name "*.toml" -o -name "*.json" \) \
    ! -path "*/__pycache__/*" \
    | sort | xargs sha256sum 2>/dev/null | sha256sum | awk '{print $1}'
}

CURRENT_HASH=$(_hash_source)

if [ ! -x "${VENV_DIR}/bin/sync-agent" ] || [ "$(cat "${HASH_FILE}" 2>/dev/null)" != "${CURRENT_HASH}" ]; then
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install -q --upgrade "${INSTALL_DIR}"
  echo "${CURRENT_HASH}" > "${HASH_FILE}"
fi

exec "${VENV_DIR}/bin/sync-agent" "$@"
```

Make executable: `chmod +x tools/sync-agent/sync_agent.sh`

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sync-agent"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
]

[project.scripts]
sync-agent = "sync_agent.__main__:main"

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.hatch.build.targets.wheel]
packages = ["sync_agent"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 4: Create `sync_agent/__init__.py`** (empty)

- [ ] **Step 5: Create `sync_agent/__main__.py`**

```python
from sync_agent.cli import app


def main():
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Create `tests/__init__.py`** (empty)

- [ ] **Step 7: Install dev venv and verify `--help` works**

```bash
cd tools/sync-agent
python3 -m venv .venv
.venv/bin/pip install -q -e ".[dev]"
.venv/bin/sync-agent --help
```

Expected: prints usage without error.

- [ ] **Step 8: Commit**

```bash
git add tools/sync-agent/
git commit -m "feat(sync-agent): scaffold hskill tool package"
```

---

## Task 2: Config Module

**Files:**
- Create: `tools/sync-agent/sync_agent/config.py`
- Create: `tools/sync-agent/tests/test_config.py`

**Interfaces:**
- Produces:
  - `Config` dataclass with `.folders: list[dict]` and `.devices: list[dict]`
  - `State` dataclass with `.api_key: str`, `.device_id: str`, `.api_url: str`
  - `load_config(base_dir: Path) -> Config`
  - `save_config(config: Config, base_dir: Path) -> None`
  - `load_state(base_dir: Path) -> State`
  - `save_state(state: State, base_dir: Path) -> None`
  - `default_base_dir() -> Path` — returns `Path.home() / ".hskill" / "sync-agent"`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import json
from pathlib import Path
import pytest
from sync_agent.config import (
    Config, State,
    load_config, save_config,
    load_state, save_state,
    default_base_dir,
)


@pytest.fixture
def base(tmp_path):
    return tmp_path


def test_load_config_missing_returns_empty(base):
    cfg = load_config(base)
    assert cfg.folders == []
    assert cfg.devices == []


def test_save_and_load_config(base):
    cfg = Config(
        folders=[{"id": "f1", "path": "~/docs", "label": "Docs"}],
        devices=[{"id": "ABC-DEF", "name": "laptop"}],
    )
    save_config(cfg, base)
    loaded = load_config(base)
    assert loaded.folders == cfg.folders
    assert loaded.devices == cfg.devices


def test_config_file_created_at_expected_path(base):
    cfg = Config(folders=[], devices=[])
    save_config(cfg, base)
    assert (base / "config.json").exists()


def test_load_state_missing_raises(base):
    with pytest.raises(FileNotFoundError):
        load_state(base)


def test_save_and_load_state(base):
    state = State(api_key="secret123", device_id="XX-YY", api_url="http://127.0.0.1:8384")
    save_state(state, base)
    loaded = load_state(base)
    assert loaded.api_key == "secret123"
    assert loaded.device_id == "XX-YY"
    assert loaded.api_url == "http://127.0.0.1:8384"


def test_default_base_dir_is_under_home():
    d = default_base_dir()
    assert d == Path.home() / ".hskill" / "sync-agent"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tools/sync-agent
.venv/bin/pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement `sync_agent/config.py`**

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Config:
    folders: list[dict] = field(default_factory=list)
    devices: list[dict] = field(default_factory=list)


@dataclass
class State:
    api_key: str
    device_id: str
    api_url: str


def default_base_dir() -> Path:
    return Path.home() / ".hskill" / "sync-agent"


def load_config(base_dir: Path) -> Config:
    path = base_dir / "config.json"
    if not path.exists():
        return Config()
    data = json.loads(path.read_text())
    return Config(
        folders=data.get("folders", []),
        devices=data.get("devices", []),
    )


def save_config(config: Config, base_dir: Path) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "config.json"
    path.write_text(json.dumps(asdict(config), indent=2) + "\n")


def load_state(base_dir: Path) -> State:
    path = base_dir / "state.json"
    if not path.exists():
        raise FileNotFoundError(f"state.json not found at {path}. Run: hskill sync setup")
    data = json.loads(path.read_text())
    return State(
        api_key=data["api_key"],
        device_id=data["device_id"],
        api_url=data["api_url"],
    )


def save_state(state: State, base_dir: Path) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / "state.json"
    path.write_text(json.dumps(asdict(state), indent=2) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_config.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/sync-agent/sync_agent/config.py tools/sync-agent/tests/test_config.py
git commit -m "feat(sync-agent): add config/state read-write module"
```

---

## Task 3: Syncthing REST Client

**Files:**
- Create: `tools/sync-agent/sync_agent/syncthing.py`
- Create: `tools/sync-agent/tests/test_syncthing.py`

**Interfaces:**
- Consumes: `State` from `sync_agent.config`
- Produces:
  - `SyncthingClient(api_url: str, api_key: str)`
  - `.ping() -> bool`
  - `.get_folders() -> list[dict]`
  - `.add_folder(folder: dict) -> None`
  - `.remove_folder(folder_id: str) -> None`
  - `.update_folder(folder_id: str, data: dict) -> None`
  - `.get_devices() -> list[dict]`
  - `.add_device(device: dict) -> None`
  - `.remove_device(device_id: str) -> None`
  - `.get_connections() -> dict`
  - `.get_completion(folder_id: str) -> float` — returns 0.0–100.0
  - `.scan_folder(folder_id: str) -> None`
  - `.get_my_device_id() -> str`
  - `.shutdown() -> None`
  - `SyncthingError(Exception)` — raised on HTTP 4xx/5xx

- [ ] **Step 1: Write failing tests**

```python
# tests/test_syncthing.py
from unittest.mock import patch, MagicMock
import pytest
from sync_agent.syncthing import SyncthingClient, SyncthingError


BASE = "http://127.0.0.1:8384"
KEY = "testkey"


def make_response(json_data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_data
    m.text = str(json_data)
    return m


@pytest.fixture
def client():
    return SyncthingClient(BASE, KEY)


def test_ping_returns_true_on_pong(client):
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.return_value = make_response({"ping": "pong"})
        assert client.ping() is True


def test_ping_returns_false_on_error(client):
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.side_effect = Exception("connection refused")
        assert client.ping() is False


def test_get_folders_returns_list(client):
    folders = [{"id": "f1", "path": "/tmp/docs"}]
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.return_value = make_response(folders)
        result = client.get_folders()
    assert result == folders


def test_add_folder_posts_to_api(client):
    folder = {"id": "f1", "path": "/tmp/docs", "label": "Docs"}
    with patch("sync_agent.syncthing.requests.post") as mock_post:
        mock_post.return_value = make_response({})
        client.add_folder(folder)
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["json"] == folder


def test_add_folder_raises_on_error(client):
    with patch("sync_agent.syncthing.requests.post") as mock_post:
        mock_post.return_value = make_response({"error": "bad"}, status=400)
        with pytest.raises(SyncthingError) as exc_info:
            client.add_folder({"id": "f1", "path": "/tmp"})
    assert "400" in str(exc_info.value)


def test_remove_folder_sends_delete(client):
    with patch("sync_agent.syncthing.requests.delete") as mock_del:
        mock_del.return_value = make_response({})
        client.remove_folder("f1")
    mock_del.assert_called_once()
    assert "f1" in mock_del.call_args[0][0]


def test_get_my_device_id(client):
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.return_value = make_response({"myID": "ABC-DEF-GHI"})
        assert client.get_my_device_id() == "ABC-DEF-GHI"


def test_get_completion(client):
    with patch("sync_agent.syncthing.requests.get") as mock_get:
        mock_get.return_value = make_response({"completion": 87.5})
        assert client.get_completion("f1") == 87.5


def test_shutdown_posts(client):
    with patch("sync_agent.syncthing.requests.post") as mock_post:
        mock_post.return_value = make_response({})
        client.shutdown()
    mock_post.assert_called_once()
    assert "shutdown" in mock_post.call_args[0][0]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_syncthing.py -v
```

Expected: `ModuleNotFoundError: No module named 'sync_agent.syncthing'`

- [ ] **Step 3: Add `requests` to `pyproject.toml` dependencies**

```toml
dependencies = [
    "typer>=0.12",
    "requests>=2.31",
]
```

Reinstall: `.venv/bin/pip install -q -e ".[dev]"`

- [ ] **Step 4: Implement `sync_agent/syncthing.py`**

```python
from __future__ import annotations
import requests


class SyncthingError(Exception):
    pass


class SyncthingClient:
    def __init__(self, api_url: str, api_key: str):
        self._base = api_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}

    def _url(self, path: str) -> str:
        return f"{self._base}/{path.lstrip('/')}"

    def _check(self, resp: requests.Response) -> requests.Response:
        if resp.status_code >= 400:
            raise SyncthingError(f"HTTP {resp.status_code}: {resp.text}")
        return resp

    def ping(self) -> bool:
        try:
            r = requests.get(self._url("/rest/system/ping"), headers=self._headers, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def get_folders(self) -> list[dict]:
        r = self._check(requests.get(self._url("/rest/config/folders"), headers=self._headers))
        return r.json()

    def add_folder(self, folder: dict) -> None:
        r = requests.post(self._url("/rest/config/folders"), headers=self._headers, json=folder)
        self._check(r)

    def remove_folder(self, folder_id: str) -> None:
        r = requests.delete(self._url(f"/rest/config/folders/{folder_id}"), headers=self._headers)
        self._check(r)

    def update_folder(self, folder_id: str, data: dict) -> None:
        r = requests.put(self._url(f"/rest/config/folders/{folder_id}"), headers=self._headers, json=data)
        self._check(r)

    def get_devices(self) -> list[dict]:
        r = self._check(requests.get(self._url("/rest/config/devices"), headers=self._headers))
        return r.json()

    def add_device(self, device: dict) -> None:
        r = requests.post(self._url("/rest/config/devices"), headers=self._headers, json=device)
        self._check(r)

    def remove_device(self, device_id: str) -> None:
        r = requests.delete(self._url(f"/rest/config/devices/{device_id}"), headers=self._headers)
        self._check(r)

    def get_connections(self) -> dict:
        r = self._check(requests.get(self._url("/rest/system/connections"), headers=self._headers))
        return r.json()

    def get_completion(self, folder_id: str) -> float:
        r = self._check(requests.get(
            self._url("/rest/db/completion"),
            headers=self._headers,
            params={"folder": folder_id},
        ))
        return r.json().get("completion", 0.0)

    def scan_folder(self, folder_id: str) -> None:
        r = requests.post(
            self._url("/rest/db/scan"),
            headers=self._headers,
            params={"folder": folder_id},
        )
        self._check(r)

    def get_my_device_id(self) -> str:
        r = self._check(requests.get(self._url("/rest/system/status"), headers=self._headers))
        return r.json()["myID"]

    def shutdown(self) -> None:
        r = requests.post(self._url("/rest/system/shutdown"), headers=self._headers)
        self._check(r)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_syncthing.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/sync-agent/sync_agent/syncthing.py tools/sync-agent/tests/test_syncthing.py tools/sync-agent/pyproject.toml
git commit -m "feat(sync-agent): add Syncthing REST API client"
```

---

## Task 4: launchd Module

**Files:**
- Create: `tools/sync-agent/sync_agent/launchd.py`

**Interfaces:**
- Produces:
  - `install_launchd(syncthing_bin: str, log_path: Path) -> Path` — writes plist, returns plist path
  - `uninstall_launchd() -> None` — removes plist if exists
  - `PLIST_PATH: Path` — `~/Library/LaunchAgents/com.harveyz.syncthing.plist`

- [ ] **Step 1: Implement `sync_agent/launchd.py`** (no test needed — file I/O + plist format, tested manually in Task 5 via CLI)

```python
from __future__ import annotations
from pathlib import Path

PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.harveyz.syncthing.plist"

_PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.harveyz.syncthing</string>
    <key>ProgramArguments</key>
    <array>
        <string>{syncthing_bin}</string>
        <string>serve</string>
        <string>--no-browser</string>
        <string>--logfile={log_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""


def install_launchd(syncthing_bin: str, log_path: Path) -> Path:
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(_PLIST_TEMPLATE.format(
        syncthing_bin=syncthing_bin,
        log_path=log_path,
    ))
    return PLIST_PATH


def uninstall_launchd() -> None:
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
```

- [ ] **Step 2: Commit**

```bash
git add tools/sync-agent/sync_agent/launchd.py
git commit -m "feat(sync-agent): add launchd plist install/uninstall"
```

---

## Task 5: CLI Commands

**Files:**
- Create: `tools/sync-agent/sync_agent/cli.py`
- Create: `tools/sync-agent/tests/test_cli.py`

**Interfaces:**
- Consumes:
  - `Config`, `State`, `load_config`, `save_config`, `load_state`, `save_state`, `default_base_dir` from `sync_agent.config`
  - `SyncthingClient`, `SyncthingError` from `sync_agent.syncthing`
  - `install_launchd`, `uninstall_launchd` from `sync_agent.launchd`
- Produces: `app` (Typer app with subcommands `start`, `stop`, `status`, `setup`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py
import json
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner
from sync_agent.cli import app
from sync_agent.config import Config, State, save_config, save_state

runner = CliRunner()


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNC_AGENT_BASE", str(tmp_path))
    return tmp_path


def test_status_no_state_file(base):
    result = runner.invoke(app, ["status"])
    assert result.exit_code != 0
    assert "hskill sync setup" in result.output


def test_status_daemon_not_running(base):
    save_state(State(api_key="k", device_id="D", api_url="http://127.0.0.1:8384"), base)
    with patch("sync_agent.cli.SyncthingClient") as MockClient:
        MockClient.return_value.ping.return_value = False
        result = runner.invoke(app, ["status"])
    assert "hskill sync start" in result.output


def test_status_shows_masked_api_key(base):
    save_state(State(api_key="abcd1234", device_id="XX-YY", api_url="http://127.0.0.1:8384"), base)
    with patch("sync_agent.cli.SyncthingClient") as MockClient:
        client = MockClient.return_value
        client.ping.return_value = True
        client.get_folders.return_value = []
        client.get_devices.return_value = []
        client.get_connections.return_value = {"connections": {}}
        result = runner.invoke(app, ["status"])
    assert "abcd****" in result.output
    assert "abcd1234" not in result.output


def test_setup_applies_config_folders(base):
    cfg = Config(
        folders=[{"id": "f1", "path": str(base / "docs"), "label": "Docs"}],
        devices=[],
    )
    save_config(cfg, base)
    (base / "docs").mkdir()

    with patch("sync_agent.cli._start_daemon"), \
         patch("sync_agent.cli._wait_for_api", return_value=True), \
         patch("sync_agent.cli._extract_state", return_value=State("key", "DEV-ID", "http://127.0.0.1:8384")), \
         patch("sync_agent.cli.SyncthingClient") as MockClient, \
         patch("sync_agent.cli.install_launchd"):
        client = MockClient.return_value
        client.get_folders.return_value = []
        client.get_devices.return_value = []
        result = runner.invoke(app, ["setup"])

    assert result.exit_code == 0
    client.add_folder.assert_called_once()
    call_kwargs = client.add_folder.call_args[0][0]
    assert call_kwargs["id"] == "f1"


def test_setup_skips_existing_folder(base):
    cfg = Config(
        folders=[{"id": "f1", "path": str(base / "docs"), "label": "Docs"}],
        devices=[],
    )
    save_config(cfg, base)
    (base / "docs").mkdir()

    with patch("sync_agent.cli._start_daemon"), \
         patch("sync_agent.cli._wait_for_api", return_value=True), \
         patch("sync_agent.cli._extract_state", return_value=State("key", "DEV-ID", "http://127.0.0.1:8384")), \
         patch("sync_agent.cli.SyncthingClient") as MockClient, \
         patch("sync_agent.cli.install_launchd"):
        client = MockClient.return_value
        client.get_folders.return_value = [{"id": "f1"}]
        client.get_devices.return_value = []
        result = runner.invoke(app, ["setup"])

    assert result.exit_code == 0
    client.add_folder.assert_not_called()


def test_stop_calls_shutdown(base):
    save_state(State(api_key="k", device_id="D", api_url="http://127.0.0.1:8384"), base)
    with patch("sync_agent.cli.SyncthingClient") as MockClient:
        client = MockClient.return_value
        client.ping.return_value = True
        result = runner.invoke(app, ["stop"])
    client.shutdown.assert_called_once()
    assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_cli.py -v
```

Expected: `ModuleNotFoundError: No module named 'sync_agent.cli'`

- [ ] **Step 3: Implement `sync_agent/cli.py`**

```python
from __future__ import annotations
import os
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import typer

from sync_agent.config import (
    Config, State,
    default_base_dir, load_config, save_config, load_state, save_state,
)
from sync_agent.launchd import install_launchd
from sync_agent.syncthing import SyncthingClient, SyncthingError

app = typer.Typer(name="sync-agent", no_args_is_help=True, add_completion=False)


def _base_dir() -> Path:
    env = os.environ.get("SYNC_AGENT_BASE")
    return Path(env) if env else default_base_dir()


def _start_daemon() -> None:
    log_path = _base_dir() / "syncthing.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    syncthing_bin = shutil.which("syncthing") or "syncthing"
    subprocess.Popen(
        [syncthing_bin, "serve", "--no-browser", f"--logfile={log_path}"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_api(api_url: str, api_key: str, timeout: int = 10) -> bool:
    client = SyncthingClient(api_url, api_key)
    for _ in range(timeout):
        if client.ping():
            return True
        time.sleep(1)
    return False


def _extract_state(base_dir: Path) -> State:
    config_xml = Path.home() / ".config" / "syncthing" / "config.xml"
    tree = ET.parse(config_xml)
    root = tree.getroot()
    api_key = root.findtext(".//gui/apikey") or ""
    api_url = "http://127.0.0.1:8384"
    client = SyncthingClient(api_url, api_key)
    device_id = client.get_my_device_id()
    return State(api_key=api_key, device_id=device_id, api_url=api_url)


def _get_client() -> tuple[SyncthingClient, State]:
    base = _base_dir()
    try:
        state = load_state(base)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    client = SyncthingClient(state.api_url, state.api_key)
    if not client.ping():
        typer.echo("Error: Syncthing daemon is not running. Run: hskill sync start", err=True)
        raise typer.Exit(1)
    return client, state


@app.command()
def start():
    """Start the Syncthing daemon."""
    base = _base_dir()
    try:
        state = load_state(base)
        client = SyncthingClient(state.api_url, state.api_key)
        if client.ping():
            typer.echo("Syncthing is already running.")
            return
    except FileNotFoundError:
        pass
    _start_daemon()
    typer.echo("Syncthing started.")


@app.command()
def stop():
    """Stop the Syncthing daemon."""
    client, _ = _get_client()
    client.shutdown()
    typer.echo("Syncthing stopped.")


@app.command()
def status():
    """Show daemon status, device ID, and folder list."""
    client, state = _get_client()
    masked = state.api_key[:4] + "****"
    typer.echo(f"Daemon: running")
    typer.echo(f"Device ID: {state.device_id}")
    typer.echo(f"API Key: {masked}")
    folders = client.get_folders()
    devices = client.get_devices()
    connections = client.get_connections().get("connections", {})
    typer.echo(f"\nFolders ({len(folders)}):")
    for f in folders:
        pct = client.get_completion(f["id"]) if not f.get("paused") else 0.0
        typer.echo(f"  {f['id']:<20} {f.get('path',''):<30} {pct:.0f}%")
    typer.echo(f"\nDevices ({len(devices)}):")
    for d in devices:
        online = "online" if d["deviceID"] in connections else "offline"
        typer.echo(f"  {d.get('name',''):<20} {d['deviceID'][:20]}...  {online}")


@app.command()
def setup():
    """Initialize Syncthing from config.json (idempotent)."""
    base = _base_dir()
    cfg = load_config(base)

    # Start if not running
    try:
        state = load_state(base)
        client = SyncthingClient(state.api_url, state.api_key)
        running = client.ping()
    except FileNotFoundError:
        running = False
        state = None

    if not running:
        typer.echo("Starting Syncthing...")
        _start_daemon()
        # Need API key to wait — extract from config XML first
        state = _extract_state(base)
        save_state(state, base)
        if not _wait_for_api(state.api_url, state.api_key):
            typer.echo("Error: Syncthing did not start within 10s.", err=True)
            raise typer.Exit(1)
    else:
        state = _extract_state(base)
        save_state(state, base)

    client = SyncthingClient(state.api_url, state.api_key)

    # Apply folders
    existing_folders = {f["id"] for f in client.get_folders()}
    for folder in cfg.folders:
        path = Path(folder["path"]).expanduser()
        if not path.exists():
            typer.echo(f"Warning: folder path does not exist: {path} — skipping")
            continue
        if folder["id"] in existing_folders:
            typer.echo(f"Folder already configured: {folder['id']}")
        else:
            client.add_folder({
                "id": folder["id"],
                "path": str(path),
                "label": folder.get("label", folder["id"]),
                "type": "sendreceive",
                "devices": [],
            })
            typer.echo(f"Added folder: {folder['id']}")

    # Apply devices
    existing_devices = {d["deviceID"] for d in client.get_devices()}
    for device in cfg.devices:
        if device["id"] in existing_devices:
            typer.echo(f"Device already configured: {device['name']}")
        else:
            client.add_device({"deviceID": device["id"], "name": device["name"]})
            typer.echo(f"Added device: {device['name']}")

    # Install launchd
    syncthing_bin = shutil.which("syncthing") or "syncthing"
    log_path = base / "syncthing.log"
    plist_path = install_launchd(syncthing_bin, log_path)
    typer.echo(f"launchd plist installed: {plist_path}")
    typer.echo("Setup complete.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_cli.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/sync-agent/sync_agent/cli.py tools/sync-agent/tests/test_cli.py
git commit -m "feat(sync-agent): add CLI commands (start, stop, status, setup)"
```

---

## Task 6: Skill SKILL.md

**Files:**
- Create: `skills/meta/sync-agent/SKILL.md`

**Interfaces:**
- Consumes: `~/.hskill/sync-agent/state.json` (api_key, api_url) at runtime
- Consumes: `~/.hskill/sync-agent/config.json` at runtime
- Produces: user-invocable Skill `/sync-agent`

- [ ] **Step 1: Create `skills/meta/sync-agent/SKILL.md`**

```markdown
---
name: sync-agent
description: "Manage Syncthing sync folders and devices at runtime. Query sync status, add/remove sync folders, add/remove devices, pause/resume folders, force scan. Reads Syncthing API credentials from ~/.hskill/sync-agent/state.json. Does NOT start/stop the daemon — use hskill sync start/setup for that. Triggers: sync status, add sync folder, remove device, pause sync, check sync, syncthing, show sync."
user_invocable: true
version: "1.0.0"
---

# sync-agent

Manage Syncthing sync configuration and query status via the REST API.

**Announce at start:** "Using sync-agent to [describe action]."

---

## 前置检查

每次执行前必须先完成前置检查，若任一检查失败则报错退出，不继续后续步骤。

**Step 1 — 读取 state.json**

```bash
cat ~/.hskill/sync-agent/state.json
```

若文件不存在：
> Error: state.json not found. Run `hskill sync setup` first to initialize.

从输出提取：`API_KEY`、`API_URL`（默认 `http://127.0.0.1:8384`）

**Step 2 — 确认 daemon 在运行**

```bash
curl -sf -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/system/ping"
```

若失败（curl 返回非零）：
> Error: Syncthing daemon is not running. Run `hskill sync start` to start it.

---

## 操作：查看同步状态

```bash
# 获取 folder 列表
curl -s -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/config/folders"

# 获取 device 连接状态
curl -s -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/system/connections"

# 对每个 folder 获取同步进度
curl -s -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/db/completion?folder={FOLDER_ID}"
```

**输出格式：**
```
Folders (N):
  {id:<20} {path:<35} {completion:.0f}%  {paused ? "paused" : "syncing/synced"}

Devices (N):
  {name:<20} {deviceID[:15]}...  {online/offline}
```

---

## 操作：添加 Folder

1. 确认路径存在（`ls {path}`）；若不存在告知用户并询问是否继续
2. 调用 REST API：
```bash
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"id":"{ID}","path":"{PATH}","label":"{LABEL}","type":"sendreceive","devices":[]}' \
  "${API_URL}/rest/config/folders"
```
3. 若返回 4xx/5xx：输出状态码和响应体，不静默失败
4. 回写 config.json：将新 folder 追加到 `~/.hskill/sync-agent/config.json` 的 `folders` 数组

---

## 操作：删除 Folder

```bash
curl -s -X DELETE \
  -H "X-API-Key: ${API_KEY}" \
  "${API_URL}/rest/config/folders/{FOLDER_ID}"
```

从 `config.json` 的 `folders` 数组中移除对应条目。

---

## 操作：添加 Device

验证 device ID 格式：必须是 7 组 7 个大写字母数字，以 `-` 分隔（如 `XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX-XXXXXXX`），共 63 字符加 7 个分隔符。

```bash
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"deviceID":"{DEVICE_ID}","name":"{NAME}"}' \
  "${API_URL}/rest/config/devices"
```

回写 config.json：追加到 `devices` 数组。

---

## 操作：删除 Device

```bash
curl -s -X DELETE \
  -H "X-API-Key: ${API_KEY}" \
  "${API_URL}/rest/config/devices/{DEVICE_ID}"
```

从 `config.json` 的 `devices` 数组中移除对应条目。

---

## 操作：暂停 / 恢复 Folder

先获取当前 folder 配置：
```bash
curl -s -H "X-API-Key: ${API_KEY}" "${API_URL}/rest/config/folders/{FOLDER_ID}"
```

修改 `paused` 字段后 PUT 回去：
```bash
curl -s -X PUT \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{...updated config with paused: true/false...}' \
  "${API_URL}/rest/config/folders/{FOLDER_ID}"
```

回写 config.json（paused 状态不持久化到 config.json，仅在 Syncthing 内部生效）。

---

## 操作：强制扫描

```bash
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  "${API_URL}/rest/db/scan?folder={FOLDER_ID}"
```

---

## 错误处理原则

- 所有 curl 调用加 `-w "\nHTTP %{http_code}"` 捕获状态码
- 4xx/5xx：输出状态码 + 响应体，不继续后续步骤
- 路径不存在、device ID 格式错误：在调用 API 前就报错
```

- [ ] **Step 2: Verify frontmatter is valid**

```bash
node -e "
const fs = require('fs');
const content = fs.readFileSync('skills/meta/sync-agent/SKILL.md', 'utf8');
const match = content.match(/^---\n([\s\S]*?)\n---/);
if (!match) { console.error('No frontmatter'); process.exit(1); }
console.log('Frontmatter OK');
console.log(match[1]);
"
```

Expected: prints "Frontmatter OK" and the YAML fields.

- [ ] **Step 3: Commit**

```bash
git add skills/meta/sync-agent/SKILL.md
git commit -m "feat(sync-agent): add sync-agent skill"
```

---

## Task 7: Register in skills-index.json

**Files:**
- Modify: `skills-index.json`

**Interfaces:**
- Consumes: existing `skills-index.json` structure
- Produces: `npm test` passes (skill format validation includes the new entry)

- [ ] **Step 1: Check current skills-index.json structure for meta bundle**

```bash
node -e "
const idx = JSON.parse(require('fs').readFileSync('skills-index.json','utf8'));
console.log(JSON.stringify(idx.bundleMeta?.meta || 'no meta bundle', null, 2));
const metaSkills = idx.skills.filter(s => s.path.startsWith('meta/'));
console.log(metaSkills.map(s => s.path));
"
```

- [ ] **Step 2: Add entry to `skills-index.json`**

Open `skills-index.json` and add to the `skills` array (after the last `meta/` entry):

```json
{ "path": "meta/sync-agent", "bundle": "meta" }
```

- [ ] **Step 3: Run tests to verify registration is valid**

```bash
npm test
```

Expected: all tests PASS (skill format validation should include `meta/sync-agent`).

- [ ] **Step 4: Commit**

```bash
git add skills-index.json
git commit -m "feat(sync-agent): register sync-agent skill in skills-index.json"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|-----------------|-----------|
| hskill sync setup (idempotent) | Task 5 `setup` command |
| hskill sync start | Task 5 `start` command |
| hskill sync stop | Task 5 `stop` command |
| hskill sync status (API key masked) | Task 5 `status` command |
| Skill: ping before operations | Task 6 SKILL.md 前置检查 |
| Skill: add/remove folder | Task 6 SKILL.md |
| Skill: add/remove device | Task 6 SKILL.md |
| Skill: pause/resume folder | Task 6 SKILL.md |
| Skill: force scan | Task 6 SKILL.md |
| Skill: write changes back to config.json | Task 6 SKILL.md each operation |
| launchd autostart | Task 4 + Task 5 setup step 7 |
| state.json from config XML | Task 5 `_extract_state` |
| device ID format validation | Task 6 SKILL.md 添加 Device |
| skills-index registration | Task 7 |

All spec requirements covered. No gaps.
