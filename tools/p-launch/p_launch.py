#!/usr/bin/env python3
"""p-launch v3 — local repository manager (Python + Textual)"""
import re
import subprocess
import shutil
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "p-launch" / "config.zsh"


def read_project_dirs() -> list[Path]:
    """Parse PROJECT_DIRS array from ~/.config/p-launch/config.zsh."""
    if not CONFIG_FILE.exists():
        return [Path.home() / "Projects"]
    content = CONFIG_FILE.read_text()
    match = re.search(r'PROJECT_DIRS\s*=\s*\(([^)]+)\)', content, re.DOTALL)
    if not match:
        return [Path.home() / "Projects"]
    dirs = []
    for token in re.findall(r'\S+', match.group(1)):
        p = Path(token).expanduser()
        if p.exists():
            dirs.append(p)
    return dirs or [Path.home() / "Projects"]


def collect_repos(dirs: list[Path]) -> list[Path]:
    """Find all git repos (direct children with .git) under the given dirs."""
    repos: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for child in sorted(d.iterdir()):
            if child.is_dir() and (child / ".git").exists():
                repos.append(child)
    return repos


def is_git_with_remote(path: Path) -> bool:
    r = subprocess.run(
        ["git", "-C", str(path), "remote"],
        capture_output=True, text=True
    )
    return r.returncode == 0 and bool(r.stdout.strip())


def fetch_repo(path: Path) -> None:
    try:
        subprocess.run(
            ["git", "-C", str(path), "fetch", "--all", "-q"],
            capture_output=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        pass


def get_repo_status(path: Path) -> dict:
    """Returns {'symbol': str, 'ahead': int, 'behind': int}."""
    if not is_git_with_remote(path):
        return {"symbol": "·", "ahead": 0, "behind": 0}

    r = subprocess.run(
        ["git", "-C", str(path), "for-each-ref",
         "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
         "refs/heads"],
        capture_output=True, text=True
    )
    total_ahead = total_behind = 0
    has_tracking = False
    for line in r.stdout.strip().splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        upstream, track = parts[1], parts[2]
        if not upstream or "gone" in track:
            continue
        has_tracking = True
        if m := re.search(r"ahead (\d+)", track):
            total_ahead += int(m.group(1))
        if m := re.search(r"behind (\d+)", track):
            total_behind += int(m.group(1))

    if not has_tracking:
        return {"symbol": "·", "ahead": 0, "behind": 0}

    symbol = ""
    if total_ahead:
        symbol += f"↑{total_ahead}"
    if total_behind:
        symbol += f"↓{total_behind}"
    if not symbol:
        symbol = "✓"
    return {"symbol": symbol, "ahead": total_ahead, "behind": total_behind}


def get_branches(path: Path) -> list[dict]:
    """List all branches. Each dict has: name, upstream, ahead, behind, is_current, is_local_only."""
    cur_r = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True
    )
    current = cur_r.stdout.strip()

    r = subprocess.run(
        ["git", "-C", str(path), "for-each-ref",
         "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
         "refs/heads"],
        capture_output=True, text=True
    )
    branches: list[dict] = []
    for line in r.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("|")
        name = parts[0]
        upstream = parts[1] if len(parts) > 1 else ""
        track = parts[2] if len(parts) > 2 else ""
        if upstream and "gone" in track:
            continue
        ahead = behind = 0
        if upstream:
            if m := re.search(r"ahead (\d+)", track):
                ahead = int(m.group(1))
            if m := re.search(r"behind (\d+)", track):
                behind = int(m.group(1))
        branches.append({
            "name": name, "upstream": upstream,
            "ahead": ahead, "behind": behind,
            "is_current": name == current,
            "is_local_only": not bool(upstream),
        })
    return branches


