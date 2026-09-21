---
status: 已验收
date: 2026-09-21
author_model: claude-opus-5
acceptance: hard
branch: feature/init-project
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+init-project
source_node: e25d520f-15fb-44e2-ad48-53c159f8682a
target_node: 03464d99-3269-4232-8966-3756e4ca35c0
---

# 交接：实现 init-project skill（新项目初始化 / 老仓库补缺）

**交接目的**：spec 与实施计划都已定稿并提交，实施一行未动。接手方按计划的 Task 1–4 把
`skills/coding/init-project` 实现出来并自测，由原 session 验收后合并。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，若文档里有「工作流约定」章节按其开工，没有就直接开工。
>
> **完成后不是直接推状态，先自测**（skill 的 Phase 2.5）：逐条实跑「最小验收锚点」**全集**（不是只跑你改动相关的那几条），外加文档点名要复跑的既有资产；判成败的命令不接管道（`| tail` 的退出码是 `tail` 的，恒为 0）。把结果写成**独立小节**，标题里必须有「自测」二字（如「接手方自测记录（日期）」），逐条列 pass/fail 并附实际命令——写你自己这一节，别混进原 session 的验收记录。**有红就别推状态**：要么修到绿，要么在那一条旁边写出归因证据并显式声明「带着这条红送验」，不许沉默推上来。`validate-handoff.sh` 会拦：`status` 是「待验收」而正文没有含「自测」的小节直接 exit 1。
>
> 自测过了，才把 frontmatter 的 `status` 置为「待验收」并**停在这里**——`已验收` / `打回` 由原 session 按「最小验收锚点」判定后写，不要代填。
>
> **被打回之后同理，而且默认跑全集**：复修完重新走一遍自测才能再置回「待验收」；要只跑子集，必须在记录里附改动范围证据（`git diff --name-only <打回点提交>..HEAD`）和「其余条目不可能被波及」的论证。复修记录另起一节（如「接手方复修自测记录（第 N 轮）」，同样含「自测」二字），不覆盖前几轮。
>
> **开工前**：若你也在 Agent Canvas 画布节点里，先建一条 `hands-off-to` 关系（`agent-canvas-ctl whoami` 取自己的 id，核对 `node-relations` 里没有后 `link-nodes --from e25d520f-15fb-44e2-ad48-53c159f8682a --to <自己> --type hands-off-to`），建完把自己的 id 填进 `target_node`。**只建这一条**——别建 `implements`、别另立需求节点。
>
> **在哪开工**：进 frontmatter 的 `worktree`，核对当前分支与 `branch` 一致。Claude Code 用 `EnterWorktree(path: <worktree>)` 的 `path` 模式。**不要自己 `git worktree add`**（那条分支已被这个工作区占用，再建会失败），**也绝不要 `git worktree remove`**——验收还要用。

---

## 最小验收锚点

`acceptance: hard`，逐条实跑判对错。全部在交接工作区里跑。

1. **模板校验器绿且覆盖五项**
   `node --test tests/templates.test.mjs` exit 0，且输出的 `# pass` 数 ≥ 6
   （1 条「模板目录至少有一套模板」+ code.yml 的 5 项：五段齐全 / init_phases 引用合法 /
   skills 名字可查 / on_exists 取值合法 / from 路径存在）。

2. **校验器真的会拦**——把 `code.yml` 的 `skills` 清单里任意一项临时改成 `no-such-skill`，
   重跑 `node --test tests/templates.test.mjs` 必须 exit 非 0；改回来再跑必须 exit 0。
   （这条防的是「测试写了但恒真」。请在自测记录里附两次的 exit code。）

3. **skill 格式校验绿**
   `bats tests/skills.bats` exit 0，8 个 test 全绿。

4. **索引条目正确**
   ```bash
   node -e "const i=require('./skills-index.json');const e=i.skills.find(s=>s.path==='coding/init-project');if(!e)throw new Error('未注册');if(e.bundle!=='coding')throw new Error('bundle 错: '+e.bundle);if(e.installScope!=='global')throw new Error('installScope 错: '+e.installScope);console.log('OK')"
   ```
   输出 `OK`。`installScope` 必须是 `global`——理由见「关键决定」第 3 条。

