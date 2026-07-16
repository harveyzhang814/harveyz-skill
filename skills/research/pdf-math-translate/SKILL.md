---
name: pdf-math-translate
description: "PDFMathTranslate：翻译科学论文 PDF 为中文，导出 Markdown。双语对照 + 纯翻译双版本输出。支持 Google/DeepL/GPT 等翻译服务。用户 Harvey 的常用工具。"
user_invocable: true
version: "1.0.0"
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [pdf, translation, scientific-papers, markdown, bilingual]
    related_skills: [ocr-and-documents, extract-vision]
---

# PDFMathTranslate

将科学论文 PDF 翻译为中文，支持导出 Markdown。

## 安装状态

- **CLI**：`pdf2zh`（已 PATH）
- **位置**：`/Users/harveyopenclaw/.local/share/uv/tools/pdf2zh/bin/pdf2zh`
- **源码**：`/Users/harveyopenclaw/Repositories/PDFMathTranslate`
- **uv Python**：`/Users/harveyopenclaw/.local/share/uv/tools/pdf2zh/bin/python`

## 执行命令

**关键：必须清除 PYTHONPATH**，否则 ollama/pydantic 与 hermes-agent venv 冲突导致崩溃。**

```bash
cd /Users/harveyopenclaw/Repositories/PDFMathTranslate && \
  unset PYTHONPATH && \
  /Users/harveyopenclaw/.local/share/uv/tools/pdf2zh/bin/pdf2zh \
    "/path/to/paper.pdf" \
    -s google -o "/output/dir/"
```

> **崩溃原因**：`PYTHONPATH` 包含 hermes-agent 的 venv（Python 3.11），pdf2zh 用 Python 3.12；ollama 尝试 import hermes 的 pydantic-2.x 但二进制是给 3.11 编译的，导致 `ModuleNotFoundError: pydantic_core._pydantic_core`。

## 翻译为 PDF（mono + dual）

```bash
pdf2zh "/path/to/paper.pdf" -o "/output/dir/" \
  --lang-in en --lang-out ZH \
  --service google \
  --mode fast
```

| 参数 | 说明 |
|------|------|
| `--lang-in` / `--lang-out` | 源语言 / 目标语言 |
| `--service` | `google`（默认）/ `deepl` / `gpt` 等 |
| `--mode` | `fast`（默认）/ `precise`（更高质量） |

输出两个 PDF：
- `*-mono.pdf`：纯翻译
- `*-dual.pdf`：双语对照

## 导出为 Markdown

```bash
pdf2zh document.pdf --markdown -o ./output
```

直接输出 `document-mono.md`，无需两步。

### 完整流程

```python
import os
import sys

PDF2ZH_PY = "/Users/harveyopenclaw/.local/share/uv/tools/pdf2zh/bin/python"
sys.path.insert(0, "/Users/harveyopenclaw/Repositories/PDFMathTranslate")

from pdf2zh.high_level import translate
from pdf2zh.export_markdown import export_pdf_to_markdown

INPUT_PDF = "/path/to/paper.pdf"
OUTPUT_DIR = "/output/dir/"

# 步骤1：翻译 + 提取 elements
translate(
    INPUT_PDF, OUTPUT_DIR,
    lang_in='en', lang_out='ZH',
    extract_elements=True  # 必须开启
)

# 步骤2：导出 Markdown
elem_dir = os.path.join(OUTPUT_DIR, "paper-elements")
os.makedirs(elem_dir, exist_ok=True)

md_path = export_pdf_to_markdown(
    os.path.join(OUTPUT_DIR, "paper-mono.pdf"),
    elem_dir,
    OUTPUT_DIR,
    'zh'
)
# md_path → OUTPUT_DIR/paper-mono.md
```

### 单行执行

```bash
PDF2ZH_PY=/Users/harveyopenclaw/.local/share/uv/tools/pdf2zh/bin/python
$PDF2ZH_PY -c "
import sys, os
sys.path.insert(0, '/Users/harveyopenclaw/Repositories/PDFMathTranslate')
from pdf2zh.high_level import translate
from pdf2zh.export_markdown import export_pdf_to_markdown
elem_dir = '/output/paper-elements'
os.makedirs(elem_dir, exist_ok=True)
translate('/input.pdf', '/output/', lang_in='en', lang_out='ZH', extract_elements=True)
print(export_pdf_to_markdown('/output/input-mono.pdf', elem_dir, '/output/', 'zh'))
"
```

## 常用命令一览

```bash
# 基础翻译（PDF 输出）
pdf2zh paper.pdf -o ./output/ --lang-in en --lang-out ZH

# 指定翻译服务
pdf2zh paper.pdf -o ./output/ --service deepl

# 仅提取 elements（不翻译）
pdf2zh paper.pdf -o ./output/ --extract-elements

# 查看所有选项
pdf2zh --help
```

## 注意事项

- **首次运行**：自动下载 ONNX 模型（~300MB），缓存在 `~/.paddlex/`
- **elements 目录**：markdown 导出的必要中间产物，保留
- **语言对**：中译英 `ZH-EN`，英译中 `EN-ZH`
- 安装问题：`pip install -e .` 可能因 babeldoc 版本冲突失败，使用已装的 uv 工具链即可
