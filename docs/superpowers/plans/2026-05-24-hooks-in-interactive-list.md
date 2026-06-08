# Hooks in Interactive List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add hooks to the `hskill` interactive fzf list so users can install hooks for Claude Code and Codex directly from the main selector, without needing `hskill hooks install`.

**Architecture:** Extend `fzfSelect()` to include hookItems with `kind: 'hook'`; add a Codex hook install path in `installer.js` (writes `~/.codex/hooks.json`); extend the interactive loop to handle hook selections with scope + target (claude/codex) fzf prompts; update `checkHookInstalled` and `printSummary` to cover codex status.

**Tech Stack:** Node.js ESM, bats-core (tests), fzf (interactive UI), spawnSync

---

## File Map

| File | Change |
|---|---|
| `lib/targets.js` | Add `HOOK_TARGETS`, `buildHookTargetChoices()` |
| `lib/installer.js` | Add Codex hook install logic; extend `installHooks()` to accept `targets` array |
| `lib/bundles.js` | Extend `checkHookInstalled()` to also check `~/.codex/hooks.json` |
| `bin/cli.js` | `fzfSelect()` + interactive loop + `printSummary()` |
| `tests/hooks.bats` | Add Codex target install tests |
| `tests/interactive.bats` | Add hook selection tests |

---

### Task 1: Add hook targets to `lib/targets.js`

**Files:**
- Modify: `lib/targets.js`

- [ ] **Step 1: Write the failing test**

In `tests/hooks.bats`, add at the end:

```bash
# ── codex target ──────────────────────────────────────────────────────────────

@test "hooks install --target codex --scope user: copies script to ~/.codex/hooks/" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex
  [ -f "${MOCK_HOME}/.codex/hooks/${HOOK_NAME}.sh" ]
}
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
bats tests/hooks.bats --filter "codex target"
```

Expected: FAIL — `--target` flag not yet recognised.

- [ ] **Step 3: Add HOOK_TARGETS and buildHookTargetChoices to `lib/targets.js`**

Add after the existing `buildTargetChoices` function:

```js
export const HOOK_TARGETS = ['claude', 'codex']

export function buildHookTargetChoices() {
  const home = os.homedir()
  return [
    { name: `claude   (~/.claude/hooks/)`, value: 'claude' },
    { name: `codex    (~/.codex/hooks/)`,  value: 'codex'  },
  ]
}
```

- [ ] **Step 4: Commit**

```bash
git add lib/targets.js tests/hooks.bats
git commit -m "feat: add HOOK_TARGETS and buildHookTargetChoices to targets.js"
```

---

### Task 2: Add Codex install logic to `lib/installer.js`

**Files:**
- Modify: `lib/installer.js`

The Codex `hooks.json` format is a standalone file (not inside `settings.json`):
```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "command": "/abs/path/to/script.sh", "timeout": 60 }] }
    ]
  }
}
```
Note: no `type: "command"` field, uses absolute path for command.

- [ ] **Step 1: Write failing tests for Codex install**

Add to `tests/hooks.bats`:

```bash
@test "hooks install --target codex --scope user: registers in ~/.codex/hooks.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex
  node -e "
    const d = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.codex/hooks.json','utf8'));
    const entries = d.hooks?.PreToolUse ?? [];
    const found = entries.some(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh')));
    if (!found) throw new Error('hook not registered in ~/.codex/hooks.json');
  "
}

@test "hooks install --target codex: command uses absolute path" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex
  node -e "
    const d = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.codex/hooks.json','utf8'));
    const entries = d.hooks?.PreToolUse ?? [];
    const cmd = entries.flatMap(e => e.hooks ?? []).find(h => h.command?.includes('${HOOK_NAME}.sh'))?.command;
    if (!cmd) throw new Error('command not found');
    if (!cmd.startsWith('/') && !cmd.startsWith(process.env.HOME)) throw new Error('command is not absolute: ' + cmd);
  "
}

@test "hooks install --target codex: no type field in hooks.json entry" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex
  node -e "
    const d = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.codex/hooks.json','utf8'));
    const entries = d.hooks?.PreToolUse ?? [];
    const entry = entries.flatMap(e => e.hooks ?? []).find(h => h.command?.includes('${HOOK_NAME}.sh'));
    if (!entry) throw new Error('entry not found');
    if ('type' in entry) throw new Error('type field must not be present in codex hooks.json');
  "
}

@test "hooks install --force --target codex: no duplicate registration" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user --target codex
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user --target codex --force
  node -e "
    const d = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.codex/hooks.json','utf8'));
    const entries = d.hooks?.PreToolUse ?? [];
    const count = entries.filter(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh'))).length;
    if (count !== 1) throw new Error('expected 1 registration, got ' + count);
  "
}
```

