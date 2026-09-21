# init-project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `init-project` skill——按声明式模板为新项目建仓库骨架、差量补齐 skill、编排可独立触发的初始化相位，并提供只读诊断模式给已有仓库补缺。

**Architecture:** 模板（`assets/templates/*.yml`）是数据，SKILL.md 是执行器。执行器不含任何项目类型的具体知识，也不写任何 `.hskill/<skill>/` 配置——那些归各 skill 自己。两条路径（执行 / `check`）共用同一段「探测」描述。

**Tech Stack:** Markdown skill（Claude 解析 YAML 模板）、Node `node:test` + `js-yaml`（模板校验）、bats（既有 skill 格式校验）

**Spec:** `docs/superpowers/specs/2026-09-21-init-project-design.md`

## Global Constraints

- 新 skill 路径：`skills/coding/init-project/`，frontmatter `name: init-project`、`version: "0.1.0"`、`user_invocable: true`
- `skills-index.json` 条目：`path: "coding/init-project"`、`bundle: "coding"`、`installScope: "global"`
- **`installScope` 必须是 `global`**——这个 skill 要在还不存在的项目里被调起，不可能事先装在那里
- SKILL.md 每次 invoke 全文进上下文：主文件只留高频路径，低频内容进 `references/`（对齐 `skills/coding/capture-vocab/SKILL.md` 的做法）
- 运行时模板路径是**安装后**的位置：`~/.claude/skills/init-project/assets/templates/<name>.yml`，不是源码仓库路径
- 所有 `hskill` 调用必须写成 `cd <PROJECT> && hskill ...`——project 档由 `process.cwd()` 推出（`lib/bundles.js:158`）
- 本仓库分支规范：在 `feature/init-project` 上提交，不直接提 `staging`/`main`

### 偏离 spec 的一处，实施时按本计划执行

spec 未提及骨架文件的变量替换。skeleton 里的 `README.md` / `CLAUDE.md` 需要项目名，
本计划引入**一个**占位符 `{{PROJECT_NAME}}`，拷贝时替换为项目目录名。不引入任何其他变量，
也不引入表达式——多一个变量就是多一套模板语言。

---

## Task 1: 模板 schema、code.yml 与校验器

**Files:**
- Create: `tests/templates.test.mjs`
- Create: `skills/coding/init-project/assets/templates/code.yml`
- Create: `skills/coding/init-project/references/template-schema.md`
- Modify: `package.json`（新增 `devDependencies.js-yaml`、`scripts.test` 加一个测试文件）

**Interfaces:**
- Consumes: `skills-index.json` 的 `skills[].path`（取 basename 作为 skill 名）
- Produces: 模板 YAML 的字段契约——`name`、`scaffold.{git_init,dirs,files[]}`、`skills[]`、`init_phases[].{skill,probe?,invoke,ask_first?}`、`language_hints`、`register.hub`。Task 2 校验 `scaffold.files[].from`，Task 3/4 的 SKILL.md 读这些字段。

- [ ] **Step 1: 装 js-yaml 并挂上测试入口**

先装依赖（`package.json` 目前没有 `devDependencies` 段，这条命令会自己建）：

```bash
npm install js-yaml --save-dev
```

再手工改 `scripts.test`，在 `node --test` 的文件列表里插入新测试：

```json
  "scripts": {
    "prepack": "node scripts/generate-npmignore.js",
    "test": "bats tests/ && bash scripts/run-skill-tests.sh && node --test tests/mcp.test.mjs tests/templates.test.mjs tests/harness/*.test.mjs"
  },
```

选 `js-yaml` 而不是复用 python3 + PyYAML：PyYAML 在本机装着，但不在仓库任何依赖清单里，
测试会在没装它的机器上静默失效。devDependency 不进 npm 包，成本只有一条开发期依赖。

- [ ] **Step 2: 写校验测试（此时必然失败）**

