# hskill upgrade Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `hskill upgrade` subcommand that updates only already-installed skills to their latest version, across 4 targeting modes.

**Architecture:** Extract a shared `buildSkillRows()` helper in `bin/cli.js` used by `status`, `outdated`, and the new `upgrade` block. The `upgrade` block filters each target's installed skills to those with `status === 'update'`, then calls the existing `installSkills(..., force=true)`. No new files; no changes to `lib/`.

**Tech Stack:** Node.js ESM, bats-core (tests), existing `installSkills` / `checkInstalled` / `resolveTargets` / `getAllSkillItems` APIs from `lib/`.

## Global Constraints

- All subcommand logic stays in `bin/cli.js` (no new lib files)
- Never install a skill that has `status === 'none'` on a given target
- Scope default: `user`; `--scope project` supported
- `--json` flag outputs to stdout only; errors to stderr
- Tests use `MOCK_HOME` pattern established in `tests/install.bats` and `tests/agent-cli.bats`
- `bats-core` required (`brew install bats-core`)

---

## File Map

| File | Change |
|---|---|
| `bin/cli.js` | Extract `buildSkillRows()` helper; update `status`/`outdated` callers; add `upgrade` block; add `upgrade` to `--help --json` commands array |
| `tests/upgrade.bats` | New: end-to-end bats tests for upgrade subcommand |

---

## Task 1: Extract `buildSkillRows()` and update callers

**Files:**
- Modify: `bin/cli.js` (status/outdated block, ~lines 247–255)

**Interfaces:**
- Produces: `buildSkillRows(nameFilter?: string | null) → Array<{ name, bundle, version, installScope, srcPath, userStatus, projectStatus, userDetail, projectDetail }>`

- [ ] **Step 1: Locate the existing skillRows scan in cli.js**

In `bin/cli.js`, find the block starting around line 220 (`if (subcommand === 'status' || subcommand === 'outdated')`). The skillRows scan to extract is:

```js
const skillItems = getAllSkillItems()
const skillRows  = skillItems.map(s => {
  const inst = checkInstalled(s.skillName, s.version ?? '—')
  return {
    name: s.skillName, bundle: s.bundle ?? '—', version: s.version ?? '—',
    installScope: s.installScope ?? null,
    userStatus: scopeSummary(inst.user), projectStatus: scopeSummary(inst.project),
    userDetail: inst.user, projectDetail: inst.project,
  }
}).sort((a, b) => a.bundle.localeCompare(b.bundle) || a.name.localeCompare(b.name))
```

- [ ] **Step 2: Add `buildSkillRows` helper above the status/outdated block**

Insert before the `if (subcommand === 'status' || subcommand === 'outdated')` line:

```js
// ── Shared skill scan ─────────────────────────────────────────────────────────
function buildSkillRows(nameFilter = null) {
  const items = nameFilter
    ? getAllSkillItems().filter(s => s.skillName === nameFilter)
    : getAllSkillItems()
  return items.map(s => {
    const inst = checkInstalled(s.skillName, s.version ?? '—')
    return {
      name:         s.skillName,
      bundle:       s.bundle        ?? '—',
      version:      s.version       ?? '—',
      installScope: s.installScope  ?? null,
      srcPath:      s.srcPath,
      userStatus:   scopeSummary(inst.user),
      projectStatus: scopeSummary(inst.project),
      userDetail:   inst.user,
      projectDetail: inst.project,
    }
  })
}
```

- [ ] **Step 3: Replace the inlined skillRows scan with a call to `buildSkillRows`**

Inside the `if (subcommand === 'status' || subcommand === 'outdated')` block, replace:

```js
const skillItems = getAllSkillItems()
const skillRows  = skillItems.map(s => {
  const inst = checkInstalled(s.skillName, s.version ?? '—')
  return {
    name: s.skillName, bundle: s.bundle ?? '—', version: s.version ?? '—',
    installScope: s.installScope ?? null,
    userStatus: scopeSummary(inst.user), projectStatus: scopeSummary(inst.project),
    userDetail: inst.user, projectDetail: inst.project,
  }
}).sort((a, b) => a.bundle.localeCompare(b.bundle) || a.name.localeCompare(b.name))
```

with:

```js
const skillRows = buildSkillRows().sort((a, b) =>
  a.bundle.localeCompare(b.bundle) || a.name.localeCompare(b.name)
)
```

