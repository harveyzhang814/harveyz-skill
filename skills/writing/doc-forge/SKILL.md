---
name: doc-forge
description: "Convert documents between formats. Trigger when the user wants to convert or export a Markdown file to Word (.docx) or PDF — e.g. 'export as docx', 'convert to Word', 'export as pdf', 'generate PDF' — or when the user writes a document in the conversation and wants it as .docx or .pdf."
user_invocable: true
version: "2.1.0"
---

## 概述

将 Markdown 文件转换为 Word（.docx）或 PDF。两种格式均支持标题、表格、代码块、列表、行内格式、引用块、嵌入图片和 Mermaid 图表（DOCX 渲染为 PNG，PDF 渲染为矢量 SVG）。

**脚本位置（`hskill` 安装后）：**
- DOCX：`~/.claude/skills/doc-forge/scripts/md_to_docx.py`
- PDF：`~/.claude/skills/doc-forge/scripts/md_to_pdf.py`

---

## DOCX 转换

**基础用法：**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_docx.py input.md
# → 在同目录生成 input.docx
```

**指定输出路径：**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_docx.py input.md output.docx
```

**自定义样式：**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_docx.py input.md --style custom.json
```

**导出默认样式以便修改：**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_docx.py --dump-style > style.json
```

**依赖：** `pip install python-docx`（Mermaid 图表需额外安装 playwright，同 PDF 转换）

---

## PDF 转换

**基础用法：**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_pdf.py input.md
# → 在同目录生成 input.pdf
```

**指定输出路径：**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_pdf.py input.md output.pdf
```

**自定义样式：**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_pdf.py input.md --style custom.css
```

**导出默认 CSS 以便修改：**
```bash
python3 ~/.claude/skills/doc-forge/scripts/md_to_pdf.py --dump-style > style.css
```

**依赖：** `pip install markdown`（playwright 已为必需项）

**Mermaid（可选，离线使用）：** 在 skill 目录内执行 `npm install mermaid`。不安装时从 CDN 加载。

---

## 支持的元素

| Markdown | DOCX | PDF |
|----------|------|-----|
| `# H1` … `#### H4` | 带样式标题 | 带样式标题 |
| 段落 | 首行缩进 2 字符，宋体 | 2em 缩进 |
| **粗体**、*斜体*、`行内代码`、~~删除线~~、[链接](url) | 行内 runs | 行内 HTML |
| 代码块（` ``` `） | Courier New，带缩进 | 等宽字体，灰底 |
| `>` 引用块 | 仿宋，带缩进 | 缩进，灰色 |
| 有序/无序列表 | 项目符号/编号 | 标准 HTML 列表 |
| 管道表格 | 带表头底色 | 带表头底色 |
| `---` 分隔线 | 灰色横线 | 灰色横线 |
| `![alt](path)` 图片 | ✅ 相对/绝对路径均支持 | ✅ 通过 base_url 加载 |
| ` ```mermaid` 图表 | ✅ 渲染为 PNG（需 playwright） | ✅ 渲染为 SVG |

---

## 样式定制

**DOCX** — style.json 键：`page`、`body`、`headings`（h1–h4）、`code_block`、`blockquote`、`table`。只需包含要覆盖的部分，其余使用默认值。

**PDF** — style.css：标准 CSS 文件。用 `--dump-style` 导出完整默认样式作为起点。支持 Chromium 识别的所有 CSS 属性（包括用于页边距/尺寸的 `@page`）。

---

## 未安装 skill 目录时

```bash
# DOCX
python3 skills/writing/doc-forge/scripts/md_to_docx.py input.md
# PDF
python3 skills/writing/doc-forge/scripts/md_to_pdf.py input.md
```
