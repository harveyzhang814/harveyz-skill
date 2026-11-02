# question-me / init-spec 分工改造 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 superpowers:executing-plans 逐项实施；用 `- [ ]` 跟踪步骤。跳过其中的 using-git-worktrees 步骤，工作区已由交接方建好。

**Goal:** question-me 迁入 superpowers-rewrite bundle 并改为唯一的需求澄清入口，init-spec 改为依据 question-me 确认的摘要建决定记录、做方案审查并写 Spec。

**Architecture:** 纯文档型 skill 改动。先做目录迁移和登记（行为不变、测试保持绿），再分别重写两份 `SKILL.md`，最后同步 PRD 与 CHANGELOG。每次改 `SKILL.md` 都在同一任务里更新 `skills-index.json` 的 `contentHash`/`contentVersion`，保证 `npm test` 每次提交后都是绿的。

**Tech Stack:** Markdown skill 文件、`skills-index.json`、Node 测试（`npm test`）、Python 渲染脚本测试。

**Spec:** `.hskill/spec/2026-11-02-split-clarify-spec/2026-11-02-split-clarify-spec-spec.md`

**Spec Version and Scope:** v1.1（已批准），全文。

## Global Constraints

- 版本：question-me `3.1.0` → `4.0.0`；init-spec `0.2.0` → `0.3.0`。
- `contentHash`：SKILL.md 全文中把 `version:` 行替换为 `version: __HASH_PLACEHOLDER__`，sha256 十六进制前 16 位。计算命令（下文记为 `HASH <path>`）：
  `node -e "const b=require('fs').readFileSync(process.argv[1],'utf8');console.log(require('crypto').createHash('sha256').update(b.replace(/^version:.*$/m,'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0,16))" <path>`
- question-me 正文必须保留 `自动提议（等用户确认 y/n）` 与 `当前 agent`，不得出现 `Claude`（`tests/skill-portability.test.mjs` 断言）。
- question-me 不写任何文件；不做试做。
- skill 名不变，不加 `renames` 条目。
- 不改：rephrase、`render_tree.py` 及其测试、`skill-map.html`、`docs/superpowers/`、`~/.claude/skills/`、`skills/coding/init-project/assets/templates/code.yml`。
- 提交遵守 Conventional Commits（`docs` 不是 `doc`），末尾带 `Co-Authored-By:` 行。不合并到 staging。

## Review Focus

- 被 init-spec 发起时，question-me 确认摘要后仍走“直接执行”分支 → 必须交回 init-spec，入口 A 全程无“确认后直接执行”（Task 2、Task 5 走读）。
- 用户贴入的摘要被当作已批准 → 必须交给 question-me 补问缺口并重新确认一次（Task 3）。
- init-spec 第二、三阶段残留“重新澄清”“返回相应的澄清”而去重新调用 question-me → 改为 init-spec 自行补问并按“记录决定”更新送审（Task 3）。
- 改完 SKILL.md 忘了更新 `contentHash` → `npm test` 版本与哈希断言红（Task 2、Task 3 的 Step 验证）。
- `generate-npmignore.js` 重新生成 `files` 时带入无关差异 → 放弃生成结果，手工替换 question-me 一行并在交付时报告（Task 1）。

---

### Task 1: 迁移 question-me 目录并同步登记（行为不变）

**Prerequisites:** 无

**Files:**
- Move: `skills/coding/question-me/` → `skills/superpowers-rewrite/question-me/`（含 `scripts/`）
- Modify: `skills-index.json`（question-me 条目 `path`/`bundle`；`bundleMeta.coding`；`bundleMeta.superpowers-rewrite`）
- Modify: `package.json` 的 `files`
- Modify: `tests/skill-portability.test.mjs:77`、`:105`（只改路径，版本仍为 `3.1.0`）

**Interfaces:**
- Produces: question-me 新路径 `skills/superpowers-rewrite/question-me/SKILL.md`，索引 `path: "superpowers-rewrite/question-me"`，`bundle: "superpowers-rewrite"`。

