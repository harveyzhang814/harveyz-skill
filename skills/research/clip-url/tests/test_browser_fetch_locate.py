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
