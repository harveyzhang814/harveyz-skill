---
name: forge-doc
description: "Convert documents between formats. Trigger when the user wants to convert or export a Markdown file to Word (.docx) or PDF — e.g. 'export as docx', 'convert to Word', 'export as pdf', 'generate PDF' — or when the user writes a document in the conversation and wants it as .docx or .pdf."
user_invocable: true
version: "2.5.0"
---

## 执行前必做：样式预览 → 选择样式

### Step 0 — 询问是否查看样式预览

**在运行任何转换命令之前**，若用户未显式指定样式，先用 `AskUserQuestion` 询问：

```
问题：是否先查看所有样式的预览效果？
选项：
  1. 查看样式预览（推荐）— 自动生成并打开预览 HTML
  2. 跳过预览，直接选择样式
```

**如果用户选择"查看样式预览"，或未明确选择跳过**，执行：

```bash
python3 ~/.claude/skills/forge-doc/scripts/generate_style_preview.py
open ~/.claude/skills/forge-doc/preview/style-preview.html
```

浏览器打开后告知用户："预览已打开，对比各样式后请回来选择。"

---

### Step 1 — 询问样式

再用 `AskUserQuestion` 询问：

```
问题：请选择输出样式
选项：
  1. Bain & Company（红色品牌）— Bain 正式输出
  2. BCG（深绿品牌，麦肯锡横线表格）— BCG 正式输出
  3. 中文学术论文（宋体/黑体，25磅行距）— 硕博论文、学术报告
  4. 自定义（用户提供路径或描述）
```

用户选定后再执行转换。**不得跳过此步骤，不得默认使用某一样式。**

---

## 相对路径图片注意事项

文档中含有相对路径图片（`![alt](./images/fig.png)` 或 `![[fig.png]]`）时，脚本以 MD 文件所在目录为根解析路径。

**若 MD 文件不在图片的原始目录**（例如 Claude 将内容写入临时文件），必须通过 `--base-dir` 显式指定图片根目录：

```bash
# DOCX
python3 ~/.claude/skills/forge-doc/scripts/md_to_docx.py /tmp/draft.md \
  --base-dir /Users/harvey/Documents/my-paper

# PDF
python3 ~/.claude/skills/forge-doc/scripts/md_to_pdf.py /tmp/draft.md \
  --base-dir /Users/harvey/Documents/my-paper
```

**最佳实践：转换用户已有的 MD 文件时，始终传入该文件的绝对路径，无需 `--base-dir`。**

---

## 概述

将 Markdown 文件转换为 Word（.docx）或 PDF。两种格式均支持标题、表格、代码块、列表、行内格式、引用块、嵌入图片和 Mermaid 图表（DOCX 渲染为 PNG，PDF 渲染为矢量 SVG）。

**脚本位置（`hskill` 安装后）：**
- DOCX：`~/.claude/skills/forge-doc/scripts/md_to_docx.py`
- PDF：`~/.claude/skills/forge-doc/scripts/md_to_pdf.py`

**内置样式（`assets/` 目录）：**

| 文件 | 说明 | 适用场景 |
|------|------|---------|
| `bain-style.json` / `bain.css` | Bain & Company 官方品牌（红色） | Bain 正式输出 |
| `bcg-style.json` / `bcg.css` | BCG 官方品牌（深绿，麦肯锡横线表格） | BCG 正式输出 |
| `thesis-style.json` / `thesis.css` | 中文学术论文（宋体/黑体/Times New Roman，25磅行距） | 硕博学位论文、学术报告 |

---

## DOCX 转换

**基础用法：**
```bash
python3 ~/.claude/skills/forge-doc/scripts/md_to_docx.py input.md
# → 在同目录生成 input.docx
```

**指定输出路径：**
```bash
python3 ~/.claude/skills/forge-doc/scripts/md_to_docx.py input.md output.docx
```

**自定义样式：**
```bash
python3 ~/.claude/skills/forge-doc/scripts/md_to_docx.py input.md --style custom.json
```

**导出默认样式以便修改：**
```bash
python3 ~/.claude/skills/forge-doc/scripts/md_to_docx.py --dump-style > style.json
```

**依赖：** `pip install python-docx`（Mermaid 图表需额外安装 playwright，同 PDF 转换）

---

## PDF 转换

**基础用法：**
```bash
python3 ~/.claude/skills/forge-doc/scripts/md_to_pdf.py input.md
# → 在同目录生成 input.pdf
```

**指定输出路径：**
```bash
python3 ~/.claude/skills/forge-doc/scripts/md_to_pdf.py input.md output.pdf
```

**自定义样式：**
```bash
python3 ~/.claude/skills/forge-doc/scripts/md_to_pdf.py input.md --style custom.css
```

**导出默认 CSS 以便修改：**
```bash
python3 ~/.claude/skills/forge-doc/scripts/md_to_pdf.py --dump-style > style.css
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

**切换内置风格（Bain）：**
```bash
# DOCX
python3 ~/.claude/skills/forge-doc/scripts/md_to_docx.py input.md \
  --style ~/.claude/skills/forge-doc/assets/bain-style.json

# PDF
python3 ~/.claude/skills/forge-doc/scripts/md_to_pdf.py input.md \
  --style ~/.claude/skills/forge-doc/assets/bain.css
```

**切换内置风格（BCG）：**
```bash
# DOCX
python3 ~/.claude/skills/forge-doc/scripts/md_to_docx.py input.md \
  --style ~/.claude/skills/forge-doc/assets/bcg-style.json

# PDF
python3 ~/.claude/skills/forge-doc/scripts/md_to_pdf.py input.md \
  --style ~/.claude/skills/forge-doc/assets/bcg.css
```

**切换内置风格（中文学术论文）：**
```bash
# DOCX — 宋体/黑体正文，25磅行距，A4
python3 ~/.claude/skills/forge-doc/scripts/md_to_docx.py input.md \
  --style ~/.claude/skills/forge-doc/assets/thesis-style.json

# PDF
python3 ~/.claude/skills/forge-doc/scripts/md_to_pdf.py input.md \
  --style ~/.claude/skills/forge-doc/assets/thesis.css
```

---

## 未安装 skill 目录时

```bash
# DOCX
python3 skills/writing/forge-doc/scripts/md_to_docx.py input.md
# PDF
python3 skills/writing/forge-doc/scripts/md_to_pdf.py input.md
```
