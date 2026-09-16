import json

import pytest

from roster import SCHEMA_VERSION, migrate_schema, registry, state

TODAY = "2026-08-26"
RUN = "2026-08-26T09:14:00+08:00"


def _seed_v1(data_dir):
    """手工构一份 schema_version 1 的旧数据：渠道没有 key，游标键是原始 handle。"""
    reg = {
        "schema_version": 1,
        "creators": [
            {
                "id": "tinghu888", "display_name": "TingHu888", "aliases": [],
                "placeholder": True, "added_at": TODAY,
                "channels": [{
                    "platform": "x", "handle": "TingHu888",
                    "url": "https://x.com/TingHu888",
                }],
            },
        ],
    }
    st = {
        "schema_version": 1,
        "channels": {
            "x:TingHu888": {
                "cursor": {"type": "last_seen_id", "value": "123456"},
                "last_run": RUN, "last_error": None,
            },
        },
    }
    registry.save(data_dir, reg)
    state.save(data_dir, st)


def test_migrate_schema_backfills_key(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    channel = registry.load(data_dir)["creators"][0]["channels"][0]
    assert channel["key"] == "tinghu888"
    assert channel["handle"] == "TingHu888"          # 原始大小写保留


def test_migrate_schema_bumps_registry_schema_version(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    assert registry.load(data_dir)["schema_version"] == SCHEMA_VERSION


def test_migrate_schema_renames_cursor_key(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    st = state.load(data_dir)
    assert "x:tinghu888" in st["channels"]
    assert "x:TingHu888" not in st["channels"]


def test_migrate_schema_preserves_cursor_value_byte_for_byte(data_dir):
    _seed_v1(data_dir)
    before = state.load(data_dir)["channels"]["x:TingHu888"]["cursor"]
    migrate_schema.migrate_schema(data_dir)
    after = state.load(data_dir)["channels"]["x:tinghu888"]["cursor"]
    assert after == before


def test_migrate_schema_bumps_state_schema_version(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    assert state.load(data_dir)["schema_version"] == SCHEMA_VERSION


def test_migrate_schema_is_idempotent(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    reg_once = registry.load(data_dir)
    st_once = state.load(data_dir)
    migrate_schema.migrate_schema(data_dir)
    assert registry.load(data_dir) == reg_once
    assert state.load(data_dir) == st_once


def test_migrate_schema_reports_counts(data_dir):
    _seed_v1(data_dir)
    result = migrate_schema.migrate_schema(data_dir)
    assert result == {"channels_updated": 1, "cursors_renamed": 1}


def test_migrate_schema_second_run_reports_zero(data_dir):
    _seed_v1(data_dir)
    migrate_schema.migrate_schema(data_dir)
    result = migrate_schema.migrate_schema(data_dir)
    assert result == {"channels_updated": 0, "cursors_renamed": 0}


def test_migrate_schema_leaves_already_normalized_channel_untouched(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.save(data_dir, reg)
    result = migrate_schema.migrate_schema(data_dir)
    assert result["channels_updated"] == 0


def test_cli_migrate_schema(data_dir, capsys):
    from roster.__main__ import main

    reg = {
        "schema_version": 1,
        "creators": [{
            "id": "k", "display_name": "K", "aliases": [], "placeholder": True,
            "added_at": TODAY,
            "channels": [{"platform": "x", "handle": "TingHu888",
                          "url": "https://x.com/TingHu888"}],
        }],
    }
    st = {"schema_version": 1, "channels": {
        "x:TingHu888": {"cursor": {"type": "last_seen_id", "value": "1"},
                         "last_run": RUN, "last_error": None},
    }}
    registry.save(data_dir, reg)
    state.save(data_dir, st)

    code = main(["migrate-schema"])
    out = capsys.readouterr().out.strip()
    assert code == 0
    assert out == "OK channels_updated=1 cursors_renamed=1"


def test_migrate_schema_raises_on_key_collision_and_touches_nothing(data_dir):
    reg = {
        "schema_version": 1,
        "creators": [{
            "id": "a", "display_name": "A", "aliases": [], "placeholder": True,
            "added_at": TODAY,
            "channels": [{"platform": "x", "handle": "TingHu888",
                          "url": "https://x.com/TingHu888"}],
        }],
    }
    st = {
        "schema_version": 1,
        "channels": {
            "x:TingHu888": {"cursor": {"type": "last_seen_id", "value": "1"},
                            "last_run": RUN, "last_error": None},
            "x:tinghu888": {"cursor": {"type": "last_seen_id", "value": "2"},
                            "last_run": RUN, "last_error": None},
        },
    }
    registry.save(data_dir, reg)
    state.save(data_dir, st)

    with pytest.raises(ValueError, match="相撞"):
        migrate_schema.migrate_schema(data_dir)

    assert registry.load(data_dir) == reg
    assert state.load(data_dir) == st
