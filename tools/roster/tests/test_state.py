import pytest

from roster import SCHEMA_VERSION, state

RUN = "2026-08-26T09:14:00+08:00"


def test_load_missing_returns_empty(data_dir):
    assert state.load(data_dir) == {"schema_version": SCHEMA_VERSION, "channels": {}}


def test_roundtrip(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1876543210987654321", RUN)
    state.save(data_dir, st)
    assert state.load(data_dir) == st


def test_get_cursor_before_first_fetch_is_none(data_dir):
    assert state.get_cursor(state.load(data_dir), "x", "karpathy") is None


def test_set_and_get_last_seen_id(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "123", RUN)
    assert state.get_cursor(st, "x", "karpathy") == {"type": "last_seen_id", "value": "123"}


def test_set_and_get_seen_urls(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "youtube", "AK", "seen_urls", ["https://a", "https://b"], RUN)
    assert state.get_cursor(st, "youtube", "AK") == {
        "type": "seen_urls", "value": ["https://a", "https://b"]
    }


def test_channels_are_keyed_by_platform_and_handle(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1", RUN)
    assert "x:karpathy" in st["channels"]


def test_same_handle_on_two_platforms_does_not_collide(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "same", "last_seen_id", "1", RUN)
    state.set_cursor(st, "youtube", "same", "seen_urls", ["u"], RUN)
    assert state.get_cursor(st, "x", "same")["value"] == "1"
    assert state.get_cursor(st, "youtube", "same")["value"] == ["u"]


def test_set_cursor_rejects_unknown_type(data_dir):
    with pytest.raises(ValueError, match="未知的游标类型"):
        state.set_cursor(state.load(data_dir), "x", "k", "whatever", "1", RUN)


def test_set_cursor_records_run_time(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1", RUN)
    assert st["channels"]["x:karpathy"]["last_run"] == RUN


def test_set_error_leaves_cursor_untouched(data_dir):
    """抓取失败不该让游标倒退——那会导致下一次重报一批旧物料。"""
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "123", RUN)
    state.set_error(st, "x", "karpathy", "timed out", "2026-08-27T09:00:00+08:00")
    assert state.get_cursor(st, "x", "karpathy")["value"] == "123"
    assert st["channels"]["x:karpathy"]["last_error"] == "timed out"


def test_set_error_on_never_fetched_channel(data_dir):
    st = state.load(data_dir)
    state.set_error(st, "x", "nobody", "boom", RUN)
    assert state.get_cursor(st, "x", "nobody") is None
    assert st["channels"]["x:nobody"]["last_error"] == "boom"


def test_successful_set_cursor_clears_previous_error(data_dir):
    st = state.load(data_dir)
    state.set_error(st, "x", "karpathy", "timed out", RUN)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1", RUN)
    assert st["channels"]["x:karpathy"]["last_error"] is None


def test_drop_channel(data_dir):
    st = state.load(data_dir)
    state.set_cursor(st, "x", "karpathy", "last_seen_id", "1", RUN)
    state.drop_channel(st, "x", "karpathy")
    assert st["channels"] == {}


def test_drop_missing_channel_is_silent(data_dir):
    state.drop_channel(state.load(data_dir), "x", "nobody")
