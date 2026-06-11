# Hook 版本追踪实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `hskill hooks` 增加版本追踪，与 skills/tools 行为对齐：up-to-date 跳过，outdated 提示，list/status 展示版本号。

**Architecture:** 版本号以 `# version: x.x.x` 注释存于 hook 脚本头部（对标 SKILL.md frontmatter）；`lib/bundles.js` 新增 `readHookVersion()` 读取；`lib/installer.js` `installHooks()` 加版本比较逻辑（镜像 `installSkills()`）；`bin/cli.js` list/status 展示补版本列。

**Tech Stack:** Node.js ESM, `fs-extra`, bats-core（测试）

---

## 文件变动清单

| 操作 | 文件 | 说明 |
|---|---|---|
| 修改 | `scripts/hooks/check-similar-branch.sh` | 加 `# version: 1.0.0` 头部注释 |
| 修改 | `lib/bundles.js` | 新增 `readHookVersion()`，更新 `getAllHookItems()` 和 `checkHookInstalled()` |
| 修改 | `lib/installer.js` | import `readHookVersion`，更新 `installHooks()` 版本比较逻辑 |
| 修改 | `bin/cli.js` | `hooks list` 加 VER 列，`hooks status` 块展示版本，JSON 输出加 version |
| 修改 | `tests/hooks.bats` | 补充版本相关测试场景 |

---

## Task 1: 脚本加版本号 + lib/bundles.js 版本读取

**Files:**
- Modify: `scripts/hooks/check-similar-branch.sh`
- Modify: `lib/bundles.js`

- [ ] **Step 1: 在 `scripts/hooks/check-similar-branch.sh` 第 2 行后加版本注释**

打开文件，找到：
```bash
#!/bin/bash
# check-similar-branch.sh
# PreToolUse command hook: 用 LLM 语义分析检测相似分支
```
改为：
```bash
#!/bin/bash
# check-similar-branch.sh
# version: 1.0.0
# PreToolUse command hook: 用 LLM 语义分析检测相似分支
```

- [ ] **Step 2: 验证脚本头部**

```bash
head -5 scripts/hooks/check-similar-branch.sh
# 预期第 3 行为: # version: 1.0.0
```

- [ ] **Step 3: 在 `lib/bundles.js` 新增 `readHookVersion()` 函数**

在 `// ── Hooks ────` 注释前（约 171 行），加入：

```js
function readHookVersion(scriptPath) {
  try {
    const content = fs.readFileSync(scriptPath, 'utf-8')
    const m = content.match(/^#\s*version:\s*(.+)$/m)
    return m ? m[1].trim() : '—'
  } catch { return '—' }
}
```

- [ ] **Step 4: 更新 `getAllHookItems()` 加 version 字段**

将现有：
```js
export function getAllHookItems() {
  return hookDefs.map(hook => ({
    ...hook,
    srcPath: path.join(repoRoot, hook.path),
  }))
}
```
改为：
```js
export function getAllHookItems() {
  return hookDefs.map(hook => {
    const srcPath = path.join(repoRoot, hook.path)
    return {
      ...hook,
      srcPath,
      version: readHookVersion(srcPath),
    }
  })
}
```

- [ ] **Step 5: 更新 `checkHookInstalled()` 接受 availableVersion，返回带 version 字段**

将现有签名和 `checkScope` 内部逻辑改为：

```js
export function checkHookInstalled(hookName, availableVersion = '—') {
  const home = os.homedir()
  const cwd  = process.cwd()

  function checkScope(hooksDir, settingsPath) {
    const scriptPath   = path.join(hooksDir, `${hookName}.sh`)
    const scriptExists = fs.existsSync(scriptPath)
    const installedVersion = scriptExists ? readHookVersion(scriptPath) : '—'
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
    } catch { /* settings.json 不存在或解析失败 */ }

    const status = scriptExists && registered ? 'installed'
                 : scriptExists || registered ? 'partial'
                 : 'none'
    return { status, version: installedVersion }
  }

  const userHooksDir    = path.join(home, '.claude', 'hooks')
  const userSettings    = path.join(home, '.claude', 'settings.json')
  const projectHooksDir = path.join(cwd,  '.claude', 'hooks')
  const projectSettings = path.join(cwd,  '.claude', 'settings.json')

  return {
    user:    checkScope(userHooksDir, userSettings),
    project: cwd === home
      ? { status: 'none', version: '—' }
      : checkScope(projectHooksDir, projectSettings),
  }
}
```

