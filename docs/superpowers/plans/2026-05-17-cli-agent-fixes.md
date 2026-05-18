# CLI Agent-Friendliness Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 remaining gaps that cause agent invocations of hskill to hang, produce unparseable output, or silently discard input.

**Architecture:** All fixes are isolated edits to three files: `lib/installer.js`, `lib/vars.js` (indirectly via call-site guard), `bin/cli.js`. No new files, no new dependencies. Each fix is independently testable.

**Tech Stack:** Node.js ESM, chalk 5.x, @inquirer/prompts, fs-extra

---

## Files touched

| File | Changes |
|------|---------|
| `lib/installer.js` | Fix 1: TTY gate in `_patchZshrc`. Fix 2: TTY gate + default fallback before `resolveVars()` (two call sites). |
| `bin/cli.js` | Fix 3: JSON-structured error in catch block. Fix 4: unified JSON output wrapper. Fix 5: mutual-exclusion guard + schema update. |

---

## Task 1 — `_patchZshrc`: gate `confirm()` on TTY

**Files:** Modify `lib/installer.js` — `_patchZshrc` function (~line 109)

**Problem:** `_patchZshrc` calls `confirm()` with no TTY check. Any tool with a `zshrc.snippet` (e.g. `p-launch`) hangs in non-TTY.

**Change** (add 4 lines before the existing `confirm()` call):

