"""roster CLI —— 三个命令组，一组对应一份文件、对应一个消费者：

  roster registry ...   registry.json    manage-roster skill
  roster state ...      state.json       sync-* skill
  roster profile ...    profiles/*.md    认知层 skill

读跨组允许（registry list 要读 state 展示游标），写不允许。
"""
import argparse
import json
import sys
from datetime import date

from . import config, profiles, registry, state
from .urls import parse_channel_url


def _split_ref(ref: str) -> tuple[str, str]:
    if ":" not in ref:
        raise ValueError(f"渠道引用格式应为 platform:handle，收到：{ref}")
    platform, _, handle = ref.partition(":")
    if not platform or not handle:
        raise ValueError(f"渠道引用格式应为 platform:handle，收到：{ref}")
    return platform, handle


def _cmd_init(args) -> int:
    config.set_config("DATA_DIR", args.data_dir)
    print(f"OK {args.data_dir}")
    return 0


def _cmd_data_dir(args) -> int:
    print(config.get_data_dir())
    return 0


def _cmd_registry_add(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)
    creator_id, _ = registry.add_channel(reg, args.url, date.today().isoformat())
    registry.save(data_dir, reg)
    platform, handle = parse_channel_url(args.url)
    print(f"OK {creator_id} {platform}:{handle}")
    return 0


def _cmd_registry_remove(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)

    if ":" in args.ref:
        platform, handle = _split_ref(args.ref)
        registry.remove_channel(reg, platform, handle)
        registry.save(data_dir, reg)
        st = state.load(data_dir)
        state.drop_channel(st, platform, handle)
        state.save(data_dir, st)
        print(f"OK removed {platform}:{handle}")
        return 0

    creator = registry.remove_creator(reg, args.ref)
    registry.save(data_dir, reg)
    st = state.load(data_dir)
    for channel in creator["channels"]:
        state.drop_channel(st, channel["platform"], channel["handle"])
    state.save(data_dir, st)
    archived = profiles.archive(data_dir, creator["id"])
    suffix = f"profile archived at {archived}" if archived else "no profile"
    print(f"OK removed {creator['id']}, {suffix}")
    return 0


def _cmd_registry_rename(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)
    registry.rename_creator(reg, args.creator_id, args.display_name)
    registry.save(data_dir, reg)
    print("OK")
    return 0


def _cmd_registry_merge(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)
    registry.merge_creators(reg, args.id_a, args.id_b)
    registry.save(data_dir, reg)
    profiles.merge(data_dir, args.id_a, args.id_b, date.today().isoformat())
    print(f"OK merged {args.id_b} into {args.id_a}")
    return 0


def _cmd_registry_list(args) -> int:
    data_dir = config.get_data_dir()
    reg = registry.load(data_dir)
    if not reg["creators"]:
        print("EMPTY")
        return 0

    st = state.load(data_dir)
    for creator in reg["creators"]:
        mark = "  [placeholder]" if creator["placeholder"] else ""
        print(f"{creator['id']}  {creator['display_name']}{mark}")
        for channel in creator["channels"]:
            key = f"{channel['platform']}:{channel['handle']}"
            entry = st["channels"].get(key) or {}
            cursor = entry.get("cursor")
            if cursor is None:
                shown = "(none)"
            elif cursor["type"] == "seen_urls":
                shown = f"{len(cursor['value'])} urls"
            else:
                shown = str(cursor["value"])
            err = entry.get("last_error")
            tail = f"  err={err}" if err else ""
            print(f"  {key}  cursor={shown}{tail}")
    return 0


def _cmd_registry_channels(args) -> int:
    reg = registry.load(config.get_data_dir())
    print(json.dumps(registry.channels_for_platform(reg, args.platform), ensure_ascii=False))
    return 0


def _cmd_state_get(args) -> int:
    platform, handle = _split_ref(args.ref)
    st = state.load(config.get_data_dir())
    print(json.dumps(state.get_cursor(st, platform, handle), ensure_ascii=False))
    return 0


