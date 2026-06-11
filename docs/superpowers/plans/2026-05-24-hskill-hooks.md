# hskill hooks 子命令实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `hskill` CLI 增加 `hooks` 子命令，支持将 Claude Code hook 脚本像 skills/tools 一样安装到任意项目的 user/project scope。

**Architecture:** hook 元数据加进 `skills-index.json`，脚本随 npm 包发布（`scripts/hooks/`），`lib/bundles.js` 增加 hook 状态检测，`lib/installer.js` 增加安装/卸载逻辑（复制脚本 + patch settings.json），`bin/cli.js` 增加 `hooks` 子命令分支。

**Tech Stack:** Node.js ESM, `fs-extra`, `@inquirer/prompts`, bats-core（测试）

---

## 文件变动清单

| 操作 | 文件 | 说明 |
|---|---|---|
| 新建 | `scripts/hooks/check-similar-branch.sh` | hook 脚本（从 `.claude/hooks/` 移入） |
| 修改 | `package.json` | `files` 加入 `"scripts/hooks/"` |
| 修改 | `skills-index.json` | 新增顶层 `hooks[]` 字段 |
| 修改 | `.claude/settings.json` | command 路径改为安装后的绝对路径 |
| 删除 | `.claude/hooks/check-similar-branch.sh` | 移到 `scripts/hooks/` 后删除 |
| 修改 | `lib/bundles.js` | 新增 `getAllHookItems()`、`checkHookInstalled()` |
| 修改 | `lib/installer.js` | 新增 `installHooks()`、`uninstallHook()` |
| 修改 | `bin/cli.js` | 新增 `hooks` 子命令（list/install/uninstall） |
| 新建 | `tests/hooks.bats` | hooks 子命令的 bats e2e 测试 |

---

## Task 1: 移动脚本文件，更新 package.json 和 skills-index.json

**Files:**
- Create: `scripts/hooks/check-similar-branch.sh`（移动，内容不变）
- Modify: `package.json`
- Modify: `skills-index.json`
- Delete: `.claude/hooks/check-similar-branch.sh`
- Modify: `.claude/settings.json`

- [ ] **Step 1: 创建 scripts/hooks/ 目录并移动脚本**

```bash
mkdir -p scripts/hooks
cp .claude/hooks/check-similar-branch.sh scripts/hooks/check-similar-branch.sh
```

确认文件内容与 `.claude/hooks/check-similar-branch.sh` 完全一致：

```bash
diff .claude/hooks/check-similar-branch.sh scripts/hooks/check-similar-branch.sh
# 应无输出（文件完全相同）
```

- [ ] **Step 2: 删除原位置的脚本**

```bash
rm .claude/hooks/check-similar-branch.sh
# 验证
[ ! -f .claude/hooks/check-similar-branch.sh ] && echo "OK"
```

- [ ] **Step 3: 更新 package.json files 字段**

在 `package.json` 的 `"files"` 数组中加入 `"scripts/hooks/"`:

```json
"files": [
  "bin/",
  "lib/",
  "bundles.json",
  "skills-index.json",
  "scripts/hooks/",
  "skills/analysis/skill-analyzer/CHANGELOG.md",
  ...其余不变
]
```

- [ ] **Step 4: 在 skills-index.json 新增 hooks 字段**

在 `skills-index.json` 顶层加入：

```json
{
  "hooks": [
    {
      "name": "check-similar-branch",
      "description": "用 LLM 语义分析检测相似分支",
      "path": "scripts/hooks/check-similar-branch.sh",
      "event": "PreToolUse",
      "matcher": "Bash",
      "timeout": 60,
      "statusMessage": "检查相似分支..."
    }
  ],
  "toolBundleMeta": { ... },
  ...其余不变
}
```

- [ ] **Step 5: 更新 .claude/settings.json 中的 command 路径**

当前 `PreToolUse` 里的 command 是：
```
"bash \"$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/check-similar-branch.sh\""
```

