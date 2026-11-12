import os
import subprocess
import sys

REFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")
sys.path.insert(0, REFS)

import render_docs as rd  # noqa: E402
import workflow_resolve as wr  # noqa: E402

TEMPLATE_PATH = os.path.join(REFS, "git-workflow-template.md")
BEGIN = "<!-- BEGIN PROJECT NOTES -->"
END = "<!-- END PROJECT NOTES -->"

PRE_CHECK_1 = "node scripts/check-file-token-budget.js --changed-since {target}"
PRE_CHECK_2 = "python3 -m pytest -q"

STAGING_CFG = f"""\
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
        - "fix/*"
        - "chore/*"
        - "doc/*"

branch_naming:
  enforce: true
  allowed_patterns:
    - "^feature/.+"
    - "^fix/.+"
    - "^chore/.+"
    - "^doc/.+"
    - "^release/[0-9]+\\\\.[0-9]+\\\\.[0-9]+(-.+)?$"
  exempt:
    - main
    - staging

commit_message:
  enforce: true
  format: conventional
  conventional:
    types:
      - feat
      - fix
    max_subject_length: 80

merge:
  pre_checks:
    - "{PRE_CHECK_1}"
    - "{PRE_CHECK_2}"
"""

NO_FEATURE_CFG = """\
branches:
  protected:
    - name: main
      allow_direct_commit: false
      merge_from:
        - "fix/*"

branch_naming:
  enforce: true
  allowed_patterns:
    - "^fix/.+"
  exempt:
    - main
"""


def render_cfg(tmp_path, cfg_text):
    p = tmp_path / "workflow-config.yml"
    p.write_text(cfg_text)
    config = wr.load_config(str(p))
    resolved = wr.resolve(config, "workflow-config.yml")
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()
    return rd.render(config, resolved, template)


def section(doc, title):
    """取 '### title' 到下一个标题之间的文本。"""
    start = doc.index(f"### {title}")
    nxt = [i for i in (doc.find("\n### ", start + 1), doc.find("\n## ", start + 1)) if i != -1]
    return doc[start:min(nxt)] if nxt else doc[start:]


def test_no_legacy_checkout_commands(tmp_path):
    doc = render_cfg(tmp_path, STAGING_CFG)
    assert "checkout -b" not in doc
    assert "git checkout staging" not in doc
    assert "git checkout main" not in doc


def test_start_work_points_to_manage_worktree_with_fallback(tmp_path):
    doc = render_cfg(tmp_path, STAGING_CFG)
    start = section(doc, "开始新工作")
    assert "manage-worktree「准备」" in start
    assert "git worktree add .worktrees/<分支名，/ 换成 +> -b <分支> staging" in start


def test_merge_section_points_to_script_and_lists_pre_checks(tmp_path):
    doc = render_cfg(tmp_path, STAGING_CFG)
    merge = section(doc, "合并到集成分支")
    assert "scripts/merge-to-staging.sh" in merge
    assert "manage-worktree「合并」" in merge
    assert PRE_CHECK_1 in merge
    assert PRE_CHECK_2 in merge


def test_no_merge_target_keeps_generic_merge(tmp_path):
    doc = render_cfg(tmp_path, NO_FEATURE_CFG)
    assert "git merge" in section(doc, "合并到集成分支")
    assert "merge-to-" not in doc


def test_release_section_does_not_switch_main_worktree(tmp_path):
    doc = render_cfg(tmp_path, STAGING_CFG)
    release = section(doc, "发布到主分支")
    assert "release-project" in release
    assert "git checkout" not in release


def test_notes_block_preserved_byte_for_byte(tmp_path):
    rendered = render_cfg(tmp_path, STAGING_CFG)
    notes = (
        "\n本项目补充：合并前先跑 `make lint`。\n\n"
        "```bash\nmake lint\n# 中文注释\n```\n\n- 条目一\n\n\n"
    )
    existing = rendered.replace(f"{BEGIN}\n{END}", f"{BEGIN}{notes}{END}")
    assert existing != rendered
    text, warn = rd.carry_notes(existing, rendered)
    assert warn is False
    got = text[text.index(BEGIN) + len(BEGIN):text.index(END)]
    assert got == notes


def test_existing_without_markers_warns_and_overwrites(tmp_path):
    rendered = render_cfg(tmp_path, STAGING_CFG)
    text, warn = rd.carry_notes("# 手写的旧文档\n\n手改内容\n", rendered)
    assert warn is True
    assert text == rendered
    assert BEGIN in text and END in text
    assert text[text.index(BEGIN) + len(BEGIN):text.index(END)].strip() == ""


def test_header_says_outside_notes_do_not_edit(tmp_path):
    doc = render_cfg(tmp_path, STAGING_CFG)
    assert "自填区以外请勿手动编辑" in doc


def test_cli_prints_warn_before_status_and_is_idempotent(tmp_path):
    cfg = tmp_path / "workflow-config.yml"
    cfg.write_text(STAGING_CFG)
    out = tmp_path / "docs" / "reference" / "git-workflow.md"
    script = os.path.join(REFS, "render_docs.py")

    def run():
        return subprocess.run(
            [sys.executable, script, str(cfg), TEMPLATE_PATH, str(out)],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()

    assert run() == ["NEW"]
    assert run() == ["UNCHANGED"]
    out.write_text("# 手写旧文档\n", encoding="utf-8")
    assert run() == [
        f"WARN {out} 没有项目自填区标记，现有内容已被覆盖；找回手改内容：git diff HEAD -- {out}",
        "UPDATED",
    ]
    assert run() == ["UNCHANGED"]
