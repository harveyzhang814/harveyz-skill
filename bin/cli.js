#!/usr/bin/env node
import { select } from '@inquirer/prompts'
import chalk from 'chalk'
import { execSync, spawnSync } from 'child_process'
import { createRequire } from 'module'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'
import {
  getAllSkillItems, getAllToolItems, getAllHookItems, checkHookInstalled,
  checkInstalled, checkToolInstalled, scopeSummary,
  resolveSkills, resolveSkillsByName, resolveTools, resolveToolsByName,
  TOOL_BUNDLE_CHOICES,
} from '../lib/bundles.js'
import { buildTargetChoices, resolveTargets, TARGETS, USER_ONLY_TARGETS } from '../lib/targets.js'
import { installSkills, installTools, installHooks, installHooksForTarget, uninstallHook, uninstallTool, uninstallSkill } from '../lib/installer.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)
const { version } = require('../package.json')

const args = process.argv.slice(2)
const subcommand = args[0]
const jsonFlag = args.includes('--json')

// ── Help ─────────────────────────────────────────────────────────────────────
function printHelp() {
  console.log(`
  ${chalk.bold('hskill')} — skill manager for Claude Code, Cursor, Codex, OpenClaw, and Hermes  v${version}

  ${chalk.cyan('Usage:')}
    hskill                         interactive install (requires TTY + fzf)
    hskill install                 interactive install (explicit)
    hskill install --bundle <b>    install a skill bundle
    hskill install --skill <s>     install specific skill(s)
    hskill install --tool <t>      install shell tool(s)
    hskill install --target <t>    set target (claude/cursor/codex/openclaw/hermes/all)
    hskill install --scope <s>     set scope: user (default) or project
    hskill install --force         overwrite existing installs
    hskill list [--json]           list available skills and bundles
    hskill status [--json]         show install status for all skills and tools
    hskill outdated [--json]       list skills and tools with available updates
    hskill info <name> [--json]    show install detail for a skill or tool
    hskill hooks list [--json]                        list hooks and install status
    hskill hooks install [--name <n>] [--scope <s>]  install hook (scope: user|project)
    hskill hooks install [--project <path>]           target project dir (for project scope)
    hskill hooks install [--force]                    overwrite existing
    hskill hooks uninstall <name> [--scope <s>]       remove hook
    hskill uninstall <tool>            uninstall a shell tool and clean up all files
    hskill uninstall <tool> --yes      skip all confirmations (incl. config files)
    hskill uninstall <skill> --scope <s> --target <t>  uninstall a skill
    hskill update                  update hskill to the latest version
    hskill version                 show version
    hskill --help                  show this help

  ${chalk.cyan('Examples:')}
    hskill install --bundle dev --target claude
    hskill install --skill git-workflow-init --target claude --scope project
    hskill install --tool p-launch
    hskill status
    hskill status --json
    hskill outdated
    hskill info git-workflow-init

  ${chalk.cyan('Agent / CI usage:')}
    Use --json for machine-readable output on status, list, outdated, info.
    Set NO_COLOR=1 to suppress ANSI color codes in all output.
    Interactive mode (no flags) requires a TTY; use --bundle/--skill/--tool in scripts.
`)
}

if (args[0] === '--help' || args[0] === '-h') {
  if (jsonFlag || args.includes('--json')) {
    console.log(JSON.stringify({
      name: 'hskill',
      version,
      description: 'Skill manager for Claude Code, Cursor, Codex, OpenClaw, and Hermes',
      agent_notes: 'Interactive mode requires TTY. Use --json for machine-readable output. Set NO_COLOR=1 to suppress ANSI codes.',
      commands: [
        {
          name: 'install',
          description: 'Install skills or shell tools',
          interactive_fallback: 'Requires TTY + fzf when no flags given',
          note: '--skill and --tool are mutually exclusive; use --bundle to install both',
          flags: [
            { name: '--bundle', arg: '<name>',   description: 'Install a skill bundle (comma-separated)' },
            { name: '--skill',  arg: '<name>',   description: 'Install specific skill(s) (comma-separated)' },
            { name: '--tool',   arg: '<name>',   description: 'Install shell tool(s) (comma-separated)' },
            { name: '--target', arg: '<target>', description: 'Install target', enum: ['claude','cursor','codex','openclaw','hermes','all'] },
            { name: '--scope',  arg: '<scope>',  description: 'Install scope', enum: ['user','project'], default: 'user' },
            { name: '--force',  description: 'Overwrite existing installs' },
          ],
        },
        {
          name: 'list',
          description: 'List available skills and bundles',
          flags: [{ name: '--json', description: 'Machine-readable output' }],
        },
        {
          name: 'status',
          description: 'Show install status for all skills and tools',
          flags: [{ name: '--json', description: 'Machine-readable output' }],
        },
        {
          name: 'outdated',
          description: 'List skills and tools with available updates',
          flags: [{ name: '--json', description: 'Machine-readable output' }],
        },
        {
          name: 'info',
          description: 'Show install detail for a skill or tool',
          args: ['<name>'],
          flags: [{ name: '--json', description: 'Machine-readable output' }],
        },
        {
          name: 'uninstall',
          description: 'Uninstall a shell tool or skill',
          args: ['<name>'],
          flags: [
            { name: '--yes',    description: 'Skip all confirmations including config file removal' },
            { name: '--scope',  arg: '<scope>',  description: 'Skill scope: user or project', enum: ['user','project'] },
            { name: '--target', arg: '<target>', description: 'Skill target: claude, cursor, codex, etc.' },
          ],
        },
        {
          name: 'update',
          description: 'Update hskill to the latest version via npm',
        },
        {
          name: 'version',
          description: 'Print version and exit',
        },
      ],
    }, null, 2))
    process.exit(0)
  }
  printHelp()
  process.exit(0)
}

