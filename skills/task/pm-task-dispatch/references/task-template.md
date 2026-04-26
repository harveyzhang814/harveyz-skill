# Task 工单标准

> 参考：`methodology/multiagent-task/SPEC.md`

## 目录结构

每个任务创建独立文件夹，文件夹以任务号命名：

```
tasks/
└── <id>/
    └── task.md
```

示例：`tasks/T001/task.md`

id 全局唯一，全局递增。

---

## Frontmatter 字段

| 字段 | 格式 | 必填 | 说明 |
|------|------|------|------|
| `id` | `T001` | ✅ | 全局唯一编号 |
| `project` | 项目名 | ✅ | 对应 projects 下的项目 |
| `assignee` | `openclaw/<agent>` 或 `<外部AI>` | ✅ | 派发目标 |
| `assigner` | `openclaw/<agent>` | ✅ | 派发者 |
| `priority` | low / medium / high / xhigh | ✅ | |
| `status` | open / done | ✅ | |

### assignee 格式规范

- **OpenClaw 内部 Agent**：`openclaw/<agent>`，如 `openclaw/coding-master`、`openclaw/writing-assistant`
- **外部 AI 工具**：直接写工具名，如 `claude`、`cursor`

### assigner 格式规范

- 仅限 OpenClaw 内部 Agent：`openclaw/<agent>`

### status 流转

```
open → done
```

---

## 正文章节

### 主要目标（必填）

agent 要完成的核心目标。

### 关键约束（必填）

agent 必须遵守的约束条件。

### 工作流（可选）

agent 可参考的工作流步骤。

### 使用工具（可选）

agent 可以使用的工具列表。

### 评估标准（可选）

评估任务完成质量的标准，格式为 `[ ] 子项`。

### 资料管理（可选）

相关的文档或资料路径。

---

## 完整示例

```yaml
---
id: T003
project: openclaw-voice-commands
assignee: openclaw/research-scientist
assigner: openclaw/product-manager
priority: high
status: open
---

## 主要目标

研究将 Discord 语音频道音频实时转换为 OpenClaw 可执行命令的完整方案，**仅评估本地 STT 方案**。

## 关键约束

1. 不考虑云原生 STT（Deepgram、OpenAI Whisper API 等）
2. 仅评估本地转录模型
3. 延迟目标 < 3s（端到端）

## 工作流

1. 语音采集方案调研（Discord Bot / API / Webhook）
2. 本地 STT 模型选型对比（faster-whisper / whisper.cpp）
3. 实时流式处理可行性分析
4. 量化版本性能评估（INT8 / INT4）
5. 技术架构设计
6. 风险与可行性评估

## 使用工具

- web_search / web_fetch
- 本地 faster-whisper 测试
- OpenClaw sessions_send

## 评估标准

- [ ] 提供至少 2 种可对比的技术方案
- [ ] 每种方案包含完整链路（采集→识别→理解→执行）
- [ ] 给出明确推荐结论
- [ ] 量化延迟和资源消耗

## 资料管理

- 任务目录：`~/Projects/project-management/tasks/T003/`
- 项目目录：`~/Projects/project-management/projects/openclaw-voice-commands/`
- 灵感记录：`memory/2026-04-04.md`
```

---

## 与 Issue 的区别

| 维度 | Task 工单 | Issue |
|------|-----------|-------|
| 位置 | `tasks/` | `projects/{project}/issues/` |
| 用途 | 任务派发与执行追踪 | 项目问题追踪 |
| 派发 | PM → Agent | 任意创建 |
| 状态 | open → in_progress → done | open → closed |

---

## Task vs Issue vs Learn

- **Task**：PM 派发给其他 Agent 的任务工单
- **Issue**：项目中需要追踪的问题（bug/需求/里程碑）
- **Learn**：需要深入学习的独立主题
