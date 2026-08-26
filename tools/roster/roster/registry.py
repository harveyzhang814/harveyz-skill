"""registry.json —— 人（creator）与渠道（channel）的定义。

唯一写入方是 manage-roster skill（经 `roster registry` 命令组）。抓取层
只读这里、只写 state.json。

归属关系嵌套表达：渠道存在哪个 creator 的 channels 里，就属于谁。不另存
creator_id 外键——一份归属关系只有一个真值来源。
"""
import json
from pathlib import Path

from . import SCHEMA_VERSION
from .urls import parse_channel_url, slugify


def _path(data_dir: Path) -> Path:
    return Path(data_dir) / "registry.json"


def load(data_dir: Path) -> dict:
    path = _path(data_dir)
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "creators": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(data_dir: Path, reg: dict) -> None:
    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def find_creator(reg: dict, creator_id: str) -> dict | None:
    for c in reg["creators"]:
        if c["id"] == creator_id or creator_id in c.get("aliases", []):
            return c
    return None


def find_channel(reg: dict, platform: str, handle: str) -> tuple[dict, dict] | None:
    for c in reg["creators"]:
        for ch in c["channels"]:
            if ch["platform"] == platform and ch["handle"] == handle:
                return c, ch
    return None


def _free_slug(reg: dict, base: str) -> str:
    """同名 handle 跨平台不代表同一个人，所以撞了就编号，不合并。
    真是同一个人由用户跑 merge 决定——那是判断，不是解析。"""
    if find_creator(reg, base) is None:
        return base
    n = 2
    while find_creator(reg, f"{base}-{n}") is not None:
        n += 1
    return f"{base}-{n}"


def add_channel(reg: dict, url: str, today: str) -> tuple[str, bool]:
    platform, handle = parse_channel_url(url)
    if find_channel(reg, platform, handle) is not None:
        raise ValueError(f"{platform}:{handle} 已在名册中")

    creator_id = _free_slug(reg, slugify(handle))
    reg["creators"].append({
        "id": creator_id,
        "display_name": handle,
        "aliases": [],
        "placeholder": True,
        "added_at": today,
        "channels": [{"platform": platform, "handle": handle, "url": url}],
    })
    return creator_id, True


def channels_for_platform(reg: dict, platform: str) -> list[dict]:
    out = []
    for c in reg["creators"]:
        for ch in c["channels"]:
            if ch["platform"] == platform:
                out.append({"creator_id": c["id"], **ch})
    return out


def remove_creator(reg: dict, creator_id: str) -> dict:
    creator = find_creator(reg, creator_id)
    if creator is None:
        raise ValueError(f"名册里没有 {creator_id}")
    reg["creators"].remove(creator)
    return creator


def remove_channel(reg: dict, platform: str, handle: str) -> None:
    found = find_channel(reg, platform, handle)
    if found is None:
        raise ValueError(f"名册里没有 {platform}:{handle}")
    creator, channel = found
    creator["channels"].remove(channel)


def rename_creator(reg: dict, creator_id: str, display_name: str) -> None:
    creator = find_creator(reg, creator_id)
    if creator is None:
        raise ValueError(f"名册里没有 {creator_id}")
    creator["display_name"] = display_name
    creator["placeholder"] = False


def merge_creators(reg: dict, id_a: str, id_b: str) -> None:
    """b 并入 a。a 的 id 和 display_name 胜出，b 的 id 落进 a 的 aliases，
    这样外部对 b 的旧引用仍然解析得到。"""
    a = find_creator(reg, id_a)
    b = find_creator(reg, id_b)
    if a is None:
        raise ValueError(f"名册里没有 {id_a}")
    if b is None:
        raise ValueError(f"名册里没有 {id_b}")
    if a is b:
        raise ValueError("不能合并到自己")

    for alias in [b["id"], *b.get("aliases", [])]:
        if alias not in a["aliases"]:
            a["aliases"].append(alias)
    a["channels"].extend(b["channels"])
    a["placeholder"] = a["placeholder"] and b["placeholder"]
    reg["creators"].remove(b)