if (args[0] === '--version' || args[0] === '-v' || subcommand === 'version') {
  console.log(version)
  process.exit(0)
}

// ── Update ───────────────────────────────────────────────────────────────────
if (subcommand === 'update') {
  console.log(chalk.dim('  · Updating hskill…'))
  try {
    execSync('npm update -g harveyz-skill', { stdio: 'inherit' })
    console.log(chalk.green('  ✔ hskill updated'))
  } catch {
    console.error(chalk.red('  ✗ Update failed. Try: npm update -g harveyz-skill'))
    process.exit(1)
  }
  process.exit(0)
}

// ── List ─────────────────────────────────────────────────────────────────────
if (subcommand === 'list') {
  const { skills, tools = [] } = require('../skills-index.json')
  const sorted = [...skills].sort((a, b) => a.bundle.localeCompare(b.bundle) || a.path.split('/').pop().localeCompare(b.path.split('/').pop()))
  if (jsonFlag) {
    console.log(JSON.stringify({
      skills: sorted.map(s => ({ name: s.path.split('/').pop(), path: s.path, bundle: s.bundle })),
      tools: tools.map(t => t.name),
    }, null, 2))
    process.exit(0)
  }
  const nw = Math.max(...sorted.map(s => s.path.split('/').pop().length), 4)
  const bw = Math.max(...sorted.map(s => s.bundle.length), 6)
  const sep = chalk.dim('  ' + '─'.repeat(nw + bw + 4))
  console.log('')
  console.log('  ' + chalk.bold('NAME'.padEnd(nw)) + '  ' + chalk.bold('BUNDLE'))
  console.log(sep)
  for (const s of sorted) {
    console.log('  ' + s.path.split('/').pop().padEnd(nw) + '  ' + chalk.dim(s.bundle))
  }
  if (tools.length > 0) {
    console.log('')
    console.log('  ' + chalk.bold('SHELL TOOLS'))
    console.log(sep)
    for (const t of tools) console.log('  ' + t.name)
  }
  console.log('')
  process.exit(0)
}

// ── Helper: resolve displayed version for a hook ──────────────────────────────
// Priority: user-installed → project-installed → source version
function resolveHookDisplayVersion(inst, sourceVersion) {
  if (inst.user.version !== '—') return inst.user.version
  if (inst.project.version !== '—') return inst.project.version
  return sourceVersion ?? '—'
}