- [ ] **Step 2: Run to confirm they fail**

```bash
bats tests/hooks.bats --filter "codex"
```

Expected: FAIL — `--target` not handled.

- [ ] **Step 3: Add Codex helpers in `lib/installer.js`**

Add after `_hookCommand()` (around line 256):

```js
function _codexHooksDir(scope, projectDir) {
  return scope === 'user'
    ? path.join(os.homedir(), '.codex', 'hooks')
    : path.join(projectDir, '.codex', 'hooks')
}

function _codexHooksJsonPath(scope, projectDir) {
  return scope === 'user'
    ? path.join(os.homedir(), '.codex', 'hooks.json')
    : path.join(projectDir, '.codex', 'hooks.json')
}

function _codexHookCommand(hookName, scope, projectDir) {
  // Codex requires absolute paths
  const hooksDir = _codexHooksDir(scope, projectDir)
  return path.join(hooksDir, `${hookName}.sh`)
}

async function _patchCodexHooks(hooksJsonPath, hook, force) {
  let data = { hooks: {} }
  try {
    data = JSON.parse(await fs.readFile(hooksJsonPath, 'utf-8'))
  } catch { /* file doesn't exist yet */ }

  if (!data.hooks) data.hooks = {}
  if (!data.hooks[hook.event]) data.hooks[hook.event] = []

  const command = _codexHookCommand(hook.name, 'user', process.cwd()) // resolved per call site
  // Note: actual command is passed in as hook.resolvedCommand (set by caller)
  const resolvedCommand = hook.resolvedCommand

  const alreadyRegistered = data.hooks[hook.event].some(entry =>
    Array.isArray(entry.hooks) && entry.hooks.some(h => h.command === resolvedCommand)
  )

  if (alreadyRegistered && !force) return false
  if (alreadyRegistered && force) {
    data.hooks[hook.event] = data.hooks[hook.event].filter(entry =>
      !Array.isArray(entry.hooks) || !entry.hooks.some(h => h.command === resolvedCommand)
    )
  }

  // Codex format: no "type" field, use absolute path
  const hookEntry = { command: resolvedCommand }
  if (hook.timeout)       hookEntry.timeout       = hook.timeout
  if (hook.statusMessage) hookEntry.statusMessage = hook.statusMessage

  data.hooks[hook.event].push({
    matcher: hook.matcher ?? '',
    hooks: [hookEntry],
  })

  await fs.ensureDir(path.dirname(hooksJsonPath))
  await fs.writeFile(hooksJsonPath, JSON.stringify(data, null, 2) + '\n', 'utf-8')
  return true
}
```

- [ ] **Step 4: Add `installHooksForTarget()` in `lib/installer.js`**

Add after `installHooks()`:

