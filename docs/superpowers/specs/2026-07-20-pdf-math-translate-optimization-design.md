---
title: pdf-math-translate 重构设计——通用化 + 机器级 Init/Execute
date: 2026-07-20
status: approved
---

# pdf-math-translate 重构设计

## 背景

`skills/research/pdf-math-translate/SKILL.md` 是从另一台机器（用户名 `harveyopenclaw`，配合 `hermes-agent`）迁移过来的遗留文档：

- 所有路径硬编码为 `/Users/harveyopenclaw/...`，在当前机器（`harveyzhang96`）上不存在
- 描述的 PYTHONPATH/hermes-agent venv 冲突规避方法，针对的是另一台机器的 uv 工具链设置，当前环境（单一 Homebrew Python 3.11 可编辑安装）不存在此问题
- Markdown 导出流程用手写两步 Python 脚本（`translate()` + `export_pdf_to_markdown()`），而当前 CLI（pdf2zh v1.9.11）已原生支持 `--markdown` 参数，一步到位
- 服务列表、参数列表均不完整，且与实际不符（如 "gpt" 不是有效服务名）

调研确认（基于 `pdf2zh --help`、`pdf2zh/translator.py` 源码、`pip show`/`import` 探测）：

- 当前机器上 `pdf2zh` 通过 Homebrew 全局安装于 `/opt/homebrew/bin/pdf2zh`，可编辑安装（editable install）指向 `/Users/harveyzhang96/Projects/PDFMathTranslate`（用户自己 fork 的仓库）
- 实际 Python 解释器：`/opt/homebrew/opt/python@3.11/bin/python3.11`
- `pdf2zh_next`（`--mode precise` 依赖）**未安装**，目前只有 `fast` 模式可用
- 默认翻译服务是 `google`（CLI 源码默认值）
- 实际支持 24 个翻译服务（见下方服务列表，另有 `base`/`identity` 两个内部服务不面向用户）

## 目标

把 SKILL.md 改造成**可移植**的通用文档——不写死任何机器路径，而是通过一次性 Init 探测把机器相关信息写入 `$HOME/.hskill/pdf-math-translate/config.md`，之后每次调用读取该文件。这样这个 skill 可以被安装到任何机器上，首次使用时自动适配当前环境。

同时，SKILL.md 主体的命令/参数/服务文档要更新为反映当前 CLI（v1.9.11）实际能力。

## 非目标

- 不实际运行完整翻译验证输出（用户已确认跳过，基于 `--help` + 源码阅读即可）
- 不引入项目级配置（`<project-root>/.hskill/`）——本 skill 的配置是机器级的，不因项目而异，按 [[project_skill_data_dir]] 记忆中记录的 scope 约定使用全局路径 `$HOME/.hskill/pdf-math-translate/`
- 不新增翻译服务偏好、语言对偏好等未被要求的配置项（YAGNI）

## 架构：Init / Execute 两阶段

参照仓库内 `skills/meta/release-project/SKILL.md` 的既有模式。

### 入口判断

