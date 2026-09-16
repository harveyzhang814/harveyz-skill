---
status: 待执行
date: 2026-09-15
author_model: Claude Opus 5
acceptance: hard
branch: feature/hskill-install-source
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+hskill-install-source
source_node: 094dd366-9af1-490c-b001-23e8458cc1b0
target_node:
---

# 交接：实施 hskill 双来源安装与粘性更新

**交接目的**：spec 已定稿并提交，把实施工作交给下一个 session 续做——拆任务、写代码、写测试，不需要再做设计决策。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，按「工作流约定」开工。**完成后把 frontmatter 的 `status` 置为「待验收」并停在这里**——`已验收` / `打回` 由原 session 按「最小验收锚点」判定后写，不要代填。你的自测结果写成独立小节，别写进原 session 的验收记录里。
>
> **开工前**：若你也在 Agent Canvas 画布节点里，先建一条 `hands-off-to` 关系（`agent-canvas-ctl whoami` 取自己的 id，核对 `node-relations` 里没有后 `link-nodes --from 094dd366-9af1-490c-b001-23e8458cc1b0 --to <自己> --type hands-off-to`），建完把自己的 id 填进 `target_node`。**只建这一条**——别建 `implements`、别另立需求节点。
>
> **在哪开工**：工作区已由原 session 建好，进 frontmatter 的 `worktree` 干活，核对当前分支与 `branch` 一致。Claude Code 用 `EnterWorktree(path: <worktree>)` 的 `path` 模式；没有这类能力就每条命令自带限定 `git -C <worktree>`，读写文件用绝对路径，别靠裸 `cd`——它只在单条命令内有效。**不要自己 `git worktree add`**（那条分支已被这个工作区占用，再建会失败，而且原 session 验收时回的是它自己建的那个，看不到你的改动），**也绝不要销毁它**——验收还要用。路径不存在就打回原 session 重建。

---

## 背景与现状

今天 `hskill update` 是一行硬编码 `npm install -g harveyz-skill@latest`，整个更新机制只有 npm 远端一条轨道。想在发 npm 之前先把工作树装成全局 hskill 用一阵子，只能手工 `npm install -g <路径>`；而一旦这么做，下次随手一句 `hskill update` 就会静默把它替换回 npm 上的版本，没有提示、没有报错，事后从 `hskill version` 也看不出发生过替换。

本次要做的就是消灭这个静默替换，让两种来源共存于同一个 CLI。

完整设计见 **`docs/superpowers/specs/2026-09-15-hskill-install-source-design.md`**（已提交在本分支 `da797e8`）。**那份 spec 是唯一权威**，本文档只负责交接，不复述设计细节。

现状：本分支从 `staging`（`8f63508`）拉出，除 spec 一个新文件外无其他改动，工作树干净。

## 关键决定（别改动）

这五条是设计阶段逐条讨论定下的，每条都有被"优化"掉的诱惑。改动前必须回来问原 session。

1. **本地安装走 `npm pack` + `npm install -g <tgz>`，不走 `npm install -g <目录>`。**
   后者在 npm 11 上建的是**软链**（实测），拿不到独立快照，还绕过 `files[]` 白名单——未发布和 archived 的 skill 会出现在列表里，与"预演真实发布"的目的相反。

2. **`update` 是粘性的**：本地装的就从原仓库重新 pack，npm 装的就走 registry。**不做版本号比较后自动选新的**——开发分支版本号未必单调递增，自动推断会在错误的时刻把用户弹到另一条轨道上，那正是本次要消灭的故障的变体。

3. **来源痕迹只能写在全局安装目录里**（`$(npm root -g)/harveyz-skill/` 下的 `.hskill-source.json` + `package.json` 的 `+local` 后缀）。**不得写到 `~/.hskill/`、`~/.config/`、环境变量或任何用户级配置**。理由是 `npm install -g` 会清空并重建安装目录（实测），写在里面的痕迹会被下一次安装——包括用户绕过 hskill 手工跑的那次——自动抹掉，使"记录的来源"与"实际的来源"不可能分叉。写在外面就会留下能撒谎的陈旧状态。这是 spec §0 的主线，推翻它等于推翻整个设计。

4. **版本后缀只标 `+local`，不含分支与 commit。** 版本串只承担"是不是本地装的"这一个标识职责；新旧判断全部交给 `.hskill-source.json` 里的 `commit`。别为了信息量把 branch/sha 塞回版本串——那会连带引入分支名洗字符的问题（build metadata 只允许 `[0-9A-Za-z-]`）。

5. **`--local` 的路径必须显式给出**，不回退到当前目录。回退到 cwd 意味着在别的仓库里手滑跑一次就会试图安装别的包。

## 范围铁律

**in**：`bin/cli.js` 的 `update` / `version` 两个子命令、`lib/version-check.js` 的 `compareVersions`、新增 `lib/install-source.js`、对应测试、`printHelp()` 里 `update` 相关的用法行。

