---
name: task-close
description: 任务收尾技能。当 Agent 完成接受的任务后自触发，执行任务验收、总结、文档归档和问题记录。触发条件：Agent 已实际完成任务，需要进行收尾工作时使用。
---

# Task Acceptance - 任务收尾技能

当 Agent 完成接受的任务后，自执行收尾流程。

## 路径约定

```
任务文件夹：    ~/Projects/project-management/tasks/<id>/
任务文件：      ~/Projects/project-management/tasks/<id>/task.md         （PM 写，Agent 只更新 frontmatter）
完成报告：      ~/Projects/project-management/tasks/<id>/completion-report.md  （Agent 写）
问题记录：      ~/Projects/project-management/tasks/<id>/lessons-learned.md    （Agent 写，可选）
```

## 触发条件

Agent 已实际完成任务，满足以下任一条件：
- 任务所有子项已完成
- 主要目标已实现
- 接收到 Harvey 或 PM 的收尾指令

## 工作流

```
1. 任务验收 → 2. 任务总结 → 3. 文档归档 → 4. 问题记录 → 5. 发送完成通知
```

---

## Step 1：任务验收

**核心原则：必须实际执行并验证，不能仅凭印象判断。**

### 读取任务文件

读取任务文件（`~/Projects/project-management/tasks/<id>/task.md`）。

**文件不存在时：** 停止收尾流程，向 Harvey 或 PM 报告：
```
任务文件 tasks/<id>/task.md 不存在，无法执行收尾。
请确认任务编号是否正确，或由 PM 补充任务文件后重试。
```

### 生成评估标准（如任务文件无评估标准章节）

Agent 根据任务主要目标，设计合理的评估标准：

```markdown
## 评估标准

- [ ] <评估项1> - 对应主要目标的第1个子目标
- [ ] <评估项2> - 对应主要目标的第2个子目标
- [ ] <评估项3> - 关键约束的满足情况
```

设计原则：
- 每个主要目标对应至少 1 个评估项
- 每个关键约束对应至少 1 个评估项
- 评估项可验证、可判定通过/不通过

### 逐一验证

- `[ ]` 子项 → 标记为 `[x]` 并说明验证方法和结果
- 无法验证的子项 → 评估：1. 是否合理（验证方法本身是否正确）2. 是否代表任务失败（未验证 ≠ 未完成，如因外部依赖缺失则不算失败）

### 输出验收报告

创建 `completion-report.md`，写入验收报告（详见 [output-templates.md](references/output-templates.md)）。

---

## Step 2：任务总结

在 `completion-report.md` 中追加任务总结章节（详见 [output-templates.md](references/output-templates.md)）。

更新 `task.md` frontmatter（仅此两个字段，其他内容不动）：

```yaml
---
status: done
completed: YYYY-MM-DD
---
```

---

## Step 3：文档归档

### 评估标准

文档满足以下任一条件时，必须归档：
- 是任务产出的核心交付物
- 对后续工作有参考价值
- 包含关键决策或配置

### 归档流程

1. 扫描任务过程中产生的文档
2. 评估每份文档的价值
3. 必要文档保存到任务文件夹（`tasks/<id>/`）
4. 在 `completion-report.md` 中更新 Reference 章节（总索引表，包含所有任务相关文档）

---

## Step 4：问题记录

判断是否有内容可记录（遇到问题、做了关键决策、有经验教训）：

- **有内容** → 创建 `~/Projects/project-management/tasks/<id>/lessons-learned.md`，记录实际有价值的内容，跳过空表格（详见 [output-templates.md](references/output-templates.md)）。路径同步更新到 `completion-report.md` Reference 章节。
- **没有内容** → 跳过，不创建文件。

---

## Step 5：发送完成通知

收尾全部完成后，在 Agent 自己绑定的 Discord channel 发送任务完成消息：

```
任务 <id> 已完成。
任务文件：tasks/<id>/task.md
```

---

## 输出清单

完成收尾后，任务文件夹应包含：

| 文件 | 内容 | 必须 |
|------|------|------|
| `task.md` | frontmatter 更新为 `status: done`、`completed: YYYY-MM-DD` | ✅ |
| `completion-report.md` | 验收报告 + 任务总结 + Reference 章节 | ✅ |
| `lessons-learned.md` | 问题记录（有内容才创建） | 可选 |

---

## 注意事项

1. **验收必须实际执行**——禁止仅凭印象打勾，必须说明验证方法
2. **无评估标准时自行设计**——基于主要目标和关键约束设计可验证的评估项
3. **任务文件不存在时自创建**——根据接受的任务信息补全主要结构
4. **无法验证≠任务失败**——因外部依赖缺失导致无法验证的子项，如验证方法本身合理，则不算任务失败
5. **如实记录**——问题就是问题，不要美化，经验就是经验，不要夸张
6. **文档路径要准确**——方便后续快速定位
