---
name: learn-video
version: "1.6.1"
description: "Process a YouTube or Bilibili video using the vdl CLI: transcribe, generate article and summary. Triggers when the user provides a YouTube or Bilibili URL and wants to learn from, summarize, transcribe, or extract key points from the video — e.g. 'help me understand this talk', 'summarize this YouTube video', 'summarize this Bilibili video', 'get the transcript', 'process this video', 'summarize it'."
user_invocable: true
---

# Video Learner

使用本地 `vdl` CLI 处理 YouTube / Bilibili 视频，产出转录稿、结构化文章与摘要。

---

## 前置：确认 vdl 可用

```bash
which vdl
```

若未找到，提示用户先安装：

```bash
cd "$HOME/Projects/Video-Learner"
npm link
```

---

## 参数收集

在运行前确认以下信息：

| 参数 | 说明 | 处理方式 |
|------|------|---------|
| `url` | YouTube 或 Bilibili 链接 | 从用户消息提取 |
| `--focus` | 关注点（影响摘要内容） | 若用户未提供，主动询问："你最想从这个视频中了解什么？（例如：核心论点、技术细节、行动项）" |
| `--mode` | 处理模式 | **必须询问用户**（见下方「模式选择」） |
| `--lang` | 输出语言 | 默认 `zh-CN`；若用户用英文交流则用 `en`；必须将解析结果赋给 `<LANG>` 占位符 |

### 模式选择

**每次都必须询问用户选择模式**，用 `AskUserQuestion` 工具展示以下选项：

| 选项 | `--mode` | 说明 |
|------|----------|------|
| 仅转录 + 摘要（最快） | `transcript` | 只下载字幕/转录，生成文章和摘要，无音视频文件 |
| 含音频文件 | `audio` | 在 transcript 基础上保留 `.m4a` 音频 |
| 含视频文件 | `media` | 在 transcript 基础上保留 `.mp4` 视频 |
| 音频 + 视频都要 | `full` | 保留音频和视频文件 |

若用户消息中已明确提到"要视频"、"要音频"、"只要文字"等信号，可直接推断模式，无需再问。

### 超长视频检测

根据用户描述自动加超时参数：

| 用户信号 | 参数 |
|---------|------|
| "讲座"、"会议"、"播客"、"1–3 小时"、"long mode" | `--long` |
| "超长"、"全天课程"、"3 小时以上" | `--ultra-long` |
| 普通视频 | 不加 |

---

## 执行命令

将以下占位符全部替换后再执行：

| 占位符 | 替换为 |
|--------|--------|
| `<URL>` | YouTube 或 Bilibili 链接 |
| `<FOCUS>` | 用户填写的关注点 |
| `<MODE>` | `transcript` / `audio` / `media` / `full` |
| `<LANG>` | `zh-CN`（中文对话）或 `en`（英文对话） |
| `<LOGFILE>` | 本次任务专用日志文件路径，如 `/tmp/vdl-<时间戳或URL摘要>.log`，避免和其他任务混用同一个文件 |

**必须后台启动，禁止前台阻塞调用。** 视频处理可能长达数小时（见「超长视频检测」），前台 Bash 调用会被运行环境的超时机制打断——任务本身在后端仍会继续跑，但 agent 拿到的是超时错误而不是真实结果，也就无法感知进度或在完成后向用户报告。

```bash
cd "$HOME/Projects/Video-Learner" && \
nohup vdl "<URL>" --focus "<FOCUS>" --mode <MODE> --lang <LANG> --json > <LOGFILE> 2>&1 &
```

启动和日志落盘之间可能有极短延迟，读取 `<LOGFILE>` 第一行拿 `task_id`（格式 `Task: <task_id>`，vdl 在真正开始跑步骤之前就会打印这一行）时不要只读一次就判定失败，读到空内容时短暂重试几次：

```bash
TASKLINE=""
for i in 1 2 3 4 5 6 7 8 9 10; do
  TASKLINE=$(sed -n '1p' "<LOGFILE>")
  [ -n "$TASKLINE" ] && break
  sleep 0.3
done
echo "$TASKLINE"
```

`vdl` 在输出被重定向到文件（非交互模式）时，每个步骤状态变化都会单独打一行日志：`[<step_display_name>] <status> (<Ns>)`；运行中的步骤还会有进度行 `[<step_display_name>] running (<Ns>) — <percent>% ...`。这些日志行就是后续「进度汇报」和「完成判定」的唯一依据。

---

## 进度汇报与完成判定

任务运行期间，定期查看 `<LOGFILE>` 相对上次已经看过的新增内容，**按 DAG 步骤颗粒度**向用户转述——每当日志里出现新的 `[<step>] done` 或 `[<step>] failed` 行，转述一条简短状态（如"第 3/9 步：转录完成"）；带百分比/速度的运行中进度行不用逐条转述，避免刷屏。

轮询节奏由当前运行环境自己的机制实现，不是本文档要规定的内容：
- 在 Claude Code 里，用 `Monitor` 的 until-loop 去等待终态出现，不要手写 `sleep` 重试循环。
- 换到其他 agent 平台，用该平台自己的"后台任务 + 定期检查"机制实现同样的等待逻辑即可，下面的判定条件不需要变。