5. **frontmatter 正确**
   `skills/coding/init-project/SKILL.md` 的 frontmatter 满足 `name: init-project`、
   `version: "0.1.0"`、`user_invocable: true`，且 `description` 里同时出现
   `/init-project` 与 `check` 两个触发线索。

6. **打包清单已重新生成**
   `node -e "const p=require('./package.json');if(!p.files.includes('skills/coding/init-project/'))throw new Error('files[] 缺条目');console.log('OK')"`
   输出 `OK`。

7. **骨架资产齐且 .gitignore 骨架带状态规则**
   `assets/skeleton/` 下四份文件都存在，且
   `grep -q '^\.hskill/\*/state\.json$' skills/coding/init-project/assets/skeleton/gitignore-code`
   exit 0。

> **锚点 8、9 怎么跑**：合并前这个 skill 没装到 `~/.claude/skills/`，
> **`/init-project check` 这条斜杠命令不存在**，别去试。改成：直接读
> `skills/coding/init-project/SKILL.md`，按它的「路由 → 探测」路径手工执行一遍。
> SKILL.md 里写的模板路径是**装机后**的 `~/.claude/skills/init-project/assets/templates/code.yml`，
> 自测时换成工作区里的 `skills/coding/init-project/assets/templates/code.yml`。
> 这个替换**只在自测时做，不要去改 SKILL.md 里的路径**——那个路径对装机后的运行时是对的。

8. **`check` 模式零写入——空目录场景**
   新建一个空目录，按上面的方式手工走一遍 `check` 路径，跑完
   `ls -A <该目录>` 输出为空（一个字节都没写）。

9. **`check` 模式零写入——成熟仓库场景**
   在交接工作区根上按同样方式走一遍 `check`，跑完 `git status --short` 输出为空。
   且报告里 `README.md`/`CLAUDE.md`/`TODO.md`/`docs/` **不出现在缺失表里**（它们都已存在），
   `.gitignore` 出现并列出缺的状态规则行。

10. **全量测试绿**
    `npm test` exit 0。

11. **提交落在正确分支**
    `git rev-parse --abbrev-ref HEAD` 输出 `feature/init-project`，且 Task 1–4 各自的
    commit 都在这条分支上（`git log --oneline` 看得到）。

---

## 接手方自测记录（2026-09-21）

Task 1–4 全部实现并逐个提交后，逐条实跑「最小验收锚点」全集，命令均不接管道
（未用 `| tail` 等掩盖真实退出码）。全部绿，无带红送验的条目。

1. **模板校验器绿且覆盖五项** — PASS
   `node --test tests/templates.test.mjs`：exit 0，`# pass` 6（要求 ≥6）。

2. **校验器真的会拦** — PASS
   把 `code.yml` 的 `skills` 首项临时改成 `no-such-skill`，重跑：exit 1（同时触发了
   `skills 清单里每个名字都能查到` 与 `init_phases 引用的 skill 必须在 skills 清单里`
   两条断言失败，因为 `init_phases` 里的 `init-workflow` 也随之失去声明——这是预期的
   连锁失败，证明校验器确实会拦，不是误报）。改回后重跑：exit 0。
   `git diff --stat` 确认 `code.yml` 已干净还原到提交状态。

3. **skill 格式校验绿** — PASS
   `bats tests/skills.bats`：exit 0，8/8 `ok`。

4. **索引条目正确** — PASS
   锚点里给的校验脚本输出 `OK`。

5. **frontmatter 正确** — PASS
   `skills/coding/init-project/SKILL.md` 首 10 行核对：`name: init-project`、
   `version: "0.1.0"`、`user_invocable: true`，`description` 同时含 `/init-project`
   与 `check`。

6. **打包清单已重新生成** — PASS
   锚点里给的校验脚本输出 `OK`（`files[]` 含 `skills/coding/init-project/`）。

7. **骨架资产齐且 `.gitignore` 骨架带状态规则** — PASS
   `assets/skeleton/` 下四份文件（README.md / gitignore-code / CLAUDE.md / TODO.md）
   均存在；`grep -q '^\.hskill/\*/state\.json$' .../gitignore-code` exit 0。