- [ ] **Step 1: 确认基线** — Run: `npm test`；Expected: exit 0。
- [ ] **Step 2: `git mv skills/coding/question-me skills/superpowers-rewrite/question-me`**；Expected: `ls skills/coding/question-me` 报不存在。
- [ ] **Step 3: 改 `skills-index.json`** — question-me 条目 `path` 改为 `superpowers-rewrite/question-me`、`bundle` 改为 `superpowers-rewrite`（hash/version 暂不动）；`bundleMeta.coding` 去掉 `+ question-me`；`bundleMeta.superpowers-rewrite` 在 init-spec 前加入 `question-me — 执行前需求澄清；`。
- [ ] **Step 4: 改测试路径** — `tests/skill-portability.test.mjs` 两处 `coding/question-me` 改为 `superpowers-rewrite/question-me`。
- [ ] **Step 5: 重新生成 `files`** — Run: `node scripts/generate-npmignore.js`，再 `git diff package.json`；Expected: 只有 question-me 一行从 `skills/coding/question-me/` 变为 `skills/superpowers-rewrite/question-me/`（位置可变）。有其他差异 → `git checkout package.json`，手工替换该行，记下“生成结果有无关差异”供交付报告；同时 `git status` 检查脚本是否改了其他文件，有则一并还原。
- [ ] **Step 6: 验证** — Run: `npm test`；Expected: exit 0。Run: `python3 skills/superpowers-rewrite/question-me/scripts/test_render_tree.py`；Expected: exit 0。Run: `node bin/cli.js list --json`；Expected: question-me 的 `bundle` 为 `superpowers-rewrite`。
- [ ] **Step 7: 提交** — `git add -A skills/ skills-index.json package.json tests/skill-portability.test.mjs && git commit -m "refactor(question-me): move into superpowers-rewrite bundle"`

### Task 2: 重写 question-me SKILL.md（4.0.0）

**Prerequisites:** Task 1

**Files:**
- Modify: `skills/superpowers-rewrite/question-me/SKILL.md`
- Modify: `skills-index.json`（question-me `contentHash`、`contentVersion`）
- Modify: `tests/skill-portability.test.mjs:105`（期望版本 `4.0.0`）

**Interfaces:**
- Produces（供 Task 3 引用，名称须逐字一致）：
  - 摘要七字段：`用户原始需求`、`任务定位`、`澄清标准`、`决定`、`已查明事实`、`假设`、`未决`。
  - 来源三类：`用户原始需求`、`用户选择`（`done` 节点）、`Agent 推断`（`infer` 节点）。
  - 两种模式名：`探索模式`、`定义模式`。
  - 被 init-spec 发起时的行为：确认后不执行，交回 init-spec。

- [ ] **Step 1: 写失败检查** — 下列检查在改前至少一条失败：
  - `grep -nE "Q1|Q2|Q3|至少 3 个|at least 3 options" skills/superpowers-rewrite/question-me/SKILL.md` → 期望无命中（当前有命中，FAIL）
  - `grep -n "试做" <同文件>` → 期望无命中
  - `grep -c "探索模式\|阶段性复述" <同文件>` → 期望 ≥ 2（当前 0，FAIL）
- [ ] **Step 2: 按 Spec 第 3、4、5 节重写正文**，要点：
  - frontmatter `version: "4.0.0"`；description 定位为执行前的需求澄清，去掉选项数下限表述，触发词加入“理清需求”“帮我想想这个”，保留 `/question-me` 与自动提议条件，写明结束时可提议转 init-spec（5.7）。
  - 触发条件保留 `自动提议（等用户确认 y/n）` 原样与现有四条条件；正文用“当前 agent”，不出现 `Claude`。
  - 新增“发散型请求”判定（D17 原文规则）与“判定发起方”（只凭当前会话中 init-spec 是否发起）。
  - 边界：删除“自动交棒特定 skill”；新增“需要成文 Spec → 提议转 init-spec，等用户同意，不自动交棒”“发散型请求 → 停下”“方案层面的比较不在此做”；保留“问答结果不写文件”等其余条目。
  - 初始化保留现有三步与“已了解/仍不确定”输出，补“查看当前项目以外的个人文件、数据或网络之前，说明范围并由用户决定”（5.2）。
  - 删除固定提问格式与阶段 1；新增“提问模式”：探索模式、定义模式与共用规则，按 5.3 原文要求（阶段性复述只用于探索模式）。
  - 新增“结束判据”：5.4 六项标准原文、三种状态标注、两条停止条件。
  - 动态深挖流程与决策树格式保留全部机制（节点格式、四种状态、子节点评估、兄弟扫描、选题、重大方向修正、每次更新后渲染）；去掉对 Q1/阶段 1 的引用，示例节点 id 改用不含 `Q1`–`Q3` 的写法（如 `G1`、`G1a`），首次渲染改为“第一问答完后”加 `--open`。
  - 结束摘要：5.6 七字段表、来源对应关系、自足要求、确认收尾句（被 init-spec 发起时写明确认后交回 init-spec）。
  - 摘要确认后的出口：独立使用时三选一（小任务直接执行 / 提议转 init-spec / 结束）；被 init-spec 发起时不执行、交回 init-spec。
