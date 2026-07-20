---
name: pdf-math-translate
description: "PDFMathTranslate：翻译科学论文 PDF 为中文，导出 Markdown/Word。双语对照 + 纯翻译双版本输出。支持 Google/DeepL/OpenAI 等 24 种翻译服务。首次使用自动探测本机 CLI 路径与能力，写入 ~/.hskill/pdf-math-translate/config.md。用户 Harvey 的常用工具。"
user_invocable: true
version: "2.0.0"
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

依次执行以下探测命令，不实际运行翻译：

### 1. 定位 CLI 二进制

```bash
which pdf2zh
```

### 2. 解析实际 Python 解释器

```bash
head -1 "$(which pdf2zh)"
```

shebang 行给出实际 Python 解释器路径。

### 3. 探测安装方式与源码路径

```bash
PY="<上一步解出的解释器路径>"
$PY -c "import pdf2zh; print(pdf2zh.__file__)"
```

- 若返回路径包含 `site-packages`：普通安装，无源码仓库路径
- 若返回路径不包含 `site-packages`（指向某个仓库目录）：editable install，记录该仓库根路径

### 4. 记录版本号

```bash
pdf2zh --version
```

### 5. 探测 precise 模式可用性

```bash
$PY -c "import pdf2zh_next" 2>&1
```

- 无报错 → precise 模式可用
- `ModuleNotFoundError` → 只有 fast 模式可用

### 6. 探测 PYTHONPATH 冲突风险

```bash
echo "$PYTHONPATH"
```

- 为空 → 无风险
- 非空但指向的 venv 与 `$PY` 版本一致 → 无风险
- 非空且指向其他 Python 版本的 venv/site-packages → 记录为风险，规避方法是执行 pdf2zh 前 `unset PYTHONPATH`

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