8. **`check` 模式零写入——空目录场景** — PASS
   对 `/tmp/init-project-smoke`（新建的空目录）按 SKILL.md 的「路由 → 探测」手工走一遍
   （模板路径按锚点说明换成工作区内的 `skills/coding/init-project/assets/templates/code.yml`）：
   - 骨架：`docs` 目录与四份 scaffold 文件全部「缺失」。
   - skill：本机 9 个全部 `user.claude.status = up-to-date`（全局已装），落入「已在
     全局、跳过」，待装清单为空。
   - 初始化相位：`init-workflow` 无 probe → 「总会跑一遍」；`release-project` 的
     probe 路径 `.hskill/release-project/release-profile.md` 在该空目录下不存在 →
     「未跑过」。
   - `ls -A /tmp/init-project-smoke` 输出为空——零写入确认。

9. **`check` 模式零写入——成熟仓库场景** — PASS（锚点文字与本仓库当前实况有一处不符，
   已按实况判定，见下方说明）
   对交接工作区根按同样方式手工走一遍：
   - `README.md`/`CLAUDE.md`/`TODO.md`/`docs/` 全部不出现在缺失表里（已存在，`skip`
     模式无差距）。
   - `.gitignore` 出现：本仓库的 `.gitignore` 是「默认拒绝、逐项放行」写法（`*` 开头
     再 `!` 白名单），逐行比对后两条状态规则行（`.hskill/*/state.json`、
     `.hskill/sync-design/html/`）均不存在，按预期列为「缺 2 行」。
   - `init-workflow` 无 probe → 「总会跑一遍」，且没有因本仓库已有 `.githooks/` 而
     误报（该条目本就不设 probe，探测逻辑不会去看 `.githooks/`）。
   - **`release-project` 的实际探测结果是「已跑过」，与锚点原文「未跑过」不符**：
     `.hskill/release-project/release-profile.md` 在本仓库确实存在，`git log --oneline
     -- .hskill/release-project/release-profile.md` 显示它在 `fb95985`
     （`chore: migrate release-profile.md to .hskill/release-project/`）就已提交，
     早于本次交接分支。这是撰写锚点时对仓库现状的预判有误，不是 `## 探测` 判断逻辑
     的缺陷——探测逻辑只是如实读了 probe 路径的存在性。未改动 SKILL.md 去"迁就"这条
     过时描述。
   - `git status --short`：除本次交接文档与本自测记录本身的改动外，整个 check
     走查过程零写入。

10. **全量测试绿** — PASS
    `npm test`（未接管道，`echo "REAL_EXIT:$?" >> log` 直接落盘退出码）：`REAL_EXIT:0`。
    细分：bats 三套（165/34/13 项）全 `ok`；`run-skill-tests.sh` 汇总
    `14 passed, 0 failed (14 total)`；`node --test` 汇总 `tests 335 / pass 328 / fail 0`
    （其余为 suite 汇总项，非失败）。

    过程记录：中途两次全量跑（Task 3、Task 4 提交前）出现过 `tools/browser-fetch`
    与部分 `skills/research` 用例网络超时（`Page.goto` 访问 `https://example.com`
    30s 超时），但 `curl` 直连同一 URL 返回 200——判断是沙箱内无头浏览器网络栈的环境
    限制，与本次改动的文件（`package.json`、`tests/templates.test.mjs`、
    `skills/coding/init-project/*`、`skills-index.json`）完全不相交，且两次失败的
    具体用例集合不同（典型的网络超时抖动特征，不是稳定复现的回归）。本次锚点 10
    记录的是最终这次全绿的结果，不带红送验。

11. **提交落在正确分支** — PASS
    `git rev-parse --abbrev-ref HEAD` 输出 `feature/init-project`；
    `git log --oneline` 可见 Task 1–4 四个提交（`8f75877` / `794002f` / `cf9f403` /
    `3b38e4c`），均在这条分支上。

---

## 背景与现状

仓库里有 50 个 skill，24 个是 `installScope: project`，多数依赖一份项目级配置才能工作。
新开项目时这些配置一个都不存在，于是开工头几天会被零散的配置提问反复打断。

**这个 skill 是编排器，不是生成器。** 核心事实是：handoff、capture-vocab、setup-debug、
release-project、clean-git、sync-design、capture-insight、manage-dir 这八个 skill
**全都已经内建了**「配置不存在 → 问用户 → 写配置」的分支。缺的只是一个知道
「这类项目该有哪些 skill、按什么顺序把它们叫起来」的东西。

