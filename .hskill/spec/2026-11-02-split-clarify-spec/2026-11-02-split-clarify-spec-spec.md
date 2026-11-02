# Spec：question-me 管需求澄清，init-spec 管方案与 Spec

- **版本：** v1（送审稿）
- **审查状态：** 待审
- **已批准范围：** 无（本稿整体待批）
- **决定记录：** `2026-11-02-split-clarify-spec-record.md`（同目录），引用编号 D1–D12
- **分支：** `feature/split-clarify-spec`

## 1. 意图与目标

现状：init-spec 第一阶段自带一整套需求澄清规则，question-me 也是需求澄清 skill，两者提问方法大面积重合，且规则互相矛盾（question-me 要求“每问至少 3 个选项”、固定先问 Q1–Q3；init-spec 要求“不凑虚假选项”、六项标准“不作为逐条提问的脚本”）。

目标（D1）：需求澄清只由 question-me 承担；init-spec 依据 question-me 的结果，只对方案选择和写 Spec 时发现的缺口做补充提问，然后写 Spec。question-me 的结构放松，澄清标准从 init-spec 移植（D2）。

## 2. 范围

**包含：**

- question-me 目录从 `skills/coding/question-me` 迁到 `skills/superpowers-rewrite/question-me`，改归 `superpowers-rewrite` bundle（D12）。
- 重写 question-me 的 `SKILL.md`（D2、D4–D8、D11、D17）。
- 修改 init-spec 的 `SKILL.md`（D5、D10、D11）。
- 同步登记与打包：`skills-index.json`、`package.json` 的 `files`、`tests/skill-portability.test.mjs`、`docs/product/PRD.md`、`CHANGELOG.md`。

**不包含：**

- rephrase 不改。
- `render_tree.py` 及其测试不改。
- `skill-map.html` 不改。它在本任务前已过期：没有 superpowers-rewrite 分区，question-me 仍标 v3.0.0、仍写“每问附至少 3 个选项”。
- 不清理 `~/.claude/skills/brainstorming` 旧装机副本。
- 不同步 `~/.claude/skills/` 装机副本；合并后由用户决定是否同步。
- `docs/superpowers/` 下涉及 question-me 的历史 spec 与 plan 不改。
- 不新建发散类 skill（D17）。

## 3. 必须保持的既有行为

- question-me 独立使用时，小任务仍是“确认摘要后直接执行”（D6）。
- question-me 仍不写任何文件（D4）。
- question-me 保留决策树：节点格式、四种状态、子节点评估、兄弟扫描、选题逻辑、重大方向修正、每次更新后渲染（D8）。
- question-me 正文保留字符串 `自动提议（等用户确认 y/n）` 与 `当前 agent`，正文不出现 `Claude`。这三条由 `tests/skill-portability.test.mjs` 断言。
- init-spec 的“记录决定”规则、第二阶段方案审查、第三阶段 Spec 编写、HARD-GATE 保持不变（D10），只有下文第 6 节点名的改动例外（含 HARD-GATE 中试做例外的措辞，D18）。
- skill 名不变，`skills-index.json` 不加 `renames` 条目。`init-project` 的 code 模板按 skill 名安装（`skills/coding/init-project/SKILL.md:87`），不受影响。

## 4. 两个入口的流程（D3、D5、D6）

**入口 A：用户已决定要做，从 init-spec 进入**

1. init-spec 判断：信息充分且用户已批准完整描述的简单任务，直接完成。（原有规则）
2. 会话中若已有一份本会话内经用户确认的 question-me 摘要（入口 B 转入），直接使用；否则按名调用 question-me，并告知它由 init-spec 发起。用户贴入的摘要（D15）不视为已批准：把它交给 question-me 作为已知信息，按第 5.6 节字段补问缺口，再请用户确认一次。
3. question-me 照常澄清，结束时输出摘要，用户确认。被 init-spec 发起时，question-me 确认后**不执行任务**，把摘要交回 init-spec。
4. init-spec 只依据这份摘要建决定记录，不回看对话历史（D4）。用户的这次确认即为需求批准，init-spec 直接进入第二阶段（D5）。

