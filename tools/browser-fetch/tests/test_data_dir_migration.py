"""数据目录迁移跑在 browser-fetch.sh 里（登录态实际落盘在 contexts/ 下，
迁移失败的表现是静默退回未登录，所以必须钉死三种情形）。"""
import subprocess
from pathlib import Path

SH = Path(__file__).resolve().parents[1] / "browser-fetch.sh"


def _run_migration_only(home: Path):
    """只跑脚本里的迁移函数，不进 venv 安装分支。"""
    return subprocess.run(
        ["bash", "-c", f'source "{SH}" --migrate-only'],
        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": str(home)},
    )


def test_migrates_old_dir_when_new_absent(tmp_path):
    old = tmp_path / ".hskill" / "browser-fetch-mcp" / "contexts" / "abc123"
    old.mkdir(parents=True)
    (old / "marker").write_text("x", encoding="utf-8")

    _run_migration_only(tmp_path)

    assert (tmp_path / ".hskill" / "browser-fetch" / "contexts" / "abc123" / "marker").exists()
    assert not (tmp_path / ".hskill" / "browser-fetch-mcp").exists()


def test_is_idempotent_when_old_absent(tmp_path):
    (tmp_path / ".hskill" / "browser-fetch" / "contexts").mkdir(parents=True)
    r = _run_migration_only(tmp_path)
    assert r.returncode == 0
    assert (tmp_path / ".hskill" / "browser-fetch" / "contexts").exists()


def test_does_not_clobber_existing_new_dir(tmp_path):
    old = tmp_path / ".hskill" / "browser-fetch-mcp" / "contexts"
    new = tmp_path / ".hskill" / "browser-fetch" / "contexts"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (new / "keep").write_text("keep", encoding="utf-8")

    _run_migration_only(tmp_path)

    assert (new / "keep").exists()
    assert old.exists()  # 新目录已存在时不动老目录，交给人处理
