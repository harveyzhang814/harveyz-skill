import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Mock textual before importing p_launch so the UI layer doesn't block unit tests.
for _mod in [
    "textual", "textual.app", "textual.containers", "textual.widgets",
    "textual.binding", "textual.work",
]:
    sys.modules.setdefault(_mod, MagicMock())

sys.path.insert(0, str(Path(__file__).parent.parent))
from p_launch import (
    read_project_dirs, collect_repos, get_repo_status,
    get_branches, get_branch_detail, pull_branch, push_branch,
    CONFIG_FILE,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def git(*args, cwd=None):
    subprocess.run(
        ["git"] + list(args), cwd=cwd,
        capture_output=True, check=True,
        env={**__import__("os").environ,
             "GIT_CONFIG_NOSYSTEM": "1",
             "GIT_AUTHOR_NAME": "Test",
             "GIT_AUTHOR_EMAIL": "t@t.com",
             "GIT_COMMITTER_NAME": "Test",
             "GIT_COMMITTER_EMAIL": "t@t.com",
             # Ensure default branch is always 'main' regardless of system git config
             "GIT_CONFIG_COUNT": "1",
             "GIT_CONFIG_KEY_0": "init.defaultBranch",
             "GIT_CONFIG_VALUE_0": "main"},
    )


def make_repo_with_remote(name: str, tmp_path: Path) -> tuple[Path, Path]:
    """Returns (clone_path, bare_path)."""
    bare = tmp_path / "remotes" / f"{name}.git"
    bare.mkdir(parents=True)
    git("init", "--bare", str(bare))
    # Explicitly set bare repo HEAD to main so all clones default to main
    git("symbolic-ref", "HEAD", "refs/heads/main", cwd=str(bare))
    clone = tmp_path / "repos" / name
    clone.mkdir(parents=True)
    git("clone", str(bare), str(clone))
    git("commit", "--allow-empty", "-m", "init", cwd=str(clone))
    git("push", "origin", "HEAD:main", cwd=str(clone))
    git("branch", "-M", "main", cwd=str(clone))
    git("branch", "--set-upstream-to=origin/main", "main", cwd=str(clone))
    return clone, bare


# ── read_project_dirs ─────────────────────────────────────────────────────────

def test_read_project_dirs_missing_config(tmp_path, monkeypatch):
    monkeypatch.setattr("p_launch.CONFIG_FILE", tmp_path / "nonexistent.zsh")
    dirs = read_project_dirs()
    assert any("Projects" in str(d) for d in dirs)


def test_read_project_dirs_parses_array(tmp_path, monkeypatch):
    config = tmp_path / "config.zsh"
    config.write_text(f"PROJECT_DIRS=({tmp_path})\n")
    monkeypatch.setattr("p_launch.CONFIG_FILE", config)
    dirs = read_project_dirs()
    assert tmp_path in dirs


# ── collect_repos ─────────────────────────────────────────────────────────────

def test_collect_repos_finds_git_dirs(tmp_path):
    repo = tmp_path / "my-project"
    repo.mkdir()
    (repo / ".git").mkdir()
    non_repo = tmp_path / "not-a-repo"
    non_repo.mkdir()
    result = collect_repos([tmp_path])
    assert repo in result
    assert non_repo not in result


# ── get_repo_status ───────────────────────────────────────────────────────────

def test_get_repo_status_synced(tmp_path):
    clone, _ = make_repo_with_remote("status-synced", tmp_path)
    status = get_repo_status(clone)
    assert status["symbol"] == "✓"
    assert status["ahead"] == 0
    assert status["behind"] == 0


def test_get_repo_status_behind(tmp_path):
    clone, bare = make_repo_with_remote("status-behind", tmp_path)
    tmp_clone2 = tmp_path / "tmp2"
    tmp_clone2.mkdir()
    git("clone", str(bare), str(tmp_clone2))
    git("commit", "--allow-empty", "-m", "remote commit", cwd=str(tmp_clone2))
    git("push", "origin", "main", cwd=str(tmp_clone2))
    git("fetch", "origin", cwd=str(clone))
    status = get_repo_status(clone)
    assert "↓" in status["symbol"]
    assert status["behind"] > 0


def test_get_repo_status_no_remote(tmp_path):
    bare_repo = tmp_path / "bare-local"
    bare_repo.mkdir()
    git("init", str(bare_repo))
    status = get_repo_status(bare_repo)
    assert status["symbol"] == "·"


# ── get_branches ──────────────────────────────────────────────────────────────

def test_get_branches_returns_main(tmp_path):
    clone, _ = make_repo_with_remote("branches-main", tmp_path)
    branches = get_branches(clone)
    names = [b["name"] for b in branches]
    assert "main" in names


def test_get_branches_local_only(tmp_path):
    clone, _ = make_repo_with_remote("branches-local", tmp_path)
    git("checkout", "-b", "feature/local-only", cwd=str(clone))
    branches = get_branches(clone)
    local = [b for b in branches if b["name"] == "feature/local-only"]
    assert len(local) == 1
    assert local[0]["is_local_only"] is True


# ── get_branch_detail ─────────────────────────────────────────────────────────

def test_get_branch_detail_synced(tmp_path):
    clone, _ = make_repo_with_remote("detail-synced", tmp_path)
    detail = get_branch_detail(clone, "main")
    assert detail["name"] == "main"
    assert detail["ahead"] == 0
    assert detail["behind"] == 0
    assert detail["local_sha"] != "—"


def test_get_branch_detail_local_only(tmp_path):
    clone, _ = make_repo_with_remote("detail-local", tmp_path)
    git("checkout", "-b", "local-branch", cwd=str(clone))
    detail = get_branch_detail(clone, "local-branch")
    assert detail["is_local_only"] is True
    assert detail["upstream"] == ""


# ── pull_branch ───────────────────────────────────────────────────────────────

def test_pull_branch_no_upstream(tmp_path):
    clone, _ = make_repo_with_remote("pull-local", tmp_path)
    git("checkout", "-b", "local-only", cwd=str(clone))
    result = pull_branch(clone, "local-only")
    assert "no upstream" in result


def test_pull_branch_synced(tmp_path):
    clone, _ = make_repo_with_remote("pull-synced", tmp_path)
    result = pull_branch(clone, "main")
    assert "pulled" in result or "nothing" in result or "✓" in result


def test_pull_branch_behind(tmp_path):
    clone, bare = make_repo_with_remote("pull-behind", tmp_path)
    tc2 = tmp_path / "tc2"
    tc2.mkdir()
    git("clone", str(bare), str(tc2))
    git("commit", "--allow-empty", "-m", "remote ahead", cwd=str(tc2))
    git("push", "origin", "main", cwd=str(tc2))
    git("fetch", "origin", cwd=str(clone))
    result = pull_branch(clone, "main")
    assert "✓" in result
    local_sha = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "main"],
        capture_output=True, text=True
    ).stdout.strip()
    remote_sha = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "origin/main"],
        capture_output=True, text=True
    ).stdout.strip()
    assert local_sha == remote_sha