def get_branch_detail(path: Path, branch: str) -> dict:
    """Detailed info for a single branch."""
    def git(*args) -> str:
        r = subprocess.run(["git", "-C", str(path)] + list(args),
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""

    upstream = git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    local_sha = git("rev-parse", "--short", branch) or "—"
    remote_sha = git("rev-parse", "--short", upstream) if upstream else "—"
    log = git("log", "-1", "--format=%s|%an|%cr", branch)
    parts = log.split("|", 2) if log else ["", "", ""]
    commit_msg = parts[0] if len(parts) > 0 else ""
    author = parts[1] if len(parts) > 1 else ""
    date = parts[2] if len(parts) > 2 else ""

    ahead = behind = 0
    if upstream:
        track = git("for-each-ref", "--format=%(upstream:track)", f"refs/heads/{branch}")
        if m := re.search(r"ahead (\d+)", track):
            ahead = int(m.group(1))
        if m := re.search(r"behind (\d+)", track):
            behind = int(m.group(1))

    return {
        "name": branch, "upstream": upstream,
        "local_sha": local_sha, "remote_sha": remote_sha,
        "commit_msg": commit_msg, "author": author, "date": date,
        "ahead": ahead, "behind": behind,
        "is_local_only": not bool(upstream),
    }


def pull_branch(path: Path, branch: str) -> str:
    """Pull a single branch. Returns human-readable result."""
    cur_r = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True
    )
    current = cur_r.stdout.strip()

    up_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        capture_output=True, text=True
    )
    if up_r.returncode != 0:
        return "no upstream — nothing to pull"

    if branch == current:
        r = subprocess.run(
            ["git", "-C", str(path), "pull", "--ff-only", "origin", branch],
            capture_output=True, text=True
        )
    else:
        r = subprocess.run(
            ["git", "-C", str(path), "fetch", "origin", f"{branch}:{branch}"],
            capture_output=True, text=True
        )
    return f"✓ pulled {branch}" if r.returncode == 0 else f"⚠ failed to pull {branch}"


def push_branch(path: Path, branch: str) -> str:
    """Push a single branch. Returns human-readable result."""
    up_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        capture_output=True, text=True
    )
    if up_r.returncode != 0:
        return "no upstream — branch is local only"

    r = subprocess.run(
        ["git", "-C", str(path), "push", "origin", branch],
        capture_output=True, text=True
    )
    return f"✓ pushed {branch}" if r.returncode == 0 else f"⚠ failed to push {branch}"


def launch_project(path: Path) -> tuple[bool, bool, str]:
    """Open project in Cursor + Ghostty. Returns (cursor_ok, ghostty_ok, ghostty_err)."""
    cursor_ok = False
    ghostty_ok = False
    ghostty_err = "not installed"

    if shutil.which("cursor"):
        subprocess.Popen(["cursor", str(path)])
        cursor_ok = True
    elif Path("/Applications/Cursor.app").exists():
        r = subprocess.run(["/usr/bin/open", "-na", "Cursor", "--args", str(path)])
        cursor_ok = r.returncode == 0

    mdfind = subprocess.run(
        ["mdfind", "kMDItemCFBundleIdentifier == 'com.mitchellh.ghostty'"],
        capture_output=True, text=True
    )
    ghostty_app = (mdfind.stdout.strip().splitlines() or [""])[0]
    if not ghostty_app:
        for p in ["/Applications/Ghostty.app",
                  str(Path.home() / "Applications/Ghostty.app")]:
            if Path(p).exists():
                ghostty_app = p
                break

    if ghostty_app:
        ghostty_err = "failed to open"
        children = sorted(path.iterdir()) if path.exists() else []
        service_path = str(children[0]) if children else str(path)
        safe_path = service_path.replace("\\", "\\\\").replace('"', '\\"')
        script = f'''use framework "AppKit"
use scripting additions
set thePboard to current application's NSPasteboard's generalPasteboard()
thePboard's clearContents()
thePboard's setPropertyList:{{"{safe_path}"}} forType:"NSFilenamesPboardType"
return current application's NSPerformService("New Ghostty Window Here", thePboard)'''
        r = subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True)
        if r.returncode == 0:
            ghostty_ok = True

    return cursor_ok, ghostty_ok, ghostty_err
