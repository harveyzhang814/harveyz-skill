---
name: question-me
description: "Pre-task clarification skill — clarifies ambiguous or complex tasks before execution through structured Q&A with a live decision tree. One question at a time, each with a recommended answer, in decision-dependency order. Triggers: '/question-me', 'help me clarify this', 'question me before starting', 'let's define this first'. Claude auto-triggers when detecting ambiguous or complex requests (multiple conflicting goals, vague keywords like 'optimize/refactor/clean up', missing success criteria, unstated context assumptions)."
user_invocable: true
version: "2.0.0"
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

### Step 1 — 意图校准（固定 3 问，每问答完即评估子节点）

三个固定问题按顺序问，**每答完一问立即评估子节点**，不等三问全部答完。

**Q1 — 目标：** 这件事做完，最核心的变化是什么？
**Q2 — 成功标准：** 怎么判断做对了？（可测量的验收条件）
**Q3 — 范围边界：** 明确不做什么，或哪些东西不能动？

**每问的处理流程：**
```
问 Qn → 等用户回答
  → [必须] 子节点评估：这个答案是否引出需要追问的不确定性？
      是 → 生成子节点追加到树（BFS：一次生成所有潜在子节点）
      否 → 不生成（Qn 为叶子节点）
  → 渲染树（首次调用加 --open）
  → 问 Q(n+1)
```

Q3 答完并评估子节点后，进入 Step 3。

**首次渲染（Q1 答完后）：**
```bash
echo '<当前树文本>' | python3 SKILL_DIR/scripts/render_tree.py /tmp/question-me-tree.html --open
```

---

### Step 2 — 决策树格式

**内部格式（每节点一行，平铺列出）：**

```
[label:status]  id=XX  [dep=YY]  节点文本
```

字段规则：
- `status`: `done` / `open` / `infer` / `skip`
- `id`: 全树唯一短 ID（2–3 字母），更新时引用稳定
- `dep=YY`: 可选，指向另一节点 id，表示"YY 答完后此节点才可问"；渲染器用它重建树结构
- 无 `dep` 的节点为根节点

状态含义：

| status | 含义 | 子节点 |
|--------|------|--------|
| `done` | 已答 | 可有可无；无子节点即为叶子 |
| `open` | 待问（dep 已满足或无 dep） | 答完后评估 |
| `infer` | Claude 填默认值，不追问 | 无；在摘要中透明列出 |
| `skip` | 兄弟答案使其无关，跳过 | 无 |

**叶子节点不是状态**，是结构属性——`done` 且无子节点即为叶子，分支自然结束。

**更新规则：**
- 每次用户回答后，只修改变化的行，不重写全树
- 新生成的子节点追加在父节点行之后
- `infer` 节点直接填入推断内容，不追问用户

**选题逻辑（Step 3 每轮）：**
> 从所有 `dep` 已满足（或无 `dep`）的 `open` 节点中，选被其他节点依赖次数最多的（影响面最大）；并列时按树中出现顺序选最早的

**[禁止] 顺序操纵：** 不得通过调整提问顺序来为另一个 open 节点制造 `infer` 的理由。若节点 X 的 dep 已满足且处于 `open` 状态，必须在轮到它时进行问答流程或当场评估 infer——不能先问节点 Y，再以"Y 的答案已覆盖 X"为由跳过 X。

**每次树更新后**立即重新渲染（不加 `--open`）：
```bash
echo '<更新后的决策树文本>' | python3 SKILL_DIR/scripts/render_tree.py /tmp/question-me-tree.html
```

---

### Step 3 — 动态深挖

按选题逻辑逐一追问，每轮处理流程：

```
1. 选影响面最大的 open 节点
2. 提问（附推荐答案）：
   [当前节点文本]？
   推荐答案：[Claude 的推荐]
3. 等用户回答 → 标记为 done
4. [必须] 子节点评估：
     这个答案下有需要追问的不确定性且影响执行方向？
       是 → 一次生成所有潜在子节点（dep 指向当前节点）
       否 → 不生成（当前节点为叶子）
     子问题 Claude 可合理默认的 → 标 infer，填入假设，不追问
5. [必须] 兄弟扫描：
     此答案是否让同级兄弟节点变无关或矛盾？
       是 → 标 skip
       否 → 继续
6. 更新树文本 → 重新渲染
7. 还有 open 节点？→ 是：回到 1 / 否：进入 Step 4
```

**分支切换是自动的。** 某分支 open 节点耗尽后，选题逻辑自动切到影响面最大的其他 open 节点。不需要显式"切换分支"操作。

**重大方向修正（例外情况）：** 若用户答案与已答祖先节点根本矛盾，不走兄弟扫描，而是：
1. 显式指出冲突
2. 询问用户是否需要修改已答节点
3. 用户确认后重标受影响节点为 `open`，重新提问

**停止条件：**
- 所有 `open` 节点已变为 `done` / `infer` / `skip`（树自动清空）
- 用户说"够了"、"开始"、"可以了"、"stop"等打断信号

---

### Step 4 — 输出精炼指令摘要

```
## 任务摘要

**目标：** ...
**成功标准：** ...
**范围：** 包含 ... / 不包含 ...
**关键决策：** ...
**假设：** （infer 节点的默认处理，透明列出）

确认后开始执行。
```

等用户确认，然后执行任务。

---

## 不在范围内

- 跨会话保存问答历史（每次会话独立）
- 强制跑完全部 open 节点（用户可随时打断）
- 问答结果写入文件（只在会话内输出摘要）
- 自动交棒特定 skill（执行方式由 Claude 自行判断）
- 子节点超过 1 层的预生成（孙节点等父节点答完再评估）
- 跨分支远端节点的自动扫描（只扫同级兄弟）
