import pytest

from roster import registry

TODAY = "2026-08-26"


def _two_creators(data_dir):
    reg = registry.load(data_dir)
    registry.add_channel(reg, "https://x.com/karpathy", TODAY)
    registry.add_channel(reg, "https://youtube.com/@AndrejKarpathy", TODAY)
    return reg


def test_rename_sets_name_and_clears_placeholder(data_dir):
    reg = _two_creators(data_dir)
    registry.rename_creator(reg, "karpathy", "Andrej Karpathy")
    creator = registry.find_creator(reg, "karpathy")
    assert creator["display_name"] == "Andrej Karpathy"
    assert creator["placeholder"] is False
    assert creator["id"] == "karpathy"          # id 不可变


def test_rename_missing_raises(data_dir):
    with pytest.raises(ValueError):
        registry.rename_creator(registry.load(data_dir), "nobody", "X")


def test_merge_keeps_first_id_and_name(data_dir):
    reg = _two_creators(data_dir)
    registry.rename_creator(reg, "karpathy", "Andrej Karpathy")
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    assert len(reg["creators"]) == 1
    merged = reg["creators"][0]
    assert merged["id"] == "karpathy"
    assert merged["display_name"] == "Andrej Karpathy"


def test_merge_puts_second_id_into_aliases(data_dir):
    reg = _two_creators(data_dir)
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    assert "andrejkarpathy" in registry.find_creator(reg, "karpathy")["aliases"]


def test_merged_old_id_still_resolves(data_dir):
    """旧 id 落进 aliases 的意义就在这里——外部引用不失效。"""
    reg = _two_creators(data_dir)
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    assert registry.find_creator(reg, "andrejkarpathy")["id"] == "karpathy"


def test_merge_combines_channels(data_dir):
    reg = _two_creators(data_dir)
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    merged = registry.find_creator(reg, "karpathy")
    assert {(c["platform"], c["handle"]) for c in merged["channels"]} == {
        ("x", "karpathy"), ("youtube", "AndrejKarpathy")
    }


def test_merge_carries_over_second_aliases(data_dir):
    reg = _two_creators(data_dir)
    registry.find_creator(reg, "andrejkarpathy")["aliases"].append("ancient-id")
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    aliases = registry.find_creator(reg, "karpathy")["aliases"]
    assert set(aliases) == {"andrejkarpathy", "ancient-id"}


def test_merge_clears_placeholder_if_either_is_confirmed(data_dir):
    reg = _two_creators(data_dir)
    registry.rename_creator(reg, "andrejkarpathy", "Andrej Karpathy")
    registry.merge_creators(reg, "karpathy", "andrejkarpathy")
    assert registry.find_creator(reg, "karpathy")["placeholder"] is False


def test_merge_into_self_raises(data_dir):
    reg = _two_creators(data_dir)
    with pytest.raises(ValueError, match="不能合并到自己"):
        registry.merge_creators(reg, "karpathy", "karpathy")


def test_merge_missing_raises(data_dir):
    reg = _two_creators(data_dir)
    with pytest.raises(ValueError):
        registry.merge_creators(reg, "karpathy", "nobody")
