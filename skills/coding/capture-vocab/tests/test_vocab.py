import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "vocab.py"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def run_vocab(args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def test_no_vocab_file_exits_2(tmp_path):
    result = run_vocab(["lookup", "anything"], cwd=tmp_path)
    assert result.returncode == 2
    assert result.stdout.strip() == "no vocab file"


def test_no_args_does_not_crash(tmp_path):
    result = run_vocab([], cwd=tmp_path)
    assert result.returncode != 0
    assert "Traceback" not in result.stderr


def test_lookup_hit_exit_0(tmp_path):
    result = run_vocab(["lookup", "画布"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert "画布区" in result.stdout


def test_lookup_miss_exit_1(tmp_path):
    result = run_vocab(["lookup", "zzz_no_such_term"], cwd=FIXTURE_DIR)
    assert result.returncode == 1
    assert result.stdout.strip() == "no match: zzz_no_such_term"


def test_lookup_input_too_short_is_a_miss(tmp_path):
    result = run_vocab(["lookup", "a"], cwd=FIXTURE_DIR)
    assert result.returncode == 1
    assert result.stdout.strip() == "no match: a"


def test_lookup_degrades_above_three_hits(tmp_path):
    result = run_vocab(["lookup", "把工作区的节点关系改一下"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    m = re.match(r"^(\d+) matches: (.+)$", result.stdout.strip())
    assert m, f"unexpected stdout: {result.stdout!r}"
    assert int(m.group(1)) > 3
    assert "\n" not in result.stdout.strip()


def test_lookup_case_insensitive(tmp_path):
    lower = run_vocab(["lookup", "tab"], cwd=FIXTURE_DIR)
    upper = run_vocab(["lookup", "Tab"], cwd=FIXTURE_DIR)
    assert lower.returncode == upper.returncode == 0
    assert lower.stdout == upper.stdout


def test_lookup_fullwidth_paren_alias(tmp_path):
    result = run_vocab(["lookup", "瓦片"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert "Widget (瓦片)" in result.stdout


def test_lookup_backtick_term_name(tmp_path):
    result = run_vocab(["lookup", "画布操控"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert "`画布操控` profile" in result.stdout


def test_lookup_avoid_alias_hits_canonical_term(tmp_path):
    result = run_vocab(["lookup", "抽屉"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert "## 工作区" in result.stdout


def test_avoid_aliases_split_on_ideographic_comma(tmp_path):
    # 「编辑器」的 _Avoid_ 用顿号分隔两个别名，中间那个还带括号说明：
    #   编辑器模式（…canvasVisible 取反）、PanelArea 全屏模式
    # 顿号若不在切分符集合里，整行会被当成一个超长片段、被 20 字阈值丢弃，
    # 两个别名一起失效。
    for alias in ("编辑器模式", "PanelArea 全屏模式"):
        result = run_vocab(["lookup", alias], cwd=FIXTURE_DIR)
        assert result.returncode == 0, f"{alias!r} 应命中「编辑器」"
        assert "## 编辑器" in result.stdout, f"{alias!r} -> {result.stdout[:80]!r}"


def test_lookup_long_avoid_prose_does_not_match(tmp_path):
    result = run_vocab(
        ["lookup", "这是一段刻意写得很长用来验证别名清洗阈值确实生效而不会被当成短别名参与子串匹配的散文说明文字"],
        cwd=FIXTURE_DIR,
    )
    assert result.returncode == 1


def test_lookup_section_boundary_exact(tmp_path):
    result = run_vocab(["lookup", "席位"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    assert result.stdout.startswith("## 席位")
    assert "## Pilot（主体）" not in result.stdout
    assert not result.stdout.endswith("\n\n")


def test_list_line_count_matches_section_count(tmp_path):
    vocab_path = FIXTURE_DIR / ".hskill" / "capture-vocab" / "vocab.md"
    text = vocab_path.read_text(encoding="utf-8")
    section_count = len(re.findall(r"^## ", text, flags=re.MULTILINE))
    result = run_vocab(["list"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) == section_count


def test_list_lines_are_structurally_bounded(tmp_path):
    result = run_vocab(["list"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    for line in lines:
        assert len(line) <= 80, f"line exceeds structural bound: {line!r}"


def test_list_prose_only_avoid_yields_bare_name(tmp_path):
    result = run_vocab(["list"], cwd=FIXTURE_DIR)
    assert result.returncode == 0
    seat_lines = [l for l in result.stdout.splitlines() if l.startswith("席位")]
    assert seat_lines, result.stdout
    assert seat_lines[0] == "席位"


def test_refs_same_file(tmp_path):
    result = run_vocab(
        ["refs", "src/renderer/src/components/PanelArea.tsx"], cwd=FIXTURE_DIR
    )
    assert result.returncode == 0
    lines = result.stdout.splitlines()
    workspace_lines = [l for l in lines if l.startswith("工作区 |")]
    assert workspace_lines, result.stdout
    assert "same-file" in workspace_lines[0]


def test_refs_dir_contains(tmp_path):
    result = run_vocab(
        ["refs", "src/main/pilot/pilotConfig.ts"], cwd=FIXTURE_DIR
    )
    assert result.returncode == 0
    pilot_lines = [l for l in result.stdout.splitlines() if l.startswith("Pilot（主体） |")]
    assert pilot_lines, result.stdout
    assert "dir-contains" in pilot_lines[0]


def test_refs_no_hits_exit_1(tmp_path):
    result = run_vocab(["refs", "src/totally/unrelated/path.ts"], cwd=FIXTURE_DIR)
    assert result.returncode == 1