```js
async function _patchZshrc(srcPath, toolName) {
  const snippetPath = path.join(srcPath, 'zshrc.snippet')
  if (!await fs.pathExists(snippetPath)) return

  const zshrcPath = path.join(os.homedir(), '.zshrc')
  const marker = `# >>> ${toolName}`

  const existing = await fs.pathExists(zshrcPath)
    ? await fs.readFile(zshrcPath, 'utf-8')
    : ''

  if (existing.includes(marker)) {
    console.log(chalk.dim(`  · ~/.zshrc already has ${toolName} config, skipping`))
    return
  }

  // ── NEW: skip in non-TTY rather than hang ──
  if (!process.stdout.isTTY) {
    console.log(chalk.dim(`  · Skipped ~/.zshrc patch for ${toolName} (non-TTY — add manually)`))
    return
  }
  // ──────────────────────────────────────────

  const ok = await confirm({
    message: `Add ${toolName} PATH and alias to ~/.zshrc?`,
    default: true,
  })
  if (!ok) return

  const snippet = await fs.readFile(snippetPath, 'utf-8')
  await fs.appendFile(zshrcPath, snippet, 'utf-8')
  console.log(chalk.green(`  ✓ Written to ~/.zshrc`))
}
```

- [ ] Apply the edit to `lib/installer.js`
- [ ] Verify: `node bin/cli.js install --tool p-launch --force 2>&1 | cat` — should complete without hanging (p-launch has a zshrc.snippet)
- [ ] Commit: `git add lib/installer.js && git commit -m "fix(hskill): gate _patchZshrc confirm() on TTY"`

---

## Task 2 — `resolveVars`: use defaults in non-TTY instead of hanging

**Files:** Modify `lib/installer.js` — two call sites of `resolveVars()`: inside `installTools` (~line 67) and `installSkills` (~line 160)

**Problem:** Any skill/tool with a `vars.json` hangs in non-TTY because `resolveVars()` calls `input()` unconditionally.

**Fix:** At each call site, check TTY. If non-TTY, compute defaults without prompting using `substituteVars`. `substituteVars` is already imported from `./vars.js`.

**Change in `installTools`** (replace the existing `if (varDefs.length > 0)` block):

```js
const varDefs = await loadVarDefs(srcPath)
let varsMap = {}
if (varDefs.length > 0) {
  if (!process.stdout.isTTY) {
    const autoVars = buildAutoVars()
    for (const def of varDefs) {
      autoVars[def.name] = substituteVars(def.default ?? '', autoVars)
    }
    varsMap = autoVars
    console.log(chalk.dim(`  · ${toolName}: using default vars (non-TTY)`))
  } else {
    console.log(chalk.bold(`\n  Configure ${toolName}:`))
    varsMap = await resolveVars(varDefs, buildAutoVars())
    for (const def of varDefs) {
      if (def.configFile && def.configKey) {
        await _writeToolConfigVar(def, varsMap[def.name])
      }
    }
  }
}
```

**Change in `installSkills`** (replace the existing `if (varDefs.length > 0)` block):

```js
const varDefs = await loadVarDefs(srcPath)
let varsMap = {}
if (varDefs.length > 0) {
  if (!process.stdout.isTTY) {
    const autoVars = buildAutoVars()
    for (const def of varDefs) {
      autoVars[def.name] = substituteVars(def.default ?? '', autoVars)
    }
    varsMap = autoVars
    console.log(chalk.dim(`  · ${skillName}: using default vars (non-TTY)`))
  } else {
    console.log(chalk.bold(`\n  Configure ${skillName}:`))
    varsMap = await resolveVars(varDefs, buildAutoVars())
  }
}
```

- [ ] Apply both edits to `lib/installer.js`
- [ ] Verify: create a temp skill with a `vars.json` and install it non-interactively — confirm it installs with defaults without prompting
- [ ] Commit: `git add lib/installer.js && git commit -m "fix(hskill): use var defaults in non-TTY instead of hanging on input()"`

---

## Task 3 — Structured JSON errors in `--json` mode

**Files:** Modify `bin/cli.js` — catch block at end of file (~line 631)

**Problem:** The outer `catch` always emits `chalk.red(...)` to stderr as plain text. In `--json` mode an agent receives structured stdout but unstructured stderr on error.

**Change** (replace the existing catch):

```js
} catch (err) {
  if (jsonFlag) {
    process.stderr.write(JSON.stringify({ error: true, message: err.message }) + '\n')
  } else {
    console.error(chalk.red('  ✗ ' + err.message))
  }
  process.exit(1)
}
```

- [ ] Apply the edit to `bin/cli.js`
- [ ] Verify: `node bin/cli.js install --skill nonexistent --target claude --json 2>&1 >/dev/null` → outputs `{"error":true,"message":"Unknown skill: \"nonexistent\""}` to stderr, exit 1
- [ ] Verify: `node bin/cli.js install --skill nonexistent --target claude 2>&1` → outputs `  ✗ Unknown skill: "nonexistent"` (unchanged human format)
- [ ] Commit: `git add bin/cli.js && git commit -m "fix(hskill): emit structured JSON error in --json mode"`

---

## Task 4 — Unified JSON output for skill + tool install

**Files:** Modify `bin/cli.js` — the `if (skillItems.length > 0)` and `if (toolItems.length > 0)` blocks inside `try` (~lines 555–635)

**Problem:** Skills and tools each independently call `console.log(JSON.stringify(...))`. If both run (possible via `--bundle` which can resolve both skill and tool bundles), stdout contains two JSON objects — invalid for any parser. Schema also differs: skills return `{ [target]: { installed, skipped, failed } }`, tools return `{ installed, skipped, failed }` (flat).

**Fix:** Collect both results into variables, then emit a single top-level JSON object `{ skills, tools }` at the end. In human mode, output is unchanged.

**Change** — restructure the install output section:

```js
  // ── Install skills ──────────────────────────────────────────────────────────
  let skillSummary = null
  if (skillItems.length > 0) {
    const targets = resolveTargets(selectedTargets, scope)
    console.log('')
    skillSummary = await installSkills(skillItems, targets, forceFlag)
    console.log('')
  }

  // ── Install shell tools ─────────────────────────────────────────────────────
  let toolSummary = null
  if (toolItems.length > 0) {
    console.log('')
    toolSummary = await installTools(
      toolItems.map(t => ({ toolName: t.toolName, srcPath: t.srcPath })),
      TARGETS.shell,
      forceFlag,
    )
    console.log('')
  }

  // ── Output ──────────────────────────────────────────────────────────────────
  if (jsonFlag) {
    const out = {}
    if (skillSummary !== null) out.skills = skillSummary
    if (toolSummary  !== null) out.tools  = toolSummary
    console.log(JSON.stringify(out, null, 2))
  } else {
    if (skillSummary !== null) {
      const anyInstalled = Object.values(skillSummary).some(r => r.installed.length > 0)
      if (!anyInstalled) {
        console.log(chalk.dim('  · No skills installed'))
      } else {
        console.log(chalk.green.bold('✔ Skills installed:'))
        for (const [target, { installed }] of Object.entries(skillSummary)) {
          if (installed.length > 0)
            console.log(`  ${chalk.bold(target)} ← ${installed.join(', ')}`)
        }
      }
      for (const [target, { skipped, failed }] of Object.entries(skillSummary)) {
        for (const s of skipped) {
          const detail = s.reason === 'up-to-date'
            ? `up-to-date ${s.version}`
            : `outdated ${s.installed} → ${s.available}, use --force`
          console.log(chalk.dim(`  · ${target}/${s.name} skipped (${detail})`))
        }
        for (const f of failed) {
          console.log(chalk.red(`  ✗ ${target}/${f.name} failed: ${f.reason}${f.detail ? ` — ${f.detail}` : ''}`))
        }
      }
    }
    if (toolSummary !== null) {
      if (toolSummary.installed.length === 0 && !toolSummary.skipped.length && !toolSummary.failed.length) {
        console.log(chalk.dim('  · No shell tools installed'))
      } else {
        if (toolSummary.installed.length > 0) {
          console.log(chalk.green.bold('✔ Shell tools installed:'))
          for (const name of toolSummary.installed) {
            console.log(`  ${chalk.bold('~/.local/bin')} ← ${name}`)
          }
          console.log('')
          console.log(chalk.yellow.bold('  ⚡ Reload your shell to apply changes:'))
          console.log('')
          console.log(`     ${chalk.bold.cyan('source ~/.zshrc')}`)
          console.log('')
        }
        for (const s of toolSummary.skipped) {
          console.log(chalk.dim(`  · ${s.name} skipped (${s.reason === 'already_exists' ? 'already exists — use --force to overwrite' : s.reason})`))
        }
        for (const f of toolSummary.failed) {
          console.log(chalk.red(`  ✗ ${f.name} failed: ${f.reason}${f.detail ? ` — ${f.detail}` : ''}`))
        }
      }
    }
  }
