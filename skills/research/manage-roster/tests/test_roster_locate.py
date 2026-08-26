"""roster_locate 的两种布局：仓库 checkout 内 / hskill 装机后。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import roster_locate


def test_finds_launcher_in_repo_checkout():
    """本测试就跑在 checkout 里，dev 路径必须命中真实文件。"""
    found = Path(roster_locate.find_roster())
    assert found.name == "roster.sh"
    assert found.exists()


def test_raises_when_nothing_found(monkeypatch, tmp_path):
    monkeypatch.setattr(roster_locate, "_dev_path", lambda: tmp_path / "nope.sh")
    monkeypatch.setattr(roster_locate.shutil, "which", lambda _: None)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    with pytest.raises(FileNotFoundError, match="roster"):
        roster_locate.find_roster()