判定终态只看 `<LOGFILE>` 里出现的文本内容，不依赖任何"进程退出自动通知"之类的运行时特性（这类机制不是所有平台都有）：

- **成功**：日志中出现一行以 `{"task_id"` 开头的 JSON（因为启动命令带了 `--json`），例如：
  ```
  {"task_id":"...","elapsed":812,"transcript":"work/.../original.md","article":"work/.../article.md","summary":"work/.../summary.md"}
  ```
  直接从这行 JSON 取 `transcript`/`article`/`summary` 三个路径，跳到「向用户报告」——不需要再手工拼 `work/<task_id>/...` 路径。
- **失败**：日志中出现一行 `Error: Step <step_display_name> failed: <原因>`（stderr 已通过 `2>&1` 合并进日志）。提取步骤名和原因，跳到「处理步骤失败」。

---

## 步骤名对照表

`vdl rerun` 使用 **DAG 内部名**，不是进度显示名（日志里 `[...]` 方括号中打印的是进度显示名）：

| 进度显示名 | `vdl rerun` 用这个 |
|-----------|-------------------|
| `fetch_info` | `fetch` |
| `download_subs` | `subs` |
| `convert_vtt_md` | `vtt2md` |
| `translate` | `translate` |
| `convert_md_vtt` | `md2vtt` |
| `generate_article` | `article` |
| `generate_summary` | `summary` |
| `download_video` | `video` |
| `download_audio` | `audio` |
| `asr_transcribe` | `asr` |

---

## 处理步骤失败

某步骤失败后，用 **DAG 内部名** 重跑。`vdl rerun` 无论 `--reset step` 还是 `--reset downstream` 都会阻塞轮询直到该步骤（或下游）跑完，同样**必须后台启动**，不要前台阻塞调用：

```bash
# 仅重跑该步骤
nohup vdl rerun <task_id> <dag_step_name> --reset step > <LOGFILE> 2>&1 &

# 从该步骤级联重跑下游
nohup vdl rerun <task_id> <dag_step_name> --reset downstream > <LOGFILE> 2>&1 &
```

按「进度汇报与完成判定」的方式 tail `<LOGFILE>`：`rerun` 不支持 `--json`，成功时终态是纯文本行 `Done in <n>s`（没有 JSON），失败判定依然是 `Error: Step ... failed`。成功后执行「获取结果」拿最新产物路径。

### 常见错误

**`BAD_ANCHOR_MODE`**：要重跑的步骤不属于当前任务模式的 DAG。
例如：任务以 `transcript` 模式创建，则 `audio`/`video` 步骤不在 DAG 中，无法 rerun。
→ 解决：用新模式 + `--force` 重建任务（见下方「更改任务模式」）。

**`ECONNREFUSED 127.0.0.1:3000`**：后端服务已退出。
`vdl` 主命令会自动启动服务；但 `vdl rerun`/`vdl status` 等子命令在服务不存在时**无法自启**。
→ 解决：先手动启动服务，再执行子命令：
```bash
cd "$HOME/Projects/Video-Learner"
npm run agent:serve &
# 等服务就绪后再执行 rerun
nohup vdl rerun <task_id> <step> --reset step > <LOGFILE> 2>&1 &
```

---

## 更改任务模式

任务模式创建后不能直接修改。若需要在已完成任务上补跑不同模式的步骤（如为 `transcript` 任务补下载音频），用 `--force` 以新模式重建，同样后台启动：

```bash
cd "$HOME/Projects/Video-Learner" && \
nohup vdl "<URL>" --focus "<FOCUS>" --mode audio --force --json > <LOGFILE> 2>&1 &
```

由于 task_id 由 URL 决定，返回的仍是同一个任务，但模式更新、对应步骤会重新跑。按「进度汇报与完成判定」的方式处理这次调用。

---

## 重新生成摘要（更换 focus）

```bash
nohup vdl rerun <task_id> summary --reset step > <LOGFILE> 2>&1 &
```

运行前可通过 HTTP API 更新 focus（需服务在运行）：

```bash
TOKEN=$(cat /tmp/vl-agent-token)
curl -s -X POST http://127.0.0.1:3000/api/tasks/<task_id>/steps/summary/run \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"focus": "<新关注点>", "reset_scope": "step"}'
```

---

## 获取结果

首次运行成功时，产物路径已经在「进度汇报与完成判定」里从终态 JSON 拿到了，不需要再跑下面的命令。以下命令用于事后重新查询，或 `rerun`（不产出 JSON）成功后刷新结果：

```bash
cd "$HOME/Projects/Video-Learner"

# 摘要（TL;DR + Outline + Key Points + Action Items）
vdl result <task_id> --type summary

# 结构化文章
vdl result <task_id> --type article
```

**产物路径**：

```
work/<task_id>/
├── transcript/original.md   # 带时间戳逐字稿
└── writing/
    ├── article.md            # 结构化文章
    └── summary.md            # TL;DR + Outline + Key Points
```

---

## 向用户报告

当「进度汇报与完成判定」判定任务成功后，立即执行，不要等用户追问：

1. 展示 **summary.md** 全文
2. 告知产物路径（成功 JSON 里的 `transcript`/`article`/`summary` 三个字段，或「获取结果」里的固定路径）
3. 询问是否需要：查看完整文章、转录稿，或用不同 focus 重新生成摘要
