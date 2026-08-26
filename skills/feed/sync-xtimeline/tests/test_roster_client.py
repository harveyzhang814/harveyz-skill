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


def test_channels_asks_for_x(fake_roster):
    _reply(fake_roster, '[{"creator_id":"k","platform":"x",'
                        '"handle":"karpathy","url":"https://x.com/karpathy"}]\n')
    assert roster_client.channels()[0]["handle"] == "karpathy"
    assert "registry channels --platform x" in _argv(fake_roster)


def test_channels_empty(fake_roster):
    _reply(fake_roster, "[]\n")
    assert roster_client.channels() == []


def test_get_cursor_unwraps_last_seen_id(fake_roster):
    _reply(fake_roster, '{"type":"last_seen_id","value":"123"}\n')
    assert roster_client.get_cursor("karpathy") == "123"


def test_get_cursor_null_means_never_fetched(fake_roster):
    _reply(fake_roster, "null\n")
    assert roster_client.get_cursor("karpathy") is None


def test_set_cursor_sends_last_seen_id_type(fake_roster):
    _reply(fake_roster, "OK\n")
    roster_client.set_cursor("karpathy", "123", "2026-08-26T09:00:00+08:00")
    argv = _argv(fake_roster)
    assert "state set x:karpathy" in argv
    assert "--type last_seen_id" in argv


def test_set_error_sends_fail(fake_roster):
    _reply(fake_roster, "OK\n")
    roster_client.set_error("karpathy", "timed out", "2026-08-26T09:00:00+08:00")
    assert "state fail x:karpathy" in _argv(fake_roster)


def test_nonzero_exit_raises(fake_roster, tmp_path, monkeypatch):
    failing = tmp_path / "failing-roster"
    failing.write_text('#!/usr/bin/env bash\necho "boom" >&2\nexit 1\n', encoding="utf-8")
    failing.chmod(0o755)
    monkeypatch.setattr(roster_client, "_launcher", lambda: str(failing))
    with pytest.raises(RuntimeError, match="boom"):
        roster_client.channels()
