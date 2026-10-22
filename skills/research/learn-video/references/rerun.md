# learn-video — 失败重跑、改模式与换 focus

本文件中的 `vdl rerun` 与 `--force` 重建同样一律后台启动；`<LOGFILE>`、`<URL>`、`<FOCUS>` 等占位符与 SKILL.md「执行命令」一致，进度与终态按 SKILL.md「进度汇报与完成判定」处理。

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

某步骤失败后，用 **DAG 内部名** 重跑。`vdl rerun` 无论 `--reset step` 还是 `--reset downstream` 都会阻塞轮询直到该步骤（或下游）跑完：

```bash
# 仅重跑该步骤
nohup vdl rerun <task_id> <dag_step_name> --reset step > <LOGFILE> 2>&1 &

# 从该步骤级联重跑下游
nohup vdl rerun <task_id> <dag_step_name> --reset downstream > <LOGFILE> 2>&1 &
```

按「进度汇报与完成判定」的方式 tail `<LOGFILE>`：`rerun` 不支持 `--json`，成功时终态是纯文本行 `Done in <n>s`（没有 JSON），失败判定依然是 `Error: Step ... failed`。成功后按 SKILL.md「获取结果」拿最新产物路径。

### 常见错误

**`BAD_ANCHOR_MODE`**：要重跑的步骤不属于当前任务模式的 DAG。
例如：任务以 `transcript` 模式创建，则 `audio`/`video` 步骤不在 DAG 中，无法 rerun。
→ 解决：用新模式 + `--force` 重建任务（见下方「更改任务模式」）。

**`ECONNREFUSED 127.0.0.1:3000`**：后端服务已退出。
`vdl` 主命令会自动启动服务；但 `vdl rerun`/`vdl status` 等子命令在服务不存在时**无法自启**。
→ 解决：仅当用户已明确提供 `<VIDEO_LEARNER_ROOT>`、该目录的 `package.json` 存在且其中的 `npm run agent:serve` 脚本存在时，才手动启动服务，再执行子命令；否则询问用户或停止，不猜测源码根目录：
```bash
cd "<VIDEO_LEARNER_ROOT>" && npm run agent:serve &
# 等服务就绪后再执行 rerun
nohup vdl rerun <task_id> <step> --reset step > <LOGFILE> 2>&1 &
```

---

## 更改任务模式

任务模式创建后不能直接修改。若需要在已完成任务上补跑不同模式的步骤（如为 `transcript` 任务补下载音频），用 `--force` 以新模式重建：

```bash
nohup vdl "<URL>" --focus "<FOCUS>" --mode audio --force --json > <LOGFILE> 2>&1 &
```

由于 task_id 由 URL 决定，返回的仍是同一个任务，但模式更新、对应步骤会重新跑。按「进度汇报与完成判定」的方式处理这次调用。

---

## 重新生成摘要（更换 focus）

两种方式二选一：

**不换 focus**：

```bash
nohup vdl rerun <task_id> summary --reset step > <LOGFILE> 2>&1 &
```

**换 focus**：只调 HTTP API（需服务在运行）。该接口本身会重置并重跑 summary；新 focus 只用于这一次，不写回任务。**不要再接 `vdl rerun`**，否则会用任务里存的旧 focus 覆盖新摘要。

```bash
TOKEN=$(cat /tmp/vl-agent-token)
curl -s -X POST http://127.0.0.1:3000/api/tasks/<task_id>/steps/summary/run \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"focus": "<新关注点>", "reset_scope": "step"}'
```