脚本已从项目的 `.claude/hooks/` 移走，这个路径将失效。等 Task 3 的安装逻辑完成后再用 `hskill hooks install --scope project` 重新注册，此步先把整条 hook 条目从 `.claude/settings.json` 删除，避免启动时报 file not found 错误。

打开 `.claude/settings.json`，删除 `hooks.PreToolUse` 数组中 matcher 为 `"Bash"` 且 command 包含 `check-similar-branch.sh` 的那一条。

- [ ] **Step 6: 验证文件结构**

```bash
ls scripts/hooks/check-similar-branch.sh
node -e "const i = JSON.parse(require('fs').readFileSync('skills-index.json','utf8')); console.log(i.hooks)"
# 应输出：[ { name: 'check-similar-branch', ... } ]
```

- [ ] **Step 7: Commit**

```bash
git add scripts/hooks/check-similar-branch.sh package.json skills-index.json .claude/
git commit -m "chore: move hook script to scripts/hooks, register in skills-index"
```

---

## Task 2: lib/bundles.js — 新增 hook 工具函数

**Files:**
- Modify: `lib/bundles.js`

### 背景

`lib/bundles.js` 是 skills/tools 的元数据中心，负责从 `skills-index.json` 解析数据和检测安装状态。我们在这里加两个导出函数：
- `getAllHookItems()` — 返回所有可用 hook 的元数据 + 解析后的 srcPath
- `checkHookInstalled(hookName)` — 检查 user/project scope 的安装状态

### 安装状态定义

- `installed`：脚本文件存在 **且** `settings.json` 中有包含该脚本名的 command 条目
- `partial`：二者之一存在
- `none`：都不存在

- [ ] **Step 1: 在 lib/bundles.js 顶部读取 hooks 数据**

在 `lib/bundles.js` 中找到这行：
```js
const { bundleMeta, skills: skillDefs, toolBundleMeta = {}, tools: toolDefs = [] } = require('../skills-index.json')
```

改为：
```js
const { bundleMeta, skills: skillDefs, toolBundleMeta = {}, tools: toolDefs = [], hooks: hookDefs = [] } = require('../skills-index.json')
```

- [ ] **Step 2: 新增 getAllHookItems() 函数**

在 `lib/bundles.js` 末尾 `export { formatChoice, readVersion }` 之前加入：

```js
// ── Hooks ────────────────────────────────────────────────────────────────────

export function getAllHookItems() {
  return hookDefs.map(hook => ({
    ...hook,
    srcPath: path.join(repoRoot, hook.path),
  }))
}
```

- [ ] **Step 3: 新增 checkHookInstalled() 函数**

紧接 `getAllHookItems()` 之后加入：

```js
export function checkHookInstalled(hookName) {
  const home = os.homedir()
  const cwd  = process.cwd()

  function checkScope(hooksDir, settingsPath) {
    const scriptExists = fs.existsSync(path.join(hooksDir, `${hookName}.sh`))
    let registered = false
    try {
      const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf-8'))
      registered = Object.values(settings.hooks ?? {}).some(entries =>
        Array.isArray(entries) && entries.some(e =>
          Array.isArray(e.hooks) && e.hooks.some(h =>
            typeof h.command === 'string' && h.command.includes(`${hookName}.sh`)
          )
        )
      )
    } catch { /* settings.json 不存在或解析失败，registered 保持 false */ }

    if (scriptExists && registered)  return { status: 'installed' }
    if (scriptExists || registered)  return { status: 'partial' }
    return { status: 'none' }
  }

  const userHooksDir    = path.join(home, '.claude', 'hooks')
  const userSettings    = path.join(home, '.claude', 'settings.json')
  const projectHooksDir = path.join(cwd,  '.claude', 'hooks')
  const projectSettings = path.join(cwd,  '.claude', 'settings.json')

  return {
    user:    checkScope(userHooksDir, userSettings),
    project: cwd === home
      ? { status: 'none' }
      : checkScope(projectHooksDir, projectSettings),
  }
}
```