创建 `tests/templates.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import yaml from 'js-yaml'

const root        = path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
const templateDir = path.join(root, 'skills/coding/init-project/assets/templates')
const index       = JSON.parse(readFileSync(path.join(root, 'skills-index.json'), 'utf8'))
const knownSkills = new Set(index.skills.map(s => path.basename(s.path)))

const templates = readdirSync(templateDir)
  .filter(f => f.endsWith('.yml'))
  .map(f => ({ file: f, doc: yaml.load(readFileSync(path.join(templateDir, f), 'utf8')) }))

test('模板目录至少有一套模板', () => {
  assert.ok(templates.length > 0, `没有 .yml 模板：${templateDir}`)
})

for (const { file, doc } of templates) {
  test(`${file}: name + 五段齐全`, () => {
    for (const key of ['name', 'scaffold', 'skills', 'init_phases', 'language_hints', 'register']) {
      assert.notEqual(doc[key], undefined, `缺顶层字段: ${key}`)
    }
  })

  test(`${file}: init_phases 引用的 skill 必须在 skills 清单里`, () => {
    const declared = new Set(doc.skills)
    for (const phase of doc.init_phases) {
      assert.ok(declared.has(phase.skill), `init_phases 引用了未声明的 skill: ${phase.skill}`)
    }
  })

  test(`${file}: skills 清单里每个名字都能在 skills-index.json 查到`, () => {
    for (const name of doc.skills) {
      assert.ok(knownSkills.has(name), `skills-index.json 里没有这个 skill: ${name}`)
    }
  })

  test(`${file}: on_exists 取值合法`, () => {
    for (const f of doc.scaffold.files) {
      if (f.on_exists === undefined) continue
      assert.ok(['skip', 'append-missing-lines'].includes(f.on_exists),
        `${f.path}: 非法 on_exists=${f.on_exists}`)
    }
  })
}
```

- [ ] **Step 3: 跑测试确认失败**

Run: `node --test tests/templates.test.mjs`
Expected: FAIL，报 `ENOENT` —— `skills/coding/init-project/assets/templates` 不存在。

- [ ] **Step 4: 写 code.yml**

创建 `skills/coding/init-project/assets/templates/code.yml`：

```yaml
name: code

scaffold:
  git_init: true
  dirs: [docs]
  files:                       # on_exists 默认 skip
    - {path: README.md,  from: skeleton/README.md}
    - {path: .gitignore, from: skeleton/gitignore-code, on_exists: append-missing-lines}
    - {path: CLAUDE.md,  from: skeleton/CLAUDE.md}
    - {path: TODO.md,    from: skeleton/TODO.md}

skills:
  - init-workflow
  - clean-git
  - release-project
  - capture-todo
  - capture-insight
  - capture-vocab
  - handoff
  - question-me
  - rephrase

init_phases:
  - skill: init-workflow          # 无 probe：重复调用安全，它自己有差量检测
    invoke: "/init-workflow"
  - skill: release-project
    probe: .hskill/release-project/release-profile.md
    invoke: "/release-project 重新初始化"
    ask_first: "这个项目要发版吗？"

language_hints:
  node: "npm init -y"
  python: "uv init"
  rust: "cargo init"

register:
  hub: true
```

- [ ] **Step 5: 跑测试确认通过**

Run: `node --test tests/templates.test.mjs`
Expected: PASS，5 个 test 全绿（1 个目录非空 + 4 个 code.yml 检查）。

- [ ] **Step 6: 写 schema 参考文档**

创建 `skills/coding/init-project/references/template-schema.md`：

````markdown
# 模板 schema

模板放在本 skill 的 `assets/templates/<name>.yml`，跟 skill 版本号走——改模板 = 改 skill。
装机后的运行时路径是 `~/.claude/skills/init-project/assets/templates/<name>.yml`。

## 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | ✓ | 模板名，与文件名同 |
| `scaffold` | ✓ | 仓库骨架 |
| `skills` | ✓ | 要保证可用的 skill 名清单 |
| `init_phases` | ✓ | 要当场跑的初始化，按数组顺序执行 |
| `language_hints` | ✓ | 只打印、不执行的脚手架命令 |
| `register` | ✓ | 外部登记开关 |

## `scaffold`

```yaml
scaffold:
  git_init: true          # 目标目录不是 git 仓库时是否 git init
  dirs: [docs]            # 要创建的目录，已存在则跳过
  files:
    - path: .gitignore            # 相对项目根
      from: skeleton/gitignore-code   # 相对本 skill 的 assets/
      on_exists: append-missing-lines # 可选，默认 skip
```

`on_exists` 两个合法值：

| 取值 | 行为 | 用在 |
|---|---|---|
| `skip`（默认） | 文件已存在则整体不动 | README、CLAUDE.md、TODO.md——内容是项目自己的 |
| `append-missing-lines` | 逐行比对，只追加缺失的行 | `.gitignore` |

`append-missing-lines` 是纯文本行比对，不理解 ignore 文件的语义：已有整目录 ignore 规则时，
它仍会追加更细的那条，产生一条冗余规则。无害，但会让 `.gitignore` 变难看。

