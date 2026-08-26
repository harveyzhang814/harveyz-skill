"""sync-ytchannel 的测试隔离。名册化之后本 skill 不再持有自己的 DATA_DIR
（改为向 roster 要），所以这里不再需要伪造配置文件——需要隔离 roster 的
测试自己 monkeypatch roster_client。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
