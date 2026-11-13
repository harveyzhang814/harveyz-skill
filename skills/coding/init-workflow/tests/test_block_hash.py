import os
import subprocess
import sys

REFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")
sys.path.insert(0, REFS)

import block_hash as bh  # noqa: E402
import render_merge_script as rms  # noqa: E402

SCRIPT = os.path.join(REFS, "block_hash.py")

BODY = '''if [ "$BRANCH" = "main" ]; then
    echo "❌ no"
    exit 1
fi'''


def hook(body=BODY, h="PLACEHOLDER", block_id="branches.protected/main"):
    return (f"#!/bin/sh\nBRANCH=x\n"
            f"# --- BEGIN MANAGED: {block_id} (hash:{h}) ---\n{body}\n"
            f"# --- END MANAGED: {block_id} ---\nexit 0\n")


def git_hash(content):
    r = subprocess.run(["git", "hash-object", "--stdin"], input=content.encode(),
                       capture_output=True, check=True)
    return r.stdout.decode()[:8]


def test_hash_is_git_blob_of_stripped_content():
    # 首行缩进与末尾换行去掉，中间各行缩进保留
    content = "\n    " + BODY + "\n\n"
    assert bh.block_hash(content) == git_hash(BODY)


def test_merge_script_reuses_the_same_hash():
    assert rms._block_hash(BODY) == bh.block_hash(BODY)


def test_check_reports_ok_and_modified():
    good = hook(h=bh.block_hash(BODY))
    assert bh.check(good) == [("branches.protected/main", bh.block_hash(BODY), bh.block_hash(BODY), "OK")]
    edited = good.replace("exit 1", "exit 0")
    [(bid, recorded, actual, status)] = bh.check(edited)
    assert status == "MODIFIED" and recorded != actual


def test_stamp_fills_only_placeholders():
    text = hook() + hook(body="echo user-edited", h="deadbeef", block_id="commit-msg/format")
    stamped = bh.stamp(text)
    assert f"(hash:{bh.block_hash(BODY)})" in stamped
    assert "(hash:deadbeef)" in stamped  # 已有 hash 的块不动，手改不会被洗白
    assert "PLACEHOLDER" not in stamped


def test_cli_check_exit_1_on_modified(tmp_path):
    f = tmp_path / "pre-commit"
    f.write_text(hook(h="00000000"))
    r = subprocess.run([sys.executable, SCRIPT, "check", str(f)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "MODIFIED branches.protected/main" in r.stdout


def test_cli_stamp_rewrites_file(tmp_path):
    f = tmp_path / "pre-commit"
    f.write_text(hook())
    r = subprocess.run([sys.executable, SCRIPT, "stamp", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, SCRIPT, "check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0
    assert r.stdout.strip() == f"OK branches.protected/main {bh.block_hash(BODY)}"