- [ ] **Step 3: 更新登记** — `skills-index.json` question-me `contentVersion: "4.0.0"`、`contentHash` 取 `HASH skills/superpowers-rewrite/question-me/SKILL.md` 的输出；测试期望版本改 `4.0.0`。
- [ ] **Step 4: 验证** — 重跑 Step 1 三条检查，全部满足期望；`grep -n "Claude" <同文件>` 无命中；`grep -n "init-spec" <同文件>` 命中边界中转 init-spec 的条目；Run: `npm test` → exit 0；Run: `python3 skills/superpowers-rewrite/question-me/scripts/test_render_tree.py` → exit 0。
- [ ] **Step 5: 提交** — `git commit -am "feat(question-me): own requirement clarification, emit self-contained summary (4.0.0)"`

### Task 3: 修改 init-spec SKILL.md（0.3.0）

**Prerequisites:** Task 2（引用其摘要字段名与交回行为）

**Files:**
- Modify: `skills/superpowers-rewrite/init-spec/SKILL.md`
- Modify: `skills-index.json`（init-spec `contentHash`、`contentVersion`）

**Interfaces:**
- Consumes: Task 2 产出的七字段名、来源三类、交回行为。

- [ ] **Step 1: 写失败检查** —
  - `grep -nE "共同澄清范围|探索性对话|定义性对话|阶段性复述|探索性试做" skills/superpowers-rewrite/init-spec/SKILL.md` → 期望无命中（当前有，FAIL）
  - `grep -n "clarify requirements" <同文件>` → 期望无命中（当前有，FAIL）
  - `grep -nE "重新澄清|返回相应的澄清" <同文件>` → 期望无命中（当前有，FAIL）
- [ ] **Step 2: 按 Spec 第 6 节改正文**：
  - frontmatter `version: "0.3.0"`；description 与“触发条件”去掉 “clarify requirements”“理清需求”“帮我想想这个功能”，定位为用户已决定要做、需在实现前形成获批 Spec；保留“比较几个方案”“写个设计 Spec”“把想法做成 Spec”与“有未定需求或关键选择的新功能”；“不触发”指向 question-me 的条目保留。
  - 开头介绍段改为：依据 question-me 澄清的需求形成方案并写 Spec。
  - 第一阶段：删除“你的第一条消息”“对话方式”“共同澄清”三节；写入 Spec 第 4 节入口 A 第 1–4 步（含会话内已确认摘要直接用、贴入摘要须交 question-me 补问并重新确认、只依据摘要建记录不回看对话、确认即需求批准）与入口 A 两条非正常出口；新增按摘要建档规则（Spec 第 6 节第一阶段第三条原文：五个字段各自的建档方式、“已批准”与批准依据“question-me 摘要确认”）。“记录决定”小节原文保留。
  - 第二阶段“需求确认与人工闸门”：改为需求批准来自 question-me 摘要的确认；方案审查或核查中出现影响需求的新问题时 init-spec 自行补问、更新决定记录并重新送审；本节其余不变。
  - “方案形成标准”中“影响方案的新需求须重新澄清并通过人工闸门”与构建者检查“必须由用户决定”一条中的“返回相应的澄清”：改为 init-spec 自行补充提问并按“记录决定”规则更新、送审，不重新调用 question-me（D16）。
  - “方案形成标准”加试做条目：对方案可行性拿不准时，经用户同意可做用后即弃、无需完整测试和规划的试做，发现写回决定记录（D18）。
  - HARD-GATE 只把“经他们同意的探索性试做可以构建”改为“经他们同意、在方案审查中做的试做可以构建”，其余字句不动。
