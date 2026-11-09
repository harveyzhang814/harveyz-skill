# 计划后交接与统一 worktree 管理 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 [执行交接时确定的执行技能] 逐项实施；用 `- [ ]` 跟踪步骤。

**Goal:** 新建 `manage-worktree` skill 统一负责 worktree 的建立或复用、进出与检测；把 `superpowers-rewrite` bundle 改名为 `devflow`；让 init-spec、develop-plan、handoff 调用它，并在仓库指令中加入“计划后交接给执行模型”的规则。

**Architecture:** `manage-worktree` 由一份 SKILL.md（动作约定、建或复用规则、按宿主进出）和一个只读检测脚本 `inspect-worktree.sh`（输出 `key=value`，用退出码表示结论）组成。调用方只调用它的「准备」「进入」「检测」「离开」四个动作，不再自己写 worktree 步骤。handoff 的 `validate-handoff.sh` 只补文档类检查（是否已提交、是否写明工作区），生效范围限定为含 `workspace_mode` 且状态为「待执行」的文档。

**Tech Stack:** Markdown SKILL 文档；bash + git + awk（脚本不引入其他依赖）；bats；Node.js `node:test`。

**Spec:** `.hskill/spec/2026-11-08-plan-handoff-worktree/2026-11-08-plan-handoff-worktree-spec.md`

**Spec Version and Scope:** v0.2（2026-11-08 获批），全文：第 2 节“本轮做”及第 8 节 S1–S13。

## Global Constraints

- 所有工作都在 worktree `/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+plan-handoff-worktree`（分支 `feature/plan-handoff-worktree`）中进行；不合并，不向 `staging`、`main` 提交。
- 提交信息遵循 Conventional Commits，类型取 `feat|fix|chore|docs|refactor|test|style|perf`（是 `docs`，不是 `doc`）；每条提交末尾加 `Co-Authored-By` 行。
- 版本号：`manage-worktree` 为 `0.1.0`；init-spec `0.3.0 → 0.4.0`；develop-plan `0.4.0 → 0.5.0`；handoff `1.17.1 → 1.18.0`；question-me 保持 `4.1.2`，内容不改。
- `skills-index.json` 中的 `contentVersion` 等于 SKILL.md 的 `version`。`contentHash` 用下面的命令计算，SKILL.md 内容改变后必须重算：
  `node -e 'const b=require("fs").readFileSync(process.argv[1],"utf8");console.log(require("crypto").createHash("sha256").update(b.replace(/^version:.*$/m,"version: __HASH_PLACEHOLDER__")).digest("hex").slice(0,16))' <SKILL.md 路径>`
- 脚本只用 bash、git、awk 和 coreutils，要能在任意仓库里运行，与 `validate-handoff.sh` 的约束一致。
- `manage-worktree` 不执行 `git worktree remove`、`git branch -d/-D`、`git merge`，也不执行任何会删除工作区或分支的命令。
- handoff accept 阶段里，用于验收重建和分叉点归因的临时 `git worktree add --detach … / remove` 保持原样，不迁出。
- 不修改：init-skill、contribute-skill、`.claude/settings.json`、`docs/commute/` 与 `.hskill/spec/` 下的历史文档、`.claude/worktrees/` 下已有的目录、`.gitignore`（`.worktrees/` 已被忽略）。
- 文案中带引号或代码格式的短语，按本计划给出的原文写入，因为测试按原文断言。
- 全部任务完成后运行 `npm test`，退出码须为 0（Spec 第 7 节第 1 条）。Spec 第 7 节第 6 条的端到端演练放在合并之后，不属于本计划。

## Review Focus

- 已存在但未提交的被引用文件，或未提交的交接文档（文档含 `workspace_mode`、状态为「待执行」）→ ERROR；状态为执行中、待验收等其他状态时，结果与改动前一致（Task 5）。
- 主路径 `.hskill/init-workflow/workflow-config.yml` 与 `.claude/workflow-config.yml` 同时存在 → 取主路径（Task 2）。
- 主工作树停在功能分支上 → 不算链接 worktree，检测不通过（Task 2）。
- 不含 `workspace_mode` 的旧文档 → 新检查一律不生效（Task 5）。
- 传入的路径是 worktree 的子目录 → 检测不通过，原因 `not-root`（Task 2）。

---

### Task 1: `superpowers-rewrite` bundle 改名为 `devflow`

**Prerequisites:** 无

**Files:**
- Move: `skills/superpowers-rewrite/` → `skills/devflow/`（用 `git mv`）
- Modify: `skills-index.json`（三个 skill 的 `path` 与 `bundle`；`bundleMeta` 删除 `superpowers-rewrite` 键，新增 `devflow` 键）
- Modify: `tests/skill-portability.test.mjs:77`、`tests/skill-portability.test.mjs:105`（路径前缀改为 `devflow/`）
- Modify: `skills/devflow/init-spec/SKILL.md:100`（“调用本 `superpowers-rewrite` bundle 的”改为“调用本 `devflow` bundle 的”）
- Modify: `docs/product/PRD.md:15`（bundle 名改为 `devflow`）
- Modify: `package.json`（运行 `node scripts/generate-npmignore.js` 重新生成 `files`）
- Test: `tests/devflow-bundle.test.mjs`