- [ ] **Step 6: 导出 readHookVersion**

在文件末尾的 `export { formatChoice, readVersion }` 改为：
```js
export { formatChoice, readVersion, readHookVersion }
```

- [ ] **Step 7: 验证**

```bash
node --input-type=module <<'EOF'
import { getAllHookItems, checkHookInstalled } from './lib/bundles.js'
const items = getAllHookItems()
console.log('version:', items[0].version)   // 应输出 1.0.0
const inst = checkHookInstalled('check-similar-branch', items[0].version)
console.log('inst:', inst)
// inst.user.version 和 inst.project.version 应有值（非 undefined）
EOF
```

- [ ] **Step 8: 运行现有测试，确认无回归**

```bash
bats tests/ 2>&1 | tail -5
```

- [ ] **Step 9: Commit**

```bash
git add scripts/hooks/check-similar-branch.sh lib/bundles.js
git commit -m "feat(hooks): add version to script header and readHookVersion to bundles

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: lib/installer.js — 版本比较逻辑

**Files:**
- Modify: `lib/installer.js`

- [ ] **Step 1: 更新 import，加入 `readHookVersion`**

找到文件顶部：
```js
import { readVersion } from './bundles.js'
```
改为：
```js
import { readVersion, readHookVersion } from './bundles.js'
```

- [ ] **Step 2: 写失败测试（先在脑中验证，Step 3 之后运行）**

现有 `tests/hooks.bats` 里的 skip 测试目前 reason 是 `already_exists`，Task 3 会修改测试，此处先确认测试文件存在：

```bash
grep -n "skip\|already\|up-to-date\|outdated" tests/hooks.bats
```

- [ ] **Step 3: 更新 `installHooks()` 中的跳过逻辑**

找到约 307-313 行：
```js
    const scriptExists = await fs.pathExists(destScript)

    if (scriptExists && !force) {
      skipped.push({ name: hook.name, reason: 'already_exists' })
      console.error(chalk.dim(`  · Skipped ${hook.name} (already exists — use --force to overwrite)`))
      continue
    }
```

替换为（镜像 `installSkills()` 的版本比较逻辑）：
```js
    const scriptExists = await fs.pathExists(destScript)

    if (scriptExists && !force) {
      const installedVersion  = readHookVersion(destScript)
      const availableVersion  = hook.version ?? '—'

      if (availableVersion !== '—' && installedVersion === availableVersion) {
        skipped.push({ name: hook.name, reason: 'up-to-date', version: installedVersion })
        console.error(chalk.dim(`  · Skipped ${hook.name} (up-to-date ${installedVersion})`))
        continue
      }

      if (!process.stdout.isTTY) {
        skipped.push({
          name: hook.name, reason: 'outdated',
          installed: installedVersion, available: availableVersion,
        })
        console.error(chalk.dim(`  · Skipped ${hook.name} (outdated ${installedVersion} → ${availableVersion}, use --force to overwrite)`))
        continue
      }

      const ok = await confirm({
        message: `${hook.name} ${installedVersion} → ${availableVersion}. Overwrite?`,
        default: false,
      })
      if (!ok) {
        skipped.push({
          name: hook.name, reason: 'outdated',
          installed: installedVersion, available: availableVersion,
        })
        console.error(chalk.dim(`  · Skipped ${hook.name}`))
        continue
      }
    }
```

- [ ] **Step 4: 快速功能验证**

```bash
node --input-type=module <<'EOF'
import { installHooks, uninstallHook } from './lib/installer.js'
import { getAllHookItems } from './lib/bundles.js'
import { mkdtempSync, rmSync } from 'fs'

const tmpDir = mkdtempSync('/tmp/hskill-ver-test-')
const hooks  = getAllHookItems()

// 第一次安装
const r1 = await installHooks(hooks, 'project', tmpDir, false)
console.log('first install:', r1.installed)   // ['check-similar-branch']

