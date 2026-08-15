---
name: explain-pm
description: "Restate a technical explanation in language a product manager can act on — what changes for users, which components are involved, and the call/timing dependencies between them — keeping technical terms that carry architecture and dropping pure implementation mechanics. May read related code to fill in facts the original left out. Product-angle observations, if any, go in a separate optional section, never mixed into the restatement. Triggers: '/explain-pm', '/explain-pm <topic or file>', 'explain this like a PM', 'restate from a PM perspective'."
user_invocable: true
version: "1.2.0"
---

# explain-pm — PM 视角复述

把一段技术性表述复述成 PM（产品经理）能听懂、能据以决策的版本。

输出分两层，边界必须清晰：

1. **核心复述**（必出）——严格不超出原材料的范围。
2. **产品角度的延伸**（可选）——有才写，没有就整节不出现。

## 触发

仅手动调用：`/explain-pm` 或 `/explain-pm <主题或文件路径>`。不自动检测触发，不主动插话。

## 技术语言的保留边界

不是把技术语言全部剥离——PM 本身熟悉基础技术语言，剥干净反而看不懂全貌。判据是：

> PM 依赖的是「什么在什么之后发生、谁依赖谁」，不依赖「这段代码是怎么写的」。

**保留**（撑起架构轮廓和调用关系的技术表述）：

- 组件、服务、模块的名字
- 调用方向：谁调用谁，同步还是异步
- 依赖与时序：谁必须先就绪，哪一步是阻塞的
- 失败传播：某一环挂了，影响面到哪里为止

**剥离**（纯实现机制，对理解全貌没有帮助）：

- 函数签名、参数、返回值类型
- 数据结构、字段名、序列化格式
- 算法实现、设计模式名称
- 具体代码怎么写的、用了哪个库的哪个 API

## 核心复述的组织维度

分析时的参考，不必在回复里逐条列出，也不套固定小标题：

- **用户侧变化**：这件事最终让用户感受到什么？
- **参与者**：涉及哪些组件/角色，各自负责什么？
- **调用关系与时序依赖**：谁先谁后、谁依赖谁、哪一环可能卡住？
- **执行机制与影响面**：谁来做、分几步、影响什么协作节奏、边界在哪？

## 执行

1. **取材料**：带参数用参数指定的主题或文件；无参数则取调用前的最后一条 assistant 消息。
2. **按需调研**：如果原表述没交代清楚 PM 需要知道的调用关系或依赖顺序，去读相关代码/文件把事实补齐。调研只为补核心复述的事实，不用于给延伸小节攒素材。
3. **写核心复述**：对照上面的维度和保留边界重述，严格限定在原材料（含第 2 步补齐的事实）范围内，不做评价、不做建议。
4. **写延伸（视情况）**：判断是否真有值得从产品角度说的——产品哲学上是否符合一贯取舍、有无明显技术债或长期维护风险、范围是否合理、优先级是否搞错、是否过度工程化。有就单独成节，与核心复述之间保持明确分隔；**挑不出就整节不写，不硬造**。
5. **输出**：在对话中直接回复，简短（核心复述几句话量级）。默认不写文件；仅当用户明确要求存档时，才写入用户指定的文件。

## 不做

多轮追问式澄清、自动检测技术语言并主动触发、默认生成或保存文档、在核心复述里夹带评价或改进建议、为了凑出延伸小节而硬造关注点。
