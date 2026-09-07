import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_fetch_locate  # noqa: E402


def test_finds_dev_launcher_in_repo_checkout():
    found = browser_fetch_locate.find_browser_fetch()
    assert Path(found).name == "browser-fetch.sh"
    assert Path(found).exists()


def test_falls_back_to_path_lookup_when_dev_path_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(browser_fetch_locate, "_dev_path", lambda: tmp_path / "nope.sh")
    monkeypatch.setattr(browser_fetch_locate.shutil, "which", lambda name: "/usr/local/bin/browser-fetch")

    assert browser_fetch_locate.find_browser_fetch() == "/usr/local/bin/browser-fetch"


def test_falls_back_to_local_bin_when_not_on_path(monkeypatch, tmp_path):
    monkeypatch.setattr(browser_fetch_locate, "_dev_path", lambda: tmp_path / "nope.sh")
    monkeypatch.setattr(browser_fetch_locate.shutil, "which", lambda name: None)

    fake_home = tmp_path / "home"
    installed = fake_home / ".local" / "bin" / "browser-fetch"
    installed.parent.mkdir(parents=True)
    installed.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    monkeypatch.setattr(browser_fetch_locate.Path, "home", classmethod(lambda cls: fake_home))

    assert browser_fetch_locate.find_browser_fetch() == str(installed)


def test_raises_when_nothing_found(monkeypatch, tmp_path):
    monkeypatch.setattr(browser_fetch_locate, "_dev_path", lambda: tmp_path / "nope.sh")
    monkeypatch.setattr(browser_fetch_locate.shutil, "which", lambda _: None)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    with pytest.raises(FileNotFoundError, match="browser-fetch"):
        browser_fetch_locate.find_browser_fetch()


def test_main_prints_found_and_exits_zero(monkeypatch, tmp_path, capsys):
    dev_sh = tmp_path / "tools" / "browser-fetch" / "browser-fetch.sh"
    dev_sh.parent.mkdir(parents=True)
    dev_sh.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(browser_fetch_locate, "_dev_path", lambda: dev_sh)

    browser_fetch_locate.main()

    captured = capsys.readouterr()
    assert captured.out.strip() == f"FOUND: {dev_sh}"


def test_main_prints_not_found_and_exits_one(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(browser_fetch_locate, "_dev_path", lambda: tmp_path / "nope.sh")
    monkeypatch.setattr(browser_fetch_locate.shutil, "which", lambda name: None)
    monkeypatch.setattr(browser_fetch_locate.Path, "home", classmethod(lambda cls: tmp_path / "empty-home"))

    with pytest.raises(SystemExit) as exc_info:
        browser_fetch_locate.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out.startswith("NOT_FOUND: ")
    assert "hskill install" in captured.out
