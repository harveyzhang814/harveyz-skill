import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "design_html.py"


def run_check(root):
    return subprocess.run([sys.executable, str(SCRIPT), "check", str(root / ".hskill/sync-design/manifest.json")],
                          capture_output=True, text=True)


class TestCheckLocalRefs(unittest.TestCase):
    """设计稿用相对路径引用项目内文件（令牌、组件样式、脚本）时，check 报告指不到文件的引用。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "design-system/shared").mkdir(parents=True)
        (self.root / "design-system/tokens.css").write_text(":root{}", encoding="utf-8")
        (self.root / "design-system/shared/icons.js").write_text("", encoding="utf-8")
        drafts = self.root / ".hskill/sync-design/html/drafts"
        drafts.mkdir(parents=True)
        self.draft = drafts / "home-renderer-design.html"
        manifest = {"version": 6, "entries": [], "drafts": [
            {"id": "home-renderer", "htmlFile": ".hskill/sync-design/html/drafts/home-renderer-design.html",
             "uiStates": ["idle"]}]}
        (self.root / ".hskill/sync-design/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, head):
        self.draft.write_text(f"<html><head>{head}</head><body><!-- ── idle ── --><p>x</p></body></html>",
                              encoding="utf-8")

    def test_resolvable_refs_pass(self):
        self.write('<link rel="stylesheet" href="../../../../design-system/tokens.css">'
                   '<script src="../../../../design-system/shared/icons.js"></script>')
        r = run_check(self.root)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("全部合规", r.stdout)

    def test_broken_link_reported(self):
        self.write('<link rel="stylesheet" href="../../../design-system/tokens.css">')
        r = run_check(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("引用的文件不存在", r.stdout)
        self.assertIn("../../../design-system/tokens.css", r.stdout)

    def test_broken_script_reported(self):
        self.write('<script src="../../../../design-system/shared/missing.js"></script>')
        r = run_check(self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing.js", r.stdout)

    def test_urls_and_fragments_ignored(self):
        self.write('<link rel="stylesheet" href="https://example.com/a.css">'
                   '<script src="data:text/javascript,"></script><link rel="icon" href="#x">')
        r = run_check(self.root)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_query_suffix_stripped(self):
        self.write('<link rel="stylesheet" href="../../../../design-system/tokens.css?v=2">')
        r = run_check(self.root)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