所以 `init-project` **不写任何 `.hskill/<skill>/` 配置文件**。这是整个设计的主线，
spec 里写成了可证伪的形式：如果实施中发现必须由它亲自写某份 skill 配置才能跑通，主线就是错的——
那时停下来找原 session，不要自己动手改设计。

**现状**：spec 与 plan 已提交，代码一行未写。工作树干净。

---

## 关键决定（别改动）

这八条都是和用户逐条确认过的，不要在实施中重新纠结或"顺手优化"：

1. **不写任何 skill 的项目级配置**，委托各 skill 自己的初始化分支（理由见上）。

2. **初始化分两档**。只有 `init-workflow`（整个 skill 就是初始化入口）和 `release-project`
   （显式 Init/Execute 两相位）能被单独叫起来跑初始化。其余六个的初始化是**干活时的副作用**，
   没有独立入口——要让 handoff 生成 `config.md`，只能假装去写一份交接文档，那是误用。
   所以它们只安装，在收尾清单里登记成「首次使用时会问你 X」。
   **不要为了"初始化更完整"去改那六个 skill**——那是另一件事，明确不在本次范围内。

3. **`installScope` 必须是 `global`**。这个 skill 要在一个**还不存在**的项目里被调起来，
   不可能事先装在那里。别照抄 `mint/init-skill` 的 `project`——那个只在本仓库内用，情况相反。

4. **模板只在 skill 仓库里**（`assets/templates/*.yml`），跟版本号走，改模板 = 改 skill。
   不要引入 `~/.hskill/init-project/templates/` 的用户副本——用户明确否掉了，理由是双套模板会分叉。

5. **本期只做 `code` 一套模板**。不要顺手加 writing / research 模板。

6. **不升级已装的 skill**。`hskill status --json` 里 `update` 状态（全局装了旧版）
   按「已有」处理、跳过，只在收尾清单提示一句 `hskill outdated`。
   升级全局 skill 会波及所有项目，不该由初始化某个项目顺手触发。

7. **`probe` 只加在重复调用有破坏性的条目上**。`release-project` 的 `invoke` 是
   `/release-project 重新初始化`，而「重新初始化」在它 SKILL.md 里是**显式覆盖旧 profile**
   的指令——没有 `probe` 的话第二次跑 init-project 会把用户调好的 profile 冲掉。
   `init-workflow` **不加** `probe`：它自己有差量检测，重跑不但安全还能检出配置漂移，
   加了反而把这个能力关掉。

8. **`check` 的判断逻辑只有一份**。它存在于 SKILL.md 的 `## 探测` 一节，
   `references/check-report.md` 只管报告排版。一旦报告文档里冒出新的判断规则，
   两条路径就开始分叉——那比没有 `check` 更糟，因为它会报「缺 X」而执行路径不装 X。

---

## 范围铁律

**In：**
- 新建 `skills/coding/init-project/`（SKILL.md + assets/templates/code.yml +
  assets/skeleton/ 四份 + references/ 两份）
- 新建 `tests/templates.test.mjs`
- 改 `package.json`（devDependency `js-yaml`、`scripts.test`、以及由
  `node scripts/generate-npmignore.js` 重新生成的 `files[]`）
- 改 `skills-index.json`（新增一条 + `bundleMeta.coding` 描述补上新 skill）

**Out：**
- **不改任何现有 skill 的内容**。一个字都不改。
- 不加第二套模板
- 不实现语言脚手架生成、不碰远程仓库、不装 shell tool（这三条同时也是 skill 自身的边界，
  要写进 SKILL.md 的「边界」一节）
- **不合并到 `staging`**。合并由原 session 在验收通过后做。

---

## 相关文档索引

| 文档 | 作用 |
|---|---|
| `docs/superpowers/specs/2026-09-21-init-project-design.md` | 设计权威。有分歧以它为准 |
| `docs/superpowers/plans/2026-09-21-init-project.md` | **实施权威**。Task 1–4 含完整代码与验证步骤，照着做 |
| `.hskill/handoff/config.md` | 本仓库的分支/验证约定 |
| `docs/reference/testing-guide.md` | 写新测试前读 |
| `docs/reference/todo-format-spec.md` | TODO.md 骨架必须符合它，否则 capture-todo 的 parser 认不出分区 |
| `skills/coding/capture-vocab/SKILL.md` | SKILL.md 的行文与渐进式披露范式，40 行，照这个密度写 |