// ── Status / Outdated ─────────────────────────────────────────────────────────
if (subcommand === 'status' || subcommand === 'outdated') {
  const outdatedOnly = subcommand === 'outdated'
  const skillItems   = getAllSkillItems()
  const toolItems    = getAllToolItems()
  const hookItems    = getAllHookItems()

  function icon(status) {
    if (status === 'up-to-date') return chalk.green('✓')
    if (status === 'update')     return chalk.yellow('↑')
    return chalk.dim('—')
  }

  const skillRows = skillItems.map(s => {
    const inst = checkInstalled(s.skillName, s.version ?? '—')
    return {
      name: s.skillName, bundle: s.bundle ?? '—', version: s.version ?? '—',
      userStatus: scopeSummary(inst.user), projectStatus: scopeSummary(inst.project),
      userDetail: inst.user, projectDetail: inst.project,
    }
  }).sort((a, b) => a.bundle.localeCompare(b.bundle) || a.name.localeCompare(b.name))
  const toolRows = toolItems.map(t => {
    const inst = checkToolInstalled(t.toolName, t.srcPath)
    return { name: t.toolName, version: t.version ?? '—', ...inst }
  })

  if (jsonFlag) {
    const targets = ['claude', 'cursor', 'codex', 'openclaw', 'hermes']
    const jsonSkills = skillRows.map(r => ({
      name: r.name,
      version: r.version,
      user:    Object.fromEntries(targets.map(t => [t, r.userDetail[t]])),
      project: Object.fromEntries(targets.map(t => [t, r.projectDetail[t]])),
    }))
    const jsonTools = toolRows.map(r => ({ name: r.name, version: r.version, status: r.status }))
    const jsonHooks = hookItems.map(h => {
      const inst = checkHookInstalled(h.name)
      return { name: h.name, description: h.description, user: inst.user, project: inst.project }
    })
    if (outdatedOnly) {
      console.log(JSON.stringify({
        skills: jsonSkills.filter(s => Object.values(s.user).some(v => v.status === 'update') || Object.values(s.project).some(v => v.status === 'update')),
        tools:  jsonTools.filter(t => t.status === 'update'),
      }, null, 2))
    } else {
      console.log(JSON.stringify({ skills: jsonSkills, tools: jsonTools, hooks: jsonHooks }, null, 2))
    }
    process.exit(0)
  }

  if (outdatedOnly) {
    const outdatedSkills = skillRows.filter(r => r.userStatus === 'update' || r.projectStatus === 'update')
    const outdatedTools  = toolRows.filter(r => r.status === 'update')

    if (!outdatedSkills.length && !outdatedTools.length) {
      console.log(chalk.green.bold('\n  ✓ All installed skills and tools are up to date\n'))
      process.exit(0)
    }

    const targets = ['claude', 'cursor', 'codex', 'openclaw', 'hermes']

    if (outdatedSkills.length) {
      console.log('\n  ' + chalk.bold('SKILLS WITH UPDATES'))
      const nw = Math.max(...outdatedSkills.map(r => r.name.length))
      for (const r of outdatedSkills) {
        console.log('  ' + r.name.padEnd(nw) + '  available: ' + chalk.yellow(r.version))
        for (const scope of ['user', 'project']) {
          const detail = scope === 'user' ? r.userDetail : r.projectDetail
          for (const t of targets) {
            if (detail[t].status === 'update') {
              console.log('    ' + chalk.dim(scope.padEnd(8) + t.padEnd(8)) + detail[t].version + ' → ' + chalk.yellow(r.version))
            }
          }
        }
      }
    }

    if (outdatedTools.length) {
      console.log('\n  ' + chalk.bold('TOOLS WITH UPDATES'))
      const nw = Math.max(...outdatedTools.map(r => r.name.length))
      for (const r of outdatedTools) {
        console.log('  ' + r.name.padEnd(nw) + '  ' + chalk.dim(r.version) + ' → ' + chalk.yellow(r.version))
      }
    }
    console.log('')
    process.exit(0)
  }

  // Full status table
  const allNames = [...skillRows.map(r => r.name), ...toolRows.map(r => r.name), ...hookItems.map(h => h.name)]
  const allVers  = [...skillRows, ...toolRows].map(r => r.version)
  const nw = Math.max(...allNames.map(n => n.length), 4)
  const vw = Math.max(...allVers.map(v => v.length), 7)
  const bw = Math.max(...skillRows.map(r => r.bundle.length), 6)
  const sep = chalk.dim('  ' + '─'.repeat(nw + vw + bw + 22))

  console.log('')
  console.log('  ' + chalk.bold('SKILLS') + chalk.dim(`  — ${skillRows.length} available`))
  console.log(sep)
  console.log('  ' + ''.padEnd(nw + vw + bw + 5) + chalk.dim('user    project'))
  for (const r of skillRows) {
    const u = icon(r.userStatus), p = icon(r.projectStatus)
    console.log('  ' + r.name.padEnd(nw) + '  ' + chalk.dim(r.version.padEnd(vw)) + '  ' + chalk.dim(r.bundle.padEnd(bw)) + '  ' + u + '       ' + p)
  }

  console.log('')
  console.log('  ' + chalk.bold('TOOLS') + chalk.dim(`  — ${toolRows.length} available`))
  console.log(sep)
  for (const r of toolRows) {
    console.log('  ' + r.name.padEnd(nw) + '  ' + chalk.dim(r.version.padEnd(vw)) + '  ' + icon(r.status))
  }

  // ── hooks ──
  if (hookItems.length > 0) {
    console.log('')
    console.log('  ' + chalk.bold('HOOKS') + chalk.dim(`  — ${hookItems.length} available`))
    console.log(sep)
    function hIcon(s) {
      if (s === 'installed') return chalk.green('✓')
      if (s === 'partial')   return chalk.yellow('~')
      return chalk.dim('—')
    }
    for (const h of hookItems) {
      const inst = checkHookInstalled(h.name)
      const ver = resolveHookDisplayVersion(inst, h.version)
      console.log('  ' + h.name.padEnd(nw) + '  ' + chalk.dim(ver.padEnd(vw)) + '  ' + hIcon(inst.user.status) + '       ' + hIcon(inst.project.status) + '  ' + chalk.dim(h.description))
    }
  }

  const installedSkills = skillRows.filter(r => r.userStatus !== 'none' || r.projectStatus !== 'none').length
  const installedTools  = toolRows.filter(r => r.status !== 'none').length
  const outdatedCount   = skillRows.filter(r => r.userStatus === 'update' || r.projectStatus === 'update').length
                        + toolRows.filter(r => r.status === 'update').length
  const outdatedNote    = outdatedCount ? '  ·  ' + chalk.yellow(outdatedCount + ' outdated') : ''
  console.log('')
  console.log(chalk.dim(`  ${installedSkills} of ${skillRows.length} skills installed  ·  ${installedTools} of ${toolRows.length} tools installed${outdatedNote}`))
  console.log('')
  process.exit(0)
}