- [ ] **Step 4: Run existing tests to confirm no regression**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
npm test
```

Expected: all tests pass (same as before this change).

- [ ] **Step 5: Commit**

```bash
git add bin/cli.js
git commit -m "refactor(cli): extract buildSkillRows() helper for shared skill scan"
```

---

## Task 2: Add `upgrade` subcommand

**Files:**
- Modify: `bin/cli.js` — add upgrade block after the `uninstall` block; add `upgrade` entry in `--help --json` commands array
- Create: `tests/upgrade.bats`

**Interfaces:**
- Consumes: `buildSkillRows(nameFilter?)`, `resolveTargets(selected, scope)`, `installSkills(skills, targets, force)`, `printSummary(skillSummary, null)`, `jsonFlag`, `SKILL_TARGETS`

- [ ] **Step 1: Write the failing tests**

Create `tests/upgrade.bats`:

```bash
#!/usr/bin/env bats
# End-to-end tests for `hskill upgrade`.
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"
SKILL_NAME="survey-skillrepo"
SKILL_SRC="${REPO_ROOT}/skills/research/survey-skillrepo"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  mkdir -p "${MOCK_HOME}/.claude/skills"
  mkdir -p "${MOCK_HOME}/.cursor/skills"
  mkdir -p "${MOCK_HOME}/.config/opencode/skills"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

_upgrade() {
  HOME="${MOCK_HOME}" node "${CLI}" upgrade "$@" 2>/tmp/bats-upgrade-stderr | cat
}

_upgrade_exit() {
  HOME="${MOCK_HOME}" node "${CLI}" upgrade "$@" 2>/tmp/bats-upgrade-stderr
}

_stderr() { cat /tmp/bats-upgrade-stderr; }

_skill_version() {
  grep -o 'version: [^[:space:]]*' "$1" | head -1 | awk '{print $2}' | tr -d '"'
}

_install_old_version() {
  local target="${1:-claude}"
  local dest="${MOCK_HOME}/.${target}/skills/${SKILL_NAME}"
  mkdir -p "${dest}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${SKILL_NAME}" > "${dest}/SKILL.md"
}

# ── basic upgrade ─────────────────────────────────────────────────────────────

@test "upgrade --skill --target: upgrades outdated skill" {
  _install_old_version claude
  _upgrade --skill "${SKILL_NAME}" --target claude --scope user
  local installed_ver
  installed_ver="$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL_NAME}/SKILL.md")"
  local available_ver
  available_ver="$(_skill_version "${SKILL_SRC}/SKILL.md")"
  [ "${installed_ver}" = "${available_ver}" ]
}

@test "upgrade --skill --target: skips skill not installed on that target" {
  # skill installed on claude but NOT cursor
  _install_old_version claude
  run _upgrade --skill "${SKILL_NAME}" --target cursor --scope user
  [ "$status" -eq 0 ]
  [ ! -f "${MOCK_HOME}/.cursor/skills/${SKILL_NAME}/SKILL.md" ]
  [[ "$output" == *"up to date"* ]]
}

@test "upgrade --skill --target: skips already up-to-date skill silently" {
  # Install at current version
  HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL_NAME}" --target claude --scope user --force 2>/dev/null | cat
  run _upgrade --skill "${SKILL_NAME}" --target claude --scope user
  [ "$status" -eq 0 ]
  [[ "$output" == *"up to date"* ]]
}

@test "upgrade --target: upgrades all outdated skills on that target" {
  _install_old_version claude
  _upgrade --target claude --scope user
  local installed_ver
  installed_ver="$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL_NAME}/SKILL.md")"
  local available_ver
  available_ver="$(_skill_version "${SKILL_SRC}/SKILL.md")"
  [ "${installed_ver}" = "${available_ver}" ]
}

@test "upgrade (global): nothing installed prints up-to-date message" {
  run _upgrade
  [ "$status" -eq 0 ]
  [[ "$output" == *"up to date"* ]]
}

# ── --json output ─────────────────────────────────────────────────────────────

@test "upgrade --json: valid JSON to stdout when skill upgraded" {
  _install_old_version claude
  run _upgrade --skill "${SKILL_NAME}" --target claude --scope user --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"skills"'* ]]
}

@test "upgrade --json: installed array contains skill name after upgrade" {
  _install_old_version claude
  run _upgrade --skill "${SKILL_NAME}" --target claude --scope user --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))
    const installed = d.skills?.claude?.installed ?? []
    if (!installed.includes('${SKILL_NAME}')) {
      console.error('skill not in installed:', JSON.stringify(installed))
      process.exit(1)
    }
  "
}