**受影响文件的完整清单在 plan 的每个 Task 的 `**Files:**` 块里**，本文档不重抄——
抄一遍就多一个会过期的真相源。

---

## 工作流约定

摘自 `.hskill/handoff/config.md`，与本次相关的部分：

- 分支模型 `main <- staging <- {feature,fix,chore,doc,release}/*`；`main`/`staging`
  由 `.githooks/pre-commit` 禁止直提。
- commit-msg hook 强制 Conventional Commits，类型是 **`docs`** 不是 `doc`（`doc(...)` 会被拒）。
- 进工作区后先补两条 git 配置（**不配的话 staging/main 直提保护失效**）：
  ```bash
  git config core.hooksPath .githooks
  git config merge.ff false
  ```
- **`executing-plans` 会要求先调 `using-git-worktrees` 建隔离工作区——跳过那一步。**
  工作区已经建好了，它会在 `.worktrees/` 下另建一个、还另起一条分支，交接链当场断掉。
  （该 skill 已在 `.claude/settings.json` 的 `skillOverrides` 里关掉，但别依赖它，看到就跳过。）
- 完工前不合并；合并只由原 session 做。

---

## 验证步骤

「最小验收锚点」已是自解释的硬判据，这里只补三个**会让你踩坑**的点：

**一、`contentHash` 不要编。** `config.md` 说改了 skill 内容要更新 `skills-index.json` 的
`contentHash` / `contentVersion`。本次是**新增条目**，plan 里的条目只写了
`path`/`bundle`/`installScope`——这是刻意的：`contentHash` 的算法在本仓库里查不清，
`docs/commute/2026-09-20-capture-vocab-retrieval-handoff.md:114-119` 记录了这个未解问题，
结论是「查不清就别动，编一个值比留着旧值更糟」。它唯一的消费者是
`tools/skill-harness/coverage.js:26-38`，那里对缺失值有 `?? null` 兜底，省略不会让任何测试变红。
**照 plan 写，不要自作主张补这两个字段。**

**二、Task 3 做完时 `references/check-report.md` 还不存在**，而 SKILL.md 末尾的参考表已经指向它。
`bats tests/skills.bats` 不校验 references 链接，所以不会红——但**Task 4 结束前这份交接不算完**。
别在 Task 3 之后就推「待验收」。

**三、锚点 2 是防恒真测试的。** 先确认校验器在坏数据上真的会红，再确认好数据上绿。
只跑绿的那一次，证明不了测试有效。

**另外要复跑的既有资产**：`npm test` 全量（锚点 10）。本次改了 `package.json` 的 `scripts.test`
和 `files[]`，全量跑一遍才知道没碰坏别的。

---

## 一个需要你知道的现实状况

这条分支从 `staging` 的 `bae7082` 拉出，而 `staging` 此刻已经前进到 `1466ef7`——
交接期间有别的 session 合并了东西进去。**这不影响你干活**（本次改动的文件与它们没有重叠面），
也**不需要你去 rebase 或 merge**。合并时的冲突处理由原 session 负责。
你只管在 `feature/init-project` 上把 Task 1–4 做完。

---

## 原 session 验收记录（2026-09-21）

在交接工作区 `/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+init-project`
（分支 `feature/init-project`）内逐条重跑，**不采信接手方结论**。与接手方自测记录并列，不覆盖。
机器校验 `validate-handoff.sh` exit 0。