// ── Info ──────────────────────────────────────────────────────────────────────
if (subcommand === 'info') {
  const name = args[1]
  if (!name) {
    console.error(chalk.red('  ✗ Usage: hskill info <skill-or-tool-name>'))
    process.exit(1)
  }

  const skillItems = getAllSkillItems()
  const toolItems  = getAllToolItems()
  const skill = skillItems.find(s => s.skillName === name)
  const tool  = toolItems.find(t => t.toolName === name)

  if (!skill && !tool) {
    console.error(chalk.red(`  ✗ Unknown: "${name}"`))
    process.exit(1)
  }

  const targets = ['claude', 'cursor', 'codex']

  function statusLabel(status) {
    if (status === 'up-to-date') return chalk.green('✓ up to date')
    if (status === 'update')     return chalk.yellow('↑ update available')
    return chalk.dim('— not installed')
  }

  if (jsonFlag) {
    if (skill) {
      const inst = checkInstalled(skill.skillName, skill.version ?? '—')
      console.log(JSON.stringify({
        name: skill.skillName, type: 'skill', version: skill.version ?? '—',
        user:    Object.fromEntries(targets.map(t => [t, inst.user[t]])),
        project: Object.fromEntries(targets.map(t => [t, inst.project[t]])),
      }, null, 2))
    } else {
      const inst = checkToolInstalled(tool.toolName, tool.srcPath)
      console.log(JSON.stringify({
        name: tool.toolName, type: 'tool', version: tool.version ?? '—',
        installed: inst,
      }, null, 2))
    }
    process.exit(0)
  }

  console.log('')
  if (skill) {
    const inst = checkInstalled(skill.skillName, skill.version ?? '—')
    console.log('  ' + chalk.bold(skill.skillName) + chalk.dim('  skill'))
    console.log('  ' + chalk.dim('available: ') + (skill.version ?? '—'))
    console.log('')
    for (const [scopeLabel, detail] of [['USER LEVEL', inst.user], ['PROJECT LEVEL', inst.project]]) {
      console.log('  ' + chalk.bold(scopeLabel))
      for (const t of targets) {
        const { version: v, status } = detail[t]
        console.log('  ' + t.padEnd(8) + chalk.dim(v.padEnd(10)) + statusLabel(status))
      }
      console.log('')
    }
  } else {
    const inst = checkToolInstalled(tool.toolName, tool.srcPath)
    console.log('  ' + chalk.bold(tool.toolName) + chalk.dim('  shell tool'))
    console.log('  ' + chalk.dim('available: ') + (tool.version ?? '—'))
    console.log('')
    console.log('  ' + chalk.bold('INSTALL STATUS'))
    console.log('  ' + '~/.local/bin'.padEnd(14) + chalk.dim(inst.version.padEnd(10)) + statusLabel(inst.status))
    console.log('')
  }
  process.exit(0)
}

// ── Uninstall ─────────────────────────────────────────────────────────────────
if (subcommand === 'uninstall') {
  const nameToRemove = args[1]
  if (!nameToRemove || nameToRemove.startsWith('--')) {
    console.error(chalk.red('  ✗ Usage: hskill uninstall <tool-or-skill-name> [--yes] [--scope user|project] [--target claude|...]'))
    process.exit(1)
  }

  const yesFlag    = args.includes('--yes')
  const scopeIdx2  = args.indexOf('--scope')
  const targetIdx2 = args.indexOf('--target')
  const scopeArg2  = scopeIdx2  !== -1 ? args[scopeIdx2  + 1] : 'user'
  const targetArg2 = targetIdx2 !== -1 ? args[targetIdx2 + 1] : undefined

  const toolItems2  = getAllToolItems()
  const skillItems2 = getAllSkillItems()
  const isTool  = toolItems2.some(t => t.toolName  === nameToRemove)
  const isSkill = skillItems2.some(s => s.skillName === nameToRemove)

  if (!isTool && !isSkill) {
    console.error(chalk.red(`  ✗ Unknown tool or skill: "${nameToRemove}"`))
    process.exit(1)
  }

  if (isTool) {
    const { removed, failed } = await uninstallTool(nameToRemove, { yes: yesFlag })
    if (removed.length > 0) console.error(chalk.green.bold(`✔ ${nameToRemove} uninstalled`))
    process.exit(failed.length ? 1 : 0)
  }

  // Skill uninstall
  const scope = scopeArg2
  const selectedTargets = targetArg2
    ? [targetArg2]
    : ['claude', 'cursor', 'codex', 'openclaw', 'hermes']
  const targets = resolveTargets(selectedTargets, scope)

  let anyRemoved = false
  let anyFailed  = false
  for (const { dir } of targets) {
    const { removed, failed } = await uninstallSkill(nameToRemove, dir)
    if (removed.length) anyRemoved = true
    if (failed.length)  anyFailed  = true
  }
  if (anyRemoved) console.error(chalk.green.bold(`✔ ${nameToRemove} uninstalled`))
  process.exit(anyFailed ? 1 : 0)
}

