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
