import json

import pytest

from roster import SCHEMA_VERSION, registry

TODAY = "2026-08-26"


def test_load_missing_file_returns_empty(data_dir):
    reg = registry.load(data_dir)
    assert reg == {"schema_version": SCHEMA_VERSION, "creators": []}


def test_save_then_load_roundtrip(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.save(data_dir, reg)
    assert registry.load(data_dir) == reg


def test_save_creates_parent_dir(data_dir):
    registry.save(data_dir, registry.load(data_dir))
    assert (data_dir / "registry.json").exists()


def test_add_channel_creates_placeholder_creator(data_dir):
    reg = registry.load(data_dir)
    creator_id, created = registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    assert (creator_id, created) == ("karpathy", True)
    creator = registry.find_creator(reg, "karpathy")
    assert creator["display_name"] == "karpathy"
    assert creator["placeholder"] is True
    assert creator["added_at"] == TODAY
    assert creator["aliases"] == []
    assert creator["channels"] == [
        {"platform": "x", "handle": "karpathy", "url": "https://x.com/karpathy"}
    ]


def test_add_second_channel_for_same_handle_on_other_platform_makes_second_creator(data_dir):
    """同名 handle 跨平台不代表同一个人——不自动合并，交给 merge。"""
    reg = registry.load(data_dir)
    a, _ = registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    b, _ = registry.add_channel(reg, "https://youtube.com/@karpathy", TODAY)
    assert a == "karpathy"
    assert b == "karpathy-2"
    assert len(reg["creators"]) == 2


def test_add_duplicate_channel_raises(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    with pytest.raises(ValueError, match="已在名册"):
        registry.add_channel(reg, "https://x.com/karpathy", TODAY)


def test_add_channel_rejects_bad_url(data_dir):
    reg = registry.load(data_dir)
    with pytest.raises(ValueError):
        registry.add_channel(reg, "https://youtube.com/watch?v=abc", TODAY)


def test_find_channel_returns_creator_and_channel(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    creator, channel = registry.find_channel(reg, "x", "karpathy")
    assert creator["id"] == "karpathy"
    assert channel["handle"] == "karpathy"


def test_find_channel_missing_returns_none(data_dir):
    assert registry.find_channel(registry.load(data_dir), "x", "nobody") is None


def test_find_creator_matches_alias(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.find_creator(reg, "karpathy")["aliases"].append("old-id")
    assert registry.find_creator(reg, "old-id")["id"] == "karpathy"


def test_channels_for_platform_filters_and_carries_creator_id(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.add_channel(reg, "https://youtube.com/@TwoMinutePapers", TODAY)
    assert registry.channels_for_platform(reg, "x") == [
        {"creator_id": "karpathy", "platform": "x",
         "handle": "karpathy", "url": "https://x.com/karpathy"}
    ]
    assert len(registry.channels_for_platform(reg, "youtube")) == 1


def test_channels_for_platform_empty(data_dir):
    assert registry.channels_for_platform(registry.load(data_dir), "x") == []


def test_remove_channel_leaves_creator_behind(data_dir):
    """人可以暂时没有渠道——认识但还没订阅。删渠道不连带删人。"""
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.remove_channel(reg, "x", "karpathy")
    assert registry.find_creator(reg, "karpathy")["channels"] == []


def test_remove_channel_missing_raises(data_dir):
    with pytest.raises(ValueError):
        registry.remove_channel(registry.load(data_dir), "x", "nobody")


def test_remove_creator_returns_it_and_drops_channels(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    removed = registry.remove_creator(reg, "karpathy")
    assert removed["id"] == "karpathy"
    assert reg["creators"] == []


def test_remove_creator_missing_raises(data_dir):
    with pytest.raises(ValueError):
        registry.remove_creator(registry.load(data_dir), "nobody")


def test_saved_json_is_readable_utf8(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.find_creator(reg, "karpathy")["display_name"] = "安德烈"
    registry.save(data_dir, reg)
    raw = (data_dir / "registry.json").read_text(encoding="utf-8")
    assert "安德烈" in raw          # 不是 \uXXXX 转义
    assert json.loads(raw)["schema_version"] == SCHEMA_VERSION
