---
name: explain-pm
description: "Restate a recent technical explanation from a product-manager's analytical lens — user experience, product philosophy, execution mechanics, and architectural health — rather than translating jargon, and flag product-perspective concerns like scope, over-engineering, priority, or drift from user need. Triggers: '/explain-pm', '/explain-pm <topic or file>', 'explain this like a PM', 'restate from a PM perspective'."
user_invocable: true
version: "1.1.1"
---

# explain-pm — PM 视角复述

把一段技术性表述从 PM 视角复述：换成 PM 关注的分析维度，再视情况指出值得从产品角度重新考虑的地方。

## 触发

仅手动调用：`/explain-pm` 或 `/explain-pm <主题或文件路径>`。不自动检测触发，不主动插话。

## PM 视角的关注维度

不是语言转译——PM 本身熟悉基础技术语言。要转换的是关注点：

- **用户体验**：这个决定最终会让用户感受到什么变化？
- **产品哲学**：是否符合产品一贯的取舍和原则？
- **执行机制与流程**：具体怎么落地——谁来做、分几步、影响什么协作节奏？
- **架构健康度（次要）**：是否有明显的技术债或长期维护风险，只做提醒，不展开实现细节本身。

## 执行

1. **取材料**：带参数用参数指定的主题或文件；无参数则取调用前的最后一条 assistant 消息。
2. **换视角**：对照上面的关注维度重新审视材料——不必在回复里逐条列出，只是分析时的参考。
3. **提出关注点（视情况）**：判断原表述从 PM 角度是否有值得重新审视的地方，比如是否偏离用户实际需求、范围是否合理、是否过度工程化、优先级是否搞错了。如果原表述本身已经很贴近产品目标，挑不出问题，就只做视角复述，不硬造关注点。关注点如果成立，放在回复最后，不要打断前面的视角复述。
4. **输出**：在对话中直接回复，简短（几句话量级）。默认不写文件；仅当用户明确要求存档时，才把这段评论写入用户指定的文件。

## 不做

多轮追问式澄清、自动检测技术语言并主动触发、默认生成或保存文档、固定的输出小标题模板。
