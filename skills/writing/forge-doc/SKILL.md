---
name: forge-doc
description: "Convert documents between formats. Trigger when the user wants to convert or export a Markdown file to Word (.docx) or PDF — e.g. 'export as docx', 'convert to Word', 'export as pdf', 'generate PDF' — or when the user writes a document in the conversation and wants it as .docx or .pdf."
user_invocable: true
version: "2.6.1"
---

`SKILL_DIR` 为当前 host 安装本 skill 的目录（包含 `scripts/`、`assets/` 和 `preview/`）；也可设为仓库中的 `skills/writing/forge-doc`，直接使用未安装的版本。

## 执行前必做：样式预览 → 选择样式

Step 0、Step 1 的提问：host 有提问机制就用，没有就在对话中问。

### Step 0 — 询问是否查看样式预览

**在运行任何转换命令之前**，若用户未显式指定样式，询问：

```
问题：是否先查看所有样式的预览效果？
选项：
  1. 查看样式预览（推荐）— 自动生成并打开预览 HTML
  2. 跳过预览，直接选择样式
```

**如果用户选择"查看样式预览"，或未明确选择跳过**，执行：

```bash
python3 SKILL_DIR/scripts/generate_style_preview.py
```

可选地用当前 host 打开 `SKILL_DIR/preview/style-preview.html`；若未打开，告知用户该预览位置并请其对比后回来选择。

---

### Step 1 — 询问样式

若用户未显式指定样式，询问：

```
问题：请选择输出样式
选项：
  1. Bain & Company（红色品牌）— Bain 正式输出
  2. BCG（深绿品牌，麦肯锡横线表格）— BCG 正式输出
  3. Roland Berger — RB 正式输出
  4. 中文学术论文（宋体/黑体，25磅行距）— 硕博论文、学术报告
  5. 自定义（用户提供路径或描述）
```

用户选定后再执行转换。**用户未指定样式时不得跳过此步骤，不得默认使用某一样式。**

---

## 转换

支持标题、表格、代码块、列表、行内格式、引用块、图片和 Mermaid（DOCX 渲染为 PNG，PDF 渲染为 SVG）。

| 格式 | 脚本 | `--style` 文件 | 依赖 |
|------|------|---------------|------|
| DOCX | `SKILL_DIR/scripts/md_to_docx.py` | `.json` | `pip install python-docx`；含 Mermaid 时还需 playwright |
| PDF | `SKILL_DIR/scripts/md_to_pdf.py` | `.css` | `pip install markdown` + playwright |

```bash
python3 <脚本> input.md [output] [--style <文件>] [--base-dir <图片根目录>]
python3 <脚本> --dump-style > style.json   # PDF 用 style.css；导出默认样式作为定制起点
```

- 不给 output 时，在 input 同目录生成同名文件。
- 内置样式在 `SKILL_DIR/assets/`，DOCX 用 `<slug>-style.json`，PDF 用 `<slug>.css`：

  | slug | 样式 | 适用场景 |
  |------|------|---------|
  | `bain` | Bain & Company（红色） | Bain 正式输出 |
  | `bcg` | BCG（深绿，麦肯锡横线表格） | BCG 正式输出 |
  | `rolandberger` | Roland Berger | RB 正式输出 |
  | `thesis` | 中文学术论文（宋体/黑体/Times New Roman，25磅行距） | 硕博学位论文、学术报告 |

- 图片（`![alt](./images/fig.png)` 或 `![[fig.png]]`）：相对路径以 MD 文件所在目录为根解析。转换已有的 MD 时传绝对路径；MD 不在图片原目录时（如写到 /tmp 的临时稿），加 `--base-dir <图片根目录>`，例如 `python3 SKILL_DIR/scripts/md_to_pdf.py /tmp/draft.md --base-dir /Users/harvey/Documents/my-paper`。
- 离线 Mermaid：在 skill 目录执行 `npm install mermaid`，否则从 CDN 加载。
- 自定义 DOCX 样式：style.json 键为 `page`、`body`、`headings`（h1–h4）、`code_block`、`blockquote`、`table`，只写要覆盖的部分。自定义 PDF 样式：标准 CSS，支持 `@page`。
