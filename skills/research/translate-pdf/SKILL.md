---
name: translate-pdf
description: "Extract an English PDF (academic paper or industry research report) into a section tree and deliver it as a reflowed, editable Chinese Word (.docx) / Markdown document with the local `filetranslator` CLI: headings with a TOC, a consistent glossary, real tables, figures as separate files, and a degradation report. Use when the user wants a PDF's content as a Chinese Word/Markdown document or knowledge-base material, mentions filetranslator / File Translator, or wants a PDF parsed into a section-tree IR. Not for getting a translated PDF that keeps the original page layout (use pdf-math-translate for that), nor for text snippets or web pages. Runs MinerU + pi + pandoc locally and is long-running, so run it in the background."
user_invocable: true
version: "1.0.0"
---

# translate-pdf — 用 filetranslator CLI 把 PDF 译成中文 Word / Markdown

`filetranslator` 是一个面向 agent 的本地 CLI：PDF →（MinerU 解析）→ 章节树 IR →（pi 翻译）
→（pandoc 渲染）→ 中文 `.docx` / `.md`。输出默认就是 NDJSON，退出码有稳定契约。
直接用 shell 调它，不要绕道 MCP——后台跑长任务、读完整 stderr 只有 shell 做得到。

## 1. 前置自检

```bash
command -v filetranslator && filetranslator config show
```

- 找不到命令：在 File Translator 仓库根目录执行 `uv tool install --editable .`，或问用户仓库在哪。
- 命令存在但一跑就 `ModuleNotFoundError` / `ImportError`：editable 安装只跟代码不跟依赖，
  仓库新增依赖后工具环境就过期了。在仓库根目录执行 `uv tool install --editable --force .`
  重装（会改用户的全局工具环境，先告诉用户）。
- `config show` 的 NDJSON 里看两件事：
  - `effective` / `source`：产物落在哪个 workdir。**`source` 为默认值时 workdir 是当前目录下
    的 `work/`**——在别人的项目目录里跑会把产物撒进那个项目。这种情况显式传
    `-w <目录>`，目录拿不准就问用户。
  - `provider` / `model`：翻译用的模型；未设置则用 pi 自己的默认。
- 外部依赖 `mineru`、`pi`、`pandoc` 缺哪个，运行时会以对应错误码报出来（见 §5），不必预先逐个检查。

## 2. 主路径：一条 run，后台跑

```bash
filetranslator run "<abs>/paper.pdf" -w "<workdir>" > run.ndjson 2> run.err
```

- **必须后台执行。** MinerU 冷启动要数分钟，翻译是几十次模型调用，整篇常见十几分钟以上。
  Claude Code 用 Bash 的 `run_in_background`，跑完会通知你；其他宿主用
  `nohup … &` 再轮询 `run.ndjson`。不要前台阻塞等待，也不要给它套一个短超时。
- `--jobs N` 并发调用模型，能明显提速；用户没提就保持默认。
- `--bilingual` 额外产出中英对照 Markdown（用户要对照版时才加）。
- 同一份 PDF 再跑会命中 MinerU 缓存，不会重新解析；只有怀疑解析结果坏了才加 `--force`
  （会重跑数分钟）。

## 3. 读输出

stdout 每行一个 JSON 事件：

| `type` | 何时出现 | 关键字段 |
|---|---|---|
| `stage` | build / translate / render 各**完成**时一条 | `stage`、`status`、`artifacts`、`degraded`、`report` |
| `result` | 全部结束时一条 | `status`（`ok` / `degraded`）、`exit_code`、`artifacts`、`degraded_total`、`reports` |

`result.artifacts` 全是绝对路径：`docx`、`md`、`html`、`report`、`ir`、`zh_ir`，加
`--bilingual` 时还有 `bilingual_md`。