| 锚点 | 结果 | 实跑证据 |
|---|---|---|
| 1 模板校验器 | PASS | `node --test tests/templates.test.mjs` exit 0，`pass 6`（≥6） |
| 2 校验器真会拦 | PASS | 改 `no-such-skill` 后 exit 1；还原后 exit 0；`git status --short` 确认 code.yml 干净 |
| 3 skill 格式校验 | PASS | `bats tests/skills.bats` exit 0，8/8 `ok` |
| 4 索引条目 | PASS | 校验脚本输出 `OK` |
| 5 frontmatter | PASS | `name: init-project` / `version: "0.1.0"` / `user_invocable: true`，description 含 `/init-project` 与 `check` |
| 6 打包清单 | PASS | 校验脚本输出 `OK` |
| 7 骨架资产 | PASS | 四份齐；`grep -q '^\.hskill/\*/state\.json$'` exit 0 |
| 8 check 零写入（空目录） | PASS | 见下 |
| 9 check 零写入（成熟仓库） | PASS | 见下 |
| 10 `npm test` | **红，归因为既有环境抖动，判定不构成未达成** | 见下 |
| 11 提交落分支 | PASS | HEAD=`feature/init-project`；四个 Task 提交 `8f75877`/`794002f`/`cf9f403`/`3b38e4c` 均在本分支 |

### 锚点 8 实跑

对新建空目录 `/tmp/accept-smoke` 按 SKILL.md 的「路由 → 探测」手工走一遍：

- 骨架：`docs`/`README.md`/`CLAUDE.md`/`TODO.md`/ignore 文件全部「缺失」
- skill：`hskill status --json` exit 0，模板声明的 9 个全部 `user.claude.status = up-to-date`，
  待装清单为空
- 相位：`release-project` probe 路径不存在 →「未跑过」；`init-workflow` 无 probe →「总会跑一遍」
- **`ls -A /tmp/accept-smoke` 计数 0**——零写入确认

### 锚点 9 实跑

对本工作区根同样走一遍：

- `docs`/`README.md`/`CLAUDE.md`/`TODO.md` 全部「存在（skip，无差距）」，不进缺失表
- ignore 文件：两条状态规则 `.hskill/*/state.json`、`.hskill/sync-design/html/` 逐行比对均「缺」，
  按 `append-missing-lines` 列为待补
- **`git status --short` 为空**——零写入确认

**更正接手方自测记录中锚点 9 的一处描述**（显式写出，不静默改）：自测记录称
`release-project` 的实际探测结果与锚点原文「未跑过」不符。我复核确认**接手方是对的**——
`.hskill/release-project/release-profile.md` 在本仓库确实存在，
`git log --oneline -1 -- .hskill/release-project/release-profile.md` 输出 `fb95985`，
且 `git merge-base --is-ancestor fb95985 bae7082` 成立，即该文件早于本分支基线。
**错在撰写锚点的我**（对仓库现状预判有误），不在探测逻辑，也不在接手方。
接手方没有为迁就过时描述去改 SKILL.md，处理正确。

### 锚点 10：红，以及为什么判定不构成未达成

我这次 `npm test` 实跑 **REAL_EXIT=1**（退出码直接落盘，未接管道），7 条失败：

- `skills/research/clip-url`：3 条
- `tools/browser-fetch`：4 条

接手方自测记录该条写的是 `REAL_EXIT:0`。**两个结果都是真的**——这套用例是抖的。归因证据三项：

1. **被测代码两端逐字节相同**：`git diff --stat bae7082..HEAD -- tools/browser-fetch/ skills/research/clip-url/`
   无输出。本分支改动的 16 个文件（见 `git diff --name-only bae7082..HEAD`）与这两个目录不相交。
2. **失败集合在不同轮次间不一致**：把 browser-fetch 那 4 条单独重跑，2 条转绿、2 条仍红；
   再把其中一条 `test_page_auth_with_empty_profile_injects_nothing` 完全单跑 → exit 0 通过。
   稳定回归不会这样。
3. **失败形态全是网络**：7 条的报错都是 `Page.goto: Timeout 30000ms exceeded` 访问
   `https://example.com/`；同一时刻 `curl https://example.com` 返回 HTTP 200。
   是沙箱内无头浏览器网络栈的环境限制。

**判定：达成。** 锚点 10 字面是红的，此处显式记录，不粉饰；但红因可归到本次改动之外的既有
环境抖动，不作为未达成的依据。

**遗留给后续的一笔**（不属于本次交接范围）：`tools/browser-fetch` 与 `skills/research/clip-url`
有 7 条用例依赖真实外网，在受限网络下会随机变红，使 `npm test` 不再是可靠的门禁信号。
建议后续单开一条分支把这些用例改成打桩或标记为 network-gated。
