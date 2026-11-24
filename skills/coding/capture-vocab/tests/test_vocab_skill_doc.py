from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
MANAGE_MD = SKILL_DIR / "references" / "manage.md"


def test_skill_md_line_budget():
    assert len(SKILL_MD.read_text(encoding="utf-8").splitlines()) <= 47


def test_version_bumped():
    assert 'version: "1.3.0"' in SKILL_MD.read_text(encoding="utf-8")


def test_query_invokes_capture_feature():
    text = SKILL_MD.read_text(encoding="utf-8")
    assert ".hskill/capture-feature/" in text
    assert "capture-feature" in text


def test_add_routes_to_capture_feature():
    text = MANAGE_MD.read_text(encoding="utf-8")
    assert "capture-feature" in text
    assert "add" in text