# ── push_branch ───────────────────────────────────────────────────────────────

def test_push_branch_no_upstream(tmp_path):
    clone, _ = make_repo_with_remote("push-local", tmp_path)
    git("checkout", "-b", "local-only", cwd=str(clone))
    result = push_branch(clone, "local-only")
    assert "no upstream" in result


def test_push_branch_ahead(tmp_path):
    clone, bare = make_repo_with_remote("push-ahead", tmp_path)
    git("commit", "--allow-empty", "-m", "local commit", cwd=str(clone))
    result = push_branch(clone, "main")
    assert "✓" in result
    repo_sha = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "main"],
        capture_output=True, text=True
    ).stdout.strip()
    bare_sha = subprocess.run(
        ["git", "-C", str(bare), "rev-parse", "main"],
        capture_output=True, text=True
    ).stdout.strip()
    assert repo_sha == bare_sha


def _make_diverged(tmp_path, name: str) -> tuple[Path, Path]:
    """Create a repo where local and remote have diverged (both ahead and behind)."""
    clone, bare = make_repo_with_remote(name, tmp_path)
    tc = tmp_path / f"tc-{name}"
    tc.mkdir()
    git("clone", str(bare), str(tc))
    git("commit", "--allow-empty", "-m", "remote advance", cwd=str(tc))
    git("push", "origin", "main", cwd=str(tc))
    git("commit", "--allow-empty", "-m", "local advance", cwd=str(clone))
    git("fetch", "origin", cwd=str(clone))
    return clone, bare


def test_pull_branch_diverged(tmp_path):
    clone, _ = _make_diverged(tmp_path, "pull-div")
    result = pull_branch(clone, "main")
    assert "diverged" in result
    assert "✓" not in result


def test_push_branch_diverged(tmp_path):
    clone, _ = _make_diverged(tmp_path, "push-div")
    result = push_branch(clone, "main")
    assert "diverged" in result
    assert "✓" not in result
