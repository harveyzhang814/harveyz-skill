---
name: youtube-learner
version: "1.3.0"
description: "Process a YouTube video using the vdl CLI: transcribe, generate article and summary. Triggers when the user provides a YouTube URL and wants to learn from, summarize, transcribe, or extract key points from the video — e.g. 'help me understand this talk', 'summarize this YouTube video', 'get the transcript', 'process this video', 'summarize it'."
user_invocable: true
---

# YouTube Learner

使用本地 `vdl` CLI 处理 YouTube 视频，产出转录稿、结构化文章与摘要。

---

## 前置：确认 vdl 可用

```bash
which vdl
```

若未找到，提示用户先安装：

```bash
cd /Users/harveyzhang96/Projects/Video-Learner
npm link
```

---

## 参数收集

在运行前确认以下信息：

| 参数 | 说明 | 处理方式 |
|------|------|---------|
| `url` | YouTube 链接 | 从用户消息提取 |
| `--focus` | 关注点（影响摘要内容） | 若用户未提供，主动询问："你最想从这个视频中了解什么？（例如：核心论点、技术细节、行动项）" |
| `--mode` | 处理模式 | **必须询问用户**（见下方「模式选择」） |
| `--lang` | 输出语言 | 默认 `zh-CN`；若用户用英文交流则用 `en` |

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

```bash
cd /Users/harveyzhang96/Projects/Video-Learner && \
vdl "<URL>" --focus "<FOCUS>" --mode <MODE> --lang zh-CN
```

`vdl` 会自动：
- 启动后端服务（若未运行）
- 实时显示各步骤进度
- 完成后打印产物路径

---

## 步骤名对照表

`vdl rerun` 使用 **DAG 内部名**，不是进度显示名：

| 进度显示名 | `vdl rerun` 用这个 |
|-----------|-------------------|
| `fetch_info` | `fetch` |
| `download_subs` | `subs` |
| `convert_vtt_md` | `vtt2md` |
| `generate_article` | `article` |
| `generate_summary` | `summary` |
| `download_video` | `video` |
| `download_audio` | `audio` |
| `asr_transcribe` | `asr` |
| `convert_md_vtt` | `md2vtt` |

---

## 处理步骤失败

某步骤失败后，用 **DAG 内部名** 重跑：

```bash
# 仅重跑该步骤
vdl rerun <task_id> <dag_step_name> --reset step

# 从该步骤级联重跑下游
vdl rerun <task_id> <dag_step_name> --reset downstream
```

> `--reset downstream` 返回 202 后自动切换为轮询等待，无需额外操作。

### 常见错误

**`BAD_ANCHOR_MODE`**：要重跑的步骤不属于当前任务模式的 DAG。
例如：任务以 `transcript` 模式创建，则 `audio`/`video` 步骤不在 DAG 中，无法 rerun。
→ 解决：用新模式 + `--force` 重建任务（见下方「更改任务模式」）。

**`ECONNREFUSED 127.0.0.1:3000`**：后端服务已退出。
`vdl` 主命令会自动启动服务；但 `vdl rerun`/`vdl status` 等子命令在服务不存在时**无法自启**。
→ 解决：先手动启动服务，再执行子命令：
```bash
cd /Users/harveyzhang96/Projects/Video-Learner
npm run agent:serve &
# 等服务就绪后再执行 rerun
vdl rerun <task_id> <step> --reset step
```

---

## 更改任务模式

任务模式创建后不能直接修改。若需要在已完成任务上补跑不同模式的步骤（如为 `transcript` 任务补下载音频），用 `--force` 以新模式重建：

```bash
vdl "<URL>" --focus "<FOCUS>" --mode audio --force
```

由于 task_id 由 URL 决定，返回的仍是同一个任务，但模式更新、对应步骤会重新跑。

---

## 重新生成摘要（更换 focus）

```bash
vdl rerun <task_id> summary --reset step
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

```bash
cd /Users/harveyzhang96/Projects/Video-Learner

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

1. 展示 **summary.md** 全文
2. 告知产物路径 `work/<task_id>/writing/`
3. 询问是否需要：查看完整文章、转录稿，或用不同 focus 重新生成摘要
