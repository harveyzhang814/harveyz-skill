---
name: md-to-docx
description: "Convert Markdown (.md) files to Word (.docx) documents using the bundled md_to_docx.py script. Trigger whenever the user wants to: convert/export a .md file to Word or docx, says 'md转docx', 'markdown转word', '生成Word文档', 'export as docx', '导出Word', or has a markdown file they need to share as a Word document. Also trigger when the user writes a document in the conversation and wants it as a .docx."
user_invocable: true
version: "1.0.0"
---

## Overview

Convert a Markdown file to a formatted Word document (.docx). The script handles headings, paragraphs, tables, code blocks, lists, inline formatting, and blockquotes — with sensible Chinese-document defaults out of the box.

**Script location (after `hskill` install):** `~/.claude/skills/md-to-docx/scripts/md_to_docx.py`

---

## Steps

1. **Identify the input file** — get the `.md` path from context or ask the user.
2. **Determine the output path** — default is the same name with `.docx` extension in the same directory. Confirm with the user if they want a different location.
3. **Check dependencies** — if `python-docx` isn't installed, install it first (see below).
4. **Run the conversion.**
5. **Report** the output path.

---

## Commands

**Basic conversion:**
```bash
python3 ~/.claude/skills/md-to-docx/scripts/md_to_docx.py input.md
# → saves input.docx next to input.md
```

**Specify output path:**
```bash
python3 ~/.claude/skills/md-to-docx/scripts/md_to_docx.py input.md output.docx
```

**Custom style:**
```bash
python3 ~/.claude/skills/md-to-docx/scripts/md_to_docx.py input.md --style style.json
```

**Dump default style (to customize):**
```bash
python3 ~/.claude/skills/md-to-docx/scripts/md_to_docx.py --dump-style > style.json
```

---

## Dependencies

```bash
pip install python-docx
```

If the conversion fails with `ModuleNotFoundError: No module named 'docx'`, run the above and retry.

---

## What gets converted

| Markdown | Word output |
|----------|-------------|
| `# H1` … `#### H4` | Styled headings (黑体/Arial, sized by level) |
| Paragraphs | 宋体/Times New Roman, 12pt, 2-char first-line indent |
| `**bold**`, `*italic*`, `` `code` ``, `~~strike~~`, `[link](url)` | Inline runs with correct formatting |
| ` ``` ` fenced code | Courier New monospace block |
| `>` blockquote | 仿宋, indented |
| `- / * / +` unordered list | Bullet `•` with nesting |
| `1.` ordered list | Numbered with nesting |
| Pipe tables | Styled table with header shading |
| `---` horizontal rule | Thin gray line |

Headings deeper than H4 are styled as H4. HTML comments are stripped.

---

## Style Customization

The default style follows Chinese government-document standards. To tweak it:

1. Dump the defaults: `python3 ~/.claude/skills/md-to-docx/scripts/md_to_docx.py --dump-style > style.json`
2. Edit the JSON (any section: `page`, `body`, `headings`, `code_block`, `blockquote`, `table`)
3. Pass it: `python3 ~/.claude/skills/md-to-docx/scripts/md_to_docx.py input.md --style style.json`

You only need to include the sections you want to override — the rest uses the defaults.

---

## If the skill directory isn't installed

If `~/.claude/skills/md-to-docx/` doesn't exist (e.g., running in the repo itself during development), find the script relative to the repo root:

```bash
python3 tools/md-formatter/md_to_docx.py input.md
```
