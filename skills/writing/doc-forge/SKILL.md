---
name: doc-forge
description: "Convert documents between formats. Trigger whenever the user wants to: convert/export a .md file to Word or docx, says 'md转docx', 'markdown转word', '生成Word文档', 'export as docx', '导出Word'; OR convert to PDF, says 'md转pdf', 'markdown转pdf', '导出PDF', 'export as pdf', '生成PDF'; OR has a markdown file they need to share or browse as Word/PDF. Also trigger when the user writes a document in the conversation and wants it as .docx or .pdf."
user_invocable: true
version: "2.0.0"
---

## Overview

Convert a Markdown file to Word (.docx) or PDF. Both formats support headings, tables, code blocks, lists, inline formatting, blockquotes, and embedded images. PDF additionally supports Mermaid diagrams (rendered as vector SVG).

**Script locations (after `hskill` install):**
- DOCX: `~/.claude/skills/doc-forge/scripts/md_to_docx.py`
- PDF:  `~/.claude/skills/doc-forge/scripts/md_to_pdf.py`

---

## DOCX Conversion

**Basic:**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_docx.py input.md
# → input.docx in the same directory
```

**Specify output:**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_docx.py input.md output.docx
```

**Custom style:**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_docx.py input.md --style custom.json
```

**Dump default style to customize:**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_docx.py --dump-style > style.json
```

**Dependencies:** `pip install python-docx`

---

## PDF Conversion

**Basic:**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_pdf.py input.md
# → input.pdf in the same directory
```

**Specify output:**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_pdf.py input.md output.pdf
```

**Custom style:**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_pdf.py input.md --style custom.css
```

**Dump default CSS to customize:**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_pdf.py --dump-style > style.css
```

**Dependencies:** `pip install markdown` (playwright already required)

**Mermaid (optional, for offline use):** `npm install mermaid` inside the skill directory. Without this, mermaid.js is loaded from CDN.

---

## What Gets Converted

| Markdown | DOCX | PDF |
|----------|------|-----|
| `# H1` … `#### H4` | Styled headings | Styled headings |
| Paragraphs | 2-char indent, 宋体 | 2em indent |
| **bold**, *italic*, `code`, ~~strike~~, [links](url) | Inline runs | Inline HTML |
| ` ``` ` code blocks | Courier New, indented | Monospace, shaded |
| `>` blockquotes | 仿宋, indented | Indented, grey |
| Lists (ordered & unordered) | Bullets/numbers | Standard HTML lists |
| Pipe tables | Styled with header shading | Styled with header shading |
| `---` horizontal rule | Grey line | Grey line |
| `![alt](path)` images | ❌ Not supported | ✅ Loaded via base_url |
| ` ```mermaid` diagrams | ❌ Not supported | ✅ Rendered as SVG |

---

## Style Customization

**DOCX** — style.json keys: `page`, `body`, `headings` (h1–h4), `code_block`, `blockquote`, `table`. Only include sections to override; rest uses defaults.

**PDF** — style.css: standard CSS file. Use `--dump-style` to get the full default as a starting point. Supports all CSS properties recognized by Chromium (including `@page` for margins/size).

---

## If the skill directory isn't installed

```bash
# DOCX
python3 tools/md-formatter/md_to_docx.py input.md
# PDF
python3 skills/writing/doc-forge/scripts/md_to_pdf.py input.md
```
