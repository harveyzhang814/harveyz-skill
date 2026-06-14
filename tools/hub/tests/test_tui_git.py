from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hub.tui.git import (
    get_recent_commits,
    get_working_tree,
    read_project_dirs,
)


def test_get_working_tree_clean():
    with patch("hub.tui.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = get_working_tree(Path("/fake"))
    assert result == {"modified": 0, "new": 0, "deleted": 0}


def test_get_working_tree_dirty():
    output = " M README.md\n?? newfile.py\nD  deleted.py\n M other.py\n"
    with patch("hub.tui.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        result = get_working_tree(Path("/fake"))
    assert result == {"modified": 2, "new": 1, "deleted": 1}


def test_get_recent_commits():
    output = "abc123|Fix bug|2 hours ago\ndef456|Add feature|1 day ago\n"
    with patch("hub.tui.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        commits = get_recent_commits(Path("/fake"), n=2)
    assert len(commits) == 2
    assert commits[0] == {"sha": "abc123", "msg": "Fix bug", "date": "2 hours ago"}
    assert commits[1] == {"sha": "def456", "msg": "Add feature", "date": "1 day ago"}


def test_get_recent_commits_empty():
    with patch("hub.tui.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        commits = get_recent_commits(Path("/fake"), n=5)
    assert commits == []


def test_read_project_dirs_default(tmp_path, monkeypatch):
    monkeypatch.setattr("hub.tui.git.CONFIG_FILE", tmp_path / "nonexistent.zsh")
    result = read_project_dirs()
    assert result == [Path.home() / "Projects"]


def test_read_project_dirs_from_config(tmp_path, monkeypatch):
    projects_dir = tmp_path / "my_projects"
    projects_dir.mkdir()
    config = tmp_path / "config.zsh"
    config.write_text(f'PROJECT_DIRS=("{projects_dir}")\n')
    monkeypatch.setattr("hub.tui.git.CONFIG_FILE", config)
    result = read_project_dirs()
    assert result == [projects_dir]
