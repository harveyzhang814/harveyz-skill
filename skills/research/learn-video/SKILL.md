---
name: learn-video
version: "1.9.3"
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

若未找到，只有在用户已经明确给出 Video-Learner 源码根目录、且其中的 `package.json` 存在时，才可在该目录执行：

```bash
cd "<VIDEO_LEARNER_ROOT>" && npm link
```

未提供可验证的根目录时，询问用户或停止；不得猜测个人项目目录。`vdl` 主命令、`rerun` 与 `result` 使用已发现的 CLI，不要求源码根目录。

---

## 前置：检查统一存储根

先定位当前安装或源码 skill 目录的实际绝对路径并绑定为 `SKILL_DIR`；不得假定维护者仓库位置。运行 `python3 "$SKILL_DIR/scripts/store_config.py" check`。若输出 `MISSING:`，询问用户"抓取产物统一存到哪个目录？（直接回车使用默认：`~/knowledge`）"，将回答展开为绝对路径，写入 `~/.hskill/config.json` 的 `knowledgeRoot` 字段（文件不存在则新建；若已存在 `skillDir` 等其他字段，只增改 `knowledgeRoot`，不覆盖）。**默认值刻意不选 `~/Documents/...`、`~/Desktop/...`、`~/Downloads/...`**——这几个目录受 macOS TCC 隐私保护，无 Full Disk Access 的 agent 执行环境写入会被拒绝；`$HOME` 下的普通目录（如 `~/knowledge`）不受此限制。

**再核对下游是否同步。** vdl、scholia 都直接读写统一存储根，运行 `python3 "$SKILL_DIR/scripts/store_config.py" check-downstream` 核对两者当前配置是否等于 `knowledgeRoot` 推出的期望值：

```bash
python3 "$SKILL_DIR/scripts/store_config.py" check-downstream
```

输出 `DRIFT:` 时，把对应的 `fix:` 命令原样报告给用户，由用户自己决定要不要执行——**不要代替用户改 vdl/scholia 的配置文件**，那是另一个程序的配置。输出 `SKIP:` 表示该下游工具未安装，忽略即可。

**运行中写入失败时的处理。** 若上述核对都通过、但实际归档/写入时仍然失败（权限不足、目录只读等），必须原样把错误报告给用户并停下来，禁止擅自把 `knowledgeRoot` 或 vdl 的 `WORK_ROOT` 改指到别的路径来"绕过"。这两个值是多个 skill 共用的配置，擅自改会让产物静默散落到不同目录，用户毫不知情，且难以事后排查。

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

运行前必须得到用户的模式选择。若消息已明确要文字、音频、视频或全部，直接映射到 `transcript`、`audio`、`media` 或 `full`；否则用当前宿主可用的提问方式列出以下四项并等待回答。不得因结构化提问工具不可用而默选。

| 选项 | `--mode` | 说明 |
|------|----------|------|
| 仅转录 + 摘要（最快） | `transcript` | 只下载字幕/转录，生成文章和摘要，无音视频文件 |
| 含音频文件 | `audio` | 在 transcript 基础上保留 `.m4a` 音频 |
| 含视频文件 | `media` | 在 transcript 基础上保留 `.mp4` 视频 |
| 音频 + 视频都要 | `full` | 保留音频和视频文件 |

Claude Code 适配示例：可用 `AskUserQuestion` 展示四项；其他宿主使用其可用的结构化提问能力或普通对话等待用户回答。

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

**本 skill（含 `references/rerun.md`）中所有 `vdl` 主命令、`vdl rerun` 与 `--force` 重建一律后台启动**（前台调用会被宿主超时打断，拿不到终态）。

启动前先确认当前宿主能可靠启动并追踪长期任务，且可持续读取 `<LOGFILE>` 至终态。若不能可靠启动并追踪长期任务，启动前向用户说明此限制并停止；不得启动一个无法收尾的孤儿任务。

```bash
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
  {"task_id":"...","elapsed":812,"transcript":"work/.../original_zh.md","article":"work/.../article.md","summary":"work/.../summary.md"}
  ```
  直接从这行 JSON 取 `transcript`/`article`/`summary` 三个路径，跳到「向用户报告」——不需要再手工拼 `work/<task_id>/...` 路径。
- **失败**：日志中出现一行 `Error: Step <step_display_name> failed: <原因>`（stderr 已通过 `2>&1` 合并进日志）。提取步骤名和原因，读取 `references/rerun.md` 按「处理步骤失败」处理。

---

## 失败重跑、改模式与换 focus

步骤失败、需要为已有任务改模式、或用户要换 focus 重新生成摘要时，读取 `references/rerun.md`。

---

## 获取结果

仅在 `rerun` 成功后或事后重新查询时使用：

```bash
# 摘要（TL;DR + Outline + Key Points + Action Items）
vdl result <task_id> --type summary

# 结构化文章
vdl result <task_id> --type article
```

**产物路径**：

```
<knowledgeRoot>/videos/work/<task_id>/
├── meta.json                 # vdl 写入（fetch 步骤完成时）
├── media/                    # vdl 下载的音视频，体积大
├── transcript/
│   ├── original_zh.md        # 带时间戳逐字稿（语言后缀随视频而定）
│   └── original_en.md
└── writing/
    ├── article.md            # 结构化文章
    └── summary.md            # TL;DR + Outline + Key Points
```

---

## 归档到统一存储根

vdl 的产物已经落在统一存储根里了（`WORK_ROOT` 指向 `<knowledgeRoot>/videos`），meta.json 也已经由 vdl 自己写好——本 skill 不再写它，只校验：

```bash
TASK_ID="<task_id>" python3 "$SKILL_DIR/scripts/archive.py"
```

成功输出两行 `VIDEO_DIR: <path>` 和 `META_PATH: <path>`。**若报错说缺统一存储契约必填字段**（`source_url`/`title`/`fetched_at`），说明 vdl 那次没有把任务跑到 `completed`，不要试图在这里补字段——回去确认 vdl 那边的任务状态，或联系维护者核对 vdl 版本。

校验通过后重建 creator 索引：

```bash
python3 "$SKILL_DIR/scripts/build_creator_index.py" build
```

---

## 向用户报告

当「进度汇报与完成判定」判定任务成功后，立即执行，不要等用户追问：

1. 展示 **summary.md** 全文
2. 告知产物路径（「归档到统一存储根」步骤打印的 `VIDEO_DIR` 路径，即 `<knowledgeRoot>/videos/work/<task_id>/`）
3. 询问是否需要：查看完整文章、转录稿，或用不同 focus 重新生成摘要

---

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/store_config.py` | 读共享 `knowledgeRoot`（`~/.hskill/config.json`），四个入范围 skill 各存一份内容相同的副本 |
| `scripts/archive.py` | 校验 vdl 已写好的 `meta.json` 是否满足统一存储契约（`source_url`/`title`/`fetched_at`）；不写文件，不足则报错退出 |
| `scripts/build_creator_index.py` | 全量重算 `<knowledgeRoot>/videos/creators.json`（`build`），或核对索引是否与磁盘实体数一致（`check`）——不读 `registry.json` |
