from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
MANAGE_MD = SKILL_DIR / "references" / "manage.md"


def test_skill_md_line_budget():
    assert len(SKILL_MD.read_text(encoding="utf-8").splitlines()) <= 47


def test_version_bumped():
    assert 'version: "1.3.1"' in SKILL_MD.read_text(encoding="utf-8")


def test_query_invokes_capture_feature():
    text = SKILL_MD.read_text(encoding="utf-8")
    assert ".hskill/capture-feature/" in text
    assert "capture-feature" in text


def test_add_routes_to_capture_feature():
    text = MANAGE_MD.read_text(encoding="utf-8")
    assert "capture-feature" in text
    assert "add" in text


def test_add_routing_does_not_require_existing_feature_map():
    text = MANAGE_MD.read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("2b."))
    assert "已安装" in line
    assert "项目有功能地图时" not in line


def test_add_three_way_choice_covers_feature_candidates():
    text = MANAGE_MD.read_text(encoding="utf-8")
    assert "capture-feature" in text.split("5. 对已得到的候选")[1].split("6. 展示条目")[0]


def test_add_routing_uses_d20_criterion():
    line = next(l for l in MANAGE_MD.read_text(encoding="utf-8").splitlines() if l.startswith("2b."))
    assert "直接看到或操作" not in line
    assert "功能" in line and "界面" in line and "定位" in line
