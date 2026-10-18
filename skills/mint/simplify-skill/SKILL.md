---
name: simplify-skill
description: "Use when shortening or clarifying an existing Skill without changing its behavior, triggers, or output contract."
user_invocable: true
version: "0.1.2"
---

# 精简 Skill

## 拟定建议

1. 阅读目标 `SKILL.md` 及必要的引用文件，识别必须保留的触发条件、判断规则、步骤、输出格式、授权边界和跨 Skill 接口。
2. 删除重复、空泛和通用教程；通用能力需要提示时只留关键词。
3. 将可由既有术语或专有名词无歧义表达的说明压缩为该词；保留任务特有的条件、边界和输出要求。
4. 若能减少无关内容加载，对仅在明确情境下需要的内容采用渐进式披露；保留共同规则与始终生效的约束。
5. 将含糊表述改为明确的条件和动作；一句话能说清的规则不拆句。
6. 指令写清何时做、做什么、产出什么；解释单列，且只保留影响决策的内容。
7. 对照原文核对保留项及必要的术语、字段、路径和顺序；保留并标记无法确认的语义。

## 审批与执行

逐条列出修改前文本、修改后文本及理由，等待用户明确批准；获批后仅修改批准项，验证并在 Git 仓库中提交，报告实际改动与疑点。