**out**（spec §9 明确不做，逐条都别顺手做）：
- 不加第三种来源（软链 / `npm link`）
- 不做从固定 git ref（如 `staging`）打包
- 不做自动来源推断
- **不改 `hskill install` / `hskill upgrade`** —— skill 内容如何落到 `~/.claude/skills/` 与本次无关
- 不重构 `bin/cli.js` 的整体结构。它是扁平顶层脚本、每个子命令块自己 `process.exit()` 结尾（文件里有注释解释为什么不能用 `return`），照这个既有形状加，别改架构

## 相关文档索引

| 文档 | 用途 |
|---|---|
| `docs/superpowers/specs/2026-09-15-hskill-install-source-design.md` | **本次唯一权威设计**。§2 那四条实测事实是整个设计的地基，实施中若与观察不符，先复验再改设计 |
| `docs/reference/testing-guide.md` | 写新测试前必读 |
| `docs/reference/git-workflow.md` | 分支与提交规范（自动生成，勿手改） |
| `CLAUDE.md` | 仓库定位与 skill 结构约定 |

## 受影响文件/落点

| 文件 | 动作 |
|---|---|
| `lib/install-source.js` | **新建**。四个导出：`globalRoot()` / `readSource()` / `writeSource()` / `gitInfo()`，见 spec §4 |
| `bin/cli.js` | 改 `update` 块（约 226–256 行）加来源分叉与 `--local` / `--npm` 旗标；改 `version` 块（约 159–179 行）加来源展示与 `--check` 分叉；改 `printHelp()` 补用法行 |
| `lib/version-check.js` | 改 `compareVersions`，比较前截断 `+` 及其后内容 |
| `tests/install-source.bats` | **新建** |
| `tests/version-check.bats` | 扩写 |

**实施顺序上的一个坑**：`lib/version-check.js` 的 `compareVersions` 修复不是可选项，**且要先做**。它现在是 `a.split('.').map(Number)`，喂 `0.33.0+local` 得到 `[0, 33, NaN]`，比较结果无意义；不先修的话，本地安装之后连 npm 来源的 `version --check` 路径也会跟着坏。

**另一个坑**：本仓库的 `prepack` 是 `node scripts/generate-npmignore.js`，它写入的 `.npmignore` **是被 git 跟踪的**（`.gitignore` 第 15 行 `!.npmignore` 显式反排除）。所以 `npm pack` 会弄脏工作树，git 信息必须在 pack **之前**采集，否则 `dirty` 恒为真。详见 spec §6.4。

## 工作流约定

- 就在本工作区、本分支 `feature/hskill-install-source` 上累积提交。**完工前不要合并到 staging**，合并只由原 session 做。
- 进来后补上：`git config core.hooksPath .githooks && git config merge.ff false`
- commit-msg hook 强制 Conventional Commits，类型是 **`docs`** 不是 `doc`。
- 建议先用 `superpowers:writing-plans` 从 spec 拆任务，再用 `superpowers:executing-plans` 执行。
- **`executing-plans` 会要求先调 `using-git-worktrees` 建隔离工作区——跳过那一步。** 工作区已经建好了，它会在 `.worktrees/` 下另建一个、还另起一条分支，交接链当场断掉。（该 skill 已在 `.claude/settings.json` 的 `skillOverrides` 里关掉，但别依赖它，看到就跳过。）

## 验证步骤

1. `npm test` —— 覆盖 hskill CLI 行为 + 所有 skill 的 SKILL.md 格式校验。
2. 新增测试按 spec §7 的七类覆盖，用 `HSKILL_GLOBAL_ROOT` 把全局安装目录指到临时目录、PATH 上放 `npm` shim 拦真实安装。**真实的 `npm install -g` 不进自动化测试**（会改动跑测试那台机器的全局环境）。
3. spec §8 那份人工清单（六条）由你实跑一遍，结果写进本文档的自测小节。这部分拦不住自动化测试——spec §2 那四条 npm 行为事实全是实测得来的，只有真装一次才验得到。

## 最小验收锚点

以下五条逐条对/错，全绿才算达成：

1. `npm test` 全绿。
2. `tests/install-source.bats` 存在，且覆盖 spec §7 列出的全部七类断言（`readSource` 缺失/损坏、粘性分叉、旗标误用、repo 失效、`compareVersions` build metadata、`version --check` local 三分支、`version` 在 npm 来源下输出不变）。
3. `compareVersions('0.33.0+local', '0.33.0') === 0` 且 `compareVersions('0.33.0+local', '0.34.0') < 0`。
4. `grep -rn "hskill-source" lib/ bin/` 的所有结果，路径基准都是 `globalRoot()`，**没有任何一处**用 `path.join(__dirname, '..')` 或指向 `~/.hskill/` —— 这条是关键决定 3 的可证伪形式。
5. 本文档里有你留下的 spec §8 人工清单六条实跑记录，每条写明实际观察到什么（不是"已完成"三个字）。
