#!/usr/bin/env python3
"""统一存储根解析：读 ~/.hskill/config.json 的 knowledgeRoot 字段，为
clip-url / learn-video / sync-xtimeline / sync-ytchannel 四个 skill 提供
落盘路径。四份内容相同的副本——本仓库既定模式（browser_fetch_locate.py
就在三处各存一份）。

只做"读一个字符串再拼一层固定子目录名"，不做目录创建——各 skill 在真正
写文件时自己 mkdir -p，保持"读路径"与"建目录"分离。

支持 HSKILL_CONFIG 环境变量覆盖 config 路径，供测试注入临时根；每次调用
时读取（不在 import 时绑定），进程内 monkeypatch 才能生效。

check-downstream 子命令核对 vdl / scholia 当前配置是否等于 knowledgeRoot
推出的期望值——knowledgeRoot 是唯一事实依据，vdl/scholia 的值只是被检查
的对象，不参与仲裁。只读，不改任何下游文件；发现漂移只打印修复命令。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

_INIT_HINT = "抓取产物统一存到哪个目录？（直接回车使用默认：~/knowledge）"


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


def _run_downstream_command(cmd):
    """跑一个下游程序的 CLI，拿不到（未安装/非 0 退出）时返回 None。"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _check_vdl():
    output = _run_downstream_command(["vdl", "config", "get"])
    if output is None:
        return [("SKIP", "vdl not installed (command not found)")]
    actual = ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("workRoot:"):
            actual = line.split(":", 1)[1].strip()
    expected = str(videos_dir())
    if actual == expected:
        return [("OK", "vdl WORK_ROOT")]
    return [
        ("DRIFT", f"vdl WORK_ROOT={actual} (expect {expected})"),
        ("FIX", f"vdl config set work-root {expected}"),
    ]


def _check_scholia():
    output = _run_downstream_command(["scholia", "config", "list"])
    if output is None:
        return [("SKIP", "scholia not installed (command not found)")]
    actual = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        actual[key.strip()] = value.strip()
    expected = {
        "work-dir": str(videos_dir() / "work"),
        "content-dir": str(articles_dir()),
        "x-dir": str(feeds_dir("tweets") / "creators"),
    }
    results = []
    for key, exp in expected.items():
        act = actual.get(key, "")
        if act == exp:
            results.append(("OK", f"scholia {key}"))
        else:
            results.append(("DRIFT", f"scholia {key}={act} (expect {exp})"))
            results.append(("FIX", f"scholia config set {key} {exp}"))
    return results


def check_downstream() -> int:
    get_root()  # 触发 MISSING 异常，交给调用方处理
    entries = _check_vdl() + _check_scholia()
    has_drift = False
    for kind, message in entries:
        if kind == "FIX":
            print(f"  fix: {message}")
        elif kind == "DRIFT":
            has_drift = True
            print(f"DRIFT: {message}")
        else:
            print(f"{kind}: {message}")
    return 1 if has_drift else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        try:
            print(f"OK: {get_root()}")
        except (FileNotFoundError, KeyError) as e:
            print(f"MISSING: {e}", file=sys.stderr)
            sys.exit(1)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "check-downstream":
        try:
            sys.exit(check_downstream())
        except (FileNotFoundError, KeyError) as e:
            print(f"MISSING: {e}", file=sys.stderr)
            sys.exit(1)
        return
    print("Usage: store_config.py check|check-downstream", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
