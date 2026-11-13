import os
import subprocess
import sys

import pytest

REFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")
sys.path.insert(0, REFS)

import bootstrap_branches as bb  # noqa: E402
import deploy_artifacts as da  # noqa: E402
import workflow_resolve as wr  # noqa: E402

SCRIPT = os.path.join(REFS, "bootstrap_branches.py")
RULE = ".hskill/init-workflow/workflow-config.yml"
TRAILER = "Merge-Via: merge-to-staging.sh"

CFG = """\
branches:
  protected:
    - name: main
      allow_direct_commit: false
      merge_from:
        - staging
        - "release/*"
    - name: staging
      allow_direct_commit: false
      merge_from:
        - "feature/*"
        - "chore/*"
branch_naming:
  enforce: true
  allowed_patterns:
    - "^feature/.+"
    - "^chore/.+"
  exempt:
    - main
    - staging
"""


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r.stdout.strip()


def make_repo(path, branch=None):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", *(["-b", branch] if branch else []))
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "t")
    return path


def write_cfg(repo):
    p = repo / RULE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(CFG)


def commit_file(repo, name, msg):
    (repo / name).write_text(msg + "\n")
    git(repo, "add", name)
    git(repo, "commit", "-qm", msg, "--no-verify")


def install_blocking_hooks(repo):
    """模拟已部署的 hooks：任何提交都被拒。起步引导的根提交必须不受它影响。"""
    hooks = repo / ".githooks"
    hooks.mkdir(exist_ok=True)
    for name in ("pre-commit", "commit-msg"):
        h = hooks / name
        h.write_text("#!/bin/sh\necho blocked >&2\nexit 1\n")
        h.chmod(0o755)
    git(repo, "config", "core.hooksPath", ".githooks")


def protected(tmp_path):
    p = tmp_path / "cfg.yml"
    p.write_text(CFG)
    return wr.load_config(str(p))["protected"]


# ---- branch_order ----

def test_branch_order_root_first(tmp_path):
    assert bb.branch_order(protected(tmp_path)) == [("main", None), ("staging", "main")]


def test_branch_order_rejects_multiple_roots():
    two_roots = [
        {"name": "main", "allow_direct_commit": False, "merge_from": ["release/*"]},
        {"name": "staging", "allow_direct_commit": False, "merge_from": ["feature/*"]},
    ]
    with pytest.raises(wr.ConfigError):
        bb.branch_order(two_roots)


def test_branch_order_rejects_cycle():
    cyc = [
        {"name": "a", "allow_direct_commit": False, "merge_from": ["b"]},
        {"name": "b", "allow_direct_commit": False, "merge_from": ["a"]},
    ]
    with pytest.raises(wr.ConfigError):
        bb.branch_order(cyc)


# ---- 全新仓库 ----

def fresh_deployed(tmp_path):
    repo = make_repo(tmp_path / "proj")  # 不带 -b：git 默认分支名（可能是 master）
    (repo / "README.md").write_text("hello\n")  # 用户自己的文件，进根提交
    (repo / "src").mkdir()
    (repo / "src" / "app.sh").write_text("echo hi\n")
    (repo / "debug.log").write_text("noise\n")  # 被 .gitignore 忽略，不进根提交
    write_cfg(repo)
    da.deploy(str(repo))
    with open(repo / ".gitignore", "a") as f:
        f.write("*.log\n")
    install_blocking_hooks(repo)
    return repo


FRESH_FILES = sorted([
    ".githooks/commit-msg", ".githooks/pre-commit", ".gitignore",
    ".hskill/init-workflow/resolved.env", RULE, "README.md",
    "docs/reference/git-workflow.md", "scripts/merge-to-staging.sh", "src/app.sh",
])
FRESH_PLAN = ([("ROOT-COMMIT", "main")] + [("FILE", p) for p in FRESH_FILES]
              + [("CREATE", "staging", "main"), ("SWITCH", "staging"),
                 ("WARN", "first-publish", "staging")])


def test_fresh_repo_root_commit_and_branches(tmp_path):
    repo = fresh_deployed(tmp_path)
    assert bb.bootstrap(str(repo)) == FRESH_PLAN
    assert git(repo, "rev-list", "--count", "main") == "1"
    assert git(repo, "rev-parse", "staging") == git(repo, "rev-parse", "main")
    assert sorted(git(repo, "ls-tree", "-r", "--name-only", "main").splitlines()) == FRESH_FILES


def test_fresh_repo_main_worktree_rests_on_merge_target(tmp_path):
    repo = fresh_deployed(tmp_path)
    bb.bootstrap(str(repo))
    assert git(repo, "symbolic-ref", "--short", "HEAD") == "staging"
    # 切换只改 HEAD 指向；两条分支同一提交，工作区与索引都干净（被忽略的文件不算）
    assert git(repo, "status", "--porcelain") == ""


def test_dry_run_changes_nothing(tmp_path):
    repo = fresh_deployed(tmp_path)
    head_before = git(repo, "symbolic-ref", "HEAD")
    assert bb.bootstrap(str(repo), dry_run=True) == FRESH_PLAN
    assert git(repo, "symbolic-ref", "HEAD") == head_before
    assert git(repo, "rev-parse", "-q", "--verify", "HEAD", check=False) == ""
    assert git(repo, "for-each-ref", "refs/heads") == ""
    assert git(repo, "ls-files") == ""


def test_rerun_after_bootstrap_only_repeats_the_warning(tmp_path):
    repo = fresh_deployed(tmp_path)
    bb.bootstrap(str(repo))
    assert bb.bootstrap(str(repo)) == [
        ("EXISTS", "main"), ("EXISTS", "staging"), ("WARN", "first-publish", "staging")]


