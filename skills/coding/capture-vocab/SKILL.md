---
name: capture-vocab
version: "1.2.0"
description: Use when you need to add, query, update, or remove project-specific domain terms — invoke with /capture-vocab add|query|update|remove <term> to manage a shared vocabulary file at .hskill/capture-vocab/vocab.md
user_invocable: true
---

# Domain Vocabulary

## 概述

管理项目级领域术语字典。词汇表存于 `.hskill/capture-vocab/vocab.md`，供用户和 agent 定义、查询业务专有名词。每个术语包含：规范名称、定义、Avoid 列表、Reference（可选）。

词汇表只存业务领域概念（跨前后端、跨 AI/人类对话都会出现的词）。函数名、变量名等技术命名不进词汇表。

## 用法

```
/capture-vocab add <term>
/capture-vocab query <term>
/capture-vocab update <term>
/capture-vocab remove <term>
```

## 词汇文件

`<project-root>/.hskill/capture-vocab/vocab.md`

```markdown
# Domain Vocabulary

## 术语名
定义文本（一到两句话，说清楚概念是什么）。
_Avoid_: 旧叫法, 混用词
_Reference_: src/models/order.ts:42, docs/business/order-flow.md
```

`_Avoid_:` 和 `_Reference_:` 均为可选，不填时省略该行。`_Reference_:` 为自由文本，可写代码文件路径+行号、文档位置、任意引用。

## 操作

### query `<term>`

1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<term>"`
2. exit 0：按输出的 section 定义回答
3. exit 1：跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py list`，列出全部术语名供用户挑选
4. exit 2 或脚本不可用（如 python3 缺失）：退回读取整份 `.hskill/capture-vocab/vocab.md`，用 `## <term>` 标题手动定位（大小写不敏感）

### add `<term>`

**分层查重，按成本从低到高，严格顺序：**

1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<term>"`。命中（exit 0）→ 输出"术语 '<term>' 已存在，请用 `update` 修改"并退出
2. 从当前对话上下文推断该词的**定义 / Avoid / Reference**（Reference 留空则跳过第 3 层）
3. 对推断出的每个 Reference 路径，跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py refs "<path>"`，收集分档候选（`same-file` / `dir-contains`）
4. **仅当第 1、3 步均空手**（`lookup` 未命中 且 `refs` 无候选）时，才跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py list`，人工比对全量术语名+别名找语义相近候选；否则跳过这一步，不付这个 O(N) 成本
5. 对已得到的候选（第 3 或第 4 步产出的）逐个 `lookup` 取完整定义，**必须显式判一个结论并说给用户**，三选一：
   - **同一实体两个名字** → 建议改用 `update`，把新叫法并进该条目的 `_Avoid_`
   - **父子实体各有其名** → 正常新增，建议在两条定义里互相点名
   - **无关** → 正常新增
6. 展示条目 + 查重结论，等用户确认（`y` 或直接输入修改内容），格式：
   ```
   准备添加以下条目，请确认或直接修改：

   ## <term>
   <推断的定义，或"（请输入）"若无法推断>
   _Avoid_: <推断的 avoid，或省略>
   _Reference_: <推断的 reference，或省略>

   查重结论：<同一实体两个名字 / 父子实体各有其名 / 无关，附简要理由>

   确认添加？(y / 直接输入修改内容)
   ```
7. 若目录 `.hskill/capture-vocab/` 不存在，创建它；若 `vocab.md` 不存在，创建并写入 `# Domain Vocabulary\n`
8. 在文件末尾追加新 section，Avoid/Reference 为空时省略对应行

**退路**：`vocab.py` 不存在或 python3 不可用时，退回读取整份 `vocab.md` 手动检查 `## <term>` 是否已存在，跳过第 3/4 层查重（无法自动化），仅凭对话上下文判断是否重复。

### update `<term>`

1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<term>"` 确认存在；exit 1 或 2 → 输出对应错误后退出
2. 展示当前条目的完整内容
3. **从当前对话上下文推断**需要更新的字段（定义/Avoid/Reference）；若无新信息可推断，各字段显示为原值
4. 展示推断后的新条目，请用户确认或修改（格式同 add 步骤 6）
5. 用最终值替换该 section 内容，写回文件；未修改的字段保持原值不变

### remove `<term>`

1. 跑 `python3 ~/.claude/skills/capture-vocab/scripts/vocab.py lookup "<term>"` 确认存在；exit 1 或 2 → 输出对应错误后退出
2. 展示该术语的当前条目
3. 提示"确认删除 '<term>'？(y/N)"，等待用户输入
4. 若输入 `y`：删除该 section（含前后空行），写回文件
5. 若输入其他：输出"已取消"并退出

## Agent 加载约定

**不要在 session 开始时读取整份 `vocab.md`。** 在项目 `CLAUDE.md` 中加入：

```markdown
## 术语澄清

遇到定义含糊的词或特殊称谓，不要凭猜测理解，用 `capture-vocab` skill 查该词条。
两种时机都要查：
(1) 用户消息里出现不像通用软件概念、像本项目自造的名词；
(2) 要在回复、文档或 commit message 里首次使用某个项目名词时
    （避免用上 `_Avoid_` 里的旧叫法）。
```

**项目侧只声明「什么时候查」，不声明「怎么查」。** 脚本路径、子命令、退出码语义全部留在本 skill 内（见上面的 `query`）。把这些写进项目 `CLAUDE.md` 等于把调用契约复制一份出去——本 skill 换子命令、改路径、换实现语言时，那些副本会静默失效，不报错。

**代价**：走 skill 意味着每次查词要加载这份 SKILL.md，比直接调脚本贵。这是**固定开销，不随词汇表增长**——设计要守的「成本与词汇表总量无关」那条性质不受影响。
