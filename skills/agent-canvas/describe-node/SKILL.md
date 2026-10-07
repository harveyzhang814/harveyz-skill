---
name: describe-node
description: Auto-generate a title and description for the Agent Canvas node you are running in — use it to summarize what the session is doing, name the node, or update its title/description; only usable inside an Agent Canvas node.
user_invocable: true
version: "1.1.0"
---

# 为当前节点生成标题与描述（describe-node）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

## 怎么调

```
agent-canvas-ctl summarize-self [--spec <规格文档绝对路径>]
```

**不需要传节点 id**——它按祖先进程链反查你所在的节点，"谁调用就摘要谁"。

- `--spec` 指定据以撰写的规格文档，**必须是绝对路径**。相对路径不报错、退出码照样是
  0，只是读不到文件，`specUsed` 静默返回 null——和"没找到"长得一模一样。它是在主进程
  里按主进程的 cwd 解析的，不是你会话的当前目录，所以"从我这儿看是对的"不作数。
- 不传 `--spec` 时会从本会话记录里自动发现你写过或读过的 `docs/superpowers/specs/*.md`，
  按 Write > Edit > Read 取最后一次；**只有 Read 命中、且读过不止一份不同的 spec 时，
  自动发现会直接放弃**（归属不明，它不猜）。会话里读过别人的 spec 就属于这种情况。
  `specUsed` 为 null 就表示没用上，知道该用哪份就补传 `--spec`。
- **命令受理即返回**：stdout 返回 `{nodeId, status: "submitted", specUsed}`，退出码 0，
  表示**已受理**，不是已写回。模型调用（通常 5–15 秒，上限约 90 秒）和写回在主进程后台
  完成，**不要等它**，接着做别的事。返回里不再有 `title` / `description`。
  受理阶段的前置失败（节点没有会话、没配置摘要模型、上一次还在进行中等）仍然同步报错：
  错误写 stderr、退出码非 0。
- **旧版 App 兼容**：如果返回里直接带着 `title` / `description` 而没有 `status`，说明
  对端是旧版（同步写回），此时已经写完，不需要查状态。

## 怎么确认写回结果

一般不用确认。只有需要保证标题已落地时才查——典型是**收尾、汇报之前**：

```
agent-canvas-ctl get-node <nodeId>      # nodeId 取自上面返回的 nodeId
```

看返回里的 `backgroundJob`：

| `status` | 含义 | 怎么办 |
|---|---|---|
| `running` | 后台还在跑 | 先做别的，稍后再查 |
| `succeeded` | 已写回，节点当前的 `title` / `description` 就是结果 | 完成 |
| `failed` | 没写成，`error` 写明原因 | 如实汇报，不要静默重试 |

- `error` 以「摘要失败：」开头表示模型调用或校验失败；以「写回…失败（已写回：…）：」开头
  表示写回中途失败，括号里是已经写进去的部分（比如标题已改、描述没改）。失败时用户的
  通知中心也会出现一条 error 通知。
- **`running` 从 `startedAt` 起超过 120 秒，按丢失处理**，不要再等——后台任务可能因为窗口
  关闭、节点被删而没能写回终态。
- **没有 `backgroundJob` ≠ 成功。** App 重启或窗口重开会清掉它，此时分不清是没跑过还是
  丢了。以节点当前的 `title` 为准：还是默认类型名就是没写成。

## 什么时候值得调

- **节点标题还是默认的类型名**（`Claude Code` / `Pi Agent` / `Shell`）时——这时画布上
  同类节点长得一模一样，无法区分，最该起名。
- 刚写完或刚确定一份 spec 之后。
- 一个阶段性任务完成、会话主题已经明确之后。
- 用户明确要求"给这个节点起个名 / 写个描述 / 总结一下这个节点在做什么"。

## 什么时候不要调

- 会话刚开始、还没有任何实质内容时——没东西可摘，只会得到空泛的标题。
- 用户手动改过标题、而这一轮并没有要求重新生成时——**本命令会覆盖标题**。写回发生在
  受理之后的几秒到十几秒里，这段时间内用户手改的标题同样会被覆盖。
- 同一节点上一次调用还没完成时（`backgroundJob.status` 为 `running`）——会直接报
  "正在进行中"。受理后立刻再调一次也属于这种情况；等它变成 `succeeded` 或 `failed`
  再调。

## 边界

本命令**只产出 title/description/taskType**，不再撰写需求。若材料能清楚判断任务类型
（执行/评估/分析/计划），也会一并写入并覆盖已有值——taskType 不做"仅未设置时写"的保护，
即使是人工在面板下拉框里手动设置的值也会被覆盖。

需要把当前会话在实现的需求立项成一个节点，用 `capture-requirement` skill，不是本命令。