- [ ] **Step 4: 快速验证（无测试框架）**

```bash
node -e "
import { getAllHookItems, checkHookInstalled } from './lib/bundles.js'
console.log('hooks:', getAllHookItems())
console.log('status:', checkHookInstalled('check-similar-branch'))
" --input-type=module 2>&1 || node --input-type=module <<'EOF'
import { getAllHookItems, checkHookInstalled } from './lib/bundles.js'
console.log('hooks:', getAllHookItems())
console.log('status:', checkHookInstalled('check-similar-branch'))
EOF
```

Expected 输出（未安装时）：
```
hooks: [ { name: 'check-similar-branch', description: '...', ..., srcPath: '/.../.../scripts/hooks/check-similar-branch.sh' } ]
status: { user: { status: 'none' }, project: { status: 'none' } }
```

- [ ] **Step 5: Commit**

```bash
git add lib/bundles.js
git commit -m "feat(bundles): add getAllHookItems and checkHookInstalled"
```

---

## Task 3: lib/installer.js — 新增 installHooks() 和 uninstallHook()

**Files:**
- Modify: `lib/installer.js`

### installHooks 参数

```js
installHooks(hooks, scope, projectDir, force)
// hooks:      [{ name, description, path, event, matcher, timeout?, statusMessage?, srcPath }]
// scope:      'user' | 'project'
// projectDir: string — project 根目录，scope='user' 时忽略
// force:      boolean
```

返回 `{ installed: string[], skipped: string[], failed: Array<{name, reason, detail?}> }`

### uninstallHook 参数

```js
uninstallHook(hookName, scope, projectDir)
// 返回 { removed: boolean }
```

- [ ] **Step 1: 在 lib/installer.js 顶部 import 中加入 os**

当前 `installer.js` 已有 `import os from 'os'`，确认存在后继续。

- [ ] **Step 2: 新增内部辅助函数 _hooksDir 和 _settingsPath**

在 `lib/installer.js` 末尾，`export async function installSkills` 之后加入：

```js
// ── Hooks ────────────────────────────────────────────────────────────────────

function _hooksDir(scope, projectDir) {
  return scope === 'user'
    ? path.join(os.homedir(), '.claude', 'hooks')
    : path.join(projectDir, '.claude', 'hooks')
}

function _settingsPath(scope, projectDir) {
  return scope === 'user'
    ? path.join(os.homedir(), '.claude', 'settings.json')
    : path.join(projectDir, '.claude', 'settings.json')
}

function _hookCommand(hookName, scope) {
  return scope === 'user'
    ? `bash ~/.claude/hooks/${hookName}.sh`
    : `bash "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/${hookName}.sh"`
}
```

- [ ] **Step 3: 新增 _patchSettings 辅助函数**

紧接 `_hookCommand` 之后加入：

```js
async function _patchSettings(settingsPath, hook, scope, force) {
  let settings = {}
  try {
    settings = JSON.parse(await fs.readFile(settingsPath, 'utf-8'))
  } catch { /* 文件不存在时从空对象开始 */ }

  if (!settings.hooks) settings.hooks = {}
  if (!settings.hooks[hook.event]) settings.hooks[hook.event] = []

  const command = _hookCommand(hook.name, scope)

  // 检查是否已有相同 command
  const alreadyRegistered = settings.hooks[hook.event].some(entry =>
    Array.isArray(entry.hooks) && entry.hooks.some(h => h.command === command)
  )

  if (alreadyRegistered && !force) return false   // 跳过
  if (alreadyRegistered && force) {
    // 删除旧条目
    settings.hooks[hook.event] = settings.hooks[hook.event].filter(entry =>
      !Array.isArray(entry.hooks) || !entry.hooks.some(h => h.command === command)
    )
  }

  const hookEntry = { type: 'command', command }
  if (hook.timeout)       hookEntry.timeout       = hook.timeout
  if (hook.statusMessage) hookEntry.statusMessage = hook.statusMessage

  const matchers = hook.matcher ?? ''
  settings.hooks[hook.event].push({
    matcher: matchers,
    hooks: [hookEntry],
  })

  await fs.ensureDir(path.dirname(settingsPath))
  await fs.writeFile(settingsPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8')
  return true
}
```

