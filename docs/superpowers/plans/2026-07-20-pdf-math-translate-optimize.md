# pdf-math-translate Optimize Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `skills/research/pdf-math-translate/SKILL.md` from a machine-specific, stale document into a portable one that probes machine config into `$HOME/.hskill/pdf-math-translate/config.md` on first use (Init/Execute two-phase pattern), and documents the current pdf2zh v1.9.11 CLI capabilities accurately.

**Architecture:** Single-file skill (`SKILL.md`). No code, no runtime test harness — the "tests" are (a) the repo's existing SKILL.md frontmatter validator (`npm test`), and (b) manual cross-checks of documented content against `pdf2zh --help` / `pdf2zh/translator.py` source output captured during design research.

**Tech Stack:** Markdown (SKILL.md), bash (verification commands), no new code.

## Global Constraints

- Design source of truth: `docs/superpowers/specs/2026-07-20-pdf-math-translate-optimization-design.md` — every requirement below traces to that spec.
- Config location is **global**, not project-local: `$HOME/.hskill/pdf-math-translate/config.md` (per the repo convention that machine-level, cross-project config lives under `$HOME/.hskill/<skill-name>/`).
- No machine-specific paths (e.g. `/Users/harveyopenclaw/...`, `/Users/harveyzhang96/...`) may appear anywhere in the final `SKILL.md` body — those values only ever live in the generated `config.md`.
- Do not add translation-service or language-pair preference config — out of scope (spec's Non-Goals).
- Do not actually run a full `pdf2zh` translation to verify (user declined) — verification is `--help`/source cross-check only.
- Frontmatter `version` must be bumped (this is a breaking rewrite of the skill's documented workflow) and must remain valid per this repo's SKILL.md format rules (checked by `npm test`).

---

### Task 1: Rewrite frontmatter, entry check, and Init phase

**Files:**
- Modify: `skills/research/pdf-math-translate/SKILL.md` (full rewrite of frontmatter + top section)

**Interfaces:**
- Produces: the `## 入口判断` and `## Init 阶段` sections, and the `config.md` template block, which Task 2's `## Execute 阶段` section refers to by field name (`CLI 路径`, `Python 解释器`, `安装方式`/`源码仓库路径`, `precise 模式`, `PYTHONPATH 冲突风险`, `默认输出目录`).

- [ ] **Step 1: Read the current file to confirm the exact old content being replaced**

Run: `cat skills/research/pdf-math-translate/SKILL.md`

Confirm it still contains the old `harveyopenclaw` paths (this is the file being replaced — if it doesn't, stop and re-check you're on the right branch/worktree).

- [ ] **Step 2: Replace the file's frontmatter and everything up through a new Init phase section**

Overwrite `skills/research/pdf-math-translate/SKILL.md` entirely with the following content for now (Task 2 will append the Execute phase section below this):

```markdown
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
```

- [ ] **Step 3: Verify the file parses as valid markdown with frontmatter**

Run: `head -13 skills/research/pdf-math-translate/SKILL.md`

Expected: the `---`-delimited frontmatter block prints exactly as written in Step 2, ending with the second `---` on its own line, followed by a blank line then `# PDFMathTranslate`.

- [ ] **Step 4: Verify no stale machine paths remain yet in what's written so far**

Run: `grep -n "harveyopenclaw" skills/research/pdf-math-translate/SKILL.md; echo "exit: $?"`

Expected: no matches, `exit: 1` (grep found nothing).

- [ ] **Step 5: Commit**

```bash
git add skills/research/pdf-math-translate/SKILL.md
git commit -m "$(cat <<'EOF'
docs(pdf-math-translate): rewrite frontmatter and add Init phase

Replaces the harveyopenclaw-machine-specific setup instructions with a
portable Init phase that probes CLI path, Python interpreter, install
type, precise-mode availability, and PYTHONPATH risk into
$HOME/.hskill/pdf-math-translate/config.md on first use.
EOF
)"
```

---

### Task 2: Add the Execute phase (command reference, parameter table, services)

**Files:**
- Modify: `skills/research/pdf-math-translate/SKILL.md` (append below Task 1's content)

**Interfaces:**
- Consumes: config field names produced by Task 1's `config.md` template (`CLI 路径`, `Python 解释器`, `安装方式`, `precise 模式`, `PYTHONPATH 冲突风险`, `默认输出目录`) — referenced by name in prose, not by any code interface.
- Produces: the complete parameter table and service list that Task 3 will cross-check against `pdf2zh --help`.

- [ ] **Step 1: Append the Execute phase section to the end of the file**

Add the following to the end of `skills/research/pdf-math-translate/SKILL.md` (after the Init phase content from Task 1):

```markdown

## Execute 阶段

读取 `$HOME/.hskill/pdf-math-translate/config.md`，按其中记录的信息执行：

- 若 config 记录了 PYTHONPATH 风险，执行 pdf2zh 命令前先按记录的规避方法处理（通常是 `unset PYTHONPATH`）
- 若用户要求 `--mode precise` 但 config 标注「不可用」，提示用户该模式依赖 `pdf2zh_next`（当前未安装），询问是否改用 `fast` 模式或先安装 `pdf2zh_next`
- 未显式指定 `-o` 时，使用 config 中的默认输出目录

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

### 完整参数表

| 参数 | 说明 |
|------|------|
| `--lang-in` / `-li` | 源语言代码 |
| `--lang-out` / `-lo` | 目标语言代码 |
| `--service` / `-s` | 翻译服务（见下方服务列表），默认 `google` |
| `--output` / `-o` | 输出目录 |
| `--mode` | `fast`（默认，v1）/ `precise`（v2，需要 `pdf2zh_next`，本机是否可用见 config.md） |
| `--pages` / `-p` | 指定翻译的页码列表 |
| `--thread` / `-t` | 翻译并发线程数 |
| `--extract-elements` | 提取图表为独立图片文件（`--word`/`--markdown` 会自动隐含） |
| `--elements-output-dir` | 提取元素的输出目录，不指定则与翻译后 PDF 同目录 |
| `--markdown` | 导出为 Markdown（互斥于 `--word`） |
| `--word` | 导出为 Word .docx（互斥于 `--markdown`） |
| `--no-pdf` | 配合 `--word` 使用，丢弃中间 mono/dual PDF，只保留 docx |
| `--compatible` / `-cp` | 转换为 PDF/A 格式提升兼容性 |
| `--skip-subset-fonts` | 跳过字体子集化，提升兼容性但增大文件体积 |
| `--ignore-cache` | 忽略缓存，强制重新翻译 |
| `--config` | 指定配置文件路径 |
| `--mcp` | 以 STDIO 模式启动 MCP server |
| `--sse` | 以 SSE 模式启动 MCP server |
| `--dir` | 翻译整个目录 |
| `--debug` / `-d` | debug 日志级别 |

### 支持的翻译服务

`google`（默认）、`bing`、`deepl`、`deeplx`、`ollama`、`xinference`、`openai`、`azure-openai`、`azure`、`modelscope`、`zhipu`、`silicon`、`302ai`、`gemini`、`tencent`、`anythingllm`、`dify`、`argos`、`grok`、`groq`、`deepseek`、`minimax`、`openailiked`、`qwen-mt`

### 语言对说明

- 中译英：`ZH-EN`
- 英译中：`EN-ZH`

## 注意事项

- **首次运行**：自动下载 ONNX 模型（约 300MB），缓存在 `~/.paddlex/`
- **elements 目录**：Markdown/Word 导出的必要中间产物，保留
- **precise 模式**：依赖 `pdf2zh_next`，是否已安装以本机 config.md 为准，未安装时只能用 `fast` 模式
- 安装问题：`pip install -e .` 可能因 babeldoc 版本冲突失败，优先使用已有工具链
```

- [ ] **Step 2: Verify the file has exactly one `## Execute 阶段` heading and one `## 注意事项` heading**

Run: `grep -c "^## Execute 阶段$" skills/research/pdf-math-translate/SKILL.md; grep -c "^## 注意事项$" skills/research/pdf-math-translate/SKILL.md`

Expected: both commands print `1`.

- [ ] **Step 3: Verify no stale machine paths anywhere in the full file**

Run: `grep -nE "harveyopenclaw|/Users/harveyzhang96" skills/research/pdf-math-translate/SKILL.md; echo "exit: $?"`

Expected: no matches, `exit: 1`.

- [ ] **Step 4: Commit**

```bash
git add skills/research/pdf-math-translate/SKILL.md
git commit -m "$(cat <<'EOF'
docs(pdf-math-translate): add Execute phase with current CLI reference

Adds the command reference, full parameter table, and 24-service list
matching pdf2zh v1.9.11's actual --help output, replacing the old
two-step manual Python markdown-export script with the CLI's native
--markdown/--word flags.
EOF
)"
```

---

### Task 3: Validate against the live CLI and repo test suite

**Files:**
- No new files. Verification only, against:
  - `skills/research/pdf-math-translate/SKILL.md` (the file from Tasks 1-2)
  - live `pdf2zh --help` output
  - `pdf2zh/translator.py` in the editable-installed repo (path discovered via `python3.11 -c "import pdf2zh; print(pdf2zh.__file__)"`)

**Interfaces:**
- Consumes: the parameter table and service list produced by Task 2.
- Produces: nothing new — this task only confirms Tasks 1-2's output is correct. No further tasks depend on it.

- [ ] **Step 1: Run the repo's SKILL.md format test suite**

Run: `npm test 2>&1 | grep -i "skill"`

Expected: no failures reported for `pdf-math-translate`; overall suite still reports the same pass count structure as the pre-existing baseline (`16 passed, 0 failed` for custom skill tests, plus the untouched Python/unittest suites).

If it fails on `pdf-math-translate` specifically, read the failure message, fix the frontmatter or structure in `SKILL.md`, and re-run.

- [ ] **Step 2: Cross-check the parameter table against live `--help` output**

Run:
```bash
pdf2zh --help 2>&1 > /tmp/pdf2zh-help-actual.txt
grep -oE '^\s+--[a-z-]+' /tmp/pdf2zh-help-actual.txt | sed 's/^\s*//' | sort -u
```

Expected: every flag in this output (`--authorized`, `--babeldoc`, `--backend`, `--celery`, `--compatible`, `--config`, `--debug`, `--dir`, `--elements-output-dir`, `--extract-elements`, `--flask`, `--ignore-cache`, `--interactive`, `--lang-in`, `--lang-out`, `--markdown`, `--mcp`, `--mode`, `--no-pdf`, `--onnx`, `--output`, `--pages`, `--prompt`, `--serverport`, `--service`, `--share`, `--skip-subset-fonts`, `--sse`, `--thread`, `--vchar`, `--version`, `--vfont`, `--word`) is either present in the `完整参数表` written in Task 2, or is a low-relevance/dev-only flag intentionally omitted (`--authorized`, `--celery`, `--flask`, `--interactive`, `--onnx`, `--prompt`, `--serverport`, `--share`, `--backend`, `--vfont`, `--vchar`, `--babeldoc` — these are UI/server/font-tuning internals not needed for the documented CLI workflows). If any translation-relevant flag is missing from the table, add it.

- [ ] **Step 3: Cross-check the service list against the translator source**

Run:
```bash
PY=$(head -1 "$(which pdf2zh)" | sed 's/^#!//')
REPO=$($PY -c "import pdf2zh, os; print(os.path.dirname(os.path.dirname(pdf2zh.__file__)))")
grep -oE 'name = "[a-z0-9-]+"' "$REPO/pdf2zh/translator.py" | sed -E 's/name = "(.+)"/\1/' | sort
```

Expected output (26 names total; `base` and `identity` are internal/non-user-facing and intentionally excluded, leaving 24 in the doc's service list):
```
302ai
anythingllm
argos
azure
azure-openai
base
bing
deepl
deeplx
deepseek
dify
gemini
google
grok
groq
identity
minimax
modelscope
ollama
openai
openailiked
qwen-mt
silicon
tencent
xinference
zhipu
```

Confirm every name except `base` and `identity` appears in the `支持的翻译服务` list written in Task 2. If any is missing, add it; if any extra/wrong name (e.g. a leftover `gpt`) is present, remove it.

- [ ] **Step 4: Final full-file review**

Run: `cat skills/research/pdf-math-translate/SKILL.md`

Read the whole file top to bottom. Confirm:
- Frontmatter `version` is `"2.0.0"`
- No `harveyopenclaw` or other hardcoded absolute machine paths anywhere
- Every config.md field referenced in `## Execute 阶段` prose matches a field name that exists in the Init phase's config.md template exactly (`CLI 路径`, `Python 解释器`, `安装方式`, `precise 模式`, `PYTHONPATH 冲突风险`, `默认输出目录`)

Fix any mismatch found directly in the file.

- [ ] **Step 5: Commit any fixes from Steps 2-4 (skip if nothing changed)**

```bash
git status --porcelain skills/research/pdf-math-translate/SKILL.md
```

If it shows a modified file:
```bash
git add skills/research/pdf-math-translate/SKILL.md
git commit -m "$(cat <<'EOF'
docs(pdf-math-translate): fix parameter/service list gaps found in cross-check
EOF
)"
```

If `git status --porcelain` prints nothing, no commit is needed — the file already matched on first write.

---

## Post-Plan Notes

- This plan does not cover actually running `pdf2zh` end-to-end (translating a real PDF) — the user explicitly deferred that verification. If a future session wants to validate the documented workflows behaviorally, that would be a separate task requiring a sample PDF and a configured translation service (most services need an API key; `google` needs none).
- The design spec (`docs/superpowers/specs/2026-07-20-pdf-math-translate-optimization-design.md`) is the source of truth if any task step here appears to contradict it.
