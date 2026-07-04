---
name: domain-vocab
version: "1.1.0"
description: Use when you need to add, query, update, or remove project-specific domain terms — invoke with /domain-vocab add|query|update|remove <term> to manage a shared vocabulary file at hskill/domain-vocab/vocab.md
user_invocable: true
---

# Domain Vocabulary

## 概述

管理项目级领域术语字典。词汇表存于 `hskill/domain-vocab/vocab.md`，供用户和 agent 定义、查询业务专有名词。每个术语包含：规范名称、定义、Avoid 列表、Reference（可选）。

词汇表只存业务领域概念（跨前后端、跨 AI/人类对话都会出现的词）。函数名、变量名等技术命名不进词汇表。

## 用法

```
/domain-vocab add <term>
/domain-vocab query <term>
/domain-vocab update <term>
/domain-vocab remove <term>
```

## 词汇文件

`<project-root>/hskill/domain-vocab/vocab.md`

```markdown
# Domain Vocabulary

## 术语名
定义文本（一到两句话，说清楚概念是什么）。
_Avoid_: 旧叫法, 混用词
_Reference_: src/models/order.ts:42, docs/business/order-flow.md
```

`_Avoid_:` 和 `_Reference_:` 均为可选，不填时省略该行。`_Reference_:` 为自由文本，可写代码文件路径+行号、文档位置、任意引用。

## 操作

### add `<term>`

1. 检查 `hskill/domain-vocab/vocab.md` 是否存在 `## <term>` section（大小写不敏感匹配）
2. 若已存在：输出"术语 '<term>' 已存在，请用 `update` 修改"并退出
3. 若不存在，**先从当前对话上下文推断**各字段：
   - **定义**：从对话中该词的使用方式推断一到两句话的定义；无法推断则留空
   - **Avoid**：从对话中出现过的同义词或混用叫法推断；无法推断则留空
   - **Reference**：从对话中提到的代码文件/文档位置推断；无法推断则留空
4. 展示推断结果，格式如下，请用户确认或修改：
   ```
   准备添加以下条目，请确认或直接修改：

   ## <term>
   <推断的定义，或"（请输入）"若无法推断>
   _Avoid_: <推断的 avoid，或省略>
   _Reference_: <推断的 reference，或省略>

   确认添加？(y / 直接输入修改内容)
   ```
5. 用户确认后（输入 `y` 或不输入内容直接回车）写入；若用户输入了修改内容，用修改后的值写入
6. 若目录 `hskill/domain-vocab/` 不存在，创建它；若 `vocab.md` 不存在，创建并写入 `# Domain Vocabulary\n`
7. 在文件末尾追加新 section，Avoid/Reference 为空时省略对应行

### query `<term>`

1. 检查 `hskill/domain-vocab/vocab.md` 是否存在；若不存在，输出"词汇表尚未初始化，请先用 `add` 添加术语"并退出
2. 按 `## <term>` 标题匹配（大小写不敏感），读取该 section 直到下一个 `##` 或文件末尾
3. 返回该 section 的完整内容（定义 + Avoid + Reference）
4. 若未找到，输出"未找到术语 '<term>'"，然后列出 vocab.md 中所有 `##` 标题作为已有术语名

### update `<term>`

1. 检查词汇表存在且包含该术语；若文件不存在或术语不存在，输出对应错误后退出
2. 展示当前条目的完整内容
3. **从当前对话上下文推断**需要更新的字段（定义/Avoid/Reference）；若无新信息可推断，各字段显示为原值
4. 展示推断后的新条目，请用户确认或修改（格式同 add 步骤 4）
5. 用最终值替换该 section 内容，写回文件；未修改的字段保持原值不变

### remove `<term>`

1. 检查词汇表存在且包含该术语；若不存在，输出对应错误后退出
2. 展示该术语的当前条目
3. 提示"确认删除 '<term>'？(y/N)"，等待用户输入
4. 若输入 `y`：删除该 section（含前后空行），写回文件
5. 若输入其他：输出"已取消"并退出

## Agent 加载约定

本 Skill 不自动注入词汇表到 session 上下文。如需在每次 session 开始时加载术语，在项目 `CLAUDE.md` 中加入：

```markdown
每次 session 开始，读取 `hskill/domain-vocab/vocab.md`（如存在）。
```