- [ ] **Step 4: 新增 installHooks() 导出函数**

紧接 `_patchSettings` 之后加入：

```js
export async function installHooks(hooks, scope, projectDir, force = false) {
  const hooksDir    = _hooksDir(scope, projectDir)
  const settingsPath = _settingsPath(scope, projectDir)

  await fs.ensureDir(hooksDir)

  const installed = []
  const skipped   = []
  const failed    = []

  for (const hook of hooks) {
    const destScript = path.join(hooksDir, `${hook.name}.sh`)
    const scriptExists = await fs.pathExists(destScript)

    if (scriptExists && !force) {
      skipped.push({ name: hook.name, reason: 'already_exists' })
      console.error(chalk.dim(`  · Skipped ${hook.name} (already exists — use --force to overwrite)`))
      continue
    }

    try {
      if (!await fs.pathExists(hook.srcPath)) {
        failed.push({ name: hook.name, reason: 'source_not_found' })
        console.error(chalk.red(`  ✗ Source not found: ${hook.srcPath}`))
        continue
      }

      await fs.copy(hook.srcPath, destScript, { overwrite: true })
      await fs.chmod(destScript, 0o755)

      const patched = await _patchSettings(settingsPath, hook, scope, force)
      if (!patched && !scriptExists) {
        // 文件是新的，但 settings 已有相同注册 — 仍算安装成功
      }

      installed.push(hook.name)
      console.error(chalk.green(`  ✓ ${hook.name} → ${destScript}`))
    } catch (err) {
      failed.push({ name: hook.name, reason: 'copy_failed', detail: err.message })
      console.error(chalk.red(`  ✗ Failed to install ${hook.name}: ${err.message}`))
    }
  }

  return { installed, skipped, failed }
}
```

- [ ] **Step 5: 新增 uninstallHook() 导出函数**

紧接 `installHooks` 之后加入：

```js
export async function uninstallHook(hookName, scope, projectDir) {
  const hooksDir     = _hooksDir(scope, projectDir)
  const settingsPath = _settingsPath(scope, projectDir)
  const destScript   = path.join(hooksDir, `${hookName}.sh`)
  let removed = false

  // 删除脚本文件
  if (await fs.pathExists(destScript)) {
    await fs.remove(destScript)
    removed = true
    console.error(chalk.green(`  ✓ Removed ${destScript}`))
  }

  // 从 settings.json 移除注册
  try {
    const settings = JSON.parse(await fs.readFile(settingsPath, 'utf-8'))
    let changed = false
    for (const event of Object.keys(settings.hooks ?? {})) {
      const before = settings.hooks[event].length
      settings.hooks[event] = settings.hooks[event].filter(entry =>
        !Array.isArray(entry.hooks) ||
        !entry.hooks.some(h => typeof h.command === 'string' && h.command.includes(`${hookName}.sh`))
      )
      if (settings.hooks[event].length !== before) {
        changed = true
        removed = true
        // 若 event 数组变空，删除该键
        if (settings.hooks[event].length === 0) delete settings.hooks[event]
      }
    }
    if (changed) {
      await fs.writeFile(settingsPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8')
      console.error(chalk.green(`  ✓ Unregistered from ${settingsPath}`))
    }
  } catch { /* settings.json 不存在，忽略 */ }

  return { removed }
}
```

- [ ] **Step 6: Commit**

```bash
git add lib/installer.js
git commit -m "feat(installer): add installHooks and uninstallHook"
```

---

## Task 4: tests/hooks.bats — 写测试

**Files:**
- Create: `tests/hooks.bats`

- [ ] **Step 1: 创建测试文件**

