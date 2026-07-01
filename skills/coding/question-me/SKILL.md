---
name: question-me
description: "Pre-task clarification skill — clarifies ambiguous or complex tasks before execution through structured Q&A with a live decision tree. One question at a time, each with a recommended answer, in decision-dependency order. Triggers: '/question-me', 'help me clarify this', 'question me before starting', 'let's define this first'. Claude auto-triggers when detecting ambiguous or complex requests (multiple conflicting goals, vague keywords like 'optimize/refactor/clean up', missing success criteria, unstated context assumptions)."
user_invocable: true
version: "1.0.0"
---

# question-me — 执行前指令澄清

在开始执行前，通过结构化问答帮助用户澄清指令、对齐预期。参考 grill-me 风格：一次一问、每问附推荐答案、按决策依赖顺序推进。

---

## 触发条件

**主动调用：** 用户输入 `/question-me [任务描述]`，直接进入流程。

**自动提议（等用户确认 y/n）：**
- 请求涉及多个可能互相矛盾的目标
- 关键词模糊："优化一下"、"整理"、"重构"、"改改"
- 缺少明确的成功标准或截止范围
- 任务依赖未指明的上下文假设

**不触发：** 简单明确的指令（"运行测试"、"读这个文件"、"git status"）。

---

## 执行步骤

### Step 0 — 自查

在问用户之前，先：
1. 读取任务中提到的文件/目录，推断上下文
2. 查 `git status`、近期 commit，了解当前进展
3. 对能从代码/文档直接确认的问题，自行解答——不占用用户的问答配额

自查结束后简短说明：

```
已了解：[X、Y、Z]
仍不确定：[A、B]
开始澄清...
```

---

### Step 1 — 意图校准（固定 3 问）

每问一次，等用户回答后再问下一问。每问附推荐答案。

**Q1 — 目标：** 这件事做完，最核心的变化是什么？
**Q2 — 成功标准：** 怎么判断做对了？（可测量的验收条件）
**Q3 — 范围边界：** 明确不做什么，或哪些东西不能动？

Step 1 全部回答后：
1. 初始化决策树（格式见下节）
2. 调用渲染器（首次加 `--open`）：
   ```bash
   echo '<决策树文本>' | python3 SKILL_DIR/scripts/render_tree.py /tmp/question-me-tree.html --open
   ```
3. 进入 Step 2。

---

### Step 2 — 决策树格式

**内部格式（每节点一行，平铺列出）：**

```
[label:status]  id=XX  [dep=YY]  节点文本
```

字段规则：
- `status`: `done` / `open` / `infer` / `skip`
- `id`: 全树唯一短 ID（2–3 字母），更新引用稳定
- `dep=YY`: 可选，指向另一节点 id，表示"YY 答完后此节点才可问"；渲染器用它重建树结构
- 无 `dep` 的节点为根节点

示例（Phase 1 结束后初始化的树）：
```
[goal:done]     id=G              将 tags 拆为 fixed_tags + candidate_tags
[success:done]  id=S              新文章有两字段；旧文章不迁移
[scope:done]    id=SC             只改 Python 脚本；SKILL.md 可补充
[storage:open]  id=ST  dep=SC     fixed_tags 词表存放位置
[format:open]   id=FF  dep=ST     frontmatter 字段结构变化
[compat:open]   id=CP  dep=FF     旧文章向后兼容处理
[review:open]   id=RV  dep=SC     candidate_tags review 流程
```

**更新规则：**
- 每次用户回答后，**只修改变化的行**，不重写全树
- 依赖节点变为 `done` 后，不需要手动标注其他节点的 dep 状态——渲染器自行查 ID 状态
- `infer` 节点直接填入推断内容，不追问用户

**选题逻辑（Phase 2 每轮）：**
> 找所有 `open` 节点中，`dep` 指向的节点状态为 `done` 的（或无 `dep` 的） → 优先选被其他节点依赖次数最多的（影响面最大）

**每次树更新后**立即重新渲染（不加 `--open`）：
```bash
echo '<更新后的决策树文本>' | python3 SKILL_DIR/scripts/render_tree.py /tmp/question-me-tree.html
```

---

### Step 3 — 动态深挖

按选题逻辑逐一追问，每问格式：

```
[当前节点文本]？
推荐答案：[Claude 的推荐]
```

等用户回答 → 更新树对应行 → 重新渲染 → 继续选下一问。

**停止条件：**
- 所有 `open` 节点已变为 `done` 或 `infer`
- 用户说"够了"、"开始"、"可以了"、"stop"等打断信号

**不追问的节点：** 可以合理默认处理的，标为 `infer` 并填入推断理由，在摘要中透明列出。

---

### Step 4 — 输出精炼指令摘要

```
## 任务摘要

**目标：** ...
**成功标准：** ...
**范围：** 包含 ... / 不包含 ...
**关键决策：** ...
**假设：** ...

确认后开始执行。
```

等用户确认，然后执行任务。

---

## 不在范围内

- 跨会话保存问答历史（每次会话独立）
- 强制跑完全部 open 节点（用户可随时打断）
- 问答结果写入文件（只在会话内输出摘要）
- 自动交棒特定 skill（执行方式由 Claude 自行判断）