@test "upgrade --json: upToDate:true when nothing to upgrade" {
  run _upgrade --skill "${SKILL_NAME}" --target claude --scope user --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))
    if (!d.upToDate) { console.error('upToDate missing'); process.exit(1) }
  "
}

@test "upgrade --skill unknown: exits 1 with error" {
  run _upgrade_exit --skill __nonexistent__ --target claude --scope user
  [ "$status" -eq 1 ]
  [[ "$(_stderr)" == *"Unknown skill"* ]]
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
bats tests/upgrade.bats
```

Expected: all tests fail with "Unknown command" or similar — `upgrade` subcommand does not exist yet.

- [ ] **Step 3: Add `upgrade` to `--help --json` commands array**

In `bin/cli.js`, inside the `--help --json` block, add to the `commands` array after the `uninstall` entry:

```js
{
  name: 'upgrade',
  description: 'Upgrade already-installed skills to their latest version',
  note: 'Only upgrades skills already installed on the given target. Never installs new ones.',
  flags: [
    { name: '--skill',  arg: '<name>',   description: 'Upgrade a specific skill (default: all installed)' },
    { name: '--target', arg: '<target>', description: 'Limit to one target', enum: ['claude','cursor','codex','openclaw','hermes','opencode'] },
    { name: '--scope',  arg: '<scope>',  description: 'Install scope', enum: ['user','project'], default: 'user' },
    { name: '--json',   description: 'Machine-readable output' },
  ],
},
```

- [ ] **Step 4: Add `upgrade` subcommand block in cli.js**

Insert the following block after the `if (subcommand === 'hooks')` block and before the `// ── Install` section:

```js
// ── Upgrade ───────────────────────────────────────────────────────────────────
if (subcommand === 'upgrade') {
  const upgradeSkillIdx  = args.indexOf('--skill')
  const upgradeTargetIdx = args.indexOf('--target')
  const upgradeScopeIdx  = args.indexOf('--scope')
  const upgradeSkillArg  = upgradeSkillIdx  !== -1 ? args[upgradeSkillIdx  + 1] : null
  const upgradeTargetArg = upgradeTargetIdx !== -1 ? args[upgradeTargetIdx + 1] : null
  const upgradeScopeArg  = upgradeScopeIdx  !== -1 ? args[upgradeScopeIdx  + 1] : 'user'

  // Validate --skill name early for clear error feedback
  if (upgradeSkillArg) {
    const known = getAllSkillItems().some(s => s.skillName === upgradeSkillArg)
    if (!known) {
      const msg = `Unknown skill: "${upgradeSkillArg}"`
      if (jsonFlag) process.stderr.write(JSON.stringify({ error: true, message: msg }) + '\n')
      else console.error(chalk.red('  ✗ ' + msg))
      process.exit(1)
    }
  }

  const rows        = buildSkillRows(upgradeSkillArg)
  const targetList  = resolveTargets(upgradeTargetArg ? [upgradeTargetArg] : ['all'], upgradeScopeArg)
  const scopeKey    = upgradeScopeArg + 'Detail'   // 'userDetail' or 'projectDetail'

  const summary = {}
  for (const { name: targetName, dir } of targetList) {
    const upgradeList = rows
      .filter(r => r[scopeKey]?.[targetName]?.status === 'update')
      .map(r => ({ skillName: r.name, srcPath: r.srcPath, version: r.version }))

    if (!upgradeList.length) continue

    console.log('')
    const result = await installSkills(upgradeList, [{ name: targetName, dir }], true)
    summary[targetName] = result
    console.log('')
  }

  const nothingUpgraded = Object.keys(summary).length === 0
  if (jsonFlag) {
    if (nothingUpgraded) {
      console.log(JSON.stringify({ skills: {}, upToDate: true }, null, 2))
    } else {
      console.log(JSON.stringify({ skills: summary }, null, 2))
    }
  } else {
    if (nothingUpgraded) {
      console.log(chalk.green('  ✓ All installed skills are up to date'))
    } else {
      printSummary(summary, null)
    }
  }
  process.exit(0)
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
bats tests/upgrade.bats
```

Expected: all tests pass.

- [ ] **Step 6: Run full test suite to confirm no regressions**

```bash
npm test
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add bin/cli.js tests/upgrade.bats
git commit -m "feat(cli): add upgrade subcommand for batch skill updates"
```
