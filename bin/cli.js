#!/usr/bin/env node
import { select } from '@inquirer/prompts'
import chalk from 'chalk'
import { execSync, spawnSync } from 'child_process'
import { createRequire } from 'module'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'
import {
  getAllSkillItems, getAllToolItems,
  checkInstalled, checkToolInstalled, scopeSummary,
  resolveSkills, resolveSkillsByName, resolveTools, resolveToolsByName,
  TOOL_BUNDLE_CHOICES,
} from '../lib/bundles.js'
import { buildTargetChoices, resolveTargets, TARGETS } from '../lib/targets.js'
import { installSkills, installTools } from '../lib/installer.js'

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
  const { bundleMeta, skills, tools = [] } = require('../skills-index.json')
  const byBundle = {}
  for (const s of skills) {
    if (!byBundle[s.bundle]) byBundle[s.bundle] = []
    byBundle[s.bundle].push(s.path)
  }
  if (jsonFlag) {
    const bundles = {}
    for (const [name, paths] of Object.entries(byBundle)) {
      bundles[name] = { description: bundleMeta[name] ?? name, skills: paths }
    }
    console.log(JSON.stringify({ bundles, tools: tools.map(t => t.name) }, null, 2))
    process.exit(0)
  }
  for (const [name, paths] of Object.entries(byBundle)) {
    console.log(chalk.bold(name) + ' — ' + (bundleMeta[name] ?? name))
    for (const p of paths) console.log('  ' + p)
  }
  if (tools.length > 0) {
    console.log('')
    console.log(chalk.bold('shell tools:'))
    for (const t of tools) console.log('  ' + t.name)
  }
  process.exit(0)
}

