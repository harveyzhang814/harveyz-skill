import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
CJK_RE = re.compile(r"[一-鿿]")


def frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    block = text.split("---", 2)[1]
    return dict(line.split(":", 1) for line in block.strip().splitlines() if ":" in line)


def test_skill_md_within_budget():
    assert len(SKILL_MD.read_bytes()) <= 2641


def test_frontmatter():
    fm = {k.strip(): v.strip().strip('"') for k, v in frontmatter().items()}
    assert fm["name"] == "capture-feature"
    assert fm["version"] == "0.3.0"
    assert fm["user_invocable"] == "true"
    assert fm["description"] and not CJK_RE.search(fm["description"])


def test_referenced_files_exist():
    refs = re.findall(r"references/[\w.-]+\.md", SKILL_MD.read_text(encoding="utf-8"))
    assert refs
    for ref in refs:
        assert (SKILL_DIR / ref).is_file(), ref


def test_skill_md_has_query_only():
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "feature.py lookup" in text
    assert "put --new" not in text


def test_docs_use_v02_types_and_criterion():
    # Spec v0.2 §11-14 / D20
    texts = [SKILL_MD.read_text(encoding="utf-8")] + [
        p.read_text(encoding="utf-8") for p in (SKILL_DIR / "references").glob("*.md")
    ]
    joined = "\n".join(texts)
    for legacy in ("surface", "`entry`", "UI surfaces", "直接看到或操作"):
        assert legacy not in joined, legacy
    assert "`interface`" in joined and "`feature`" in joined
