# Agent 通道映射

## 当前已登记 Agent

| Agent | openclaw/<agent> | Discord 频道 | Channel ID |
|-------|----------------|-------------|-----------|
| research-scientist | `openclaw/research-scientist` | #research-scientist | `1489128984246751242` |
| coding-master | `openclaw/coding-master` | #coding-master | `1484628751005515886` |
| writing-assistant | `openclaw/writing-assistant` | #writing-assistant | `1482389159636107474` |
| general-affairs | `openclaw/general-affairs` | #general-affair | `1481354036580978688` |

---

## Agent 职责速查

| Agent | 典型任务类型 |
|-------|-------------|
| **research-scientist** | 技术调研、方案研究、竞品分析、架构设计 |
| **coding-master** | 代码开发、功能实现、PR 审查、Git 操作 |
| **writing-assistant** | 文章抓取、翻译、内容整理、文档撰写 |
| **general-affairs** | 日常事务、提醒设置、信息查询、配额监控 |

---

## 通知频道

- **Channel ID：** `1484647806127050753`（#notification）
- **用途：** Agent 完成任务后发送 `task_complete` 通知

---

## sessions_send 标准格式

```javascript
sessions_send({
  sessionKey: "agent:{target-agent}:discord:channel:{channel-id}",
  message: "Task #{id} 开始执行：{标题}\n\n...",
  timeoutSeconds: 0    // 必须为 0
})
```

### 常见错误

| 错误 | 后果 |
|------|------|
| `timeoutSeconds` 非 0 | PM session 等待目标响应时卡住 |
| 发到错误 channel | 目标 Agent 收不到 |
| 通知发到 #product-manager | 回不到原 session |

---

## 任务派发后追踪

1. **通知查询**：去 #notification（1484647806127050753）查 `task_complete`
2. **兜底查询**：`sessions_history({ sessionKey: "agent:{target}:...", limit: 3 })`
3. **状态判断**：
   - `stopReason: stop` = 完成
   - `toolUse` = 进行中
   - `lane wait exceeded` = 目标队列堵塞