骨架文件里唯一的占位符是 `{{PROJECT_NAME}}`，拷贝时替换为项目目录名。没有其他变量，
也没有表达式——多一个变量就是多一套模板语言。

## `init_phases`

```yaml
init_phases:
  - skill: release-project
    probe: .hskill/release-project/release-profile.md   # 可选
    invoke: "/release-project 重新初始化"
    ask_first: "这个项目要发版吗？"                       # 可选
```

- `probe`：指向一份配置文件，**已存在则跳过整条**。只加在「重复调用有破坏性」的条目上。
  `init-workflow` 不加——它自己有差量检测，重跑不但安全，还能检出配置漂移；
  给它加 `probe` 反而会把这个能力关掉。
- `ask_first`：模板里唯一的条件逻辑口子，只接一句是非问，**不可嵌套**。
  条件逻辑一旦能嵌套，模板就变成了脚本语言，而脚本语言该写在 SKILL.md 里。
  代价是模板表达力封顶——真需要复杂分支时这套 schema 撑不住，得另想办法。

## 加一套新模板

1. 写 `assets/templates/<name>.yml`
2. 需要的骨架文件放 `assets/skeleton/`
3. 跑 `node --test tests/templates.test.mjs`——五项校验（含 `from` 路径存在性）自动覆盖新模板
````

- [ ] **Step 7: 跑全量测试并提交**

Run: `npm test`
Expected: 全绿。

```bash
git add package.json package-lock.json tests/templates.test.mjs skills/coding/init-project/
git commit -m "feat(init-project): 模板 schema、code.yml 与校验器

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: 骨架资产四份

**Files:**
- Create: `skills/coding/init-project/assets/skeleton/README.md`
- Create: `skills/coding/init-project/assets/skeleton/gitignore-code`
- Create: `skills/coding/init-project/assets/skeleton/CLAUDE.md`
- Create: `skills/coding/init-project/assets/skeleton/TODO.md`
- Modify: `tests/templates.test.mjs`（新增 `from` 路径存在性校验）

**Interfaces:**
- Consumes: Task 1 的 `scaffold.files[].from` 字段（相对 `assets/`）
- Produces: 四份骨架文件。Task 3 的 SKILL.md Step 1 按 `on_exists` 拷贝它们，并替换 `{{PROJECT_NAME}}`。

`.gitignore` 的文件名故意不叫 `.gitignore`——源码仓库里一个名为 `.gitignore` 的骨架文件
会被本仓库自己的 git 当成真的忽略规则。叫 `gitignore-code`，拷贝时改名。

- [ ] **Step 1: 写 from 路径校验（此时必然失败）**

在 `tests/templates.test.mjs` 的 `for` 循环内、`on_exists` 那个 test 之后追加：

```js
  test(`${file}: scaffold.files 的 from 路径都存在`, () => {
    const assetDir = path.join(templateDir, '..')
    for (const f of doc.scaffold.files) {
      const src = path.join(assetDir, f.from)
      assert.ok(existsSync(src), `找不到骨架资产: ${f.from}`)
    }
  })
```

并把文件顶部的 import 改为：

```js
import { readFileSync, readdirSync, existsSync } from 'node:fs'
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/templates.test.mjs`
Expected: FAIL，报 `找不到骨架资产: skeleton/README.md`（四条 from 全缺）。

- [ ] **Step 3: 写 README.md 骨架**

创建 `skills/coding/init-project/assets/skeleton/README.md`：

```markdown
# {{PROJECT_NAME}}

一句话说明这个项目做什么、给谁用。

## 快速开始

（安装与运行步骤）

## 文档