// ── Hooks ─────────────────────────────────────────────────────────────────────
if (subcommand === 'hooks') {
  const hooksSubcmd    = args[1]
  const hookArgs       = args.slice(2)
  const hookJsonFlag   = hooksSubcmd === '--json' || hookArgs.includes('--json')
  const hookNameIdx    = hookArgs.indexOf('--name')
  const hookScopeIdx   = hookArgs.indexOf('--scope')
  const hookProjectIdx = hookArgs.indexOf('--project')
  const hookTargetIdx  = hookArgs.indexOf('--target')
  const hookForce      = hookArgs.includes('--force')
  const hookNameArg    = hookNameIdx    !== -1 ? hookArgs[hookNameIdx    + 1] : undefined
  const hookScopeArg   = hookScopeIdx   !== -1 ? hookArgs[hookScopeIdx   + 1] : 'user'
  const hookProjectArg = hookProjectIdx !== -1 ? hookArgs[hookProjectIdx + 1] : process.cwd()
  const hookTargetArg  = hookTargetIdx  !== -1 ? hookArgs[hookTargetIdx  + 1] : 'claude'

  // Validate scope for install/uninstall commands
  if (!['user', 'project'].includes(hookScopeArg) && ['install', 'uninstall'].includes(hooksSubcmd)) {
    console.error(chalk.red(`  ✗ Invalid scope: "${hookScopeArg}". Use user or project.`))
    process.exit(1)
  }

  // ── hooks list ──────────────────────────────────────────────────────────────
  if (hooksSubcmd === 'list' || !hooksSubcmd || hooksSubcmd.startsWith('--')) {
    const hookItems = getAllHookItems()
    if (hookJsonFlag) {
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
      console.log(JSON.stringify({ hooks: out }, null, 2))
      process.exit(0)
    }
    function hookIcon(s) {
      if (s === 'installed') return chalk.green('✓')
      if (s === 'partial')   return chalk.yellow('~')
      return chalk.dim('—')
    }
    const nameWidth = Math.max(...hookItems.map(h => h.name.length), 4)
    const verWidth = 7
    console.log('')
    console.log('  ' + chalk.bold('NAME'.padEnd(nameWidth)) + '  ' + chalk.bold('VER'.padEnd(verWidth)) + '  U  P  CX  ' + chalk.bold('DESCRIPTION'))
    console.log('  ' + '─'.repeat(nameWidth) + '  ' + '─'.repeat(verWidth) + '  ─  ─  ──  ' + '─'.repeat(20))
    for (const h of hookItems) {
      const inst = checkHookInstalled(h.name)
      const ver = resolveHookDisplayVersion(inst, h.version)
      console.log(
        '  ' + h.name.padEnd(nameWidth) +
        '  ' + chalk.dim(ver.padEnd(verWidth)) +
        '  ' + hookIcon(inst.user.status) +
        '  ' + hookIcon(inst.project.status) +
        '  ' + hookIcon(inst.codex.user.status) +
        '   ' + h.description
      )
    }
    console.log('')
    console.log(chalk.dim(`  U=claude-user  P=claude-project  CX=codex-user  ${chalk.green('✓')}=installed  ${chalk.yellow('~')}=partial  ${chalk.dim('—')}=none`))
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
      toInstall = hookItems
    } else {
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

    const { installed, skipped, failed } = await installHooksForTarget(toInstall, hookTargetArg, hookScopeArg, hookProjectArg, hookForce)

    if (hookJsonFlag) {
      console.log(JSON.stringify({ installed, skipped, failed }, null, 2))
      process.exit(failed.length ? 1 : 0)
    } else {
      if (installed.length) console.error(chalk.green.bold(`✔ Hooks installed (${hookScopeArg}):`), installed.join(', '))
      for (const s of skipped) console.error(chalk.dim(`  · ${s.name} skipped (${s.reason})`))

      for (const f of failed)  console.error(chalk.red(`  ✗ ${f.name} failed: ${f.reason}${f.detail ? ` — ${f.detail}` : ''}`))
      process.exit(failed.length ? 1 : 0)
    }
  }

  // ── hooks uninstall ──────────────────────────────────────────────────────────
  if (hooksSubcmd === 'uninstall') {
    const nameToRemove = args[2]
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

// ── Install ───────────────────────────────────────────────────────────────────
// subcommand is 'install' or omitted (default behavior)
const installArgs = subcommand === 'install' ? args.slice(1) : args

const forceFlag = installArgs.includes('--force')
const bundleIdx = installArgs.indexOf('--bundle')
const targetIdx = installArgs.indexOf('--target')
const toolIdx   = installArgs.indexOf('--tool')
const skillIdx  = installArgs.indexOf('--skill')
const scopeIdx  = installArgs.indexOf('--scope')
const bundleArg = bundleIdx !== -1 ? installArgs[bundleIdx + 1] : undefined
const targetArg = targetIdx !== -1 ? installArgs[targetIdx + 1] : undefined
const toolArg   = toolIdx   !== -1 ? installArgs[toolIdx   + 1] : undefined
const skillArg  = skillIdx  !== -1 ? installArgs[skillIdx  + 1] : undefined
const scopeArg  = scopeIdx  !== -1 ? installArgs[scopeIdx  + 1] : undefined

const TOOL_BUNDLE_VALUES = new Set(TOOL_BUNDLE_CHOICES.map(c => c.value))

// ── Two-step target→scope selector ───────────────────────────────────────────
const ALL_SKILL_TARGETS = ['claude', 'cursor', 'codex', 'openclaw', 'hermes']

function selectTargetThenScope() {
  // Step 1: platform (target)
  const targetInput = [
    'claude    ~/.claude/skills/',
    'cursor    ~/.cursor/skills/',
    'codex     ~/.codex/skills/',
    'openclaw  ~/.openclaw/skills/',
    'hermes    ~/.hermes/skills/',
    'all       all 5 targets',
  ].join('\n')

  const targetResult = spawnSync('fzf', [
    '--multi',
    '--prompt=  › ',
    '--header=  安装到  ·  tab 多选  ·  enter 确认  ·  esc 取消',
    '--layout=reverse',
    '--border=rounded',
    '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
  ], {
    input: targetInput,
    encoding: 'utf8',
    stdio: ['pipe', 'pipe', 'inherit'],
  })

  if (!targetResult.stdout.trim()) return null

  const rawTargets = targetResult.stdout.trim().split('\n')
    .map(l => l.trim().split(/\s+/)[0])
  const expandedTargets = rawTargets.includes('all') ? ALL_SKILL_TARGETS : rawTargets

  // Step 2: scope (user/project) — skip if all selected targets are user-only
  const allUserOnly = expandedTargets.every(t => USER_ONLY_TARGETS.has(t))
  let scope = 'user'
  if (!allUserOnly) {
    const scopeResult = spawnSync('fzf', [
      '--prompt=  › ',
      '--header=  安装范围  ·  enter 确认  ·  esc 取消',
      '--layout=reverse',
      '--border=rounded',
      '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
    ], {
      input: 'user     — 所有项目共享  (~/.{target}/skills/)\nproject  — 仅当前项目  (.{target}/skills/)',
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'inherit'],
    })
    if (!scopeResult.stdout.trim()) return null
    scope = scopeResult.stdout.trim().startsWith('project') ? 'project' : 'user'
  }

  // Build final list — openclaw/hermes always resolve to user scope
  const seen = new Set()
  const result = []
  for (const t of expandedTargets) {
    const effectiveScope = USER_ONLY_TARGETS.has(t) ? 'user' : scope
    const key = `${effectiveScope}/${t}`
    if (!seen.has(key)) { seen.add(key); result.push({ scope: effectiveScope, target: t }) }
  }
  return result  // [{ scope, target }]
}

function requireFzf() {
  const probe = spawnSync('fzf', ['--version'], { encoding: 'utf8' })
  if (probe.error || probe.status !== 0) {
    console.error(chalk.red('  ✗ fzf is required but not installed.'))
    console.error('')
    console.error('  Install it with:')
    console.error(chalk.cyan('    brew install fzf') + chalk.dim('          # macOS'))
    console.error(chalk.cyan('    sudo apt install fzf') + chalk.dim('      # Debian/Ubuntu'))
    console.error(chalk.cyan('    sudo dnf install fzf') + chalk.dim('      # Fedora'))
    console.error('')
    process.exit(1)
  }
}

// 用 fzf 交互式选择 skill/tool，返回选中的 item 列表
function fzfSelect() {
  requireFzf()
  const skillItems  = getAllSkillItems()
  const toolItems   = getAllToolItems()
  const hookItems   = getAllHookItems()
  const previewPath = path.join(__dirname, 'preview.mjs')

  // 构建 fzf 输入：每行 "NAME\tVERSION\tBUNDLE\tKIND\tSRCPATH"
  const lines = [
    ...skillItems.map(s => {
      const bundle = s.srcPath.split('/').slice(-2, -1)[0]
      return `${s.skillName}\t${s.version ?? '—'}\t${bundle}\tskill\t${s.srcPath}`
    }),
    ...toolItems.map(t => `${t.toolName}\t${t.version ?? '—'}\tshell-tool\ttool\t${t.srcPath}`),
    ...hookItems.map(h => `${h.name}\t${h.version ?? '—'}\thook\thook\t${h.srcPath}`),
  ]

  const nameWidth    = Math.max(...lines.map(l => l.split('\t')[0].length))
  const versionWidth = Math.max(...lines.map(l => l.split('\t')[1].length))

  const G = '\x1b[32m', Y = '\x1b[33m', D = '\x1b[2m', R = '\x1b[0m'
  function colorIcon(status) {
    if (status === 'up-to-date') return G + '✓' + R
    if (status === 'update')     return Y + '↑' + R
    return D + '—' + R
  }

  // fzf 展示格式：NAME   VERSION   U:?  P:?  BUNDLE
  const displayLines = lines.map(l => {
    const [name, ver, bundle, kind, srcPath] = l.split('\t')
    let uIcon = D + '—' + R, pIcon = D + '—' + R
    if (kind === 'skill') {
      const installed = checkInstalled(name, ver)
      uIcon = colorIcon(scopeSummary(installed.user))
      pIcon = colorIcon(scopeSummary(installed.project))
    } else if (kind === 'tool') {
      uIcon = colorIcon(checkToolInstalled(name, srcPath).status)
    } else if (kind === 'hook') {
      const inst = checkHookInstalled(name)
      uIcon = colorIcon(inst.user.status === 'installed' ? 'up-to-date'
             : inst.user.status === 'partial'            ? 'update' : '')
      pIcon = colorIcon(inst.project.status === 'installed' ? 'up-to-date'
             : inst.project.status === 'partial'             ? 'update' : '')
    }
    return `${name.padEnd(nameWidth)}  ${ver.padEnd(versionWidth)}  U:${uIcon}  P:${pIcon}  ${bundle}`
  })

  // 把原始数据附在末尾（隐藏列，用于解析和 preview）
  const fzfInput = displayLines.map((d, i) => `${d}\t${lines[i]}`).join('\n')

  const header = `  hskill  ·  U=user P=project  ${G}✓${R}=ok ${Y}↑${R}=update ${D}—${R}=none  ·  tab 多选  ·  enter 确认`

  const result = spawnSync('fzf', [
    '--multi',
    '--ansi',
    '--delimiter=\t',
    '--with-nth=1',
    '--prompt=  › ',
    `--header=${header}`,
    '--layout=reverse',
    '--border=rounded',
    '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
    `--preview=node ${previewPath} {2} {3} {5} {6}`,
    '--preview-window=right:42%:wrap',
  ], {
    input: fzfInput,
    encoding: 'utf8',
    stdio: ['pipe', 'pipe', 'inherit'],
  })

  if (result.status !== 0 || !result.stdout.trim()) return []

  return result.stdout.trim().split('\n').map(line => {
    const parts = line.split('\t')
    const [, name, ver, bundle, kind, srcPath] = parts
    if (kind === 'skill') return { kind: 'skill', skillName: name, srcPath, version: ver }
    if (kind === 'hook') return { kind: 'hook', name, srcPath, version: ver }
    return { kind: 'tool', toolName: name, srcPath, version: ver }
  })
}

// ── Print install summary (shared between interactive loop and non-interactive) ──
function printSummary(skillSummary, toolSummary, hookSummary = null) {
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

try {
  if (toolArg && skillArg) {
    const msg = '--tool and --skill cannot be combined; use --bundle to install both'
    if (jsonFlag) process.stderr.write(JSON.stringify({ error: true, message: msg }) + '\n')
    else console.error(chalk.red('  ✗ ' + msg))
    process.exit(1)
  }

  const isInteractive = !toolArg && !skillArg && !bundleArg

  // ── Interactive mode: loop back to skill selector after each install ────────
  if (isInteractive) {
    if (!process.stdout.isTTY && !process.env.HSKILL_TEST_INTERACTIVE) {
      console.error(chalk.red('  ✗ Interactive mode requires a TTY. Use --bundle, --skill, or --tool flags for non-interactive install.'))
      console.error(chalk.dim('  Example: hskill install --bundle dev --target claude'))
      process.exit(1)
    }

    while (true) {
      // ── Test shortcut: HSKILL_TEST_ACTION bypasses fzf entirely ───────────
      let selected
      if (process.env.HSKILL_TEST_ACTION && process.env.HSKILL_TEST_TOOL) {
        const testTool = getAllToolItems().find(t => t.toolName === process.env.HSKILL_TEST_TOOL)
        selected = testTool ? [{ kind: 'tool', ...testTool }] : []
      } else {
        selected = fzfSelect()
      }

      if (!selected.length) {
        console.log(chalk.dim('  · Nothing selected, exiting'))
        break
      }

      const toolItems = selected.filter(s => s.kind === 'tool')
      const hookItems = selected.filter(s => s.kind === 'hook')
      const seen = new Set()
      const skillItems = selected.filter(s => s.kind === 'skill').filter(s => {
        if (seen.has(s.skillName)) return false
        seen.add(s.skillName); return true
      })

      if (!skillItems.length && !toolItems.length && !hookItems.length) continue

      // ── Action selection (install / uninstall) ─────────────────────────────
      // Skip the prompt when nothing is installed yet — default to install.
      let action = 'install'
      if (process.env.HSKILL_TEST_ACTION) {
        action = process.env.HSKILL_TEST_ACTION
      } else {
        const anyInstalled =
          skillItems.some(s => {
            const inst = checkInstalled(s.skillName, s.version ?? '—')
            return scopeSummary(inst.user) !== 'none' || scopeSummary(inst.project) !== 'none'
          }) ||
          toolItems.some(t => checkToolInstalled(t.toolName, t.srcPath).status !== 'none') ||
          hookItems.some(h => {
            const inst = checkHookInstalled(h.name)
            return inst.user.status !== 'none' || inst.project.status !== 'none'
          })

        if (anyInstalled) {
          const actionResult = spawnSync('fzf', [
            '--prompt=  › ',
            '--header=  Action  ·  enter 确认  ·  esc 取消',
            '--layout=reverse',
            '--border=rounded',
            '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
          ], {
            input: `install    安装 / 重新安装\nuninstall  卸载并清理文件`,
            encoding: 'utf8',
            stdio: ['pipe', 'pipe', 'inherit'],
          })
          if (!actionResult.stdout.trim()) {
            console.log(chalk.dim('  · Cancelled'))
            break
          }
          action = actionResult.stdout.trim().startsWith('uninstall') ? 'uninstall' : 'install'
        }
      }

      if (action === 'install') {
        let skillSummary = null
        if (skillItems.length > 0) {
          // Combined scope+target selection (one step instead of two)
          const selectedST = selectTargetThenScope()
          if (!selectedST) {
            console.log(chalk.dim('  · Cancelled'))
            break
          }

          // Group by scope so we make one installSkills call per scope
          const byScope = {}
          for (const { scope, target } of selectedST) {
            if (!byScope[scope]) byScope[scope] = []
            byScope[scope].push(target)
          }

          console.log('')
          for (const [scope, selectedTargets] of Object.entries(byScope)) {
            const targets = resolveTargets(selectedTargets, scope)
            const result = await installSkills(skillItems, targets, forceFlag)
            skillSummary = skillSummary ? { ...skillSummary, ...result } : result
          }
          console.log('')
        }

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

        // ── Hook install ────────────────────────────────────────────────────────
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

        printSummary(skillSummary, toolSummary, hookSummary)
      } else {
        // ── Uninstall ───────────────────────────────────────────────────────
        const yesFlag2 = !!process.env.HSKILL_TEST_YES
        console.log('')

        // Re-filter after possible HSKILL_TEST_TOOL injection
        const uToolItems  = selected.filter(s => s.kind === 'tool')
        const uSkillItems = selected.filter(s => s.kind === 'skill')
        const uHookItems  = selected.filter(s => s.kind === 'hook')

        for (const item of uToolItems) {
          const { removed, failed } = await uninstallTool(item.toolName, { yes: yesFlag2 })
          if (removed.length) console.error(chalk.green.bold(`✔ ${item.toolName} uninstalled`))
          if (failed.length)  console.error(chalk.red(`  ✗ ${item.toolName}: some files could not be removed`))
        }

        for (const item of uSkillItems) {
          // Step 1: target (platform)
          const targetChoices2 = buildTargetChoices('user')
          const targetRes = spawnSync('fzf', [
            '--multi', '--prompt=  › ',
            '--header=  从哪里卸载  ·  tab 多选  ·  enter 确认  ·  esc 取消',
            '--layout=reverse', '--border=rounded',
            '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
          ], {
            input: targetChoices2.map(c => c.name).join('\n') + '\nall      — all targets',
            encoding: 'utf8', stdio: ['pipe', 'pipe', 'inherit'],
          })
          if (!targetRes.stdout.trim()) { console.log(chalk.dim('  · Cancelled')); break }
          const selTargets2 = targetRes.stdout.trim().split('\n').map(l => l.trim().split(/\s+/)[0])

          // Step 2: scope (user/project)
          const scopeRes = spawnSync('fzf', [
            '--prompt=  › ',
            '--header=  卸载范围  ·  enter 确认  ·  esc 取消',
            '--layout=reverse', '--border=rounded',
            '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
          ], {
            input: 'user     — 所有项目  (~/.{target}/skills/)\nproject  — 仅当前项目  (.{target}/skills/)',
            encoding: 'utf8', stdio: ['pipe', 'pipe', 'inherit'],
          })
          if (!scopeRes.stdout.trim()) { console.log(chalk.dim('  · Cancelled')); break }
          const scope2 = scopeRes.stdout.trim().startsWith('project') ? 'project' : 'user'

          const targets2 = resolveTargets(selTargets2, scope2)
          for (const { dir } of targets2) {
            await uninstallSkill(item.skillName, dir)
          }
        }

        for (const item of uHookItems) {
          const hookScopeRes = spawnSync('fzf', [
            '--prompt=  › ',
            '--header=  Hook scope  ·  enter 确认',
            '--layout=reverse', '--border=rounded',
            '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
          ], {
            input: `user     — ~/.claude/hooks/\nproject  — .claude/hooks/`,
            encoding: 'utf8', stdio: ['pipe', 'pipe', 'inherit'],
          })
          if (!hookScopeRes.stdout.trim()) { console.log(chalk.dim('  · Cancelled')); break }
          const hookScope2 = hookScopeRes.stdout.trim().startsWith('project') ? 'project' : 'user'
          await uninstallHook(item.name, hookScope2, process.cwd())
        }

        console.log('')
      }

      // In test mode with HSKILL_TEST_ACTION, run once and exit
      if (process.env.HSKILL_TEST_ACTION) break

      // Loop back to skill selector automatically
    }

    process.exit(0)
  }

  // ── Non-interactive mode: resolve items from flags, install once ────────────
  let skillItems = []
  let toolItems  = []

  if (toolArg) {
    const names = toolArg.split(',').map(s => s.trim()).filter(Boolean)
    toolItems = resolveToolsByName(names).map(t => ({ kind: 'tool', ...t }))
  } else if (skillArg) {
    const names = skillArg.split(',').map(s => s.trim()).filter(Boolean)
    skillItems = resolveSkillsByName(names).map(s => ({ kind: 'skill', ...s }))
  } else if (bundleArg) {
    const bundles = bundleArg.split(',').map(s => s.trim()).filter(Boolean)
    const skillBundles = bundles.filter(b => !TOOL_BUNDLE_VALUES.has(b))
    const toolBundles  = bundles.filter(b =>  TOOL_BUNDLE_VALUES.has(b))
    if (skillBundles.length) skillItems = resolveSkills(skillBundles).map(s => ({ kind: 'skill', ...s }))
    if (toolBundles.length)  toolItems  = resolveTools(toolBundles).map(t => ({ kind: 'tool', ...t }))
  }

  if (!skillItems.length && !toolItems.length) {
    console.log(chalk.dim('  · Nothing selected, exiting'))
    process.exit(0)
  }

  // ── Install skills ──────────────────────────────────────────────────────────
  let skillSummary = null
  if (skillItems.length > 0) {
    // When --target is given, use it directly (with --scope or default 'user').
    // When only --skill is given and no --target, use the combined selector.
    if (targetArg) {
      const scope = scopeArg ?? 'user'
      const selectedTargets = targetArg === 'all' ? ['claude', 'cursor', 'codex', 'openclaw', 'hermes'] : [targetArg]
      const targets = resolveTargets(selectedTargets, scope)
      console.log('')
      skillSummary = await installSkills(skillItems, targets, forceFlag)
      console.log('')
    } else {
      if (!process.stdout.isTTY) {
        console.error(chalk.red('  ✗ Interactive target selection requires a TTY. Use --target claude|cursor|codex|openclaw|hermes|all.'))
        process.exit(1)
      }
      const selectedST = selectTargetThenScope()
      if (!selectedST) {
        console.log(chalk.dim('  · Cancelled'))
        process.exit(0)
      }
      const byScope = {}
      for (const { scope, target } of selectedST) {
        if (!byScope[scope]) byScope[scope] = []
        byScope[scope].push(target)
      }
      console.log('')
      for (const [scope, selectedTargets] of Object.entries(byScope)) {
        const targets = resolveTargets(selectedTargets, scope)
        const result = await installSkills(skillItems, targets, forceFlag)
        skillSummary = skillSummary ? { ...skillSummary, ...result } : result
      }
      console.log('')
    }
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
    printSummary(skillSummary, toolSummary)
  }
} catch (err) {
  if (jsonFlag) {
    process.stderr.write(JSON.stringify({ error: true, message: err.message }) + '\n')
  } else {
    console.error(chalk.red('  ✗ ' + err.message))
  }
  process.exit(1)
}
