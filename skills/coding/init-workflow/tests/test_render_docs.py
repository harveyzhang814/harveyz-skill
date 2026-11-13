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


def h2_section(doc, title):
    """取 '## title' 到下一个 '## ' 标题之间的文本。"""
    start = doc.index(f"## {title}")
    nxt = doc.find("\n## ", start + 1)
    return doc[start:nxt] if nxt != -1 else doc[start:]


def rule_line(doc, branch):
    rules = h2_section(doc, "分支保护规则")
    return next(l for l in rules.splitlines() if l.startswith(f"- **`{branch}`**"))


# ── I-3：合并目标分支的保护规则写真实机制，不再列来源分支 ───────────────────

def test_merge_target_rule_states_script_and_trailer_hooks(tmp_path):
    doc = render_cfg(tmp_path, STAGING_CFG)
    line = rule_line(doc, "staging")
    assert "禁止直接提交" in line
    assert "scripts/merge-to-staging.sh" in line
    assert "Merge-Via: merge-to-staging.sh" in line
    assert ".githooks/commit-msg" in line and ".githooks/pre-push" in line
    assert "只接受来自" not in line
    assert "`feature/*`" not in line


def test_other_protected_branch_keeps_source_list(tmp_path):
    doc = render_cfg(tmp_path, STAGING_CFG)
    assert rule_line(doc, "main") == "- **`main`** — 禁止直接提交。只接受来自 `staging`、`release/*` 的合并。"


def test_rules_intro_does_not_attribute_everything_to_pre_commit(tmp_path):
    rules = h2_section(render_cfg(tmp_path, STAGING_CFG), "分支保护规则")
    assert "以下规则由 `.githooks/pre-commit` 自动强制执行" not in rules


def test_no_merge_target_keeps_source_list_wording(tmp_path):
    doc = render_cfg(tmp_path, NO_FEATURE_CFG)
    assert rule_line(doc, "main") == "- **`main`** — 禁止直接提交。只接受来自 `fix/*` 的合并。"
    assert "Merge-Via" not in doc


# ── M-1：分支类型行的合并目标取 base.<类型> ─────────────────────────────────

def test_branch_table_targets_follow_resolved_base(tmp_path):
    doc = render_cfg(tmp_path, STAGING_CFG)
    table = h2_section(doc, "分支模型")
    assert "| `release/<名称>` | 发版切点 | `main` |" in table
    assert "| `feature/<名称>` | 新功能 | `staging` |" in table


# ── I-2 / M-3：FAQ 指向合并脚本，并说明远端同步用快进 ───────────────────────

def test_hotfix_faq_brings_fix_back_via_merge_script(tmp_path):
    faq = h2_section(render_cfg(tmp_path, STAGING_CFG), "常见问题")
    hotfix = faq[faq.index("紧急热修复"):]
    hotfix = hotfix[:hotfix.index("\n\n")]
    assert "scripts/merge-to-staging.sh" in hotfix
    assert "反向合并到 staging" not in hotfix


def test_faq_explains_remote_sync_by_fast_forward(tmp_path):
    faq = h2_section(render_cfg(tmp_path, STAGING_CFG), "常见问题")
    assert "git pull --ff-only" in faq
    assert "Merge remote-tracking branch" in faq
    assert "Merge-Via: merge-to-staging.sh" in faq


def test_topology_lists_each_branch_once_as_a_tree(tmp_path):
    model = h2_section(render_cfg(tmp_path, STAGING_CFG), "分支模型")
    block = model[model.index("```\n") + 4:]
    block = block[:block.index("```")].rstrip("\n")
    assert block == "\n".join([
        "main",
        "  <- staging",
        "       <- feature/*",
        "       <- fix/*",
        "       <- chore/*",
        "       <- doc/*",
        "  <- release/*",
    ])


def test_faq_explains_worktree_cleanup_after_merge(tmp_path):
    faq = h2_section(render_cfg(tmp_path, STAGING_CFG), "常见问题")
    item = faq[faq.index("合并后"):]
    item = item[:item.index("\n\n")]
    assert "git worktree remove" in item
    assert "git branch -d" in item


def test_faq_explains_rejected_manual_merge_and_fast_forward(tmp_path):
    faq = h2_section(render_cfg(tmp_path, STAGING_CFG), "常见问题")
    item = faq[faq.index("手动合并被拒"):]
    item = item[:item.index("\n\n")]
    assert "git merge --abort" in item
    assert "pre-push" in item
    assert "scripts/merge-to-staging.sh" in item


def test_no_merge_target_faq_has_no_merge_via_items(tmp_path):
    faq = h2_section(render_cfg(tmp_path, NO_FEATURE_CFG), "常见问题")
    assert "merge-to-" not in faq
    assert "--ff-only" not in faq


def test_main_only_hotfix_faq_uses_merge_script(tmp_path):
    cfg = NO_FEATURE_CFG.replace('"fix/*"', '"feature/*"\n        - "release/*"').replace(
        '    - "^fix/.+"\n', '    - "^feature/.+"\n    - "^release/.+"\n')
    faq = h2_section(render_cfg(tmp_path, cfg), "常见问题")
    assert "scripts/merge-to-main.sh" in faq
    assert "反向合并" not in faq