```js
// Install hooks for a specific target ('claude' or 'codex').
// Returns { installed, skipped, failed } (same shape as installHooks).
export async function installHooksForTarget(hooks, target, scope, projectDir, force = false) {
  if (target === 'claude') {
    return installHooks(hooks, scope, projectDir, force)
  }

  // target === 'codex'
  const hooksDir     = _codexHooksDir(scope, projectDir)
  const hooksJsonPath = _codexHooksJsonPath(scope, projectDir)

  await fs.ensureDir(hooksDir)

  const installed = []
  const skipped   = []
  const failed    = []

  for (const hook of hooks) {
    const destScript   = path.join(hooksDir, `${hook.name}.sh`)
    const scriptExists = await fs.pathExists(destScript)

    if (scriptExists && !force) {
      const installedVersion = readHookVersion(destScript)
      const availableVersion = hook.version

      if (availableVersion && installedVersion === availableVersion) {
        skipped.push({ name: hook.name, reason: 'up-to-date', version: installedVersion })
        console.error(chalk.dim(`  · Skipped ${hook.name} (up-to-date ${installedVersion})`))
        continue
      }

      if (!process.stdout.isTTY) {
        skipped.push({ name: hook.name, reason: 'outdated', installed: installedVersion, available: availableVersion ?? '—' })
        console.error(chalk.dim(`  · Skipped ${hook.name} (outdated ${installedVersion} → ${availableVersion}, use --force)`))
        continue
      }

      const ok = await confirm({ message: `${hook.name} ${installedVersion} → ${availableVersion}. Overwrite?`, default: false })
      if (!ok) {
        skipped.push({ name: hook.name, reason: 'outdated', installed: installedVersion, available: availableVersion ?? '—' })
        console.error(chalk.dim(`  · Skipped ${hook.name}`))
        continue
      }
    }

    try {
      if (!await fs.pathExists(hook.srcPath)) {
        failed.push({ name: hook.name, reason: 'source_not_found' })
        console.error(chalk.red(`  ✗ Source not found: ${hook.srcPath}`))
        continue
      }

      await fs.copy(hook.srcPath, destScript, { overwrite: true })
      await fs.chmod(destScript, 0o755)

      // Patch hooks.json with absolute command path
      const resolvedCommand = path.join(hooksDir, `${hook.name}.sh`)
      await _patchCodexHooks(hooksJsonPath, { ...hook, resolvedCommand }, force)

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

- [ ] **Step 5: Export `installHooksForTarget` and wire up `--target` flag in `bin/cli.js`**

In `bin/cli.js`, update the import at the top:

```js
import { installSkills, installTools, installHooks, installHooksForTarget, uninstallHook } from '../lib/installer.js'
```

In the `hooks install` block (around line 470), replace:
```js
const { installed, skipped, failed } = await installHooks(toInstall, hookScopeArg, hookProjectArg, hookForce)
```
with:
```js
const hookTargetArg = hookArgs[hookArgs.indexOf('--target') + 1] ?? 'claude'
const { installed, skipped, failed } = await installHooksForTarget(toInstall, hookTargetArg, hookScopeArg, hookProjectArg, hookForce)
```

Also add `--target` to the `hookArgs` parsing block (after `hookProjectIdx`):
```js
const hookTargetIdx  = hookArgs.indexOf('--target')
const hookTargetArg  = hookTargetIdx !== -1 ? hookArgs[hookTargetIdx + 1] : 'claude'
```

- [ ] **Step 6: Run Codex tests**

```bash
bats tests/hooks.bats --filter "codex"
```

Expected: all 4 codex tests PASS.

- [ ] **Step 7: Run full hooks test suite**

```bash
bats tests/hooks.bats
```

Expected: all tests PASS (no regressions).

- [ ] **Step 8: Commit**

```bash
git add lib/installer.js lib/targets.js bin/cli.js tests/hooks.bats
git commit -m "feat: add Codex hook install target (installHooksForTarget)"
```

---

### Task 3: Extend `checkHookInstalled` in `lib/bundles.js` to include Codex status

**Files:**
- Modify: `lib/bundles.js`

Currently returns `{ user: { status, version }, project: { status, version } }` for Claude Code only.
New shape: `{ claude: { user, project }, codex: { user, project } }`.

- [ ] **Step 1: Write failing test**

Add to `tests/hooks.bats`:

```bash
@test "hooks list --json: includes codex install status" {
  # Install into codex user scope
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex

  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks list --json 2>&1)"
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
    const h = d.hooks.find(h => h.name === '${HOOK_NAME}');
    if (!h) throw new Error('hook not found');
    if (!h.codex) throw new Error('codex field missing from hook status');
    if (h.codex.user.status !== 'installed') throw new Error('expected codex.user=installed, got: ' + h.codex.user.status);
  "
}
```

- [ ] **Step 2: Run to confirm failure**

```bash
bats tests/hooks.bats --filter "codex install status"
```

Expected: FAIL — `codex` field missing.

- [ ] **Step 3: Update `checkHookInstalled` in `lib/bundles.js`**

Replace the existing `checkHookInstalled` function (starting at line 192):

```js
export function checkHookInstalled(hookName) {
  const home = os.homedir()
  const cwd  = process.cwd()

  function checkClaudeScope(hooksDir, settingsPath) {
    const scriptPath        = path.join(hooksDir, `${hookName}.sh`)
    const scriptExists      = fs.existsSync(scriptPath)
    const installedVersion  = scriptExists ? readHookVersion(scriptPath) : '—'
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
    } catch { /* settings.json missing or invalid */ }
    const status = scriptExists && registered ? 'installed'
                 : scriptExists || registered ? 'partial'
                 : 'none'
    return { status, version: installedVersion }
  }

  function checkCodexScope(hooksDir, hooksJsonPath) {
    const scriptPath        = path.join(hooksDir, `${hookName}.sh`)
    const scriptExists      = fs.existsSync(scriptPath)
    const installedVersion  = scriptExists ? readHookVersion(scriptPath) : '—'
    let registered = false
    try {
      const data = JSON.parse(fs.readFileSync(hooksJsonPath, 'utf-8'))
      registered = Object.values(data.hooks ?? {}).some(entries =>
        Array.isArray(entries) && entries.some(e =>
          Array.isArray(e.hooks) && e.hooks.some(h =>
            typeof h.command === 'string' && h.command.includes(`${hookName}.sh`)
          )
        )
      )
    } catch { /* hooks.json missing or invalid */ }
    const status = scriptExists && registered ? 'installed'
                 : scriptExists || registered ? 'partial'
                 : 'none'
    return { status, version: installedVersion }
  }

  const userClaudeHooks    = path.join(home, '.claude', 'hooks')
  const userClaudeSettings = path.join(home, '.claude', 'settings.json')
  const projClaudeHooks    = path.join(cwd,  '.claude', 'hooks')
  const projClaudeSettings = path.join(cwd,  '.claude', 'settings.json')

  const userCodexHooks     = path.join(home, '.codex', 'hooks')
  const userCodexHooksJson = path.join(home, '.codex', 'hooks.json')
  const projCodexHooks     = path.join(cwd,  '.codex', 'hooks')
  const projCodexHooksJson = path.join(cwd,  '.codex', 'hooks.json')

  return {
    // legacy flat fields kept for backward compat with `hskill hooks list` text output
    user:    checkClaudeScope(userClaudeHooks, userClaudeSettings),
    project: cwd === home ? { status: 'none', version: '—' } : checkClaudeScope(projClaudeHooks, projClaudeSettings),
    // per-target
    claude: {
      user:    checkClaudeScope(userClaudeHooks, userClaudeSettings),
      project: cwd === home ? { status: 'none', version: '—' } : checkClaudeScope(projClaudeHooks, projClaudeSettings),
    },
    codex: {
      user:    checkCodexScope(userCodexHooks, userCodexHooksJson),
      project: cwd === home ? { status: 'none', version: '—' } : checkCodexScope(projCodexHooks, projCodexHooksJson),
    },
  }
}
```

- [ ] **Step 4: Update `hooks list --json` in `bin/cli.js` to include `codex` field**

In the `hooks list` JSON branch (around line 414), update the map:

```js
const out = hookItems.map(h => {
  const inst = checkHookInstalled(h.name)
  const ver = resolveHookDisplayVersion(inst, h.version)
  return {
    name: h.name,
    version: ver,
    description: h.description,
    event: h.event,
    user: inst.user,
    project: inst.project,
    claude: inst.claude,
    codex: inst.codex,
  }
})
```

- [ ] **Step 5: Run new test**

```bash
bats tests/hooks.bats --filter "codex install status"
```

Expected: PASS.

- [ ] **Step 6: Run full suite**

```bash
bats tests/hooks.bats
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/bundles.js bin/cli.js tests/hooks.bats
git commit -m "feat: extend checkHookInstalled to include codex target status"
```

---

### Task 4: Add hooks to `fzfSelect()` in `bin/cli.js`

**Files:**
- Modify: `bin/cli.js`

The fzf line format (tab-separated, first field is display line):
`DISPLAY\tNAME\tVERSION\tBUNDLE\tKIND\tSRCPATH`

For hooks: `DISPLAY\tcheck-similar-branch\t1.0.0\thook\thook\t/path/to/script.sh`

- [ ] **Step 1: Write failing interactive test**

Add to `tests/interactive.bats`, after the existing helper functions:

```bash
HOOK_NAME="check-similar-branch"
HOOK_SRC="${REPO_ROOT}/hooks/check-similar-branch"
HOOK_VER="1.0.0"