```

Note: the `selectedTargets` / `scope` variables need to be in scope for `resolveTargets`. They are — they're resolved in the same `if (skillItems.length > 0)` block above. The refactor moves `resolveTargets` inside the `if (skillItems.length > 0)` guard.

- [ ] Apply the edit to `bin/cli.js`
- [ ] Verify skills-only: `node bin/cli.js install --skill skill-analyzer --target claude --json 2>/dev/null` → single JSON object with `{ "skills": { ... } }`
- [ ] Verify tools-only: `node bin/cli.js install --tool p-launch --json 2>/dev/null` → single JSON object with `{ "tools": { ... } }`
- [ ] Verify human mode unchanged: `node bin/cli.js install --skill skill-analyzer --target claude` → same output as before
- [ ] Commit: `git add bin/cli.js && git commit -m "fix(hskill): unify skill+tool JSON output into single object"`

---

## Task 5 — Mutual-exclusion guard for `--skill` + `--tool`

**Files:** Modify `bin/cli.js` — top of the `try` block (~line 630) and the `--help --json` schema (~line 63)

**Problem:** Specifying `--skill` and `--tool` together silently drops `--skill` because of `if (toolArg) ... else if (skillArg)` routing. Agent gets no error, no warning.

**Change 1** — add guard at top of `try` block, before the `if (toolArg)` routing:

```js
try {
  // mutual exclusion guard
  if (toolArg && skillArg) {
    const msg = '--tool and --skill cannot be combined; use --bundle to install both'
    if (jsonFlag) process.stderr.write(JSON.stringify({ error: true, message: msg }) + '\n')
    else console.error(chalk.red('  ✗ ' + msg))
    process.exit(1)
  }

  let skillItems = []
  let toolItems  = []
  // ... rest unchanged
```

**Change 2** — add `mutually_exclusive` note to `install` command in `--help --json` schema:

```js
{
  name: 'install',
  description: 'Install skills or shell tools',
  interactive_fallback: 'Requires TTY + fzf when no flags given',
  note: '--skill and --tool are mutually exclusive; use --bundle to install both',  // ← ADD
  flags: [ ... ],
},
```

- [ ] Apply both edits to `bin/cli.js`
- [ ] Verify: `node bin/cli.js install --skill skill-analyzer --tool p-launch --target claude 2>/dev/null; echo $?` → exit 1 with error message
- [ ] Verify JSON error: `node bin/cli.js install --skill skill-analyzer --tool p-launch --target claude --json 2>&1 >/dev/null` → `{"error":true,"message":"--tool and --skill cannot be combined..."}`
- [ ] Verify schema: `node bin/cli.js --help --json | jq '.commands[0].note'` → shows the note
- [ ] Commit: `git add bin/cli.js && git commit -m "fix(hskill): error on --skill + --tool combined; document mutual exclusion in schema"`

---

## Self-Review

**Spec coverage:**
- Fix 1 (`_patchZshrc` TTY): ✓ Task 1
- Fix 2 (`vars.js` input() TTY): ✓ Task 2
- Fix 3 (JSON-mode errors): ✓ Task 3
- Fix 4 (dual JSON + schema inconsistency): ✓ Task 4
- Fix 5 (mutual exclusion): ✓ Task 5

**Placeholder scan:** None found — all steps contain exact code.

**Type consistency:** `skillSummary` shape (`{ [target]: { installed, skipped, failed } }`) matches what `installSkills` returns. `toolSummary` shape (`{ installed, skipped, failed }`) matches `installTools`. Consistent throughout Task 4.

**Edge case — Task 4 scope variable:** `scope` is resolved inside the TTY selection block. If `--scope` was provided via flag (`scopeArg`), `scope` is already set. If selected via fzf, it's also set. Task 4 reads `scope` to call `resolveTargets` — this is safe because the fzf / flag paths both set `scope` before the install section is reached.

**Edge case — Task 2 `_writeToolConfigVar`:** In the current code, `_writeToolConfigVar` is only called inside the interactive branch (`resolveVars`). In non-TTY mode with default vars, `_writeToolConfigVar` is not called. This means config files (e.g. tool API keys) won't be written in non-TTY. This is correct: a config file needing a real value can't be safely written with a blank default. Agent callers that need configured tools must use TTY.