**Interfaces:**
- Produces: 目录 `skills/devflow/`；`bundleMeta.devflow` 的值为 `"开发流程（question-me — 执行前需求澄清；init-spec — 从初步想法到获批 Spec；develop-plan — 制定实施计划；manage-worktree — 建立或复用、进出与检测 worktree）"`

- [ ] **Step 1: 编写失败测试**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const SKILLS = ['question-me', 'init-spec', 'develop-plan']

test('superpowers-rewrite directory is gone and skills live under devflow', () => {
  assert.equal(existsSync(resolve(root, 'skills/superpowers-rewrite')), false)
  for (const s of SKILLS) assert.ok(existsSync(resolve(root, `skills/devflow/${s}/SKILL.md`)), s)
})

test('skills-index registers the three skills under the devflow bundle', async () => {
  const index = JSON.parse(await read('skills-index.json'))
  assert.equal(index.bundleMeta['superpowers-rewrite'], undefined)
  assert.match(index.bundleMeta.devflow, /manage-worktree/)
  for (const s of SKILLS) {
    const entry = index.skills.find(x => x.path === `devflow/${s}`)
    assert.ok(entry, s)
    assert.equal(entry.bundle, 'devflow', s)
  }
})

test('no shipped file still names the old bundle', async () => {
  for (const f of ['skills-index.json', 'package.json', 'tests/skill-portability.test.mjs', 'docs/product/PRD.md', 'skills/devflow/init-spec/SKILL.md']) {
    assert.doesNotMatch(await read(f), /superpowers-rewrite/, f)
  }
  assert.match(await read('skills/devflow/init-spec/SKILL.md'), /调用本 `devflow` bundle 的 `develop-plan` 技能/)
})
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/devflow-bundle.test.mjs`
Expected: FAIL，第一条断言提示 `skills/superpowers-rewrite` 仍存在

- [ ] **Step 3: 执行改名并修改上面 Files 列出的各处引用，然后运行 `node scripts/generate-npmignore.js`**

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/devflow-bundle.test.mjs tests/skill-portability.test.mjs && bats tests/skills.bats`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add -A skills/ skills-index.json package.json tests/devflow-bundle.test.mjs tests/skill-portability.test.mjs docs/product/PRD.md
git commit -m "refactor: rename superpowers-rewrite bundle to devflow"
```

---

### Task 2: 检测脚本 `inspect-worktree.sh`

**Prerequisites:** Task 1

**Files:**
- Create: `skills/devflow/manage-worktree/scripts/inspect-worktree.sh`
- Test: `skills/devflow/manage-worktree/tests/inspect-worktree.bats`

**Interfaces:**
- Produces: `inspect-worktree.sh [--path <目录>] [--type <分支类型>]`
  - `--path` 默认当前目录；`--type` 默认 `feature`。
  - stdout 每行一个 `key=value`，键依次为：`root`、`linked`(yes|no)、`branch`、`detached`(yes|no)、`rule_file`（相对仓库根的路径，或 `none`）、`integration`（空格分隔的分支名）、`is_integration`(yes|no)、`base`、`hooks`(ok|missing|n/a)、`verdict`(pass|fail|n/a)；每个未通过的项另起一行 `reason=<代码>`，代码取 `not-root|not-linked|detached|integration-branch|hooks-missing`。
  - 退出码：0 表示 pass，1 表示 fail，2 表示用法错误，3 表示目标不是 git 目录（此时输出 `verdict=n/a`）。
- 规则：
  - **规则文件**：在 `root` 下按顺序取第一个存在的文件：`.hskill/init-workflow/workflow-config.yml` → `workflow-config.yml` → `.claude/workflow-config.yml`。
  - **`integration`**：规则文件中 `branches.protected` 下各项的 `name`；没有规则文件时取默认分支。
  - **`base`**：`merge_from` 中含 `<type>/*`（去掉引号后比较）的那个受保护分支；找不到时取默认分支。
  - **默认分支**：`refs/remotes/origin/HEAD` 指向的分支（去掉 `origin/`）；没有时依次取存在的 `main`、`master`；都没有则为空。
  - **`linked`**：`git rev-parse --absolute-git-dir` 与 `--git-common-dir` 的绝对路径不同即为 yes。
  - **`hooks`**：`root` 下有 `.githooks/` 目录时，`core.hooksPath` 为 `.githooks` 或其绝对路径则为 ok，否则为 missing；没有该目录时为 n/a。
  - **`verdict=pass`**：要求路径就是 `root`，且 `linked=yes`、`detached=no`、`is_integration=no`、`hooks` 不为 missing。

- [ ] **Step 1: 编写失败测试**

```bash
#!/usr/bin/env bats

SCRIPT="${BATS_TEST_DIRNAME}/../scripts/inspect-worktree.sh"
REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/../../../.." && pwd)"

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  git init -q -b main repo && cd repo
  git config user.email t@example.com && git config user.name t
  echo x > seed.txt && git add seed.txt && git commit -qm seed
  REPO="$TMP/repo"
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

rule_file() { # rule_file <相对路径>
  mkdir -p "$(dirname "$REPO/$1")"
  cat > "$REPO/$1" <<'YML'
branches:
  protected:
    - name: main
      allow_direct_commit: false
      merge_from:
        - staging
        - "release/*"
    - name: staging
      allow_direct_commit: false
      merge_from:
        - "feature/*"
        - "fix/*"
branch_naming:
  enforce: true
YML
  git -C "$REPO" add -A && git -C "$REPO" commit -qm rules
}
linked() { git -C "$REPO" worktree add -q -b "$1" "$TMP/wt" HEAD >/dev/null; echo "$TMP/wt"; }

@test "01 non-git directory -> exit 3, verdict n/a" {
  mkdir "$TMP/plain"
  run bash "$SCRIPT" --path "$TMP/plain"
  [ "$status" -eq 3 ]; [[ "$output" == *"verdict=n/a"* ]]
}

@test "02 main worktree on a feature branch is not linked -> exit 1" {
  git -C "$REPO" checkout -q -b feature/x
  run bash "$SCRIPT" --path "$REPO"
  [ "$status" -eq 1 ]; [[ "$output" == *"linked=no"* ]]; [[ "$output" == *"reason=not-linked"* ]]
}

@test "03 linked worktree on feature branch without rules or hooks -> pass" {
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 0 ]; [[ "$output" == *"verdict=pass"* ]]; [[ "$output" == *"hooks=n/a"* ]]
  [[ "$output" == *"rule_file=none"* ]]; [[ "$output" == *"base=main"* ]]
}

@test "04 detached linked worktree -> exit 1, detached" {
  git -C "$REPO" worktree add -q --detach "$TMP/wt" HEAD
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"detached=yes"* ]]; [[ "$output" == *"reason=detached"* ]]
}

@test "05 without rules the default branch counts as integration" {
  git -C "$REPO" checkout -q -b feature/park
  git -C "$REPO" worktree add -q "$TMP/wt" main
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"is_integration=yes"* ]]; [[ "$output" == *"reason=integration-branch"* ]]
}

@test "06 primary rule file gives integration branches and staging base for feature" {
  rule_file .hskill/init-workflow/workflow-config.yml
  git -C "$REPO" branch staging
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type feature
  [ "$status" -eq 0 ]
  [[ "$output" == *"rule_file=.hskill/init-workflow/workflow-config.yml"* ]]
  [[ "$output" == *"integration=main staging"* ]]; [[ "$output" == *"base=staging"* ]]
}

@test "07 linked worktree on a protected branch from rules -> integration-branch" {
  rule_file .hskill/init-workflow/workflow-config.yml
  git -C "$REPO" branch staging
  git -C "$REPO" worktree add -q "$TMP/wt" staging
  run bash "$SCRIPT" --path "$TMP/wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"reason=integration-branch"* ]]
}

@test "08 legacy .claude rule file is found when primary is absent" {
  rule_file .claude/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [[ "$output" == *"rule_file=.claude/workflow-config.yml"* ]]; [[ "$output" == *"base=staging"* ]]
}

@test "09 primary rule file wins over legacy .claude file" {
  rule_file .claude/workflow-config.yml
  rule_file .hskill/init-workflow/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [[ "$output" == *"rule_file=.hskill/init-workflow/workflow-config.yml"* ]]
}

@test "10 type not listed in any merge_from falls back to default branch" {
  rule_file .hskill/init-workflow/workflow-config.yml
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type chore
  [[ "$output" == *"base=main"* ]]
}

@test "11 .githooks present but hooksPath unset -> hooks-missing; set -> pass" {
  mkdir "$REPO/.githooks" && touch "$REPO/.githooks/pre-commit"
  git -C "$REPO" add -A && git -C "$REPO" commit -qm hooks
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 1 ]; [[ "$output" == *"hooks=missing"* ]]; [[ "$output" == *"reason=hooks-missing"* ]]
  git -C "$REPO" config core.hooksPath .githooks
  run bash "$SCRIPT" --path "$wt"
  [ "$status" -eq 0 ]; [[ "$output" == *"hooks=ok"* ]]
}

@test "12 subdirectory of a worktree is not root -> exit 1" {
  wt="$(linked feature/x)"; mkdir "$wt/sub"
  run bash "$SCRIPT" --path "$wt/sub"
  [ "$status" -eq 1 ]; [[ "$output" == *"reason=not-root"* ]]
}

@test "13 this repository's real rule file yields staging as feature base" {
  cp "$REPO_ROOT/.claude/workflow-config.yml" "$REPO/workflow-config.yml"
  git -C "$REPO" add -A && git -C "$REPO" commit -qm real
  wt="$(linked feature/x)"
  run bash "$SCRIPT" --path "$wt" --type feature
  [[ "$output" == *"base=staging"* ]]; [[ "$output" == *"integration=main staging"* ]]
}

@test "14 unknown option -> exit 2" {
  run bash "$SCRIPT" --bogus
  [ "$status" -eq 2 ]
}
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `bats skills/devflow/manage-worktree/tests/inspect-worktree.bats`
Expected: FAIL，提示脚本不存在（`bash: …/inspect-worktree.sh: No such file or directory`）

- [ ] **Step 3: 在 `skills/devflow/manage-worktree/scripts/inspect-worktree.sh` 中实现 Interfaces 描述的行为**

Approach: 用 awk 按缩进解析 `branches:` → `protected:` 下的 `- name:` 与其后的 `merge_from:` 列表项。`root` 与路径比较前，都用 `pwd -P` 归一化（macOS 的 `/var` 与 `/private/var` 问题，见 `validate-handoff.bats` 的 setup 注释）。

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `bats skills/devflow/manage-worktree/tests/inspect-worktree.bats`
Expected: PASS（14 tests）

- [ ] **Step 5: 提交**

```bash
git add skills/devflow/manage-worktree/scripts/inspect-worktree.sh skills/devflow/manage-worktree/tests/inspect-worktree.bats
git commit -m "feat(manage-worktree): add read-only worktree inspection script"
```

---

### Task 3: `manage-worktree` 的 SKILL.md 与登记

**Prerequisites:** Task 1、Task 2

**Files:**
- Create: `skills/devflow/manage-worktree/SKILL.md`
- Modify: `skills-index.json`（新增条目 `{"path": "devflow/manage-worktree", "bundle": "devflow", "installScope": "global", "contentHash": <计算值>, "contentVersion": "0.1.0"}`）
- Modify: `package.json`（重新运行 `node scripts/generate-npmignore.js`）
- Test: `tests/manage-worktree-skill.test.mjs`

**Interfaces:**
- Consumes: Task 2 的 `inspect-worktree.sh` 参数、输出与退出码
- Produces: 供调用方引用的动作名「准备」「进入」「检测」「离开」，以及安装提示原文“需要安装 `devflow` bundle 中的 manage-worktree”

SKILL.md 要写清 Spec 5.2 的全部内容，包括：职责与边界；四个动作的输入与结果；规则来源与查找顺序；建或复用的规则 0–4，以及“链接 worktree 不含主工作树”；默认路径与 `.gitignore`；用检测脚本检测；按宿主进出（从 handoff「平台适配」迁入，语义不变）；非 git 目录。frontmatter 使用：

```yaml
---
name: manage-worktree
description: "Prepare, enter, inspect, or leave the git worktree a task works in — reuse the task's existing worktree or create one from an explicit, rule-derived base after one user confirmation, bind the session to it on Claude Code, Codex, or any other host, and check it is a linked worktree on a named non-integration branch. Called by init-spec, develop-plan, and handoff; never merges, removes worktrees, or deletes branches. Triggers: 'prepare a worktree', 'enter this worktree', 'check my worktree'."
user_invocable: true
version: "0.1.0"
---
```

- [ ] **Step 1: 编写失败测试**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const PATH = 'skills/devflow/manage-worktree/SKILL.md'
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)

test('manage-worktree is registered in devflow with matching version and hash', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const index = JSON.parse(await readFile(resolve(root, 'skills-index.json'), 'utf8'))
  const entry = index.skills.find(s => s.path === 'devflow/manage-worktree')
  assert.match(body, /^name: manage-worktree$/m)
  assert.match(body, /^version: ["']?0\.1\.0["']?$/m)
  assert.equal(entry.bundle, 'devflow')
  assert.equal(entry.contentVersion, '0.1.0')
  assert.equal(entry.contentHash, hash(body))
})

test('manage-worktree states its actions, rules, hosts and boundaries', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  for (const phrase of [
    '「准备」', '「进入」', '「检测」', '「离开」',
    'scripts/inspect-worktree.sh',
    '`.hskill/init-workflow/workflow-config.yml`', '`.claude/workflow-config.yml`',
    '`.worktrees/<分支名，/ 换成 +>`',
    '锚点',
    '新建前向用户一次确认基线、分支名和路径',
    'EnterWorktree(path: "<工作区绝对路径>")', 'ExitWorktree(action: "keep")',
    'codex -C <工作区>', 'git -C <工作区>',
    '不合并、不清理 worktree、不删除分支', '绝不执行 `git worktree remove`',
    '非 git 目录', '不适用',
  ]) assert.ok(body.includes(phrase), phrase)
})
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/manage-worktree-skill.test.mjs`
Expected: FAIL，提示 `ENOENT` 找不到 `skills/devflow/manage-worktree/SKILL.md`

- [ ] **Step 3: 编写 `skills/devflow/manage-worktree/SKILL.md`，登记到 `skills-index.json`，重新生成 `package.json`**

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/manage-worktree-skill.test.mjs && bats tests/skills.bats`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/devflow/manage-worktree/SKILL.md skills-index.json package.json tests/manage-worktree-skill.test.mjs
git commit -m "feat(manage-worktree): add skill for preparing, entering and inspecting worktrees"
```

---

### Task 4: init-spec 与 develop-plan 改为调用 manage-worktree

**Prerequisites:** Task 1、Task 3

**Files:**
- Modify: `skills/devflow/init-spec/SKILL.md`
  - 第一阶段第 4 步“建档”：写决定记录之前插入一句，原文为“建档前调用 `manage-worktree` 的「准备」，在返回的工作区里写决定记录与 Spec，并按项目 Git 规则提交；`manage-worktree` 不可用时停下，告诉用户需要安装 `devflow` bundle 中的 manage-worktree；返回“不适用”时在当前目录继续。”
  - “保存位置”中的“项目根目录下”改为“工作区根目录下”。
  - version 改为 `0.4.0`。
- Modify: `skills/devflow/develop-plan/SKILL.md`
  - 第 1 步“工作区”整段替换为：“**工作区：**调用 `manage-worktree` 的「准备」：接续 `init-spec` 时把已批准 Spec 的路径作为锚点传入，沿用 Spec 所在的工作区；独立调用时按它的规则复用或新建。`manage-worktree` 不可用时停下，告诉用户需要安装 `devflow` bundle 中的 manage-worktree。”
  - 第 5 步中的“确认后直接使用 `superpowers:subagent-driven-development` 执行，不询问执行方式；”替换为“确认后，项目指令对计划确认后的执行方式另有规定时按项目指令，否则直接使用 `superpowers:subagent-driven-development` 执行；”。
  - version 改为 `0.5.0`。
- Modify: `skills-index.json`（两个条目的 `contentVersion` 与 `contentHash`）
- Test: `tests/devflow-worktree-callers.test.mjs`

**Interfaces:**
- Consumes: Task 3 的动作名「准备」、安装提示原文

- [ ] **Step 1: 编写失败测试**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)
const INSTALL = '需要安装 `devflow` bundle 中的 manage-worktree'

async function checkIndexed(name, version) {
  const body = await read(`skills/devflow/${name}/SKILL.md`)
  const entry = JSON.parse(await read('skills-index.json')).skills.find(s => s.path === `devflow/${name}`)
  assert.match(body, new RegExp(`^version: ["']?${version.replace(/\./g, '\\.')}["']?$`, 'm'), name)
  assert.equal(entry.contentVersion, version, name)
  assert.equal(entry.contentHash, hash(body), name)
  return body
}

test('init-spec prepares the worktree before writing the decision record', async () => {
  const body = await checkIndexed('init-spec', '0.4.0')
  const prepare = body.indexOf('建档前调用 `manage-worktree` 的「准备」')
  assert.ok(prepare > 0)
  assert.ok(prepare < body.indexOf('**按摘要建档。**'))
  assert.ok(body.includes(INSTALL))
  assert.ok(body.includes('工作区根目录下'))
})

test('develop-plan reuses the spec worktree and defers execution mode to project instructions', async () => {
  const body = await checkIndexed('develop-plan', '0.5.0')
  assert.ok(body.includes('调用 `manage-worktree` 的「准备」'))
  assert.ok(body.includes('把已批准 Spec 的路径作为锚点传入'))
  assert.ok(body.includes('项目指令对计划确认后的执行方式另有规定时按项目指令，否则直接使用 `superpowers:subagent-driven-development` 执行'))
  assert.ok(body.includes(INSTALL))
  assert.ok(!body.includes('不询问执行方式'))
  assert.ok(!body.includes('using-git-worktrees'))
})
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/devflow-worktree-callers.test.mjs`
Expected: FAIL，版本断言不通过（init-spec 仍为 `0.3.0`）

- [ ] **Step 3: 按 Files 修改两份 SKILL.md，重算并更新 `skills-index.json` 中的 hash**

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/devflow-worktree-callers.test.mjs tests/devflow-bundle.test.mjs && bats tests/skills.bats`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/devflow/init-spec/SKILL.md skills/devflow/develop-plan/SKILL.md skills-index.json tests/devflow-worktree-callers.test.mjs
git commit -m "feat(devflow): init-spec and develop-plan prepare worktrees via manage-worktree"
```

---

### Task 5: `validate-handoff.sh` 新增文档类检查

**Prerequisites:** 无

**Files:**
- Modify: `skills/coding/handoff/scripts/validate-handoff.sh`
- Modify: `skills/coding/handoff/tests/validate-handoff.bats`：改用例 37、40 的 fixture；新增用例 41–49
- Test: `skills/coding/handoff/tests/validate-handoff.bats`

**Interfaces:**
- Produces: 新检查只在文档含 `workspace_mode` 字段且 `status` 为「待执行」时生效：
  - 任一模式缺 `branch` 或 `worktree` → ERROR，信息中包含 `branch` 和 `worktree`。
  - 交接文档没有被 git 跟踪，或相对 `HEAD` 有改动 → ERROR，信息中包含“交接文档未提交”。
  - 正文链接解析到一个已存在的文件，且该文件在所属仓库中未被跟踪，或相对 `HEAD` 有改动 → ERROR，信息中包含“引用文件未提交”和链接原文。文件不在任何 git 仓库里时跳过。
  - 链接指向的文件不存在 → 保持现有的 WARN。

- [ ] **Step 1: 编写失败测试**

用例 37：在 `write_doc` 之后、`run` 之前插入 `git add "$DOC" && git commit -qm doc`。

用例 40：fixture 改为

```bash
  write_doc "$VALID_FM
workspace_mode: same-workspace
branch: $BRANCH
worktree: $TMP
base_commit: $commit"
  git add "$DOC" && git commit -qm doc
```

两条用例的期望值都不变。在文件末尾追加：

```bash
# ── 「待执行」文档的已提交与工作区检查（含 workspace_mode 时生效）────────────
commit_doc() { git add "$DOC" && git commit -qm doc; }
SAME_WS() { printf '%s\nworkspace_mode: same-workspace\nbranch: %s\nworktree: %s' "$VALID_FM" "$BRANCH" "$TMP"; }

@test "41 same-workspace pending doc without worktree -> exit 1" {
  write_doc "$VALID_FM
workspace_mode: same-workspace
branch: $BRANCH"
  commit_doc
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]; [[ "$output" == *worktree* ]]
}

@test "42 pending doc not tracked -> exit 1" {
  write_doc "$(SAME_WS)"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]; [[ "$output" == *交接文档未提交* ]]
}

@test "43 pending doc tracked but modified -> exit 1" {
  write_doc "$(SAME_WS)"; commit_doc; echo "extra" >> "$DOC"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]; [[ "$output" == *交接文档未提交* ]]
}

@test "44 link to an existing untracked file -> exit 1" {
  echo plan > plan.md
  write_doc "$(SAME_WS)" "$(printf '# 交接：示例\n\n**交接目的**：x\n\n见 [计划](plan.md)。\n\n## 最小验收锚点\n- x\n')"
  commit_doc
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]; [[ "$output" == *引用文件未提交* ]]; [[ "$output" == *plan.md* ]]
}

@test "45 link to a tracked but modified file -> exit 1" {
  echo plan > plan.md && git add plan.md && git commit -qm plan && echo more >> plan.md
  write_doc "$(SAME_WS)" "$(printf '# 交接：示例\n\n**交接目的**：x\n\n见 [计划](plan.md)。\n\n## 最小验收锚点\n- x\n')"
  commit_doc
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]; [[ "$output" == *引用文件未提交* ]]
}

@test "46 fully committed pending doc with committed links -> exit 0" {
  echo plan > plan.md && git add plan.md && git commit -qm plan
  write_doc "$(SAME_WS)" "$(printf '# 交接：示例\n\n**交接目的**：x\n\n见 [计划](plan.md)。\n\n## 最小验收锚点\n- x\n')"
  commit_doc
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]; [[ "$output" != *ERROR* ]]
}

@test "47 in-progress doc left uncommitted keeps old result" {
  write_doc "status: 执行中
date: 2026-09-06
author_model: opus-5
acceptance: hard
workspace_mode: same-workspace
branch: $BRANCH
worktree: $TMP"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]; [[ "$output" != *未提交* ]]
}

@test "48 pending-accept doc with self-test left uncommitted keeps old result" {
  write_doc "status: 待验收
date: 2026-09-06
author_model: opus-5
acceptance: hard
workspace_mode: same-workspace
branch: $BRANCH
worktree: $TMP" "$(printf '# 交接：示例\n\n**交接目的**：x\n\n## 最小验收锚点\n- x\n\n## 接手方自测记录（2026-09-07）\n- pass\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]; [[ "$output" != *未提交* ]]
}

@test "49 doc without workspace_mode is unaffected by the new checks" {
  echo plan > plan.md
  write_doc "$VALID_FM" "$(printf '# 交接：示例\n\n**交接目的**：x\n\n见 [计划](plan.md)。\n\n## 最小验收锚点\n- x\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]; [[ "$output" != *未提交* ]]
}
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `bats skills/coding/handoff/tests/validate-handoff.bats`
Expected: FAIL，用例 41–45 失败（脚本尚未报这些 ERROR），其余通过

- [ ] **Step 3: 在 `validate-handoff.sh` 中实现 Interfaces 描述的检查**

Approach: 是否已跟踪用 `git -C <文件所在目录> ls-files --error-unmatch -- <文件名>` 判断；是否有改动用 `git -C <文件所在目录> diff --quiet HEAD -- <文件名>` 判断。链接解析沿用脚本现有的候选路径循环。

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `bats skills/coding/handoff/tests/validate-handoff.bats`
Expected: PASS（含 1–40 原有用例与 41–49）

- [ ] **Step 5: 提交**

```bash
git add skills/coding/handoff/scripts/validate-handoff.sh skills/coding/handoff/tests/validate-handoff.bats
git commit -m "feat(handoff): require pending handoff docs and referenced files to be committed"
```

---

### Task 6: handoff 的 SKILL.md 与模板改为调用 manage-worktree

**Prerequisites:** Task 3、Task 4（两者都改 `skills-index.json`，按顺序进行以免冲突）、Task 5

**Files:**
- Modify: `skills/coding/handoff/SKILL.md`
  - **author 第 4 步**（`:34-50`）：标题括注改为“（接手方是另一个会话、需要被指到一个确定的工作区时做——计划后交接、换模型或换框架执行都属于这种情况）”。正文改为：调用 `manage-worktree` 的「准备」，有计划或 Spec 时把它的路径作为锚点传入；复用当前工作区时填 `same-workspace`，新建交接工作区时填 `shared-worktree`；写明“两种模式都必须填 `branch` 与 `worktree`”；保留 `base_commit` 说明与“不要 `git worktree remove`”；`manage-worktree` 不可用时停下，告诉用户需要安装 `devflow` bundle 中的 manage-worktree。删除原来的 `git worktree add` 步骤和 `.claude/worktrees/` 路径说法。
  - **第 7、8 步**（`:66-68`）对调：第 7 步“落库”（交接文档以及本次产生、被它引用的产物都要提交，删除“此步可省”的例外），第 8 步“跑完整性门禁”（不过就修改、重新提交、重跑，不过不放行）。正文中引用这两步编号的地方同步更新。
  - **第 9 步派发指令模板**（`:79-83`）：进入方式改为“调用 `manage-worktree` 的「进入」进入它（未安装时停下，告诉用户需要安装 `devflow` bundle 中的 manage-worktree）”。
  - **verify**（`:143-152`）：“按文末「平台适配」进去”改为“调用 `manage-worktree` 的「进入」，传入 frontmatter 的 `worktree` 与 `branch`；检测不通过就打回原 session，不自行开工”。
  - **accept**：第 1 步（`:194`）改为“调用 `manage-worktree` 的「进入」”；第 8 步的离开改为“调用 `manage-worktree` 的「离开」”。
  - **「平台适配」一节**（`:276-326`）：整节替换为一段，写明进出交接工作区一律调用 `manage-worktree` 的「进入」与「离开」，各宿主的具体做法只在 manage-worktree 里维护。
  - version 改为 `1.18.0`。
- Modify: `skills/coding/handoff/assets/handoff-template.md`：frontmatter 中 `branch`、`worktree` 两行的注释改为 `# workspace_mode 存在时必填`；`workspace_mode` 行的注释改为 `# same-workspace（复用交出方当前工作区）|shared-worktree（新建交接工作区）`。
- Modify: `skills-index.json`（`coding/handoff` 的 `contentVersion` 与 `contentHash`）
- Test: `tests/handoff-worktree.test.mjs`

**Interfaces:**
- Consumes: Task 3 的动作名「准备」「进入」「离开」与安装提示原文；Task 5 的“已提交”检查（它决定了第 7、8 步的顺序）

- [ ] **Step 1: 编写失败测试**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)

test('handoff version and index hash are updated', async () => {
  const body = await read('skills/coding/handoff/SKILL.md')
  const entry = JSON.parse(await read('skills-index.json')).skills.find(s => s.path === 'coding/handoff')
  assert.match(body, /^version: ["']?1\.18\.0["']?$/m)
  assert.equal(entry.contentVersion, '1.18.0')
  assert.equal(entry.contentHash, hash(body))
})

test('handoff delegates worktree handling to manage-worktree', async () => {
  const body = await read('skills/coding/handoff/SKILL.md')
  for (const phrase of [
    '接手方是另一个会话、需要被指到一个确定的工作区时做',
    '调用 `manage-worktree` 的「准备」', '调用 `manage-worktree` 的「进入」', '调用 `manage-worktree` 的「离开」',
    '两种模式都必须填 `branch` 与 `worktree`',
    '需要安装 `devflow` bundle 中的 manage-worktree',
  ]) assert.ok(body.includes(phrase), phrase)
  for (const gone of ['EnterWorktree(path', 'codex -C', '接手方会在**另一条分支**上开工时才做', '.claude/worktrees/']) {
    assert.ok(!body.includes(gone), gone)
  }
})

test('author commits before running the integrity gate', async () => {
  const body = await read('skills/coding/handoff/SKILL.md')
  const commit = body.indexOf('7. **落库**')
  const gate = body.indexOf('8. **跑完整性门禁**')
  assert.ok(commit > 0 && gate > commit)
})

test('handoff template marks branch and worktree as required with workspace_mode', async () => {
  const tpl = await read('skills/coding/handoff/assets/handoff-template.md')
  assert.equal((tpl.match(/workspace_mode 存在时必填/g) || []).length, 2)
})
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/handoff-worktree.test.mjs`
Expected: FAIL，版本断言不通过（仍为 `1.17.1`）

- [ ] **Step 3: 按 Files 修改 SKILL.md 与模板，重算并更新 `skills-index.json` 中的 hash**

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/handoff-worktree.test.mjs && bats skills/coding/handoff/tests/validate-handoff.bats tests/skills.bats`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/coding/handoff/SKILL.md skills/coding/handoff/assets/handoff-template.md skills-index.json tests/handoff-worktree.test.mjs
git commit -m "feat(handoff): delegate workspace preparation and entry to manage-worktree"
```

---

### Task 7: 仓库指令加入“计划后交接给执行模型”规则，并统一路径约定

**Prerequisites:** Task 3

**Files:**
- Modify: `AGENTS.md`
  - 「Git 与工作区」一节（`:33-43`）：建 worktree 改为“新建或复用 worktree 一律调用 `manage-worktree`”；路径约定改为 `.worktrees/<分支名，/ 换成 +>`，`.claude/worktrees/` 下的目录改称历史遗留、不动；保留 `core.hooksPath=.githooks`、`merge.ff=false` 两项设置；删除“`.claude/worktrees/` 是本仓库现有的路径约定”这句。
  - 「跨会话交接」一节末尾追加下面这一小节。
- Modify: `CLAUDE.md`
  - “worktree 路径习惯”一段与“建 worktree 的硬动作”代码块（`:99-110`）：改为调用 `manage-worktree`，路径改为 `.worktrees/<分支名，/ 换成 +>`。
  - 「跨 session 交接（handoff）」一节末尾追加同一小节。
- Modify: `.hskill/handoff/config.md` 的 `workflow` 段
  - 进入工作区的写法改为“按 `manage-worktree` 的「进入」进入这个已有路径”，删除其中 Claude Code、Codex 的具体进入命令。
  - 路径习惯改为 `.worktrees/<分支名，/ 换成 +>`。
  - “实施计划：用 superpowers:writing-plans … executing-plans 执行”及其后关于 `using-git-worktrees` 的整段，替换为：“计划由交出方在交接前用 develop-plan 写好并经用户确认；接手方按计划开头的 `REQUIRED SUB-SKILL` 执行，不重写计划。执行技能若建议新建 worktree，一律跳过：工作区已经建好。”
- Test: `tests/repo-handoff-rules.test.mjs`

追加到 AGENTS.md 与 CLAUDE.md 的小节原文：

```markdown
### 计划后交接给执行模型

1. develop-plan 的计划经用户确认后，先询问用户“本会话执行，还是交接给其他执行方”。
2. 选择本会话执行：按计划开头的 `REQUIRED SUB-SKILL` 执行。选择交接：不调用执行技能；交出方先把计划开头的 `REQUIRED SUB-SKILL` 填为 `superpowers:subagent-driven-development` 并提交计划，再走 `handoff` 的 `author` 阶段。一份计划对应一次交接；交接文档把 Spec 与计划列为权威依据；最小验收锚点写成“各 Task 的测试与计划写定的断言一致，并全部通过”，再加上 Spec 的验收标准。
3. 接手方按计划执行，可自行决定函数内部实现；不得修改接口签名、测试名称与断言、`Global Constraints`；计划与代码库现状冲突或无法照做时，停止并打回交出方。
```

**Interfaces:**
- Consumes: Task 3 的动作名「进入」

- [ ] **Step 1: 编写失败测试**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const RULE = [
  '### 计划后交接给执行模型',
  '先询问用户“本会话执行，还是交接给其他执行方”',
  '`REQUIRED SUB-SKILL` 填为 `superpowers:subagent-driven-development` 并提交计划',
  '各 Task 的测试与计划写定的断言一致，并全部通过',
  '不得修改接口签名、测试名称与断言、`Global Constraints`',
]

for (const file of ['AGENTS.md', 'CLAUDE.md']) {
  test(`${file} carries the plan handoff rule and the unified worktree path`, async () => {
    const body = await read(file)
    for (const phrase of [...RULE, '`manage-worktree`', '`.worktrees/<分支名，/ 换成 +>`']) assert.ok(body.includes(phrase), `${file}: ${phrase}`)
  })
}

test('old worktree recipes are gone from repo instructions', async () => {
  assert.ok(!(await read('AGENTS.md')).includes('`.claude/worktrees/` 是本仓库现有的路径约定'))
  assert.ok(!(await read('CLAUDE.md')).includes('git worktree add .claude/worktrees/feature+<slug>'))
})

test('handoff config no longer tells the receiver to re-plan', async () => {
  const body = await read('.hskill/handoff/config.md')
  assert.doesNotMatch(body, /writing-plans|executing-plans/)
  assert.ok(body.includes('计划由交出方在交接前用 develop-plan 写好并经用户确认'))
  assert.ok(body.includes('manage-worktree'))
  assert.ok(body.includes('.worktrees/<分支名，/ 换成 +>'))
  assert.ok(!body.includes('EnterWorktree(path'))
})
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/repo-handoff-rules.test.mjs`
Expected: FAIL，AGENTS.md 缺少“### 计划后交接给执行模型”

- [ ] **Step 3: 按 Files 修改 AGENTS.md、CLAUDE.md、`.hskill/handoff/config.md`**

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/repo-handoff-rules.test.mjs`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add AGENTS.md CLAUDE.md .hskill/handoff/config.md tests/repo-handoff-rules.test.mjs
git commit -m "docs: add plan handoff rule and unify worktree path on manage-worktree"
```
