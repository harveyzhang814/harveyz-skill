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