- [ ] **Step 3: 更新登记** — `skills-index.json` init-spec `contentVersion: "0.3.0"`、`contentHash` 取 `HASH skills/superpowers-rewrite/init-spec/SKILL.md`。
- [ ] **Step 4: 验证** — 重跑 Step 1 三条检查均无命中；`grep -n "试做" <同文件>` 命中第二阶段条目与 HARD-GATE；`grep -nE "用户原始需求|决定|已查明事实|假设|未决" <同文件>` 第一阶段五个字段各有建档规则；`git diff staging -- <同文件>` 中“记录决定”小节与第三阶段除 D16 一处外无改动；Run: `npm test` → exit 0。
- [ ] **Step 5: 提交** — `git commit -am "feat(init-spec): build record from question-me summary (0.3.0)"`

### Task 4: 同步 PRD 与 CHANGELOG

**Prerequisites:** Task 2、Task 3（引用最终版本号）

**Files:**
- Modify: `docs/product/PRD.md`（init-spec 节：状态行、主要要求第 1 条与最后一条）
- Modify: `CHANGELOG.md`（`[Unreleased]` 下）

- [ ] **Step 1: 改 PRD** — 状态行“当前版本 0.1.38”改为“当前版本 0.3.0”；主要要求第 1 条改为“需求澄清由 question-me 承担，init-spec 依据其确认的摘要建决定记录”；最后一条改为“与 question-me、develop-plan 同属 `superpowers-rewrite` bundle 登记打包，不覆盖上游同名技能”。
- [ ] **Step 2: 写 CHANGELOG** — `[Unreleased]` 下新增 `### Changed`，按现有条目格式写两条：`question-me` 升至 4.0.0（迁入 superpowers-rewrite bundle、移除固定 Q1–Q3 与选项数下限改为探索/定义两种模式与六项结束判据、七字段自足摘要、确认后三种出口及被 init-spec 发起时交回）；`init-spec` 升至 0.3.0（第一阶段改为依据 question-me 摘要建决定记录、摘要确认即需求批准、试做移到方案审查）。若 Task 1 Step 5 有手工改 `files` 的情况，不写进 CHANGELOG，只在交付报告说明。
- [ ] **Step 3: 验证** — `grep -n "0.1.38" docs/product/PRD.md` 无命中；Run: `npm test` → exit 0。
- [ ] **Step 4: 提交** — `git commit -am "docs: sync PRD and CHANGELOG for question-me/init-spec split"`

### Task 5: 全量验收自测

**Prerequisites:** Task 1–4

**Files:**
- Modify: `docs/commute/2026-11-02-split-clarify-spec-handoff.md`（追加“接手方自测记录（日期）”小节，`status` 置“待验收”）

- [ ] **Step 1: 逐条实跑交接文档“最小验收锚点”1–11**，判成败的命令不接管道；锚点 3 用 `git grep -n "coding/question-me"` 并逐条核对命中路径都在允许范围内；锚点 10 用 `HASH` 对两个文件分别计算并与 `skills-index.json` 比对。
- [ ] **Step 2: 走读（锚点 8）** — 按 Spec 第 4 节，在两份 SKILL.md 中逐步定位：入口 A 正常路径（init-spec 第 1–4 步 → question-me 被发起时不执行 → 交回 → 建记录 → 第二阶段）、入口 A 两条非正常出口、贴入摘要路径、入口 B 三个出口；每一步记下所在小节。
- [ ] **Step 3: 写自测记录** — 逐条 pass/fail 附命令；有红按 handoff Phase 2.5 处理；全绿后把 `status` 置为“待验收”。
- [ ] **Step 4: 提交** — `git commit -am "docs(handoff): record self-test for split-clarify-spec"`
