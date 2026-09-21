---
name: describe-node
description: Auto-generate a title and description for the Agent Canvas node you are running in — use it to summarize what the session is doing, name the node, or update its title/description; only usable inside an Agent Canvas node.
user_invocable: true
version: "1.0.2"
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
- 成功时 stdout 返回 `{nodeId, title, description, taskType?, specUsed}`，退出码 0；
  失败时错误写 stderr、退出码非 0。
- 要跑一次模型调用，通常 5–15 秒，属正常。

## 什么时候值得调

- **节点标题还是默认的类型名**（`Claude Code` / `Pi Agent` / `Shell`）时——这时画布上
  同类节点长得一模一样，无法区分，最该起名。
- 刚写完或刚确定一份 spec 之后。
- 一个阶段性任务完成、会话主题已经明确之后。
- 用户明确要求"给这个节点起个名 / 写个描述 / 总结一下这个节点在做什么"。

## 什么时候不要调

- 会话刚开始、还没有任何实质内容时——没东西可摘，只会得到空泛的标题。
- 用户手动改过标题、而这一轮并没有要求重新生成时——**本命令会覆盖标题**。
- 同一节点上一次调用还没返回时——会直接报"正在进行中"，等它完成即可。

## 边界

本命令**只产出 title/description/taskType**，不再撰写需求。若材料能清楚判断任务类型
（执行/评估/分析/计划），也会一并写入并覆盖已有值——taskType 不做"仅未设置时写"的保护，
即使是人工在面板下拉框里手动设置的值也会被覆盖。

需要把当前会话在实现的需求立项成一个节点，用 `capture-requirement` skill，不是本命令。