// ── Status / Outdated ─────────────────────────────────────────────────────────
if (subcommand === 'status' || subcommand === 'outdated') {
  const outdatedOnly = subcommand === 'outdated'
  const skillItems   = getAllSkillItems()
  const toolItems    = getAllToolItems()

  function icon(status) {
    if (status === 'up-to-date') return chalk.green('✓')
    if (status === 'update')     return chalk.yellow('↑')
    return chalk.dim('—')
  }

  const skillRows = skillItems.map(s => {
    const inst = checkInstalled(s.skillName, s.version ?? '—')
    return {
      name: s.skillName, version: s.version ?? '—',
      userStatus: scopeSummary(inst.user), projectStatus: scopeSummary(inst.project),
      userDetail: inst.user, projectDetail: inst.project,
    }
  })
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
    if (outdatedOnly) {
      console.log(JSON.stringify({
        skills: jsonSkills.filter(s => Object.values(s.user).some(v => v.status === 'update') || Object.values(s.project).some(v => v.status === 'update')),
        tools:  jsonTools.filter(t => t.status === 'update'),
      }, null, 2))
    } else {
      console.log(JSON.stringify({ skills: jsonSkills, tools: jsonTools }, null, 2))
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
  const allNames = [...skillRows, ...toolRows].map(r => r.name)
  const allVers  = [...skillRows, ...toolRows].map(r => r.version)
  const nw = Math.max(...allNames.map(n => n.length), 4)
  const vw = Math.max(...allVers.map(v => v.length), 7)
  const sep = chalk.dim('  ' + '─'.repeat(nw + vw + 20))

  console.log('')
  console.log('  ' + chalk.bold('SKILLS') + chalk.dim(`  — ${skillRows.length} available`))
  console.log(sep)
  console.log('  ' + ''.padEnd(nw + vw + 3) + chalk.dim('user    project'))
  for (const r of skillRows) {
    const u = icon(r.userStatus), p = icon(r.projectStatus)
    console.log('  ' + r.name.padEnd(nw) + '  ' + chalk.dim(r.version.padEnd(vw)) + '  ' + u + '       ' + p)
  }

  console.log('')
  console.log('  ' + chalk.bold('TOOLS') + chalk.dim(`  — ${toolRows.length} available`))
  console.log(sep)
  for (const r of toolRows) {
    console.log('  ' + r.name.padEnd(nw) + '  ' + chalk.dim(r.version.padEnd(vw)) + '  ' + icon(r.status))
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
  const previewPath = path.join(__dirname, 'preview.mjs')

  // 构建 fzf 输入：每行 "NAME\tVERSION\tBUNDLE\tKIND\tSRCPATH"
  const lines = [
    ...skillItems.map(s => {
      const bundle = s.srcPath.split('/').slice(-2, -1)[0]
      return `${s.skillName}\t${s.version ?? '—'}\t${bundle}\tskill\t${s.srcPath}`
    }),
    ...toolItems.map(t => `${t.toolName}\t${t.version ?? '—'}\tshell-tool\ttool\t${t.srcPath}`),
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
    return { kind: 'tool', toolName: name, srcPath, version: ver }
  })
}

try {
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
  } else {
    if (!process.stdout.isTTY) {
      console.error(chalk.red('  ✗ Interactive mode requires a TTY. Use --bundle, --skill, or --tool flags for non-interactive install.'))
      console.error(chalk.dim('  Example: hskill install --bundle dev --target claude'))
      process.exit(1)
    }
    const selected = fzfSelect()

    if (!selected.length) {
      console.log(chalk.dim('  · Nothing selected, exiting'))
      process.exit(0)
    }

    toolItems = selected.filter(s => s.kind === 'tool')

    const seen = new Set()
    skillItems = selected.filter(s => s.kind === 'skill').filter(s => {
      if (seen.has(s.skillName)) return false
      seen.add(s.skillName); return true
    })
  }

  if (!skillItems.length && !toolItems.length) {
    console.log(chalk.dim('  · Nothing selected, exiting'))
    process.exit(0)
  }

  // ── Install skills ──────────────────────────────────────────────────────────
  if (skillItems.length > 0) {
    // Resolve scope
    let scope = scopeArg ?? 'user'
    if (!scopeArg && !targetArg) {
      if (!process.stdout.isTTY) {
        console.error(chalk.red('  ✗ Interactive scope selection requires a TTY. Use --scope user|project.'))
        process.exit(1)
      }
      const scopeResult = spawnSync('fzf', [
        '--prompt=  › ',
        '--header=  Scope  ·  enter 确认  ·  esc 取消',
        '--layout=reverse',
        '--border=rounded',
        '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
      ], {
        input: `user     — ~/.claude/skills/  (所有项目共享)\nproject  — .claude/skills/    (仅当前项目)`,
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'inherit'],
      })
      if (!scopeResult.stdout.trim()) {
        console.log(chalk.dim('  · Cancelled'))
        process.exit(0)
      }
      scope = scopeResult.stdout.trim().startsWith('project') ? 'project' : 'user'
    }

    // Resolve target
    let selectedTargets
    if (targetArg) {
      selectedTargets = targetArg === 'all' ? ['claude', 'cursor', 'codex', 'openclaw', 'hermes'] : [targetArg]
    } else {
      if (!process.stdout.isTTY) {
        console.error(chalk.red('  ✗ Interactive target selection requires a TTY. Use --target claude|cursor|codex|openclaw|hermes|all.'))
        process.exit(1)
      }
      const targetChoices = buildTargetChoices(scope)
      const targetInput = targetChoices.map(c => c.name).join('\n') + '\nall      — all tools'
      const targetResult = spawnSync('fzf', [
        '--multi',
        '--prompt=  › ',
        '--header=  Install to  ·  tab 多选  ·  enter 确认  ·  esc 取消',
        '--layout=reverse',
        '--border=rounded',
        '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
      ], {
        input: targetInput,
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'inherit'],
      })
      if (!targetResult.stdout.trim()) {
        console.log(chalk.dim('  · Cancelled'))
        process.exit(0)
      }
      selectedTargets = targetResult.stdout.trim().split('\n')
        .map(l => l.trim().split(/\s+/)[0])
    }

    if (selectedTargets.length > 0) {
      const targets = resolveTargets(selectedTargets, scope)
      console.log('')
      const summary = await installSkills(skillItems, targets, forceFlag)
      console.log('')
      if (jsonFlag) {
        console.log(JSON.stringify(summary, null, 2))
      } else {
        const anyInstalled = Object.values(summary).some(r => r.installed.length > 0)
        if (!anyInstalled) {
          console.log(chalk.dim('  · No skills installed'))
        } else {
          console.log(chalk.green.bold('✔ Skills installed:'))
          for (const [target, { installed }] of Object.entries(summary)) {
            if (installed.length > 0)
              console.log(`  ${chalk.bold(target)} ← ${installed.join(', ')}`)
          }
        }
        for (const [target, { skipped, failed }] of Object.entries(summary)) {
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
    }
  }

  // ── Install shell tools ─────────────────────────────────────────────────────
  if (toolItems.length > 0) {
    console.log('')
    const toolResult = await installTools(
      toolItems.map(t => ({ toolName: t.toolName, srcPath: t.srcPath })),
      TARGETS.shell,
      forceFlag,
    )
    console.log('')
    if (jsonFlag) {
      console.log(JSON.stringify(toolResult, null, 2))
    } else {
      if (toolResult.installed.length === 0 && !toolResult.skipped.length && !toolResult.failed.length) {
        console.log(chalk.dim('  · No shell tools installed'))
      } else {
        if (toolResult.installed.length > 0) {
          console.log(chalk.green.bold('✔ Shell tools installed:'))
          for (const name of toolResult.installed) {
            console.log(`  ${chalk.bold('~/.local/bin')} ← ${name}`)
          }
          console.log('')
          console.log(chalk.yellow.bold('  ⚡ Reload your shell to apply changes:'))
          console.log('')
          console.log(`     ${chalk.bold.cyan('source ~/.zshrc')}`)
          console.log('')
        }
        for (const s of toolResult.skipped) {
          console.log(chalk.dim(`  · ${s.name} skipped (${s.reason === 'already_exists' ? 'already exists — use --force to overwrite' : s.reason})`))
        }
        for (const f of toolResult.failed) {
          console.log(chalk.red(`  ✗ ${f.name} failed: ${f.reason}${f.detail ? ` — ${f.detail}` : ''}`))
        }
      }
    }
  }
} catch (err) {
  console.error(chalk.red('  ✗ ' + err.message))
  process.exit(1)
}
