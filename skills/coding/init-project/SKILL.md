---
name: init-project
version: "0.1.0"
description: Bootstrap a new project repository around the harveyz-skill toolchain, or audit an existing repo for what it is missing. Builds the repo skeleton, resolves and installs the skills the project type needs, and runs the initialization phases that can be triggered standalone. Invoke with /init-project [path] to set up, or /init-project check [path] for a read-only report of what is missing. Triggers: 'initialize a new project', 'set up a new repo', 'bootstrap this project', 'what is this repo missing', '新项目初始化', '这个仓库还缺什么'.
user_invocable: true
---

# Project Initialization

按声明式模板给项目接上 harveyz-skill 工具链。两种用法：

```
/init-project [路径]         # 执行：建骨架、补 skill、跑初始化
/init-project check [路径]   # 只读：报告缺什么，不写任何文件
```

路径省略则用当前工作目录。

**这个 skill 不写任何 `.hskill/<skill>/` 配置**——那些归各 skill 自己，它们都内建了
「配置不存在就问用户并写下来」的分支。本 skill 只做编排。

## 边界：明确不做的五件事

1. **不生成语言脚手架**，只打印 `language_hints` 里的命令
2. **不写任何 `.hskill/<skill>/` 配置**
3. **不升级已装的 skill**——升级全局 skill 会波及所有项目，不该由初始化某个项目顺手触发
4. **不碰远程仓库**（`git remote add` / `gh repo create`），只在收尾清单里给出命令
5. **不装 shell tool**（`hskill install --tool` 是全局动作，不属于初始化某个项目）

## 探测

三项只读检查，执行路径和 `check` 路径**都用这一节**，不各写一遍。
先读模板 `~/.claude/skills/init-project/assets/templates/<模板名>.yml`，然后：

| 检查项 | 怎么查 |
|---|---|
| 骨架缺什么 | 对 `scaffold.dirs` 与 `scaffold.files[].path` 逐个查存在性。`on_exists: append-missing-lines` 的文件即使存在也要逐行比对，记下缺哪几行 |
| skill 缺什么 | `cd <PROJECT> && hskill status --json`，对 `skills[]` 每个名字看 `user.claude.status`：非 `none` 则记「全局已有，跳过」；为 `none` 再看 `project.claude.status`，仍为 `none` 才记入待装清单 |
| 初始化相位缺什么 | 对有 `probe` 的条目查该路径是否存在，存在则记「已跑过」 |

**`update` 状态（全局装了旧版）按「已有」处理，不升级。** 收尾时提示一句 `hskill outdated`，
把决定权留给用户。

**cwd 必须锁在项目根。** `hskill` 的 project 档是从 `process.cwd()` 推出来的，
cwd 错了它会静默去查/写别的目录，不报错。每条命令都写成 `cd <PROJECT> && hskill ...`。

## 路由

用户参数里有 `check` → 只跑「探测」，按 `references/check-report.md` 输出报告，**到此为止**。
否则走下面的 Step 0–5。

## Step 0 — 落点与模板

1. 确定目标目录绝对路径。不存在则问用户是否创建。
2. 选模板：列出 `assets/templates/` 下所有 `.yml`，让用户选。只有一套时仍然显式确认。
3. **建 todo，Step 0–5 每步一条**。Step 3 会把控制权交给别的 skill，没有 todo 钉住就回不来。

## Step 1 — 骨架落盘

`scaffold.git_init: true` 且目标目录不是 git 仓库 → 问用户是否 `git init`；拒绝则跳过，
并记下「Step 3 的 init_phases 可能因此失败」。

按 `scaffold.dirs` 建目录（已存在则跳过）。按 `scaffold.files[]` 拷文件，
源路径是 `~/.claude/skills/init-project/assets/<from>`：

| `on_exists` | 目标已存在时 |
|---|---|
| `skip`（默认，字段缺省即此值） | 整体不动，记「已跳过」 |
| `append-missing-lines` | 逐行比对，只追加缺失的行，记下实际追加了哪几行 |

