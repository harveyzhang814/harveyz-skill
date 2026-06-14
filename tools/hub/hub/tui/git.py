"""Pure git I/O functions — no Textual dependencies."""
import re
import shutil
import subprocess
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "p-launch" / "config.zsh"


def read_project_dirs() -> list[Path]:
    if not CONFIG_FILE.exists():
        return [Path.home() / "Projects"]
    content = CONFIG_FILE.read_text()
    match = re.search(r'PROJECT_DIRS\s*=\s*\(([^)]+)\)', content, re.DOTALL)
    if not match:
        return [Path.home() / "Projects"]
    dirs = []
    for token in re.findall(r'\S+', match.group(1)):
        token = token.strip('"\'')
        p = Path(token).expanduser()
        if p.exists():
            dirs.append(p)
    return dirs or [Path.home() / "Projects"]


def collect_repos(dirs: list[Path]) -> list[Path]:
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
        capture_output=True, text=True,
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
    if not is_git_with_remote(path):
        return {"symbol": "·", "ahead": 0, "behind": 0}
    r = subprocess.run(
        ["git", "-C", str(path), "for-each-ref",
         "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
         "refs/heads"],
        capture_output=True, text=True,
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
    cur_r = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    current = cur_r.stdout.strip()
    r = subprocess.run(
        ["git", "-C", str(path), "for-each-ref",
         "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
         "refs/heads"],
        capture_output=True, text=True,
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
    def git(*args) -> str:
        r = subprocess.run(
            ["git", "-C", str(path)] + list(args),
            capture_output=True, text=True,
        )
        return r.stdout.strip() if r.returncode == 0 else ""

    upstream = git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    local_sha = git("rev-parse", "--short", branch) or "—"
    remote_sha = git("rev-parse", "--short", upstream) if upstream else "—"
    log = git("log", "-1", "--format=%s|%an|%cr", branch)
    parts = log.split("|", 2) if log else ["", "", ""]
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
        "commit_msg": parts[0] if parts else "",
        "author": parts[1] if len(parts) > 1 else "",
        "date": parts[2] if len(parts) > 2 else "",
        "ahead": ahead, "behind": behind,
        "is_local_only": not bool(upstream),
    }


def get_working_tree(path: Path) -> dict:
    """Return counts of modified/new/deleted files in the working tree.

    XY-field classification is simplified: '?' = new (untracked),
    'D' anywhere in the two-char prefix = deleted, else modified.
    Staged-only deletes (D in index column) are counted as deleted.
    """
    r = subprocess.run(
        ["git", "-C", str(path), "status", "--short"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return {"modified": 0, "new": 0, "deleted": 0}
    modified = new = deleted = 0
    for line in r.stdout.splitlines():
        if not line:
            continue
        xy = line[:2]
        if "?" in xy:
            new += 1
        elif "D" in xy:
            deleted += 1
        else:
            modified += 1
    return {"modified": modified, "new": new, "deleted": deleted}


def get_recent_commits(path: Path, n: int = 5) -> list[dict]:
    """Return the last n commits as list of {sha, msg, date}.

    Returns [] on git failure (detached HEAD, empty repo, etc.).
    """
    r = subprocess.run(
        ["git", "-C", str(path), "log", f"-{n}", "--format=%h|%s|%cr"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return []
    commits = []
    for line in r.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({"sha": parts[0], "msg": parts[1], "date": parts[2]})
    return commits


def pull_branch(path: Path, branch: str) -> str:
    up_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        capture_output=True, text=True,
    )
    if up_r.returncode != 0:
        return "no upstream — nothing to pull"
    detail = get_branch_detail(path, branch)
    if detail["ahead"] > 0 and detail["behind"] > 0:
        return f"⚠ skipped {branch} (diverged — push or rebase first)"
    if detail["behind"] == 0:
        return f"nothing to pull — {branch} is up to date"
    cur_r = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    current = cur_r.stdout.strip()
    if branch == current:
        r = subprocess.run(
            ["git", "-C", str(path), "pull", "--ff-only", "origin", branch],
            capture_output=True, text=True,
        )
    else:
        r = subprocess.run(
            ["git", "-C", str(path), "fetch", "origin", f"{branch}:{branch}"],
            capture_output=True, text=True,
        )
    if r.returncode == 0:
        return f"✓ pulled {branch}"
    err = (r.stderr or r.stdout).strip().splitlines()
    reason = err[-1] if err else "unknown error"
    return f"⚠ failed to pull {branch}: {reason}"


def push_branch(path: Path, branch: str) -> str:
    up_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        capture_output=True, text=True,
    )
    if up_r.returncode != 0:
        return "no upstream — branch is local only"
    detail = get_branch_detail(path, branch)
    if detail["ahead"] == 0:
        return f"nothing to push — {branch} is up to date"
    if detail["behind"] > 0:
        return f"⚠ skipped {branch} (diverged — pull or rebase first)"
    r = subprocess.run(
        ["git", "-C", str(path), "push", "origin", branch],
        capture_output=True, text=True,
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
        capture_output=True, text=True,
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
        script = (
            'use framework "AppKit"\n'
            'use scripting additions\n'
            "set thePboard to current application's NSPasteboard's generalPasteboard()\n"
            "thePboard's clearContents()\n"
            f'thePboard\'s setPropertyList:{{"{safe_path}"}} forType:"NSFilenamesPboardType"\n'
            'return current application\'s NSPerformService("New Ghostty Window Here", thePboard)'
        )
        r = subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True)
        if r.returncode == 0:
            ghostty_ok = True

    return cursor_ok, ghostty_ok, ghostty_err
