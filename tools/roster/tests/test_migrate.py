import json

from roster import migrate, registry, state

TODAY = "2026-08-26"
RUN = "2026-08-26T09:14:00+08:00"

X_OLD = [
    {"handle": "karpathy", "profile_url": "https://x.com/karpathy",
     "last_seen_tweet_id": "1876543210987654321"},
    {"handle": "newbie", "profile_url": "https://x.com/newbie",
     "last_seen_tweet_id": None},
]
YT_OLD = [
    {"handle": "AndrejKarpathy", "channel_url": "https://youtube.com/@AndrejKarpathy",
     "seen_urls": ["https://youtu.be/a", "https://youtu.be/b"]},
    {"handle": "FreshChannel", "channel_url": "https://youtube.com/@FreshChannel",
     "seen_urls": None},
]


def test_migrate_counts(data_dir):
    result = migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    assert result == {"creators": 4, "channels": 4, "cursors": 2}


def test_migrate_creates_placeholder_creators(data_dir):
    migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    reg = registry.load(data_dir)
    assert len(reg["creators"]) == 4
    assert all(c["placeholder"] for c in reg["creators"])


def test_migrate_maps_x_cursor_to_last_seen_id(data_dir):
    migrate.from_watchlists(data_dir, X_OLD, None, TODAY, RUN)
    st = state.load(data_dir)
    assert state.get_cursor(st, "x", "karpathy") == {
        "type": "last_seen_id", "value": "1876543210987654321"
    }


def test_migrate_maps_yt_cursor_to_seen_urls(data_dir):
    migrate.from_watchlists(data_dir, None, YT_OLD, TODAY, RUN)
    st = state.load(data_dir)
    assert state.get_cursor(st, "youtube", "AndrejKarpathy") == {
        "type": "seen_urls", "value": ["https://youtu.be/a", "https://youtu.be/b"]
    }


def test_migrate_skips_null_cursors(data_dir):
    """游标为 None 表示从未成功抓过，下次运行应照常建基线。"""
    migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    st = state.load(data_dir)
    assert state.get_cursor(st, "x", "newbie") is None
    assert state.get_cursor(st, "youtube", "FreshChannel") is None


def test_migrate_does_not_guess_identity_across_platforms(data_dir):
    """karpathy 和 AndrejKarpathy 是同一个人，但迁移不猜——交给用户 merge。"""
    migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    reg = registry.load(data_dir)
    ids = {c["id"] for c in reg["creators"]}
    assert "karpathy" in ids and "andrejkarpathy" in ids


def test_migrate_is_idempotent(data_dir):
    migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    second = migrate.from_watchlists(data_dir, X_OLD, YT_OLD, TODAY, RUN)
    assert second == {"creators": 0, "channels": 0, "cursors": 0}
    assert len(registry.load(data_dir)["creators"]) == 4


def test_migrate_with_both_none_is_noop(data_dir):
    assert migrate.from_watchlists(data_dir, None, None, TODAY, RUN) == {
        "creators": 0, "channels": 0, "cursors": 0
    }


def test_cli_migrate(data_dir, tmp_path, capsys):
    from roster.__main__ import main

    x_file = tmp_path / "x-watchlist.json"
    x_file.write_text(json.dumps(X_OLD), encoding="utf-8")
    yt_file = tmp_path / "yt-watchlist.json"
    yt_file.write_text(json.dumps(YT_OLD), encoding="utf-8")

    code = main(["migrate", "--from-xtimeline", str(x_file), "--from-ytchannel", str(yt_file)])
    out = capsys.readouterr().out.strip()
    assert code == 0
    assert out == "OK creators=4 channels=4 cursors=2"


def test_cli_migrate_missing_file_exits_1(data_dir, tmp_path, capsys):
    from roster.__main__ import main

    code = main(["migrate", "--from-xtimeline", str(tmp_path / "nope.json")])
    assert code == 1
    assert "nope.json" in capsys.readouterr().err
