# 决定记录：question-me 与 init-spec 分工

建档日期：2026-11-02
分支：`feature/split-clarify-spec`

## 当前决定

### D1 分工：question-me 管需求澄清，init-spec 管方案与 Spec

- **决定：** question-me 负责向用户澄清需求、弄清所有问题；init-spec 基于 question-me 的结果只做补充提问（方案选择、构建者检查发现的缺口），并写 Spec。
- **状态：** 已提出
- **来源：** 用户原始需求——“让 Question Me 只负责向我澄清需求、弄清楚所有问题，而 IT 只负责基于 Question Me 的结果进行补充提问。”（本会话第 2 条消息；“IT”指 init-spec）
- **依据：** init-spec 定义性对话已写明“架构等方案选择留待方案审查”，分界线现成。

### D2 放松 question-me 结构，并从 init-spec 移植澄清标准

- **决定：** question-me 不再定死提问结构；它澄清时需要的标准从 init-spec 移植。
- **状态：** 已提出
- **来源：** 用户原始需求——“Question Me 本身的架构是否可以变得稍微宽松一些，不要定死这些架构，但它在执行过程中需要得知的一些信息，是可以从 IT 里面去移植过来的。”（本会话第 2 条消息）

### D3 两个入口都支持

- **决定：** 入口 A：用户已决定做某功能，从 init-spec 进，init-spec 调用 question-me。入口 B：用户只有设想、未决定要不要写 Spec，从 question-me 进。
- **状态：** 已提出
- **来源：** 用户原始需求——“我觉得两种都应该支持。init-spec 意思是我已经决定做这个功能了……还有一种是可能我一开始只是有一个设想，但还没明确是说要转到 spec。在这种情况下应该是优先去调研 question me。”（本会话第 3 条消息，语音转写已校正 skill 名）

### D4 交接摘要保留来源，两个入口同一格式

- **决定：** question-me 的结束摘要按决策树节点保留问题、选项、用户答复与原话，并标来源：用户最初请求→用户原始需求，`done` 节点→用户选择，`infer` 节点→Agent 推断。两个入口输出同一格式，init-spec 据此直接建决定记录，不重问。
- **状态：** 已提出
- **来源：** Agent 推断
- **依据：** init-spec 决定记录要求每条决定标三类来源之一；question-me 现有摘要不保留来源，交接会丢信息。

### D5 被 init-spec 调用时：确认后交回，不执行；确认即需求批准

- **决定：** 入口 A 中，question-me 在用户确认摘要后把结果交回 init-spec，不执行任务。用户对这份带来源摘要的确认，即视为 init-spec 的需求批准，init-spec 不再重复提交需求条目审查。
- **状态：** 已提出
- **来源：** Agent 推断
- **依据：** question-me 现有出口是“确认后执行”，会绕过 init-spec 的“批准前不得构建”；两次确认内容相同，重复审查无收益。

### D6 独立入口的三个出口

- **决定：** 入口 B 中，question-me 问完后按结果三选一：小任务→确认后直接执行（现有行为）；是要做的功能、需要 Spec→提议转 init-spec，等用户同意；用户想清楚了不做→结束。
- **状态：** 已提出
- **来源：** Agent 推断（用户未反对）

### D7 question-me 吸收探索性对话

- **决定：** question-me 增加探索模式：用户尚未想清楚要什么时，用具体场景的开放问题问情境和动机，不给选项；卡住时给方向，要建议时给可纠正的具体方案。定义模式沿用带选项提问。模式按任务定位判断，意图变化时切换。
- **状态：** 已提出
- **来源：** Agent 推断
- **依据：** 需求澄清整体移交后，init-spec 的探索性对话无处安放；question-me 现只有带选项一种问法。

### D8 question-me 结构放松的具体内容

- **决定：** 去掉固定 Q1–Q3 与“每问至少 3 个选项”；改用 init-spec 的六项澄清标准作为“问到什么程度算完”的判据，不作问题清单；选项要求改为互斥、覆盖主要方向、不凑数，附推荐与依据。保留决策树及其渲染。
- **状态：** 已提出
- **来源：** Agent 推断（细化 D2）
- **依据：** `skills/coding/question-me/scripts/render_tree.py` 未硬编码 Q1–Q3，放松结构不影响渲染。

### D9 发散型创意不进 question-me，暂不建新 skill

- **决定：** 方向尚未收敛（要不要做、做哪个、有哪些可能）的请求，question-me 说明“这还在发散阶段”并停下，不硬塞进决策树；暂不新建发散类 skill。
- **状态：** 已提出
- **来源：** Agent 推断（回应用户“第二种创意性质的应该让其他 skill 去做？”，用户未反对）

### D10 init-spec 第一阶段改为调用 question-me

- **决定：** init-spec 第一阶段的对话方式、共同澄清、阶段性复述移交 question-me；init-spec 保留：判断是否直接完成简单任务、据交接摘要建决定记录、第二阶段起的方案审查与 Spec 编写。
- **状态：** 已提出
- **来源：** Agent 推断（由 D1 推导）

### D11 触发边界互指

- **决定：** init-spec 描述去掉“clarify requirements / 理清需求”类触发词，定位为“已决定要做、需要 Spec”；question-me 边界补“需要成文 Spec → 提议转 init-spec”。
- **状态：** 已提出
- **来源：** Agent 推断
- **依据：** 两个 skill 现在都以“澄清”为触发词，同一句话选哪个不确定。

## 待定

- **跨 bundle 依赖：** question-me 在 `coding` bundle，init-spec 在 `superpowers-rewrite` bundle；`lib/bundles.js` 与 `bin/cli.js` 无 bundle 依赖机制（`installScope` 只影响显示与安装位置）。`docs/product/PRD.md` 写明 init-spec“作为独立 superpowers-rewrite bundle 登记并打包”。待用户决定处理方式。

## 范围外

- rephrase 不改动。
- `~/.claude/skills/brainstorming` 旧装机副本的清理不在本任务内。

## 已否定或已失效

（暂无）