```bash
cat > tests/hooks.bats << 'BATS'
#!/usr/bin/env bats
# E2E tests for `hskill hooks` subcommand.

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"

HOOK_NAME="check-similar-branch"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  MOCK_PROJECT="${TEST_DIR}/project"
  mkdir -p "${MOCK_HOME}/.claude"
  mkdir -p "${MOCK_PROJECT}/.claude"
  mkdir -p "${MOCK_HOME}/.local/bin"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

_hooks() {
  HOME="${MOCK_HOME}" node "${CLI}" hooks "$@" 2>/tmp/bats-hooks-stderr | cat
}
_stderr() { cat /tmp/bats-hooks-stderr; }
BATS
```

- [ ] **Step 2: 加入 list 测试**

```bash
cat >> tests/hooks.bats << 'BATS'

@test "hooks list: shows available hook" {
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks list 2>&1)"
  echo "$output" | grep -q "${HOOK_NAME}"
}

@test "hooks list --json: returns valid JSON with hooks array" {
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks list --json 2>&1)"
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
    if (!Array.isArray(d.hooks)) throw new Error('hooks must be array');
    if (!d.hooks.find(h => h.name === '${HOOK_NAME}')) throw new Error('hook not found');
  "
}
BATS
```

- [ ] **Step 3: 加入 install user scope 测试**

```bash
cat >> tests/hooks.bats << 'BATS'

@test "hooks install --scope user: copies script to ~/.claude/hooks/" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  [ -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
}

@test "hooks install --scope user: registers in ~/.claude/settings.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  node -e "
    const s = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.claude/settings.json','utf8'));
    const entries = s.hooks?.PreToolUse ?? [];
    const found = entries.some(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh')));
    if (!found) throw new Error('hook not registered');
  "
}

@test "hooks install --scope user: script is executable" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  [ -x "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
}
BATS
```

- [ ] **Step 4: 加入 install project scope 测试**

```bash
cat >> tests/hooks.bats << 'BATS'

@test "hooks install --scope project: copies script to .claude/hooks/ in project dir" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}"
  [ -f "${MOCK_PROJECT}/.claude/hooks/${HOOK_NAME}.sh" ]
}

@test "hooks install --scope project: registers in project .claude/settings.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}"
  node -e "
    const s = JSON.parse(require('fs').readFileSync('${MOCK_PROJECT}/.claude/settings.json','utf8'));
    const entries = s.hooks?.PreToolUse ?? [];
    const found = entries.some(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh')));
    if (!found) throw new Error('hook not registered');
  "
}

@test "hooks install: skips if already installed without --force" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user 2>&1)"
  echo "$output" | grep -qi "skipped\|already"
}

@test "hooks install --force: overwrites existing" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user --force
  # 不报错，且 settings.json 中只有一条注册（不重复）
  node -e "
    const s = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.claude/settings.json','utf8'));
    const entries = s.hooks?.PreToolUse ?? [];
    const count = entries.filter(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh'))).length;
    if (count !== 1) throw new Error('expected exactly 1 registration, got ' + count);
  "
}
BATS
```

- [ ] **Step 5: 加入 uninstall 测试**

```bash
cat >> tests/hooks.bats << 'BATS'

@test "hooks uninstall: removes script file" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  HOME="${MOCK_HOME}" node "${CLI}" hooks uninstall "${HOOK_NAME}" --scope user
  [ ! -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
}

@test "hooks uninstall: removes registration from settings.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  HOME="${MOCK_HOME}" node "${CLI}" hooks uninstall "${HOOK_NAME}" --scope user
  node -e "
    const s = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.claude/settings.json','utf8'));
    const entries = s.hooks?.PreToolUse ?? [];
    const found = entries.some(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh')));
    if (found) throw new Error('hook still registered after uninstall');
  "
}
BATS
```

- [ ] **Step 6: 运行测试，预期全部失败（CLI 尚未实现）**

```bash
bats tests/hooks.bats 2>&1 | head -30
# 预期：多个 FAILED（subcommand 'hooks' 未知）
```

