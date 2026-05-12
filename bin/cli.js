#!/usr/bin/env node
import { select } from '@inquirer/prompts'
import chalk from 'chalk'
import { execSync, spawnSync } from 'child_process'
import { createRequire } from 'module'
import {
  getAllSkillItems, getAllToolItems,
  resolveSkills, resolveSkillsByName, resolveTools, resolveToolsByName,
  TOOL_BUNDLE_CHOICES,
} from '../lib/bundles.js'
import { buildTargetChoices, resolveTargets, TARGETS } from '../lib/targets.js'
import { installSkills, installTools } from '../lib/installer.js'

const require = createRequire(import.meta.url)
const { version } = require('../package.json')

const args = process.argv.slice(2)
const subcommand = args[0]

// ── Help ─────────────────────────────────────────────────────────────────────
function printHelp() {
  console.log(`
  ${chalk.bold('hskill')} — skill manager for Claude Code, Cursor, and Codex  v${version}

  ${chalk.cyan('Usage:')}
    hskill                         interactive install
    hskill install                 interactive install (explicit)
    hskill install --bundle <b>    install a skill bundle
    hskill install --skill <s>     install specific skill(s)
    hskill install --tool <t>      install shell tool(s)
    hskill install --target <t>    set target (claude/cursor/codex/all)
    hskill install --scope <s>     set scope: user (default) or project
    hskill install --force         overwrite existing installs
    hskill list                    list available skills and bundles
    hskill update                  update hskill to the latest version
    hskill --version               show version
    hskill --help                  show this help

  ${chalk.cyan('Examples:')}
    hskill install --bundle dev --target claude
    hskill install --skill git-workflow-init --target claude --scope project
    hskill install --tool p-launch
    hskill update
`)
}

if (args[0] === '--help' || args[0] === '-h') {
  printHelp()
  process.exit(0)
}

if (args[0] === '--version' || args[0] === '-v') {
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

// 用 fzf 交互式选择 skill/tool，返回选中的 item 列表
function fzfSelect() {
  const skillItems = getAllSkillItems()
  const toolItems  = getAllToolItems()

  // 构建 fzf 输入：每行 "NAME\tVERSION\tBUNDLE\tKIND\tSRCPATH"
  // bundle 从 srcPath 推断（取倒数第二段目录名）
  const lines = [
    ...skillItems.map(s => {
      const bundle = s.srcPath.split('/').slice(-2, -1)[0]
      return `${s.skillName}\t${s.version ?? '—'}\t${bundle}\tskill\t${s.srcPath}`
    }),
    ...toolItems.map(t => {
      return `${t.toolName}\t—\tshell-tool\ttool\t${t.srcPath}`
    }),
  ]

  const nameWidth    = Math.max(...lines.map(l => l.split('\t')[0].length))
  const versionWidth = Math.max(...lines.map(l => l.split('\t')[1].length))

  // fzf 展示格式：NAME   VERSION   BUNDLE
  const displayLines = lines.map(l => {
    const [name, ver, bundle] = l.split('\t')
    return `${name.padEnd(nameWidth)}  ${ver.padEnd(versionWidth)}  ${bundle}`
  })

  // 把原始数据附在末尾（隐藏列，用于解析）
  const fzfInput = displayLines.map((d, i) => `${d}\t${lines[i]}`).join('\n')

  const result = spawnSync('fzf', [
    '--multi',
    '--ansi',
    '--delimiter=\t',
    '--with-nth=1',           // 只显示格式化的第一列
    '--prompt=  › ',
    '--header=  hskill  ·  tab 多选  ·  enter 确认  ·  esc 取消',
    '--height=50%',
    '--layout=reverse',
    '--border=rounded',
    '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
  ], {
    input: fzfInput,
    encoding: 'utf8',
    stdio: ['pipe', 'pipe', 'inherit'],
  })

  if (result.status !== 0 || !result.stdout.trim()) return []

  return result.stdout.trim().split('\n').map(line => {
    const parts = line.split('\t')
    // 原始数据从第二列开始
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
      const scopeResult = spawnSync('fzf', [
        '--prompt=  › ',
        '--header=  Scope  ·  enter 确认  ·  esc 取消',
        '--height=20%',
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
      selectedTargets = targetArg === 'all' ? ['claude', 'cursor', 'codex'] : [targetArg]
    } else {
      const targetChoices = buildTargetChoices(scope)
      const targetInput = targetChoices.map(c => c.name).join('\n') + '\nall      — all tools'
      const targetResult = spawnSync('fzf', [
        '--multi',
        '--prompt=  › ',
        '--header=  Install to  ·  tab 多选  ·  enter 确认  ·  esc 取消',
        '--height=30%',
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
      if (Object.keys(summary).length === 0) {
        console.log(chalk.dim('  · No skills installed'))
      } else {
        console.log(chalk.green.bold('✔ Skills installed:'))
        for (const [target, names] of Object.entries(summary)) {
          console.log(`  ${chalk.bold(target)} ← ${names.join(', ')}`)
        }
      }
    }
  }

  // ── Install shell tools ─────────────────────────────────────────────────────
  if (toolItems.length > 0) {
    console.log('')
    const installed = await installTools(
      toolItems.map(t => ({ toolName: t.toolName, srcPath: t.srcPath })),
      TARGETS.shell,
      forceFlag,
    )
    console.log('')
    if (installed.length === 0) {
      console.log(chalk.dim('  · No shell tools installed'))
    } else {
      console.log(chalk.green.bold('✔ Shell tools installed:'))
      for (const name of installed) {
        console.log(`  ${chalk.bold('~/.local/bin')} ← ${name}`)
      }
      console.log('')
      console.log(chalk.yellow.bold('  ⚡ Reload your shell to apply changes:'))
      console.log('')
      console.log(`     ${chalk.bold.cyan('source ~/.zshrc')}`)
      console.log('')
    }
  }
} catch (err) {
  console.error(chalk.red('  ✗ ' + err.message))
  process.exit(1)
}
