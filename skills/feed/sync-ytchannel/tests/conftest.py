"""sync-ytchannel 的测试隔离。名册化之后本 skill 不再持有自己的 DATA_DIR
（改为向 roster 要），所以这里不再需要伪造配置文件——需要隔离 roster 的
测试自己 monkeypatch roster_client。`write_config` 是给 subprocess CLI
测试用的（跨进程 monkeypatch 不过去），镜像 sync-xtimeline 的同名函数。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

ROSTER_CONFIG_ENV = "HSKILL_ROSTER_CONFIG"


def write_config(config_path: Path, data_dir: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"DATA_DIR": str(data_dir)}), encoding="utf-8")
