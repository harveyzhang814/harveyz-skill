#!/usr/bin/env python3
"""统一存储根解析：读 ~/.hskill/config.json 的 knowledgeRoot 字段，为
clip-url / learn-video / sync-xtimeline / sync-ytchannel 四个 skill 提供
落盘路径。四份内容相同的副本——本仓库既定模式（browser_fetch_locate.py
就在三处各存一份）。

只做"读一个字符串再拼一层固定子目录名"，不做目录创建——各 skill 在真正
写文件时自己 mkdir -p，保持"读路径"与"建目录"分离。

支持 HSKILL_CONFIG 环境变量覆盖 config 路径，供测试注入临时根；每次调用
时读取（不在 import 时绑定），进程内 monkeypatch 才能生效。
"""
import json
import os
import sys
from pathlib import Path

_INIT_HINT = "抓取产物统一存到哪个目录？（直接回车使用默认：~/Documents/knowledge）"


def _config_path() -> Path:
    env_cfg = os.environ.get("HSKILL_CONFIG")
    return Path(env_cfg) if env_cfg else Path.home() / ".hskill" / "config.json"


def get_root() -> Path:
    config_path = _config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"{config_path} 不存在，请先完成初始化：{_INIT_HINT}")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if "knowledgeRoot" not in cfg:
        raise KeyError(f"{config_path} 缺少 knowledgeRoot 字段，请先完成初始化：{_INIT_HINT}")
    return Path(cfg["knowledgeRoot"]).expanduser()


def articles_dir() -> Path:
    return get_root() / "articles"


def videos_dir() -> Path:
    return get_root() / "videos"


def feeds_dir(channel: str) -> Path:
    return get_root() / "feeds" / channel


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        try:
            print(f"OK: {get_root()}")
        except (FileNotFoundError, KeyError) as e:
            print(f"MISSING: {e}", file=sys.stderr)
            sys.exit(1)
        return
    print("Usage: store_config.py check", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
