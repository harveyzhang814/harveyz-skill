"""sync-xtimeline 的测试配置：把 scripts/ 加入 sys.path。

render_digest.py 的写入目录取自报告里的 archive_dir，不再读任何配置文件，
所以这里不需要环境隔离。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
