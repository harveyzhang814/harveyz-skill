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
