---
name: pm-task-dispatch
version: "1.0.0"
description: "PM task dispatch skill. Triggers when a new task needs to be created and dispatched to another Agent. Workflow: understand task → clarify requirements → analyze and refine → create task document → dispatch via sessions_send → track feedback. Trigger scenarios: (1) Harvey proposes a new task, (2) asks to dispatch a task to a specific Agent, (3) asks how to dispatch a task."
user_invocable: true
---

# PM Task Dispatch

PM 任务派发的标准流程。

## 工作流

```
1. 理解任务 → 2. 需求澄清 → 3. 分析细化 → 4. 创建任务文档 → 5. 派发任务
```

---

## Step 1：理解任务

接收 Harvey 的任务描述，明确：
- **任务目标**：要完成什么？
- **约束条件**：有哪些限制（预算、技术栈、时间等）？
- **期望输出**：结果以什么形式交付？

---

## Step 2：需求澄清

**判断标准——是否需要 brainstorming：**

```
Harvey 给了模糊指令？
  ├── 是 → 必须用 brainstorming skill 澄清
  └── 否，但缺少以下任一信息？
        ├── 任务范围和边界
        ├── 优先级（priority）
        ├── 资源限制（GPU、API key、预算）
        └── 执行 Agent（assignee）
            └── 是 → 向 Harvey 确认后再继续
```

**何时可以跳过 brainstorming：**
- Harvey 指令明确包含"做 X，用 Y agent，约束 Z"
- 任务来自已确认的 roadmap 或 project plan
- 重复性任务格式固定（如 daily article fetch）

---

## Step 3：分析细化

**与 Step 2 的边界区分：**
- Step 2 = 向 Harvey 澄清意图（提问 → 得到确认答案）
- Step 3 = 分析任务本身（不向 Harvey 提问，基于已有信息决策）

**Step 3 内容：**

1. **确定项目**：确认任务属于哪个项目（已有项目填项目名，新项目先命名）
2. **拆分任务**：将任务拆为具体的 subtask
3. **匹配 Agent**：根据任务类型匹配执行 Agent（见 `references/agent-mapping.md`）
4. **确认验收标准**：如何确认任务完成？

---

## Step 4：创建任务文档

详见 `references/task-template.md`

**路径规则：**
- Task 文件夹：`~/Projects/project-management/tasks/<id>/`
- Task 文件：`~/Projects/project-management/tasks/<id>/task.md`
- Issue 文件：`projects/{project}/issues/{open|closed}/<id>-<slug>.md`

---

## Step 5：派发任务

**优化原则：** sessions_send 消息只包含简洁指令，任务详情由目标 Agent 自行读取 Markdown 文件。

```javascript
sessions_send({
  sessionKey: "agent:{target-agent}:discord:channel:{channel-id}",
  message: "📋 新任务派发\n\n" +
    "**任务编号：** {id}\n" +
    "**任务文件夹：** tasks/{id}/\n\n" +
    "请读取 tasks/{id}/task.md，根据文件内容执行任务。\n" +
    "完成后使用 task-close skill 进行收尾。",
  timeoutSeconds: 0    // 必须为 0
})
```

**⚠️ 重要：timeoutSeconds 必须为 0（fire-and-forget）**

**任务文件结构（Agent 读取后执行）：**
- `id` / `project` / `assignee` / `assigner` / `priority` / `status` → frontmatter 元数据
- `主要目标` → 核心目标（必读）
- `关键约束` → 约束条件（必读）
- `工作流` → 分步指引（可选）
- `使用工具` → 可用工具列表（可选）
- `评估标准` → 验收标准（可选）
- `资料管理` → 相关资料（可选）

---

## 错误处理

### sessions_send 失败

```
sessions_send 返回 error？
  ├── 网络问题 → 重试 1 次，间隔 10s
  ├── session 不存在 → 检查 agent-mapping，确认 channel-id 正确
  └── 其他 → 立即向 Harvey 汇报
```

### Agent 无响应

```
派发后超过预期时间无反馈？
  ├── 检查 sessions_history 确认任务状态
  ├── 若 stopReason = "lane wait exceeded" → 目标队列堵塞，向 Harvey 汇报
  └── 若任务卡住超过 30 分钟 → 向 Harvey 汇报阻塞情况
```

### 重复派发

```
收到重复任务指令？
  ├── 检查 tasks/ 目录是否已有相同 id 的任务文件夹
  ├── 已有且 status ≠ done → 跳过派发，告知 Harvey
  └── 已有但 Harvey 要求重新执行 → 更新任务文件后重新派发
```

---

## 负面示例

> **模糊指令 → 直接派发 → 任务失败**

❌ 错误做法：
```
Harvey："研究一下 AI 模型"
→ 直接派给 research-scientist
→ Agent 问："研究什么？哪方面？什么约束？"
→ 任务卡住
```

✅ 正确做法：
```
Harvey："研究一下 AI 模型"
→ Step 2 触发：用 brainstorming 向 Harvey 确认
   "研究 AI 模型——请问：(1) 具体哪类模型？(2) 研究目的是什么（选型/学习/实现）？(3) 有预算或技术栈限制吗？"
→ Harvey 回复："研究本地 STT 模型，用于 Discord 语音转命令，成本敏感"
→ Step 3 分析：任务明确，assignee = research-scientist
→ Step 4 创建任务文档
→ Step 5 派发
```

---

## Reference 文件索引

| 文件 | 内容 |
|------|------|
| `references/task-template.md` | Task 工单格式规范（frontmatter / 正文结构 / 示例） |
| `references/agent-mapping.md` | Agent 通道映射（openclaw/<agent> / channel-id / 职责） |