入口 A 的非正常出口（D13）：
- 用户对摘要提出修改：question-me 继续澄清、更新摘要再请确认（question-me 原有行为）。
- question-me 判定为发散型并停下，或用户在澄清中决定不做：init-spec 随之结束，不建决定记录，告诉用户方向收敛后可重新发起。

**入口 B：用户只有设想，从 question-me 进入**

question-me 澄清并经用户确认摘要后，三选一（D6）：

- **小任务：** 直接执行。
- **是要做的功能、需要成文 Spec：** 提议转 init-spec，等用户同意；同意后按入口 A 第 2 步使用现有摘要。这次确认同样视为需求批准（D5）。
- **用户想清楚了不做：** 结束。

**发散型请求（D17）：** 有多个候选方向尚未选定，或还在寻找方向时，question-me 说明“这还在发散阶段”后停下，不建决策树。只有一个方向的，即使用户还没决定做不做，也走探索模式继续澄清，由“结束”出口承接“想清楚了不做”。

**判定发起方：** question-me 只凭当前会话中 init-spec 是否发起了本次调用来判断入口，不读文件、不靠外部标记。

## 5. question-me 新结构（D7、D8）

### 5.1 必须移除

- 固定的“阶段 1 — 意图校准（固定 3 问）”及 Q1–Q3。
- “每问至少 3 个选项”，包括 description 中的同义表述。
- 边界条目“自动交棒特定 skill”，替换为 5.6 的规则。

### 5.2 初始化（保留并补一条）

保留现有自查：读相关文件、看 git 状态、能自查的不问，然后简短说明已了解和仍不确定的内容。

新增一条（移植自 init-spec）：查看当前项目以外的个人文件、数据或网络之前，说明范围并由用户决定。

### 5.3 提问模式（移植自 init-spec）

依据任务定位判断模式，不看描述长短，也不问用户属于哪类；用户意图变化时切换模式。

- **探索模式：** 用户还说不清要什么。
  - 用具体场景的开放问题，引出情境、动机或期望，不给选项。
  - 用户卡住时给几个方向；用户要建议时，给一个可纠正的具体方案。
  - 自己的解释标为待确认推断。
  - 每弄清一部分，用约 200–300 词复述，标明哪些是用户所述、哪些是用户的选择、哪些是推断，以一个纠错问题收尾。阶段性复述**只用于探索模式**。
- **定义模式：** 目标已定，只差缺口。
  - 选项互斥、覆盖主要方向、不凑数，附自定义入口、推荐及依据。
  - 方案层面的选择（架构、核心机制）不在这里问。被 init-spec 发起时，这类问题留给方案审查。

两种模式共用：
- 每轮只问一个问题；
- 沿用用户的词汇；
- 不用流程术语。

### 5.4 结束判据（替代 Q1–Q3）

以下六项是判断“问到什么程度算完”的标准，**不是逐条提问的清单**。适用时逐项标为已明确、待确认或不适用（附原因）；非开发类任务只看适用项。

- 目标用户、使用场景、问题及解决时机
- 新增或改变的能力与关键流程
- 成功标准、范围边界及不可破坏的现有行为
- 现有产品、代码、接口、数据、依赖及已做尝试
- 参考产品或功能，以及希望借鉴或避免的做法
- 影响方案的质量要求与技术约束

停止条件：
- 所有 `open` 节点已变为 `done`、`infer` 或 `skip`；
- 或用户表示不想再被问。此时把剩余空缺写成假设清单，随摘要一次确认。

### 5.5 决策树

保留第 3 节列出的全部机制。选题、子节点评估、兄弟扫描的操作对象改为由第一问起动态生成的节点，不再有固定根节点。

### 5.6 结束摘要（D4）

摘要必须**自足**：不引用对话历史，不写“如上所述”这类回指，脱离对话单独读也能用。两个入口输出同一格式。至少包含：