- [ ] **Step 7: Commit**

```bash
git add tests/hooks.bats
git commit -m "test(hooks): add bats e2e tests for hooks subcommand"
```

---

## Task 5: bin/cli.js — 新增 hooks 子命令

**Files:**
- Modify: `bin/cli.js`

在 `info` 子命令结尾（第 354 行 `process.exit(0)` 后）、`Install` 块（第 356 行注释）之前插入 `hooks` 子命令。

- [ ] **Step 1: 更新 import 行，加入新函数**

在 `bin/cli.js` 顶部找到：
```js
import {
  getAllSkillItems, getAllToolItems,
  checkInstalled, checkToolInstalled, scopeSummary,
  resolveSkills, resolveSkillsByName, resolveTools, resolveToolsByName,
  TOOL_BUNDLE_CHOICES,
} from '../lib/bundles.js'
import { buildTargetChoices, resolveTargets, TARGETS } from '../lib/targets.js'
import { installSkills, installTools } from '../lib/installer.js'
```

改为：
```js
import {
  getAllSkillItems, getAllToolItems, getAllHookItems, checkHookInstalled,
  checkInstalled, checkToolInstalled, scopeSummary,
  resolveSkills, resolveSkillsByName, resolveTools, resolveToolsByName,
  TOOL_BUNDLE_CHOICES,
} from '../lib/bundles.js'
import { buildTargetChoices, resolveTargets, TARGETS } from '../lib/targets.js'
import { installSkills, installTools, installHooks, uninstallHook } from '../lib/installer.js'
```

- [ ] **Step 2: 更新 printHelp() 加入 hooks 命令描述**

在 `printHelp()` 函数里，找到 `hskill info <name>` 那行，在其后加入：

```js
    hskill hooks list [--json]                  list available hooks and install status
    hskill hooks install [--name <n>]           install hook(s)
    hskill hooks install --scope user|project   set scope (default: user)
    hskill hooks install --project <path>       target project dir (scope=project)
    hskill hooks install --force                overwrite existing
    hskill hooks uninstall <name> [--scope <s>] uninstall a hook
```

- [ ] **Step 3: 在 info 子命令结尾之后、Install 注释之前插入 hooks 分支**

在 `bin/cli.js` 第 354 行（`process.exit(0)` 结束 info 分支）后加入：

