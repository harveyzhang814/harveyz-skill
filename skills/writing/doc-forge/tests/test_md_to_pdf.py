import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from md_to_pdf import _extract_mermaid, build_html

ASSETS_DIR = Path(__file__).parent.parent / "assets"
CSS_PATH = next(ASSETS_DIR.glob("*.css"))


class TestExtractMermaid(unittest.TestCase):
    def test_no_mermaid(self):
        text = "# Hello\n\nsome text"
        result, blocks = _extract_mermaid(text)
        self.assertEqual(result, text)
        self.assertEqual(blocks, {})

    def test_single_block(self):
        text = "before\n```mermaid\ngraph LR\n  A --> B\n```\nafter"
        result, blocks = _extract_mermaid(text)
        self.assertIn("XMERMAIDX0X", result)
        self.assertEqual(len(blocks), 1)
        self.assertIn('class="mermaid"', list(blocks.values())[0])
        self.assertIn("A --> B", list(blocks.values())[0])

    def test_multiple_blocks(self):
        text = "```mermaid\nA\n```\n\n```mermaid\nB\n```"
        _, blocks = _extract_mermaid(text)
        self.assertEqual(len(blocks), 2)


class TestBuildHtml(unittest.TestCase):
    def test_produces_valid_html(self):
        html, count = build_html("# Hello\n\nParagraph.", CSS_PATH)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("<h1>Hello</h1>", html)
        self.assertEqual(count, 0)

    def test_table_rendered(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html, _ = build_html(md, CSS_PATH)
        self.assertIn("<table>", html)
        self.assertIn("<th>", html)

    def test_mermaid_count(self):
        md = "```mermaid\ngraph LR\n  A-->B\n```"
        html, count = build_html(md, CSS_PATH)
        self.assertEqual(count, 1)
        self.assertIn('class="mermaid"', html)

    def test_mermaid_not_in_code_block(self):
        md = "```mermaid\ngraph LR\n  A-->B\n```"
        html, _ = build_html(md, CSS_PATH)
        self.assertNotIn("<code>graph LR", html)

    def test_css_injected(self):
        html, _ = build_html("text", CSS_PATH)
        self.assertIn("@page", html)
        self.assertIn("font-family", html)

    def test_custom_css(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as f:
            f.write("body { color: red; }")
            tmp = f.name
        try:
            html, _ = build_html("text", Path(tmp))
            self.assertIn("color: red", html)
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