- [TODO.md](TODO.md) — 需求与任务
- [CLAUDE.md](CLAUDE.md) — 给 agent 的项目约定
```

- [ ] **Step 4: 写 gitignore-code 骨架**

创建 `skills/coding/init-project/assets/skeleton/gitignore-code`：

```
# --- harveyz-skill 运行时状态 ---
# .hskill/ 下的配置文件（workflow-config.yml、config.md、vocab.md）要进版本库，
# 团队共享；只有运行时状态不进。
.hskill/*/state.json
.hskill/sync-design/html/

# --- 通用 ---
.DS_Store
*.log
.env
.env.local

# --- 依赖与构建产物 ---
node_modules/
dist/
build/
__pycache__/
.venv/
target/
```

- [ ] **Step 5: 写 CLAUDE.md 骨架**

创建 `skills/coding/init-project/assets/skeleton/CLAUDE.md`：

```markdown
# CLAUDE.md

本文件给 Claude Code 提供 {{PROJECT_NAME}} 的项目约定。

## 项目概述

（一两句：做什么、给谁用、边界在哪）

## 开发命令

（构建、测试、运行——写实际能跑的命令，不写占位符）

## 约定

- 分支命名与合并流程：见 `docs/git-workflow.md`（由 `/init-workflow` 生成）
- 领域术语：见 `.hskill/capture-vocab/vocab.md`（由 `/capture-vocab` 维护）
- 需求与任务：见 `TODO.md`（由 `/capture-todo` 维护）
```

- [ ] **Step 6: 写 TODO.md 骨架**

创建 `skills/coding/init-project/assets/skeleton/TODO.md`。格式必须与
`docs/reference/todo-format-spec.md` 一致，否则 `capture-todo` 的 parser 认不出分区：

```markdown
# TODO / Backlog

## 🚧 待开发

---

## ✅ 已完成

---
```

- [ ] **Step 7: 跑测试确认通过并提交**

Run: `node --test tests/templates.test.mjs`
Expected: PASS，6 个 test 全绿。

```bash
git add skills/coding/init-project/assets/skeleton/ tests/templates.test.mjs
git commit -m "feat(init-project): 四份骨架资产与 from 路径校验

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: SKILL.md 执行路径与注册

**Files:**
- Create: `skills/coding/init-project/SKILL.md`
- Modify: `skills-index.json`（`skills[]` 新增一条）
- Modify: `package.json`（由 `node scripts/generate-npmignore.js` 重新生成 `files[]`）

**Interfaces:**
- Consumes: Task 1 的模板字段契约、Task 2 的骨架资产
- Produces: SKILL.md 里一节标题为 `## 探测` 的只读检查描述，Task 4 的 `check` 路径直接引用它，不另写一遍

- [ ] **Step 1: 写 SKILL.md**

创建 `skills/coding/init-project/SKILL.md`：

````markdown
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
````

- [ ] **Step 2: 注册到 skills-index.json**

在 `skills[]` 数组末尾（`agent-canvas/*` 之前的 coding 段落附近即可，顺序不影响校验）加：

```json
    {
      "path": "coding/init-project",
      "bundle": "coding",
      "installScope": "global"
    },
```

同时把 `bundleMeta.coding` 的描述补上新 skill：

```json
    "coding": "程序工具（init-project + init-workflow + setup-debug + init-goal + question-me + capture-vocab + rephrase + explain-pm）",
```

- [ ] **Step 3: 重新生成打包清单**

Run: `node scripts/generate-npmignore.js`
Expected: `package.json` 的 `files[]` 多出 `"skills/coding/init-project/"`。

- [ ] **Step 4: 跑 skill 格式校验**

Run: `bats tests/skills.bats`
Expected: PASS，8 个 test 全绿（SKILL.md 存在、frontmatter 分隔符、name/description/version 非空、semver、name 与目录名一致、bundle 在 bundleMeta 里）。

此时 `references/check-report.md` 还不存在，SKILL.md 末尾的参考表指向它——Task 4 补上。
`bats tests/skills.bats` 不校验 references 链接，所以这一步不会失败；Task 4 结束前不要合并。

- [ ] **Step 5: 跑全量测试并提交**

Run: `npm test`
Expected: 全绿。

```bash
git add skills/coding/init-project/SKILL.md skills-index.json package.json
git commit -m "feat(init-project): SKILL.md 执行路径与索引注册

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: check 只读模式与双场景验证

**Files:**
- Create: `skills/coding/init-project/references/check-report.md`
- Modify: `skills/coding/init-project/SKILL.md`（无改动则跳过——路由与探测节 Task 3 已写好；只在验证暴露问题时改）

**Interfaces:**
- Consumes: Task 3 的 `## 探测` 一节（`check` 只跑这一节然后停）
- Produces: 可复现的 `check` 报告格式

`check` 的判断逻辑**不在这里重写**。Task 3 的 `## 探测` 是唯一事实源，
本任务只定义报告怎么排版。若这里出现任何新的判断规则，说明两条路径开始分叉——
停下来把规则挪回 `## 探测`。

- [ ] **Step 1: 写报告格式参考**

创建 `skills/coding/init-project/references/check-report.md`：

````markdown
# `check` 报告格式

`/init-project check` 跑完 SKILL.md 的 `## 探测` 三项后输出本格式，**不写任何文件、
不装任何 skill、不调任何 init 相位、不问任何问题**——包括 `ask_first`，
它只报告「这条相位有 `ask_first`，执行时会先问你」。

## 输出

开头一行说明用了哪套模板和查的哪个目录：

```
模板 code，检查 /Users/x/Projects/foo
```

然后三张表。每张表**只列有差距的行**；整张表无差距则整表略去，在结尾汇总里说明。

### 骨架

| 文件 / 目录 | 状态 |
|---|---|
| `TODO.md` | 缺失 |
| `.gitignore` | 存在，缺 2 行：`.hskill/*/state.json`、`.hskill/sync-design/html/` |

### skill

| skill | 状态 |
|---|---|
| `handoff` | 两级都没装 |
| `capture-vocab` | 两级都没装 |

已在全局的不列进表，在表下用一行汇总：`已在全局、跳过：init-workflow、clean-git、…`。
其中处于 `update` 状态的（全局装了旧版）额外点名，并附一句
`需要时跑 hskill outdated 自行决定是否升级`——本 skill 不升级任何已装 skill。

### 初始化相位

| 相位 | 状态 |
|---|---|
| `init-workflow` | 无 probe，执行时总会跑一遍（它自己有差量检测） |
| `release-project` | 未跑过；执行时会先问「这个项目要发版吗？」 |

## 结尾

一行汇总 + 下一步命令：

```
骨架缺 1 项，skill 缺 2 个，初始化相位待跑 2 条。
执行：/init-project <路径>
```

三项全无差距时，只输出一行：

```
模板 code，检查 /Users/x/Projects/foo —— 无差距。
```
````

- [ ] **Step 2: 验证场景一——空目录**

这一步是人跑的烟雾测试，没有自动化断言：`check` 的输出是自然语言报告，
断言它的措辞只会锁死排版、拦不住判断逻辑出错。

**此刻 skill 还没装到 `~/.claude/skills/`，`/init-project check` 这条斜杠命令不存在。**
改成直接读工作区里的 `skills/coding/init-project/SKILL.md`，按它的「路由 → 探测」手工走一遍；
SKILL.md 里的模板路径 `~/.claude/skills/init-project/assets/templates/code.yml` 在自测时
换成 `skills/coding/init-project/assets/templates/code.yml`。**只在自测时替换，不要改 SKILL.md**——
那个路径对装机后的运行时是对的。

```bash
mkdir -p /tmp/init-project-smoke
```

对 `/tmp/init-project-smoke` 走一遍 `check`。

Expected：骨架四项全部「缺失」；skill 表只列本机全局没装的那些（多数应落在
「已在全局、跳过」那行）；初始化相位两条——`init-workflow` 标注「总会跑一遍」，
`release-project` 标注「未跑过」。**没有任何文件被创建**——跑完
`ls -a /tmp/init-project-smoke` 应只有 `.`、`..`。

- [ ] **Step 3: 验证场景二——成熟仓库**

在交接工作区根上按 Step 2 的同样方式走一遍 `check`（本仓库跑了很久，是真实的补缺场景）。

Expected：
- `README.md` / `CLAUDE.md` / `TODO.md` / `docs/` 全部**不出现在表里**（已存在）
- `.gitignore` 出现，并列出它缺的那几行状态规则
- `init-workflow` 相位标注「总会跑一遍」，**且没有因为本仓库已有 `.githooks` 而误报**
- `release-project` 标注「未跑过」——本仓库没有 `.hskill/release-project/release-profile.md`
- **没有任何文件被修改**：跑完 `git status --short` 应为空

任一条不符 → 回到 SKILL.md 的 `## 探测` 修判断规则，不要在 `check-report.md` 里打补丁。

- [ ] **Step 4: 跑全量测试并提交**

Run: `npm test`
Expected: 全绿。

```bash
git add skills/coding/init-project/references/check-report.md skills/coding/init-project/SKILL.md
git commit -m "feat(init-project): check 只读模式报告格式

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 5: 装机验证**

按本仓库 CLAUDE.md 的规定，从集成分支取、不从工作树 rsync。
**本任务不合并到 `staging`**——合并由你在验收后执行。装机验证放到合并之后：

```bash
git archive staging skills/coding/init-project | tar -x -C /tmp/hskill-sync
rsync -a --exclude '.DS_Store' /tmp/hskill-sync/skills/coding/init-project/ ~/.claude/skills/init-project/
grep '^version:' ~/.claude/skills/init-project/SKILL.md
```

Expected: `version: "0.1.0"`。