致命错误写在 **stderr**，是一行 `type:"error"` 的 JSON：`error.code`、`error.message`，
run 失败时还带 `hint`。stderr 里其余非 JSON 行是 MinerU 等子进程的日志，平时忽略；
退出码非 0 却**没有** `type:"error"` 行、末尾是 Python 堆栈时，那是代码 bug，把堆栈原样报给用户。

`stage` 只在阶段完成时出现，翻译阶段中途很长时间没有新输出是正常的，不要据此判断卡死。

## 4. 退出码

| 退出码 | 含义 | 怎么办 |
|---|---|---|
| `0` | 成功，无降级 | 交付 |
| `3` | 成功但有降级（仅 run） | 交付，同时读 `reports` 里的 report.md，向用户概括降级了什么 |
| `1` | 致命错误 | 读 stderr 的 `error.code`，按 §5 处理 |
| `2` | 参数错误 | 修正命令；先 `filetranslator run --help` 核对 |

## 5. 致命错误处理

| `error.code` | 含义 | 处理 |
|---|---|---|
| `E_INPUT_MISSING` | 输入 PDF / IR / MinerU 目录不存在 | 核对路径，用绝对路径 |
| `E_MINERU_MISSING` | 找不到 MinerU | 告诉用户需安装 MinerU 3.4.5 |
| `E_MINERU_TIMEOUT` | MinerU 超时（已自动重试） | 超长文档可设环境变量 `FILETRANSLATOR_MINERU_TIMEOUT`（秒）后重跑 |
| `E_MINERU_FAILED` | MinerU 解析失败 | 把 message 报给用户；PDF 可能是扫描件或已损坏 |
| `E_ENGINE_MISSING` | 找不到 `pi` | 告诉用户需安装并配置 pi |
| `E_ENGINE_FATAL` | pi 永久性失败（模型名错、没有 key、未认证） | 检查 `--provider` / `--model` 与 pi 的登录状态；**不要盲目重试** |
| `E_RENDER_MISSING` | 找不到 pandoc | 告诉用户需安装 pandoc |
| `E_RENDER_TIMEOUT` / `E_RENDER_FAILED` | pandoc 超时 / 失败 | 产物前的 IR 已保留，可单独重跑 render（§6） |
| `E_CONFIG` | 用户配置文件损坏 | `filetranslator config show` 定位，让用户修 |

**翻译中途失败后续跑：** 已完成阶段的产物会保留，原命令加 `--resume` 重跑即可，
已翻译的槽位不会重译、不会重复计费。

## 6. 只重跑某一段

run 的产物在 `<workdir>/<文档名>/` 下，分 `build/`、`translate/`、`render/` 三个目录。

```bash
filetranslator render "<zh_ir>" -w "<workdir>"                # 只重渲染
filetranslator translate "<ir>" --engine pi -w "<workdir>"    # 只重译
filetranslator build "<abs>/paper.pdf" -w "<workdir>"         # 只解析出 IR
```

**`translate` 子命令的默认引擎是 `echo`（假引擎，原样回填）**，真翻译必须显式写
`--engine pi`；否则会得到一份"译文"全是英文的文档。`run` 的默认引擎才是 `pi`。

## 7. 预期内行为，不是故障

- **参考文献节不翻译**，按设计保留原文。
- **原文已是简体中文**时整体跳过翻译。繁体或日文被误判成简体时，加 `--force-translate`。
- **降级不中断**：图组没认出、某个槽位翻译失败等都会降级并写进 report.md，整篇照常产出。
  `degraded_total > 0` 不等于失败。

## 8. 成本

`pi` 引擎会联网调用模型，产生真实费用。用户明确要求翻译即视为授权；但不要为了"试一下"
反复整篇重跑——出问题优先用 `--resume` 或只重跑某一段。

## 9. 向用户交付

报告：`docx` 与 `md` 的绝对路径、`status`、降级计数（有降级时附 report.md 路径并概括
主要降级类型）、总耗时。不要把整篇译文贴进对话。