# fzf output line for a hook (mirrors fzfSelect format).
_hook_line() {
  local name="$1" ver="$2" src="$3"
  printf 'display\t%s\t%s\thook\thook\t%s' "$name" "$ver" "$src"
}
```

Then add a test:

```bash
@test "interactive: hook appears in fzf list (kind=hook)" {
  # The test verifies fzfSelect produces hook lines by checking
  # that selecting a hook line routes to hook install (scope prompt appears).
  # We simulate: select hook → choose scope=user → choose target=claude → Esc loop-back
  _write_responses \
    "$(_hook_line "${HOOK_NAME}" "${HOOK_VER}" "${HOOK_SRC}")" \
    "user" \
    "claude" \
    ""

  run _run_interactive --force

  # Should have consumed 4 fzf calls (selector, scope, target, loop-back)
  [ "$(_fzf_call_count)" -eq 4 ]
  [[ "$output" == *"${HOOK_NAME}"* ]]
}
```

- [ ] **Step 2: Run to confirm failure**

```bash
bats tests/interactive.bats --filter "hook appears in fzf"
```

Expected: FAIL — hook not in fzf list, call count wrong.

- [ ] **Step 3: Update `fzfSelect()` in `bin/cli.js`**

In `fzfSelect()`, update the import at the top of the function and the `lines` array (around line 535):

```js
function fzfSelect() {
  requireFzf()
  const skillItems  = getAllSkillItems()
  const toolItems   = getAllToolItems()
  const hookItems   = getAllHookItems()          // ← ADD
  const previewPath = path.join(__dirname, 'preview.mjs')

  // Build fzf input: each line is "NAME\tVERSION\tBUNDLE\tKIND\tSRCPATH"
  const lines = [
    ...skillItems.map(s => {
      const bundle = s.srcPath.split('/').slice(-2, -1)[0]
      return `${s.skillName}\t${s.version ?? '—'}\t${bundle}\tskill\t${s.srcPath}`
    }),
    ...toolItems.map(t => `${t.toolName}\t${t.version ?? '—'}\tshell-tool\ttool\t${t.srcPath}`),
    ...hookItems.map(h => `${h.name}\t${h.version ?? '—'}\thook\thook\t${h.srcPath}`),   // ← ADD
  ]
```

Update the display line builder to handle `kind === 'hook'` (around line 559):

```js
  const displayLines = lines.map(l => {
    const [name, ver, bundle, kind, srcPath] = l.split('\t')
    let uIcon = D + '—' + R, pIcon = D + '—' + R
    if (kind === 'skill') {
      const installed = checkInstalled(name, ver)
      uIcon = colorIcon(scopeSummary(installed.user))
      pIcon = colorIcon(scopeSummary(installed.project))
    } else if (kind === 'tool') {
      uIcon = colorIcon(checkToolInstalled(name, srcPath).status)
    } else if (kind === 'hook') {                                           // ← ADD
      const inst = checkHookInstalled(name)                                 // ← ADD
      uIcon = colorIcon(inst.user.status === 'installed' ? 'up-to-date'    // ← ADD
             : inst.user.status === 'partial'            ? 'update' : '')  // ← ADD
      pIcon = colorIcon(inst.project.status === 'installed' ? 'up-to-date' // ← ADD
             : inst.project.status === 'partial'            ? 'update' : '')// ← ADD
    }                                                                       // ← ADD
    return `${name.padEnd(nameWidth)}  ${ver.padEnd(versionWidth)}  U:${uIcon}  P:${pIcon}  ${bundle}`
  })
```

Update the return parser (around line 597) to handle hooks:

```js
  return result.stdout.trim().split('\n').map(line => {
    const parts = line.split('\t')
    const [, name, ver, bundle, kind, srcPath] = parts
    if (kind === 'skill') return { kind: 'skill', skillName: name, srcPath, version: ver }
    if (kind === 'hook')  return { kind: 'hook',  name,           srcPath, version: ver }   // ← ADD
    return { kind: 'tool', toolName: name, srcPath, version: ver }
  })
```

Also add `checkHookInstalled` to imports at the top of `bin/cli.js`:

```js
import {
  getAllSkillItems, getAllToolItems, getAllHookItems, checkHookInstalled,  // ← checkHookInstalled added
  checkInstalled, checkToolInstalled, scopeSummary,
  resolveSkills, resolveSkillsByName, resolveTools, resolveToolsByName,
  TOOL_BUNDLE_CHOICES,
} from '../lib/bundles.js'
```

- [ ] **Step 4: Run the new test**

```bash
bats tests/interactive.bats --filter "hook appears in fzf"
```

Expected: PASS — fzf consumed 4 calls (still fails at loop handler, but selector part passes).

- [ ] **Step 5: Run existing interactive tests to check no regression**

```bash
bats tests/interactive.bats
```

Note: hook-related tests may still fail until Task 5. Skill/tool tests must all PASS.

- [ ] **Step 6: Commit**

```bash
git add bin/cli.js
git commit -m "feat: add hooks to fzfSelect() interactive list"
```

---

### Task 5: Handle hook selection in the interactive install loop

**Files:**
- Modify: `bin/cli.js`

After the user selects hooks in fzf, the loop must:
1. Filter `hookItems` from selected
2. Show scope fzf (user/project)
3. Show target fzf (claude/codex/all)
4. Call `installHooksForTarget()` per target

- [ ] **Step 1: Write failing tests**

Add to `tests/interactive.bats`:

```bash
@test "interactive: hook install user+claude scope installs to ~/.claude/hooks/" {
  _write_responses \
    "$(_hook_line "${HOOK_NAME}" "${HOOK_VER}" "${HOOK_SRC}")" \
    "user" \
    "claude" \
    ""

  run _run_interactive --force

  [ -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
}

@test "interactive: hook install user+codex scope installs to ~/.codex/hooks/" {
  _write_responses \
    "$(_hook_line "${HOOK_NAME}" "${HOOK_VER}" "${HOOK_SRC}")" \
    "user" \
    "codex" \
    ""

  run _run_interactive --force

  [ -f "${MOCK_HOME}/.codex/hooks/${HOOK_NAME}.sh" ]
}

@test "interactive: hook install user+all installs to both claude and codex" {
  _write_responses \
    "$(_hook_line "${HOOK_NAME}" "${HOOK_VER}" "${HOOK_SRC}")" \
    "user" \
    "all" \
    ""

  run _run_interactive --force

  [ -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
  [ -f "${MOCK_HOME}/.codex/hooks/${HOOK_NAME}.sh" ]
}

@test "interactive: hook+skill combined selection installs both" {
  _write_responses \
    "$(_skill_line "${SKILL1_NAME}" "${SKILL1_VER}" "${SKILL1_BUNDLE}" "${SKILL1_SRC}")<NL>$(_hook_line "${HOOK_NAME}" "${HOOK_VER}" "${HOOK_SRC}")" \
    "user" \
    "claude" \
    "user" \
    "claude" \
    ""

  run _run_interactive --force

  [[ "$output" == *"${SKILL1_NAME}"* ]]
  [ -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
}
```

- [ ] **Step 2: Run to confirm failure**

```bash
bats tests/interactive.bats --filter "hook install"
```

Expected: FAIL — hook items not yet handled in the loop.

- [ ] **Step 3: Update the interactive loop in `bin/cli.js`**

In the `while (true)` loop (around line 673), after the existing `toolItems`/`skillItems` filters, add hook handling:

```js
    const toolItems  = selected.filter(s => s.kind === 'tool')
    const hookItems  = selected.filter(s => s.kind === 'hook')   // ← ADD
    const seen = new Set()
    const skillItems = selected.filter(s => s.kind === 'skill').filter(s => {
      if (seen.has(s.skillName)) return false
      seen.add(s.skillName); return true
    })

    if (!skillItems.length && !toolItems.length && !hookItems.length) continue
```

After the existing `toolSummary` block and before `printSummary()`, add:

```js
      // ── Hook install ──────────────────────────────────────────────────────
      let hookSummary = null
      if (hookItems.length > 0) {
        // Scope selection
        const hookScopeResult = spawnSync('fzf', [
          '--prompt=  › ',
          '--header=  Hook scope  ·  enter 确认  ·  esc 取消',
          '--layout=reverse',
          '--border=rounded',
          '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
        ], {
          input: `user     — ~/.{claude,codex}/hooks/  (所有项目共享)\nproject  — .{claude,codex}/hooks/    (仅当前项目)`,
          encoding: 'utf8',
          stdio: ['pipe', 'pipe', 'inherit'],
        })
        if (!hookScopeResult.stdout.trim()) {
          console.log(chalk.dim('  · Cancelled'))
          break
        }
        const hookScope = hookScopeResult.stdout.trim().startsWith('project') ? 'project' : 'user'

        // Target selection (claude / codex / all)
        const hookTargetResult = spawnSync('fzf', [
          '--multi',
          '--prompt=  › ',
          '--header=  Install hook to  ·  tab 多选  ·  enter 确认  ·  esc 取消',
          '--layout=reverse',
          '--border=rounded',
          '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
        ], {
          input: `claude   — ~/.claude/hooks/\ncodex    — ~/.codex/hooks/\nall      — claude + codex`,
          encoding: 'utf8',
          stdio: ['pipe', 'pipe', 'inherit'],
        })
        if (!hookTargetResult.stdout.trim()) {
          console.log(chalk.dim('  · Cancelled'))
          break
        }

        const selectedHookTargets = hookTargetResult.stdout.trim().split('\n')
          .map(l => l.trim().split(/\s+/)[0])
        const resolvedHookTargets = selectedHookTargets.includes('all')
          ? ['claude', 'codex']
          : selectedHookTargets.filter(t => ['claude', 'codex'].includes(t))

        hookSummary = {}
        console.log('')
        for (const target of resolvedHookTargets) {
          const result = await installHooksForTarget(hookItems, target, hookScope, process.cwd(), forceFlag)
          hookSummary[target] = result
        }
        console.log('')
      }
```

Update `printSummary()` call to pass `hookSummary`:

```js
      printSummary(skillSummary, toolSummary, hookSummary)
```

- [ ] **Step 4: Update `printSummary()` to handle hookSummary**

Replace `function printSummary(skillSummary, toolSummary)` with:

```js
function printSummary(skillSummary, toolSummary, hookSummary = null) {
  // ... existing skillSummary and toolSummary blocks unchanged ...

  if (hookSummary !== null) {
    const anyInstalled = Object.values(hookSummary).some(r => r.installed.length > 0)
    if (!anyInstalled) {
      console.log(chalk.dim('  · No hooks installed'))
    } else {
      console.log(chalk.green.bold('✔ Hooks installed:'))
      for (const [target, { installed }] of Object.entries(hookSummary)) {
        if (installed.length > 0)
          console.log(`  ${chalk.bold(target)} ← ${installed.join(', ')}`)
      }
    }
    for (const { skipped } of Object.values(hookSummary)) {
      for (const s of skipped) {
        const detail = s.reason === 'outdated'
          ? `outdated ${s.installed} → ${s.available}, use --force`
          : s.reason
        console.log(chalk.dim(`  · ${s.name} skipped (${detail})`))
      }
    }
  }
}
```

- [ ] **Step 5: Run new tests**

```bash
bats tests/interactive.bats --filter "hook install"
```

Expected: all 4 new tests PASS.

- [ ] **Step 6: Run full interactive test suite**

```bash
bats tests/interactive.bats
```

Expected: all tests PASS.

- [ ] **Step 7: Run full test suite**

```bash
npm test
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add bin/cli.js tests/interactive.bats
git commit -m "feat: handle hook selection in interactive install loop (claude + codex targets)"
```

---

### Task 6: Update `hskill hooks list` text output to show codex status

**Files:**
- Modify: `bin/cli.js`

The text output of `hskill hooks list` currently shows `U` and `P` columns (user/project for Claude only). Add `codex` column.

- [ ] **Step 1: Write failing test**

Add to `tests/hooks.bats`:

```bash
@test "hooks list: shows codex install status column" {
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks list 2>&1)"
  echo "$output" | grep -qiE "codex|CX"
}
```

- [ ] **Step 2: Run to confirm failure**

```bash
bats tests/hooks.bats --filter "codex install status column"
```

Expected: FAIL.

- [ ] **Step 3: Update hooks list text output in `bin/cli.js`**

Replace the hooks list table (around line 427):

```js
    const nameWidth = Math.max(...hookItems.map(h => h.name.length), 4)
    const verWidth = 7
    console.log('')
    console.log('  ' + chalk.bold('NAME'.padEnd(nameWidth)) + '  ' + chalk.bold('VER'.padEnd(verWidth)) + '  U  P  CX  ' + chalk.bold('DESCRIPTION'))
    console.log('  ' + '─'.repeat(nameWidth) + '  ' + '─'.repeat(verWidth) + '  ─  ─  ──  ' + '─'.repeat(20))
    for (const h of hookItems) {
      const inst = checkHookInstalled(h.name)
      const ver = resolveHookDisplayVersion(inst, h.version)
      const cxIcon = hookIcon(inst.codex.user.status)
      console.log(
        '  ' + h.name.padEnd(nameWidth) +
        '  ' + chalk.dim(ver.padEnd(verWidth)) +
        '  ' + hookIcon(inst.user.status) +
        '  ' + hookIcon(inst.project.status) +
        '  ' + cxIcon +
        '   ' + h.description
      )
    }
    console.log('')
    console.log(chalk.dim(`  U=claude-user  P=claude-project  CX=codex-user  ${chalk.green('✓')}=installed  ${chalk.yellow('~')}=partial  ${chalk.dim('—')}=none`))
    console.log('')
```

- [ ] **Step 4: Run test**

```bash
bats tests/hooks.bats --filter "codex install status column"
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
npm test
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add bin/cli.js tests/hooks.bats
git commit -m "feat: show codex status column in hskill hooks list output"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|---|---|
| hooks 出现在交互式 fzf 列表 | Task 4 |
| 选中 hook 后出现 scope 选择 | Task 5 |
| 选中 hook 后出现 target 选择 (claude/codex) | Task 5 |
| Claude Code 安装路径正确 | Task 2 (现有逻辑) |
| Codex 安装到 `~/.codex/hooks/` + `hooks.json` | Task 2 |
| Codex hooks.json 无 `type` 字段，用绝对路径 | Task 2 |
| `checkHookInstalled` 返回 codex 状态 | Task 3 |
| `hskill hooks list` 显示 codex 状态列 | Task 6 |
| `printSummary` 打印 hook 安装结果 | Task 5 |
| `all` target 同时安装 claude + codex | Task 5 |
| 不破坏现有 skill/tool 交互流程 | Task 4+5 的回归测试 |

**Placeholder scan:** 无 TBD/TODO。

**Type consistency:**
- `hookItems` 统一为 `{ kind: 'hook', name, srcPath, version }` 形状 — Task 4 (fzfSelect 返回) 和 Task 5 (loop 使用) 一致。
- `hookSummary` 统一为 `{ [target]: { installed, skipped, failed } }` — Task 5 (构建) 和 printSummary (消费) 一致。
- `installHooksForTarget(hooks, target, scope, projectDir, force)` 签名在 Task 2 定义，Task 5 调用一致。