// 第二次安装（不加 force）→ 应该 skip，reason: up-to-date
const r2 = await installHooks(hooks, 'project', tmpDir, false)
console.log('second install skipped reason:', r2.skipped[0]?.reason)  // up-to-date

rmSync(tmpDir, { recursive: true })
console.log('OK')
EOF
```

Expected:
```
first install: [ 'check-similar-branch' ]
second install skipped reason: up-to-date
OK
```

- [ ] **Step 5: 运行测试**

```bash
bats tests/ 2>&1 | tail -5
```

（部分 hooks.bats 测试可能因 skip reason 变化而失败，Task 3 修复）

- [ ] **Step 6: Commit**

```bash
git add lib/installer.js
git commit -m "feat(installer): version-aware installHooks (up-to-date/outdated)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: tests/hooks.bats — 更新 + 补充版本测试

**Files:**
- Modify: `tests/hooks.bats`

- [ ] **Step 1: 修复因 skip reason 变化导致的已有测试**

找到测试：
```bash
@test "hooks install: skips if already installed without --force" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user 2>&1)"
  echo "$output" | grep -qiE "skip|already"
}
```

改为（up-to-date 也符合 skip 语义，grep 模式扩展）：
```bash
@test "hooks install: skips if already installed without --force" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user 2>&1)"
  echo "$output" | grep -qiE "skip|already|up-to-date"
}
```

- [ ] **Step 2: 补充 up-to-date 测试**

在文件末尾加入：
```bash
# ── version tracking ──────────────────────────────────────────────────────────

@test "hooks install: skip reason is up-to-date when version matches" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  # 捕获第二次安装的 stderr（进度输出）
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user 2>/tmp/bats-hooks-stderr
  grep -q "up-to-date" /tmp/bats-hooks-stderr
}

@test "hooks install --force: reinstalls even when up-to-date" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  # force 安装应成功（不跳过）
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user --force 2>&1)"
  echo "$output" | grep -qiE "installed|✔"
}

@test "hooks install: outdated version shows outdated message in non-TTY" {
  # 先安装一个"旧版本"脚本（手动写版本注释）
  mkdir -p "${MOCK_HOME}/.claude/hooks"
  cat > "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" << 'EOF'
#!/bin/bash
# version: 0.0.1
EOF
  chmod +x "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh"
  # 非 TTY 下安装新版本（stdout 非 TTY）→ 应 skip with outdated
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user 2>&1)"
  echo "$output" | grep -qiE "outdated|0\.0\.1"
}
```

- [ ] **Step 3: 运行更新后的测试，确认全部通过**

```bash
bats tests/hooks.bats 2>&1
# 预期：全部通过（包含原 11 条 + 新增 3 条 = 14 条）
```

- [ ] **Step 4: 运行全量测试**

```bash
bats tests/ 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
git add tests/hooks.bats
git commit -m "test(hooks): update skip assertion, add version tracking tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: bin/cli.js — 展示版本

**Files:**
- Modify: `bin/cli.js`

### hooks list 格式变更

当前（无版本列）：
```
NAME                         U  P  DESCRIPTION
```

目标：
```
NAME                         VER    U  P  DESCRIPTION
```

### hooks status 格式变更

当前（版本位置固定为 `'—'`）：
```
check-similar-branch   —   U:✓  P:—   用 LLM 语义分析检测相似分支
```

目标（实际版本号）：
```
check-similar-branch   1.0.0   U:✓  P:—   用 LLM 语义分析检测相似分支
```

- [ ] **Step 1: 更新 `hooks list` JSON 输出加 version**

找到 `hooks list --json` 输出（约 407-411 行）：
```js
      const out = hookItems.map(h => {
        const inst = checkHookInstalled(h.name)
        return { name: h.name, description: h.description, event: h.event, user: inst.user, project: inst.project }
      })
```
改为（传入 availableVersion，加 version 字段）：
```js
      const out = hookItems.map(h => {
        const inst = checkHookInstalled(h.name, h.version)
        return { name: h.name, description: h.description, event: h.event, version: h.version ?? '—', user: inst.user, project: inst.project }
      })
