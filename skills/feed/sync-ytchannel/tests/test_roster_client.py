"""roster_client 把 roster CLI 的输出翻成 Python 值。用假的 launcher
（一个打印固定输出的 shell 脚本）驱动，不依赖真的装了 roster。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import roster_client


@pytest.fixture
def fake_roster(tmp_path, monkeypatch):
    """造一个假 launcher，把每次调用的参数记进 argv.log，按预设脚本回话。"""
    script = tmp_path / "fake-roster"
    script.write_text(
        '#!/usr/bin/env bash\n'
        'echo "$@" >> "$FAKE_ROSTER_LOG"\n'
        'cat "$FAKE_ROSTER_OUT"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setattr(roster_client, "_launcher", lambda: str(script))
    monkeypatch.setenv("FAKE_ROSTER_LOG", str(tmp_path / "argv.log"))
    monkeypatch.setenv("FAKE_ROSTER_OUT", str(tmp_path / "out.txt"))
    return tmp_path


def _reply(fake_roster, text: str) -> None:
    (fake_roster / "out.txt").write_text(text, encoding="utf-8")


def _argv(fake_roster) -> str:
    return (fake_roster / "argv.log").read_text(encoding="utf-8")


def test_channels_parses_json_and_asks_for_youtube(fake_roster):
    _reply(fake_roster, '[{"creator_id":"ak","platform":"youtube",'
                        '"handle":"AK","url":"https://youtube.com/@AK"}]\n')
    assert roster_client.channels() == [{
        "creator_id": "ak", "platform": "youtube",
        "handle": "AK", "url": "https://youtube.com/@AK",
    }]
    assert "registry channels --platform youtube" in _argv(fake_roster)


def test_channels_empty(fake_roster):
    _reply(fake_roster, "[]\n")
    assert roster_client.channels() == []


def test_get_cursor_null_means_never_fetched(fake_roster):
    _reply(fake_roster, "null\n")
    assert roster_client.get_cursor("AK") is None


def test_get_cursor_unwraps_seen_urls(fake_roster):
    _reply(fake_roster, '{"type":"seen_urls","value":["https://a"]}\n')
    assert roster_client.get_cursor("AK") == ["https://a"]


def test_set_cursor_sends_seen_urls_type(fake_roster):
    _reply(fake_roster, "OK\n")
    roster_client.set_cursor("AK", ["https://a"], "2026-08-26T09:00:00+08:00")
    argv = _argv(fake_roster)
    assert "state set youtube:AK" in argv
    assert "--type seen_urls" in argv


def test_set_error_sends_fail(fake_roster):
    _reply(fake_roster, "OK\n")
    roster_client.set_error("AK", "timed out", "2026-08-26T09:00:00+08:00")
    assert "state fail youtube:AK" in _argv(fake_roster)


def test_nonzero_exit_raises(fake_roster, tmp_path, monkeypatch):
    failing = tmp_path / "failing-roster"
    failing.write_text('#!/usr/bin/env bash\necho "boom" >&2\nexit 1\n', encoding="utf-8")
    failing.chmod(0o755)
    monkeypatch.setattr(roster_client, "_launcher", lambda: str(failing))
    with pytest.raises(RuntimeError, match="boom"):
        roster_client.channels()