def _cmd_state_set(args) -> int:
    platform, handle = _split_ref(args.ref)
    data_dir = config.get_data_dir()
    st = state.load(data_dir)
    state.set_cursor(st, platform, handle, args.type,
                     json.loads(args.value_json), args.run_time)
    state.save(data_dir, st)
    print("OK")
    return 0


def _cmd_state_fail(args) -> int:
    platform, handle = _split_ref(args.ref)
    data_dir = config.get_data_dir()
    st = state.load(data_dir)
    state.set_error(st, platform, handle, args.error, args.run_time)
    state.save(data_dir, st)
    print("OK")
    return 0


def _cmd_profile_append(args) -> int:
    data_dir = config.get_data_dir()
    profiles.append_observation(data_dir, args.creator_id, args.date, args.source, args.body)
    print(f"OK {profiles.profile_path(data_dir, args.creator_id)}")
    return 0


def _cmd_profile_summary(args) -> int:
    data_dir = config.get_data_dir()
    profiles.set_summary(data_dir, args.creator_id, args.text, args.updated_at)
    print(f"OK {profiles.profile_path(data_dir, args.creator_id)}")
    return 0


def _cmd_profile_show(args) -> int:
    text = profiles.read(config.get_data_dir(), args.creator_id)
    print(text.rstrip() if text else "EMPTY")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="roster")
    groups = parser.add_subparsers(dest="group", required=True)

    p_init = groups.add_parser("init", help="设置数据目录")
    p_init.add_argument("data_dir")
    p_init.set_defaults(func=_cmd_init)

    groups.add_parser("data-dir", help="打印数据目录").set_defaults(func=_cmd_data_dir)

    reg_sub = groups.add_parser("registry", help="人与渠道的定义").add_subparsers(
        dest="action", required=True)

    p = reg_sub.add_parser("add"); p.add_argument("url"); p.set_defaults(func=_cmd_registry_add)
    p = reg_sub.add_parser("remove"); p.add_argument("ref"); p.set_defaults(func=_cmd_registry_remove)
    p = reg_sub.add_parser("rename")
    p.add_argument("creator_id"); p.add_argument("display_name")
    p.set_defaults(func=_cmd_registry_rename)
    p = reg_sub.add_parser("merge")
    p.add_argument("id_a"); p.add_argument("id_b"); p.set_defaults(func=_cmd_registry_merge)
    p = reg_sub.add_parser("list"); p.set_defaults(func=_cmd_registry_list)
    p = reg_sub.add_parser("channels")
    p.add_argument("--platform", required=True); p.set_defaults(func=_cmd_registry_channels)

    state_sub = groups.add_parser("state", help="游标与失败态").add_subparsers(
        dest="action", required=True)

    p = state_sub.add_parser("get"); p.add_argument("ref"); p.set_defaults(func=_cmd_state_get)
    p = state_sub.add_parser("set")
    p.add_argument("ref")
    p.add_argument("--type", required=True)
    p.add_argument("--value-json", required=True, dest="value_json")
    p.add_argument("--run-time", required=True, dest="run_time")
    p.set_defaults(func=_cmd_state_set)
    p = state_sub.add_parser("fail")
    p.add_argument("ref")
    p.add_argument("--error", required=True)
    p.add_argument("--run-time", required=True, dest="run_time")
    p.set_defaults(func=_cmd_state_fail)

    prof_sub = groups.add_parser("profile", help="画像").add_subparsers(
        dest="action", required=True)

    p = prof_sub.add_parser("append")
    p.add_argument("creator_id")
    p.add_argument("--date", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--body", required=True)
    p.set_defaults(func=_cmd_profile_append)
    p = prof_sub.add_parser("summary")
    p.add_argument("creator_id")
    p.add_argument("--text", required=True)
    p.add_argument("--updated-at", required=True, dest="updated_at")
    p.set_defaults(func=_cmd_profile_summary)
    p = prof_sub.add_parser("show")
    p.add_argument("creator_id"); p.set_defaults(func=_cmd_profile_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
