"""browser-fetch CLI —— 六个子命令，stdout 一行 compact JSON。

退出码：0 成功；2 调用方用法错（core 抛 ValueError）；1 运行时失败。
失败时 stdout 保持空，消息走 stderr。
"""
import argparse
import asyncio
import json
import sys

from browser_fetch import core


def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="browser-fetch")
    sub = parser.add_subparsers(dest="command", required=True)

    p_profile = sub.add_parser("profile", help="持久化的默认 Chrome profile")
    psub = p_profile.add_subparsers(dest="profile_command", required=True)

    p_get = psub.add_parser("get")
    p_get.set_defaults(handler=lambda a: core.get_default_chrome_profile())

    p_set = psub.add_parser("set")
    p_set.add_argument("path")
    p_set.set_defaults(handler=lambda a: core.set_default_chrome_profile(a.path))

    p_list = psub.add_parser("list")
    p_list.add_argument("--host-key", action="append", default=[], dest="host_keys")
    p_list.add_argument("--cookie-name", action="append", default=[], dest="cookie_names")
    p_list.set_defaults(handler=lambda a: core.list_chrome_profiles(a.host_keys, a.cookie_names))

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(args.handler(args))
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1
    _emit(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
