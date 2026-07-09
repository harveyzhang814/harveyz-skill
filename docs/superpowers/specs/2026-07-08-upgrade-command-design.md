---
title: hskill upgrade command
date: 2026-07-08
status: approved
migrated: 2026-07-09
docs:
  - reference/agent-cli-guide.md  # 新增 Upgrade 章节：flags、版本比较、输出格式、错误处理
implemented_in:
  - bin/cli.js  # upgrade 子命令实现、buildSkillRows() 共享 helper
---

# hskill upgrade

Add a new `upgrade` subcommand that updates already-installed skills to their latest version. Never installs skills that are not already present.

## Command Syntax

```
hskill upgrade                                        # all installed skills, all targets
hskill upgrade --target claude                        # all installed on one target
hskill upgrade --skill learn-skill                    # one skill on all targets it's installed on
hskill upgrade --skill learn-skill --target claude    # exact match
hskill upgrade --scope project                        # project-level installs (default: user)
hskill upgrade --json                                 # machine-readable output
```

`--skill` and `--target` are independently optional and combinable. Omitting either means "all".

## Scope

- Default scope: `user` (`~/.{target}/skills/`)
- `--scope project`: `.{target}/skills/` in cwd
- Mirrors install's scope model; no auto-scan of both scopes

## Algorithm

### 1. Refactor: extract `buildSkillRows(nameFilter?)`

Move the skill scan currently inlined in the `status`/`outdated` block into a named helper inside `cli.js`. `status` and `outdated` call it unchanged.

```js
function buildSkillRows(nameFilter = null) {
  const items = nameFilter
    ? getAllSkillItems().filter(s => s.skillName === nameFilter)
    : getAllSkillItems()
  return items.map(s => {
    const inst = checkInstalled(s.skillName, s.version ?? '—')
    return {
      name: s.skillName, bundle: s.bundle ?? '—', version: s.version ?? '—',
      installScope: s.installScope ?? null,
      srcPath: s.srcPath,                                         // carried through for upgrade
      userStatus: scopeSummary(inst.user), projectStatus: scopeSummary(inst.project),
      userDetail: inst.user, projectDetail: inst.project,
    }
  })
}
```

### 2. upgrade block logic

```
Parse flags: skillArg, targetArg, scopeArg (default 'user')

rows = buildSkillRows(skillArg ?? null)

targetList = resolveTargets(targetArg ? [targetArg] : ['all'], scopeArg)

summary = {}
for each { name, dir } in targetList:
  upgradeList = rows
    .filter(r => r[scopeArg + 'Detail'][name].status === 'update')
    .map(r => ({ skillName: r.name, srcPath: ..., version: r.version }))

  if upgradeList is empty: continue

  summary[name] = await installSkills(upgradeList, [{ name, dir }], force=true)

if summary is empty:
  print "✓ All installed skills are up to date"
else:
  printSummary(summary, null)
```

Version comparison: `checkInstalled` compares installed SKILL.md `version:` field against source. `status === 'update'` means versions differ. `status === 'none'` means not installed — skip. `status === 'up-to-date'` — skip silently.

`installSkills` is called with `force=true` to bypass its own version check (filtering is already done above).

### 3. upgradeList construction

`buildSkillRows` carries `srcPath` through, so upgradeList is straightforward:

```js
const scopeKey = scopeArg + 'Detail'   // 'userDetail' or 'projectDetail'
const upgradeList = rows
  .filter(r => r[scopeKey][targetName].status === 'update')
  .map(r => ({ skillName: r.name, srcPath: r.srcPath, version: r.version }))
```

## Output

### Human-readable

Reuses existing `printSummary(skillSummary, null)` — same format as `install`. Nothing to upgrade:

```
  ✓ All installed skills are up to date
```

### JSON (`--json`)

Same structure as `install --json`:

```json
{
  "skills": {
    "claude": { "installed": ["learn-skill"], "skipped": [], "failed": [] }
  }
}
```

Nothing to upgrade:

```json
{ "skills": {}, "upToDate": true }
```

## Error Handling

| Condition | Behaviour |
|---|---|
| `--skill <name>` not in skills-index | `getAllSkillItems().filter` returns empty → "✓ All installed skills are up to date" (nothing matched). Consider: throw `Unknown skill: "<name>"` for explicit feedback. |
| `--target <name>` invalid | `resolveTargets` already throws `Unknown target: "<name>"` — caught by outer try/catch |
| Source file missing | `installSkills` handles it, pushes to `failed[]` |

For `--skill` with an unknown name, throw early with a clear error rather than silently reporting "up to date" — this is the less surprising behaviour.

## Not in Scope

- Tools (`--tool`) — upgrade for tools is out of scope for this feature
- Hooks — out of scope
- Interactive mode — `upgrade` is always non-interactive; no fzf selector needed
- `--force` flag — not needed; if `status === 'update'`, we always upgrade