拷贝时把内容里的 `{{PROJECT_NAME}}` 替换为项目目录名。这是唯一的占位符。

**能力上限，Step 5 要明说**：这一步只认同名文件。仓库里若已有一套自己的钩子目录，
或 `CONTRIBUTING.md` 已经承担了 `CLAUDE.md` 的部分职责，本 skill 照样会新建一个
`CLAUDE.md`——它看不出「同一件事换了个名字」。

→ 回到 Step 2。

## Step 2 — 差量安装 skill

按「探测」第二项算出待装清单。清单非空则一次性装完：

```bash
cd <PROJECT> && hskill install --skill <a> --skill <b> --scope project --target claude
```

清单为空则跳过，记「全部已有」。

→ 回到 Step 3。

## Step 3 — 初始化相位编排

按 `init_phases` 数组顺序，每条依次判断：

1. 有 `probe` 且该路径已存在 → 跳过整条，记「已跑过」
2. 有 `ask_first` → 原样问用户，答否则跳过整条
3. 调用 `invoke` 里的命令

**每调用完一条，立刻回到本 Step 处理下一条；全部处理完回到 Step 4。**
`invoke` 会把控制权交给另一个 skill（`/init-workflow` 有它自己的多步流程），
不显式写回跳点就会在那里结束，Step 4、5 再没人执行。用 todo 逐条核对。

单条失败**不中断主流程**——例如用户拒绝 `git init` 导致 `init-workflow` 优雅停止，
记为「跳过」并写下原因，继续下一条。

→ 全部处理完，回到 Step 4。

## Step 4 — 登记

`register.hub: true` 且 `hub` 在 PATH：

```bash
hub projects add <目录名> --path <绝对路径> --desc <一句话描述>
```

这条是「注册或更新」，重复调用安全。`hub` 不在 PATH → 跳过，把命令写进收尾清单。

→ 回到 Step 5。

## Step 5 — 收尾清单

五段，缺的段不输出空标题：

1. **已建** — 新建的文件与目录 / 已跳过的（因已存在）/ `.gitignore` 实际追加的行
2. **已装** — 装到项目级的 skill / 跳过的（因全局已有，注明版本状态）
3. **已初始化** — 跑完的相位 / 跳过的及原因
4. **待办** — `language_hints` 全部命令、下表里首次使用时会问你配置的 skill、
   需要时的 `hskill outdated`、以及 `git remote add origin <url>`
5. **请自行核对** — 本次新建的文件清单，提示用户确认有没有和仓库既有约定重复
   （只在确实新建了文件时输出）

第 4 段里那批 skill 的配置是懒创建的，本 skill 不代写：

| skill | 首次使用时会问 |
|---|---|
| `handoff` | 本项目的交接约定（输出路径、分支工作流、验证工具） |
| `capture-vocab` | 无需配置，首次 `add` 时自动建 `vocab.md` |
| `clean-git` | 分支清理规则，跑完问是否存为配置 |
| `capture-insight` | insights 落盘位置 |
| `sync-design`（若装了） | manifest 的 `outputDir` 与 `baseBranch` |
| `manage-dir`（若装了） | 目标目录的组织方法论 |

## 失败态

| 情况 | 处理 |
|---|---|
| 目标目录已是 git 仓库 | `git_init` 跳过，其余照常 |
| `hskill` 不在 PATH | Step 2、3 整体降级为「打印待办」（skill 装不上，相位也调不起来），Step 1/4/5 照常走完 |
| 模板 YAML 解析失败或顶层字段缺失 | 硬停，指出缺哪个字段 |
| 用户拒绝 `git init` | Step 1 其余照常；Step 3 里依赖 git 的相位记「跳过」 |

## 参考

| 要做的事 | 读哪份 |
|---|---|
| 加一套新模板、模板字段完整语义 | `references/template-schema.md` |
| `check` 报告的输出格式 | `references/check-report.md` |
