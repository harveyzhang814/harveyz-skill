---
name: explain-pm
description: "Restate a recent technical explanation in product-manager language: translate jargon into user/business impact, and flag product-perspective concerns like scope, over-engineering, priority, or drift from user need. Triggers: '/explain-pm', '/explain-pm <topic or file>', 'explain this like a PM', 'restate from a PM perspective'."
user_invocable: true
version: "1.0.0"
---

# explain-pm — PM 视角复述

把一段技术性表述从 PM 视角复述：先转译成产品/业务语言，再视情况指出值得从产品角度重新考虑的地方。

## 触发

仅手动调用：`/explain-pm` 或 `/explain-pm <主题或文件路径>`。不自动检测触发，不主动插话。

## 执行

1. **取材料**：带参数用参数指定的主题或文件；无参数则取调用前的最后一条 assistant 消息。
2. **转译**：把技术语言换成产品/业务语言——这段话讲给 PM 听，PM 听到的是什么（用户能得到什么、解决了什么问题、有什么代价）。
3. **提出关注点（视情况）**：判断原表述从 PM 角度是否有值得重新审视的地方，比如是否偏离用户实际需求、范围是否合理、是否过度工程化、优先级是否搞错了。如果原表述本身已经很贴近产品目标，挑不出问题，就只做转译，不硬造关注点。
4. **输出**：在对话中直接回复，简短（几句话量级）。默认不写文件；仅当用户明确要求存档时，才把这段评论写入用户指定的文件。

## 不做

多轮追问式澄清、自动检测技术语言并主动触发、默认生成或保存文档、固定的输出小标题模板。
