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


if __name__ == "__main__":
    app()