```js
// ── Hooks ─────────────────────────────────────────────────────────────────────
if (subcommand === 'hooks') {
  const hooksSubcmd = args[1]   // list | install | uninstall
  const hookArgs    = args.slice(2)
  const hookJsonFlag  = hookArgs.includes('--json')
  const hookNameIdx   = hookArgs.indexOf('--name')
  const hookScopeIdx  = hookArgs.indexOf('--scope')
  const hookProjectIdx = hookArgs.indexOf('--project')
  const hookForce     = hookArgs.includes('--force')
  const hookNameArg   = hookNameIdx  !== -1 ? hookArgs[hookNameIdx  + 1] : undefined
  const hookScopeArg  = hookScopeIdx !== -1 ? hookArgs[hookScopeIdx + 1] : 'user'
  const hookProjectArg = hookProjectIdx !== -1 ? hookArgs[hookProjectIdx + 1] : process.cwd()

  // ── hooks list ──────────────────────────────────────────────────────────────
  if (hooksSubcmd === 'list' || !hooksSubcmd) {
    const hookItems = getAllHookItems()
    if (hookJsonFlag) {
      const out = hookItems.map(h => {
        const inst = checkHookInstalled(h.name)
        return { name: h.name, description: h.description, event: h.event, user: inst.user, project: inst.project }
      })
      console.log(JSON.stringify({ hooks: out }, null, 2))
      process.exit(0)
    }
    const G = chalk.green, Y = chalk.yellow, D = chalk.dim
    function hookIcon(s) {
      if (s === 'installed') return G('✓')
      if (s === 'partial')   return Y('~')
      return D('—')
    }
    const nameWidth = Math.max(...hookItems.map(h => h.name.length), 4)
    const descWidth = Math.max(...hookItems.map(h => h.description.length), 11)
    console.log('')
    console.log('  ' + chalk.bold('NAME'.padEnd(nameWidth)) + '  U  P  ' + chalk.bold('DESCRIPTION'))
    console.log('  ' + '─'.repeat(nameWidth) + '  ─  ─  ' + '─'.repeat(20))
    for (const h of hookItems) {
      const inst = checkHookInstalled(h.name)
      console.log('  ' + h.name.padEnd(nameWidth) + '  ' + hookIcon(inst.user.status) + '  ' + hookIcon(inst.project.status) + '  ' + h.description)
    }
    console.log('')
    console.log(chalk.dim(`  U=user scope  P=project scope  ${G('✓')}=installed  ${Y('~')}=partial  ${D('—')}=none`))
    console.log('')
    process.exit(0)
  }

  // ── hooks install ────────────────────────────────────────────────────────────
  if (hooksSubcmd === 'install') {
    const hookItems = getAllHookItems()
    let toInstall

    if (hookNameArg) {
      const found = hookItems.find(h => h.name === hookNameArg)
      if (!found) {
        console.error(chalk.red(`  ✗ Unknown hook: "${hookNameArg}"`))
        process.exit(1)
      }
      toInstall = [found]
    } else if (!process.stdout.isTTY) {
      // 非 TTY 且未指定 --name 则安装全部
      toInstall = hookItems
    } else {
      // TTY 交互式选择（用 @inquirer/prompts checkbox）
      const { checkbox } = await import('@inquirer/prompts')
      const selected = await checkbox({
        message: 'Select hooks to install:',
        choices: hookItems.map(h => ({ name: `${h.name.padEnd(32)} ${h.description}`, value: h })),
      })
      if (!selected.length) {
        console.log(chalk.dim('  · Nothing selected'))
        process.exit(0)
      }
      toInstall = selected
    }

    const { installed, skipped, failed } = await installHooks(toInstall, hookScopeArg, hookProjectArg, hookForce)

    if (installed.length) console.log(chalk.green.bold(`✔ Hooks installed (${hookScopeArg}):`), installed.join(', '))
    for (const s of skipped) console.log(chalk.dim(`  · ${s.name} skipped (${s.reason})`))
    for (const f of failed)  console.error(chalk.red(`  ✗ ${f.name} failed: ${f.reason}${f.detail ? ` — ${f.detail}` : ''}`))
    process.exit(failed.length ? 1 : 0)
  }

  // ── hooks uninstall ──────────────────────────────────────────────────────────
  if (hooksSubcmd === 'uninstall') {
    const nameToRemove = args[2]   // hskill hooks uninstall <name> [--scope ...]
    if (!nameToRemove || nameToRemove.startsWith('--')) {
      console.error(chalk.red('  ✗ Usage: hskill hooks uninstall <name> [--scope user|project]'))
      process.exit(1)
    }
    const { removed } = await uninstallHook(nameToRemove, hookScopeArg, hookProjectArg)
    if (!removed) console.log(chalk.dim(`  · ${nameToRemove} was not installed in ${hookScopeArg} scope`))
    process.exit(0)
  }

  console.error(chalk.red(`  ✗ Unknown hooks subcommand: "${hooksSubcmd}". Use list, install, or uninstall.`))
  process.exit(1)
}
```

- [ ] **Step 4: 运行测试，预期通过**

```bash
bats tests/hooks.bats
# 预期：全部 PASSED
```

若有失败，查看 stderr：
```bash
bats tests/hooks.bats 2>&1
```

- [ ] **Step 5: 手动冒烟测试**

```bash
node bin/cli.js hooks list
node bin/cli.js hooks install --name check-similar-branch --scope project
# 验证当前目录 .claude/hooks/check-similar-branch.sh 存在
ls .claude/hooks/check-similar-branch.sh
# 验证 .claude/settings.json 已注册
cat .claude/settings.json | python3 -m json.tool | grep -A5 check-similar-branch
node bin/cli.js hooks uninstall check-similar-branch --scope project
[ ! -f .claude/hooks/check-similar-branch.sh ] && echo "script removed OK"
```