# ---- 已有提交的仓库 ----

def test_existing_repo_creates_missing_integration_branch(tmp_path):
    repo = make_repo(tmp_path / "proj", "main")
    commit_file(repo, "a.txt", "seed")
    write_cfg(repo)
    main_before = git(repo, "rev-parse", "main")
    assert bb.bootstrap(str(repo)) == [
        ("EXISTS", "main"), ("CREATE", "staging", "main"), ("WARN", "first-publish", "staging")]
    assert git(repo, "rev-parse", "main") == main_before
    assert git(repo, "rev-parse", "staging") == main_before


def test_existing_repo_without_root_branch_stops(tmp_path):
    repo = make_repo(tmp_path / "proj", "master")
    commit_file(repo, "a.txt", "seed")
    write_cfg(repo)
    with pytest.raises(bb.BootstrapError, match="main"):
        bb.bootstrap(str(repo))
    assert git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads") == "master"


def test_missing_branch_taken_from_remote(tmp_path):
    origin = make_repo(tmp_path / "origin", "main")
    commit_file(origin, "a.txt", "seed")
    git(origin, "branch", "staging")
    git(origin, "checkout", "-q", "staging")
    commit_file(origin, "b.txt", "staging-only")
    git(origin, "checkout", "-q", "main")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    write_cfg(clone)
    assert bb.bootstrap(str(clone)) == [("EXISTS", "main"), ("CREATE", "staging", "origin/staging")]
    assert git(clone, "rev-parse", "staging") == git(origin, "rev-parse", "staging")


# ---- 推送前提醒（合并目标上未推送、不带标记行的 first-parent 提交） ----

def repo_with_remote(tmp_path):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    repo = make_repo(tmp_path / "proj", "main")
    commit_file(repo, "a.txt", "seed")
    git(repo, "branch", "staging")
    git(repo, "remote", "add", "origin", str(bare))
    write_cfg(repo)
    return repo


def test_warns_unpushed_unmarked_commits(tmp_path):
    repo = repo_with_remote(tmp_path)
    git(repo, "push", "-q", "-u", "origin", "main", "staging")
    git(repo, "checkout", "-q", "staging")
    commit_file(repo, "b.txt", "direct one")
    commit_file(repo, "c.txt", "direct two")
    git(repo, "commit", "-q", "--allow-empty", "--no-verify", "-m", f"merge: x\n\n{TRAILER}")
    assert bb.bootstrap(str(repo)) == [
        ("EXISTS", "main"), ("EXISTS", "staging"), ("WARN", "unpushed", "staging", "2")]


def test_no_warning_when_target_in_sync(tmp_path):
    repo = repo_with_remote(tmp_path)
    git(repo, "push", "-q", "-u", "origin", "main", "staging")
    assert bb.bootstrap(str(repo)) == [("EXISTS", "main"), ("EXISTS", "staging")]


def test_warns_first_publish_when_target_not_on_remote(tmp_path):
    repo = repo_with_remote(tmp_path)
    git(repo, "push", "-q", "-u", "origin", "main")
    assert bb.bootstrap(str(repo)) == [
        ("EXISTS", "main"), ("EXISTS", "staging"), ("WARN", "first-publish", "staging")]


def test_first_publish_warned_even_without_remote(tmp_path):
    # 还没加远端时也提醒：加上远端后第一次推送合并目标同样会被拒
    repo = make_repo(tmp_path / "proj", "main")
    commit_file(repo, "a.txt", "seed")
    write_cfg(repo)
    assert ("WARN", "first-publish", "staging") in bb.bootstrap(str(repo))


def test_no_first_publish_warning_after_a_script_merge(tmp_path):
    repo = make_repo(tmp_path / "proj", "main")
    commit_file(repo, "a.txt", "seed")
    git(repo, "branch", "staging")
    git(repo, "checkout", "-q", "staging")
    git(repo, "commit", "-q", "--allow-empty", "--no-verify", "-m", f"merge: x\n\n{TRAILER}")
    write_cfg(repo)
    assert bb.bootstrap(str(repo)) == [("EXISTS", "main"), ("EXISTS", "staging")]


def test_warns_when_new_branch_inherits_unpushed_commits(tmp_path):
    repo = repo_with_remote(tmp_path)
    git(repo, "branch", "-D", "staging")
    git(repo, "push", "-q", "-u", "origin", "main")
    commit_file(repo, "local.txt", "local only")
    assert bb.bootstrap(str(repo), dry_run=True) == [
        ("EXISTS", "main"), ("CREATE", "staging", "main"),
        ("WARN", "ahead", "main", "1", "staging"), ("WARN", "first-publish", "staging")]


# ---- CLI ----

def run_cli(repo, *args):
    return subprocess.run([sys.executable, SCRIPT, str(repo), *args], capture_output=True, text=True)


def test_cli_prints_results_and_exit_0(tmp_path):
    repo = fresh_deployed(tmp_path)
    r = run_cli(repo, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == [" ".join(s) for s in FRESH_PLAN] + ["DRY-RUN"]


def test_cli_exit_2_without_rule_file(tmp_path):
    repo = make_repo(tmp_path / "proj", "main")
    assert run_cli(repo).returncode == 2


def test_cli_exit_4_when_root_branch_missing(tmp_path):
    repo = make_repo(tmp_path / "proj", "master")
    commit_file(repo, "a.txt", "seed")
    write_cfg(repo)
    r = run_cli(repo)
    assert r.returncode == 4
    assert "ERROR" in r.stderr and "main" in r.stderr