| 字段 | 内容 |
|---|---|
| 用户原始需求 | 用户最初的请求原话，以及用户不在回答问题时主动提出的要求或修正（各附原话） |
| 任务定位 | 探索或定义；建议出口：执行、转 init-spec 或结束（被 init-spec 发起时固定为交回） |
| 澄清标准 | 六项各自的状态，不适用的写原因 |
| 决定 | 每条一项：节点 id、问题、提供过的选项、用户答复（保留原话）、来源；来源为 Agent 推断时附依据 |
| 已查明事实 | 自查得到、构成决定依据的事实，附出处（路径或命令） |
| 假设 | 未核实、由 agent 默认的前提 |
| 未决 | 用户明确留待以后的事项 |

来源对应关系（采用 init-spec 的三类）：

- 用户最初请求，以及用户不在回答问题时主动提出的要求或修正 → **用户原始需求**
- `done` 节点 → **用户选择**
- `infer` 节点 → **Agent 推断**

摘要共七个字段。摘要后以一句确认请求收尾；被 init-spec 发起时，写明确认后交回 init-spec。

### 5.7 触发与边界（D11）

- **description 与触发：**
  - 定位为执行前的需求澄清，触发词加入“理清需求”“帮我想想这个”。
  - 保留 `/question-me` 与现有的自动提议条件。
  - 写明结束时可提议转 init-spec。
- **边界：**
  - 需要成文 Spec → 提议转 init-spec，等用户同意，不自动交棒。
  - 发散型请求 → 停下（D17）。
  - 问答结果不写文件（保留）。
  - 方案层面的比较不在此做。

## 6. init-spec 改动（D5、D10、D11）

- **description 与“触发条件”：**
  - 去掉 “clarify requirements” 与“理清需求”“帮我想想这个功能”。
  - 定位改为：用户已决定要做、需要在实现前形成获批 Spec。
  - 保留“比较几个方案”“写个设计 Spec”“把想法做成 Spec”及“有未定需求或关键选择的新功能”。
  - “不触发”中指向 question-me 的条目保留。
- **第一阶段：**
  - 删除“你的第一条消息”“对话方式”（含探索性对话、定义性对话两小节）“共同澄清”（含共同澄清范围、结束条件、核查现状、阶段性复述）。
  - 改为第 4 节入口 A 的第 1–4 步。
  - 新增一条：依据摘要建记录时，“用户原始需求”字段中每项建一条来源为用户原始需求的决定（D14）；“决定”字段中每项建一条决定，来源沿用摘要标注。“已查明事实”只在构成决定依据时引用。“假设”中的项作为 Agent 推断建条目。“未决”中的项建为“已提出”状态的条目，在第二阶段处理。摘要已确认的条目标“已批准”，批准依据写“question-me 摘要确认”。
  - “记录决定”小节保留原文。
- **第二阶段“需求确认与人工闸门”：**
  - 改为：需求批准来自 question-me 摘要的确认（D5）。
  - 方案审查或核查中出现影响需求的新问题时，init-spec 自行补充提问，更新决定记录并重新送审。
  - 本节其余内容不变。
- **第二、三阶段中的“重新澄清”“返回相应的澄清”（D16）：** 统一改为由 init-spec 自行补充提问并按“记录决定”规则更新、送审，不重新调用 question-me。涉及：第二阶段“方案形成标准”中“影响方案的新需求须重新澄清并通过人工闸门”，第三阶段构建者检查“必须由用户决定”一条。
- **试做（D18）：** 原探索性对话中的试做随第一阶段删除，改放第二阶段“方案形成标准”：对方案可行性拿不准时，经用户同意可做用后即弃、无需完整测试和规划的试做，发现写回决定记录。question-me 不做试做。
- **HARD-GATE：** 只改试做例外一句：“经他们同意的探索性试做可以构建”改为“经他们同意、在方案审查中做的试做可以构建”，其余不改。
- **第三阶段：** 除 D16 所列一处外不改。
- **开头介绍段：** 改为说明本技能依据 question-me 澄清的需求形成方案并写 Spec。

## 7. 登记与打包