```

- [ ] **Step 2: 更新 `hooks list` 文本输出加 VER 列**

找到约 417-423 行的文本输出块：
```js
    const nameWidth = Math.max(...hookItems.map(h => h.name.length), 4)
    console.log('')
    console.log('  ' + chalk.bold('NAME'.padEnd(nameWidth)) + '  U  P  ' + chalk.bold('DESCRIPTION'))
    console.log('  ' + '─'.repeat(nameWidth) + '  ─  ─  ' + '─'.repeat(20))
    for (const h of hookItems) {
      const inst = checkHookInstalled(h.name)
      console.log('  ' + h.name.padEnd(nameWidth) + '  ' + hookIcon(inst.user.status) + '  ' + hookIcon(inst.project.status) + '  ' + h.description)
    }
```
改为：
```js
    const nameWidth = Math.max(...hookItems.map(h => h.name.length), 4)
    const verWidth  = Math.max(...hookItems.map(h => (h.version ?? '—').length), 3)
    console.log('')
    console.log('  ' + chalk.bold('NAME'.padEnd(nameWidth)) + '  ' + chalk.bold('VER'.padEnd(verWidth)) + '  U  P  ' + chalk.bold('DESCRIPTION'))
    console.log('  ' + '─'.repeat(nameWidth) + '  ' + '─'.repeat(verWidth) + '  ─  ─  ' + '─'.repeat(20))
    for (const h of hookItems) {
      const inst = checkHookInstalled(h.name, h.version)
      console.log('  ' + h.name.padEnd(nameWidth) + '  ' + chalk.dim((h.version ?? '—').padEnd(verWidth)) + '  ' + hookIcon(inst.user.status) + '  ' + hookIcon(inst.project.status) + '  ' + h.description)
    }
```

- [ ] **Step 3: 更新 `hooks status` 区块使用实际版本**

找到 status 块中的 hooks 循环（约 288-298 行）：
```js
      console.log('  ' + h.name.padEnd(nw) + '  ' + chalk.dim('—'.padEnd(vw)) + '  ' + hIcon(inst.user.status) + '       ' + hIcon(inst.project.status) + '  ' + chalk.dim(h.description))
```

注意 `inst` 此时需要传 `availableVersion`。找到该循环体，将 `checkHookInstalled(h.name)` 改为 `checkHookInstalled(h.name, h.version)`，并将版本占位 `'—'` 改为 `h.version ?? '—'`：

```js
    if (hookItems.length > 0) {
      console.log('')
      console.log(chalk.bold('  HOOKS') + chalk.dim(`  — ${hookItems.length} available`))
      for (const h of hookItems) {
        const inst = checkHookInstalled(h.name, h.version)
        function hIcon(s) {
          if (s === 'installed') return chalk.green('✓')
          if (s === 'partial')   return chalk.yellow('~')
          return chalk.dim('—')
        }
        console.log('  ' + h.name.padEnd(nw) + '  ' + chalk.dim((h.version ?? '—').padEnd(vw)) + '  ' + hIcon(inst.user.status) + '       ' + hIcon(inst.project.status) + '  ' + chalk.dim(h.description))
      }
    }
```

- [ ] **Step 4: 更新 status JSON 输出加 version**

找到 status `--json` 的 hooks 部分（约 210-213 行）：
```js
      hooks: hookItems.map(h => {
        const inst = checkHookInstalled(h.name)
        return { name: h.name, description: h.description, user: inst.user, project: inst.project }
      }),
```
改为：
```js
      hooks: hookItems.map(h => {
        const inst = checkHookInstalled(h.name, h.version)
        return { name: h.name, description: h.description, version: h.version ?? '—', user: inst.user, project: inst.project }
      }),
```

- [ ] **Step 5: 手动验证展示**

```bash
node bin/cli.js hooks list
# 应出现 VER 列，check-similar-branch 显示 1.0.0

node bin/cli.js hooks list --json | node -e "
  const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))
  console.log(d.hooks[0].version)  // 应为 1.0.0
"

node bin/cli.js status 2>&1 | grep -A3 "HOOKS"
# HOOKS 行后应有 1.0.0 版本号
```

- [ ] **Step 6: 运行全量测试**

```bash
bats tests/ 2>&1 | tail -5
npm test 2>&1 | tail -5
```

- [ ] **Step 7: Commit**

```bash
git add bin/cli.js
git commit -m "feat(cli): show version in hooks list and status

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