```bash
ls "$HOME/.hskill/pdf-math-translate/config.md" 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

- **NOT_FOUND** → 执行 Init 阶段
- **EXISTS** → 直接执行 Execute 阶段
- 用户说"重新初始化"/环境变了（如升级了 pdf2zh、换了机器）→ 重新执行 Init（覆盖旧 config）

### Init 阶段（机器级探测，均为轻量命令，不实际跑翻译）

依次执行并记录结果：

1. **定位 CLI 二进制**：`which pdf2zh`
2. **解析实际 Python 解释器**：读取 `pdf2zh` 脚本首行 shebang（`head -1 $(which pdf2zh)`）
3. **探测安装方式与源码路径**（仅当 editable install 时才有源码仓库路径）：
   ```bash
   PY=<上一步解出的解释器路径>
   $PY -c "import pdf2zh; print(pdf2zh.__file__)"
   ```
   若返回路径指向 site-packages 内，则视为普通安装，无源码仓库路径；若指向仓库目录，记录该仓库根路径。
4. **记录版本号**：`pdf2zh --version`
5. **探测 precise 模式可用性**：
   ```bash
   $PY -c "import pdf2zh_next" 2>&1
   ```
   成功则 precise 模式可用；`ModuleNotFoundError` 则只有 fast 模式可用。
6. **探测 PYTHONPATH 冲突风险**：检查当前 shell 的 `PYTHONPATH` 环境变量是否非空且指向与 `$PY` 版本不同的 site-packages/venv。若非空但版本一致则无风险；若指向其他 Python 版本的 venv，记录为已知风险并建议 `unset PYTHONPATH` 后再调用。
7. **询问用户默认输出目录**：向用户提问期望的默认翻译输出目录（例如 `~/Documents/pdf-translations/`），写死为默认值，供 Execute 阶段未显式传 `-o` 时使用。

将 1-7 的结果写入 `$HOME/.hskill/pdf-math-translate/config.md`（模板见下），写完后展示给用户确认。

### config.md 模板

```markdown
# pdf-math-translate 机器配置

探测时间：<Init 执行时间>

## CLI

- 二进制路径：`<which pdf2zh 结果>`
- 版本：`<pdf2zh --version 结果>`
- Python 解释器：`<shebang 解出的路径>`

## 安装方式

- 类型：`editable install` | `regular install`
- 源码仓库路径：`<路径，仅 editable install 时存在，否则写"（不适用，非可编辑安装）">`

## 能力

- precise 模式（`--mode precise`）：`可用` | `不可用（pdf2zh_next 未安装）`

## 已知环境注意事项

- PYTHONPATH 冲突风险：`无` | `<具体描述与规避方法>`

## 默认输出目录

- `<用户确认的默认路径>`
```

### Execute 阶段

1. 读取 `$HOME/.hskill/pdf-math-translate/config.md`，取得：CLI 路径、Python 解释器、precise 模式可用性、PYTHONPATH 注意事项、默认输出目录
2. 按 SKILL.md 主体的命令参考执行翻译（见下）
3. 若用户请求 `--mode precise` 但 config 中标注不可用，提示用户该模式依赖 `pdf2zh_next`，未安装，回退 `fast` 模式或引导安装
4. 若 config 中记录了 PYTHONPATH 风险，执行命令前按记录的规避方法处理（如 `unset PYTHONPATH`）
5. 未显式指定 `-o` 时，使用 config 中的默认输出目录

## SKILL.md 主体内容（通用，不含机器路径）

### 基础翻译（PDF 输出）

```bash
pdf2zh "/path/to/paper.pdf" -o "<输出目录>" \
  --lang-in en --lang-out ZH \
  --service google \
  --mode fast
```

输出两个 PDF：`*-mono.pdf`（纯翻译）、`*-dual.pdf`（双语对照）。

### 导出为 Markdown（原生支持，替代旧的手写脚本流程）

```bash
pdf2zh document.pdf --markdown -o <输出目录>
```

- 自动隐含 `--extract-elements`
- 图片自动导出到 `<输出目录>/images/` 子目录，Markdown 中使用 Obsidian wikilink 格式引用
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
| `--mode` | `fast`（默认，v1）/ `precise`（v2，需要 `pdf2zh_next`，是否可用见本机 config） |
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
- **precise 模式**：依赖 `pdf2zh_next`，是否已安装以本机 `config.md` 为准，未安装时只能用 `fast` 模式
- 安装问题：`pip install -e .` 可能因 babeldoc 版本冲突失败，优先使用已有工具链

## 验证方式

不做实际翻译运行验证（用户已确认）。验证范围限于：

1. SKILL.md 格式校验：`npm test` 中的 SKILL.md frontmatter 格式测试通过
2. 人工审阅：Init 阶段探测命令的输出结构与 config.md 模板字段一一对应
3. 交叉核对：主体参数表、服务列表与当前 `pdf2zh --help` 输出及 `pdf2zh/translator.py` 源码内 `name = "..."` 列表一致
