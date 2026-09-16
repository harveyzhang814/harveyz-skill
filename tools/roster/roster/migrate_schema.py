"""registry.json / state.json 从 schema_version 1 升到 2 —— 一次性、幂等。

跟 migrate.py（旧 watchlist 导入）是两件事：这里只做两件事——给每条渠道
回填 key、把游标键从原始 handle 重写成归一 key。两个文件必须在同一次
调用里一起改，否则名册按 key 查、游标按 handle 存，成了新的不一致源头
（见 docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md §3.3）。
"""
from pathlib import Path

from . import SCHEMA_VERSION, registry, state
from .urls import channel_key, normalize


def migrate_schema(data_dir: Path) -> dict:
    reg = registry.load(data_dir)
    channels_updated = 0
    for creator in reg["creators"]:
        for ch in creator["channels"]:
            new_key = normalize(ch["handle"])
            if ch.get("key") != new_key:
                ch["key"] = new_key
                channels_updated += 1
    reg["schema_version"] = SCHEMA_VERSION
    registry.save(data_dir, reg)

    st = state.load(data_dir)
    cursors_renamed = 0
    new_channels: dict = {}
    for old_key, entry in st["channels"].items():
        platform, _, handle = old_key.partition(":")
        new_key = channel_key(platform, handle)
        if new_key != old_key:
            cursors_renamed += 1
        new_channels[new_key] = entry
    st["channels"] = new_channels
    st["schema_version"] = SCHEMA_VERSION
    state.save(data_dir, st)

    return {"channels_updated": channels_updated, "cursors_renamed": cursors_renamed}