- `git mv skills/coding/question-me skills/superpowers-rewrite/question-me`。`__pycache__` 已被 `.gitignore` 忽略，不随迁移。
- `skills-index.json`：
  - question-me 条目：`path` 改为 `superpowers-rewrite/question-me`，`bundle` 改为 `superpowers-rewrite`，更新 `contentHash` 与 `contentVersion`。
  - init-spec 条目：更新 `contentHash` 与 `contentVersion`。
  - `bundleMeta.coding` 去掉 question-me；`bundleMeta.superpowers-rewrite` 加入“question-me — 执行前需求澄清”。
- `contentHash` 算法：对 SKILL.md 全文，把 `version:` 行替换为 `version: __HASH_PLACEHOLDER__`，取 sha256 十六进制前 16 位（见 `tests/skill-portability.test.mjs` 的版本与哈希断言）。
- `package.json` 的 `files`：运行 `node scripts/generate-npmignore.js` 从索引重新生成。若生成结果出现与本任务无关的差异，放弃生成结果，改为手工替换 question-me 那一行，并在交付时报告。
- `tests/skill-portability.test.mjs`：两处 `coding/question-me` 路径改为新路径，期望版本改为新版本。
- 版本（次要决定，由 agent 决定）：
  - question-me `3.1.0` → `4.0.0`：移除固定 Q1–Q3 和选项数下限，属不兼容改动；
  - init-spec `0.2.0` → `0.3.0`：第一阶段整体替换，0.x 下按 minor 计。
- `docs/product/PRD.md`：
  - 主要要求第 1 条改为：需求澄清由 question-me 承担，init-spec 依据其确认的摘要建决定记录。
  - 最后一条改为：与 question-me、develop-plan 同属 `superpowers-rewrite` bundle 登记打包。
  - “当前版本 0.1.38”改为新版本号。该行在本任务前已过期（实际为 0.2.0），属次要决定。
- `CHANGELOG.md`：在 `[Unreleased]` 下按现有格式写 Changed 条目，覆盖 question-me 4.0.0（迁 bundle、结构放松、摘要格式、出口）与 init-spec 0.3.0。

## 8. 验收标准

1. `npm test` 全绿。基线已验证：本分支改动前在 `feature/split-clarify-spec` 上全绿。
2. `python3 skills/superpowers-rewrite/question-me/scripts/test_render_tree.py` 通过。该测试不在 `npm test` 内。
3. `skills/coding/question-me` 不存在；`git grep -n "coding/question-me"` 只命中 `docs/superpowers/`、`docs/reports/`、`docs/commute/` 下的历史文档和 `CHANGELOG.md` 的既有条目。
4. question-me `SKILL.md` 中不再出现 “Q1”“Q2”“Q3”、“至少 3 个”或“at least 3 options”。
5. init-spec `SKILL.md` 中不再出现“共同澄清范围”“探索性对话”“定义性对话”“阶段性复述”“探索性试做”，第二阶段含试做条目；question-me `SKILL.md` 中不出现“试做”；question-me `SKILL.md` 中出现“探索模式”“阶段性复述”与第 5.4 节六项标准。
6. init-spec 的 description 不含 “clarify requirements”；question-me 的边界含转 init-spec 的条目。
7. 按第 5.6 节逐字段检查 question-me 的摘要模板：七个字段齐全，来源三类与节点状态的对应关系写明；init-spec 第一阶段对七个字段中“用户原始需求”“决定”“已查明事实”“假设”“未决”五个字段各有建档规则。
8. 走读一遍入口 A：从 init-spec 第一阶段读到调用 question-me，再读到 question-me 交回，确认每一步都有明确去向，不存在“确认后直接执行”的路径。入口 A 的非正常出口、贴入摘要路径、入口 B 的三个出口同样走读一遍。
9. `node bin/cli.js list --json` 中 question-me 的 bundle 为 `superpowers-rewrite`。

## 9. 未核实前提

- 自动提议或触发词的实际触发效果（同一句话最终选哪个 skill）未实测，本任务只改文字；第 8 节不含触发实测。
- 已装过 `coding` bundle 的用户执行 `hskill update` 后，question-me 是否被保留或移除，未核实。hskill 按 skill 名而非 bundle 管理已装副本的推断来自 `bin/cli.js` 的展示逻辑，未读安装/更新代码。
