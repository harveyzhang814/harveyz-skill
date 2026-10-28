---
name: pdf-math-translate
description: "PDFMathTranslate: translates scientific paper PDFs into Chinese, exporting to Markdown/Word. Produces both bilingual and translation-only outputs. Supports 24 translation services including Google/DeepL/OpenAI. On first use, auto-detects the local CLI path and capabilities and writes them to ~/.hskill/pdf-math-translate/config.md. One of Harvey's frequently used tools."
user_invocable: true
version: "2.0.1"
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [pdf, translation, scientific-papers, markdown, bilingual]
    related_skills: [ocr-and-documents, extract-vision]
---

# PDFMathTranslate

将科学论文 PDF 翻译为中文，支持导出 Markdown 或 Word。首次使用会自动探测本机 CLI 路径与能力，之后每次直接读取探测结果。

## 入口判断

```bash
ls "$HOME/.hskill/pdf-math-translate/config.md" 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

- **NOT_FOUND** → 执行下面的「Init 阶段」
- **EXISTS** → 跳过 Init，直接执行「Execute 阶段」
- 用户说"重新初始化"、或怀疑环境变了（升级了 pdf2zh、换了机器）→ 重新执行 Init 阶段（覆盖旧 config）

## Init 阶段（仅首次运行）

依次执行以下探测，不实际运行翻译：

| # | 探测 | 命令 | 判定 / 记录 |
|---|---|---|---|
| 1 | CLI 路径 | `which pdf2zh` | 记录路径 |
| 2 | 解释器 | `head -1 "$(which pdf2zh)"` | shebang 给出的解释器路径，记为 `$PY` |
| 3 | 安装方式 | `$PY -c "import pdf2zh; print(pdf2zh.__file__)"` | 路径含 `site-packages` 为 regular install；否则为 editable install，记录该仓库根路径 |
| 4 | 版本 | `pdf2zh --version` | 记录版本号 |
| 5 | precise 模式 | `$PY -c "import pdf2zh_next" 2>&1` | 无报错为可用；`ModuleNotFoundError` 为不可用（只有 fast） |
| 6 | PYTHONPATH | `echo "$PYTHONPATH"` | 非空且指向其他 Python 版本的 venv/site-packages 时记为风险，规避方法是执行 pdf2zh 前 `unset PYTHONPATH`；其余情况为无风险 |

### 7. 询问用户默认输出目录

问用户："翻译结果默认存到哪个目录？"（例如 `~/Documents/pdf-translations/`），获得答案后连同上述探测结果一起写入 config。

### 写入 config.md

```bash
mkdir -p "$HOME/.hskill/pdf-math-translate"
```

按下面模板填入 1-7 的结果，写入 `$HOME/.hskill/pdf-math-translate/config.md`：

```markdown
# pdf-math-translate 机器配置

探测时间：<日期>

## CLI

- 二进制路径：`<步骤1结果>`
- 版本：`<步骤4结果>`
- Python 解释器：`<步骤2结果>`

## 安装方式

- 类型：`editable install` | `regular install`
- 源码仓库路径：`<步骤3结果，非 editable install 时写"（不适用，非可编辑安装）">`

## 能力

- precise 模式（`--mode precise`）：`可用` | `不可用（pdf2zh_next 未安装）`

## 已知环境注意事项

- PYTHONPATH 冲突风险：`无` | `<步骤6记录的具体描述与规避方法>`

## 默认输出目录

- `<步骤7用户确认的路径>`
```

写完后展示给用户确认无误，并告知：**该文件可随时手动编辑**，是之后每次调用的唯一依据。

## Execute 阶段

读取 `$HOME/.hskill/pdf-math-translate/config.md`，按其中记录的信息执行：

- 若 config 中记录的二进制路径与当前 PATH 里的 `pdf2zh` 不一致，优先使用 config 中记录的路径调用
- 若 config 记录了 PYTHONPATH 冲突风险，执行 pdf2zh 命令前先按记录的规避方法处理（通常是 `unset PYTHONPATH`）
- 若用户要求 `--mode precise` 但 config 标注「不可用」，提示用户该模式依赖 `pdf2zh_next`（当前未安装），询问是否改用 `fast` 模式或先安装 `pdf2zh_next`
- 未显式指定 `-o` 时，使用 config 中的默认输出目录
- 若排查版本/导入相关问题，参考 config 中记录的 Python 解释器与安装方式（含源码仓库路径，若为 editable install）

### 基础翻译（PDF 输出）

```bash
pdf2zh "/path/to/paper.pdf" -o "<输出目录>" \
  --lang-in en --lang-out ZH \
  --service google \
  --mode fast
```

输出两个 PDF：
- `*-mono.pdf`：纯翻译
- `*-dual.pdf`：双语对照

### 导出为 Markdown

```bash
pdf2zh document.pdf --markdown -o <输出目录>
```

- 自动隐含 `--extract-elements`
- 图片自动导出到 `<输出目录>/images/` 子目录，Markdown 中用 Obsidian wikilink 格式引用
- 直接输出 `document-mono.md`，无需额外步骤

### 导出为 Word

```bash
pdf2zh document.pdf --word -o <输出目录>

# 只保留 docx，丢弃中间 PDF：
pdf2zh document.pdf --word --no-pdf -o <输出目录>
```

- 自动隐含 `--extract-elements`
- 与 `--markdown` 互斥

### 常用参数

`-o` 输出目录；`--lang-in` / `--lang-out`（默认 `en` → `zh`）；`--service`（默认 `google`）；`--mode fast|precise`；`--pages`；`--markdown` 与 `--word` 互斥；`--no-pdf` 只配合 `--word` 使用。其他参数和服务列表以 `pdf2zh --help` 为准。

## 注意事项

- **首次运行**：自动下载版面模型，缓存在 `~/.cache/babeldoc/`
- **elements 目录**：Markdown/Word 导出的必要中间产物，保留
- 安装问题：`pip install -e .` 可能因 babeldoc 版本冲突失败，优先使用已有工具链