- [ ] **Step 6: Commit**

```bash
git add bin/cli.js
git commit -m "feat(cli): add hooks subcommand (list/install/uninstall)"
```

---

## Task 6: hskill status 展示 hooks 区块

**Files:**
- Modify: `bin/cli.js`（status/outdated 分支）

- [ ] **Step 1: 在 status 分支读取 hook items**

在 `bin/cli.js` 的 `status / outdated` 分支（约 170 行），找到：
```js
  const skillItems   = getAllSkillItems()
  const toolItems    = getAllToolItems()
```

改为：
```js
  const skillItems   = getAllSkillItems()
  const toolItems    = getAllToolItems()
  const hookItems    = getAllHookItems()
```

- [ ] **Step 2: 在非 JSON 输出末尾加 hooks 区块**

在 status 分支末尾（`console.log(chalk.dim(...installed/outdated 统计...))` 之前），找到 tools 区块的末尾，加入：

```js
    // ── hooks ──
    if (hookItems.length > 0) {
      console.log('')
      console.log(chalk.bold('hooks:'))
      for (const h of hookItems) {
        const inst = checkHookInstalled(h.name)
        const uIcon = inst.user.status    === 'installed' ? chalk.green('✓') : inst.user.status    === 'partial' ? chalk.yellow('~') : chalk.dim('—')
        const pIcon = inst.project.status === 'installed' ? chalk.green('✓') : inst.project.status === 'partial' ? chalk.yellow('~') : chalk.dim('—')
        console.log(`  ${h.name.padEnd(28)} U:${uIcon}  P:${pIcon}  ${chalk.dim(h.description)}`)
      }
    }
```

- [ ] **Step 3: 在 JSON 输出中加入 hooks 字段**

在 status 分支的 `jsonFlag` 块中，找到构建 JSON 输出的地方，在 `tools` 字段之后加入：

```js
hooks: hookItems.map(h => {
  const inst = checkHookInstalled(h.name)
  return { name: h.name, description: h.description, user: inst.user, project: inst.project }
}),
```

- [ ] **Step 4: 验证 status 输出**

```bash
node bin/cli.js status
# 末尾应出现 hooks: 区块

node bin/cli.js status --json | python3 -m json.tool | grep -A10 '"hooks"'
```

- [ ] **Step 5: 运行全量测试**

```bash
npm test
# 预期：全部通过
```

- [ ] **Step 6: 重新安装 hook 到当前项目**

Task 1 中删除了 `.claude/settings.json` 里的旧注册。现在用新命令重新安装到 project scope：

```bash
node bin/cli.js hooks install --name check-similar-branch --scope project
# 验证
node bin/cli.js hooks list
# check-similar-branch 应显示 U:— P:✓
```

- [ ] **Step 7: 最终 commit**

```bash
git add bin/cli.js
git commit -m "feat(cli): show hooks section in hskill status"
```

---

## Task 7: 收尾

**Files:**
- Modify: `docs/reference/` 或 README（可选）

- [ ] **Step 1: 更新 README 或帮助文档加入 hooks 用法示例**

在 `README.md` 中找到 `hskill install` 的用法示例部分，加入：

```markdown
## Hook 管理

```bash
hskill hooks list                                    # 查看可用 hooks 及安装状态
hskill hooks install --name check-similar-branch     # 安装到全局（user scope）
hskill hooks install --name check-similar-branch --scope project  # 安装到当前项目
hskill hooks uninstall check-similar-branch          # 卸载
```
```

- [ ] **Step 2: 运行完整测试套件**

```bash
npm test
```

Expected 输出：全部测试通过，无 FAILED。

- [ ] **Step 3: 最终 commit**

```bash
git add README.md
git commit -m "docs: add hooks usage to README"
```
