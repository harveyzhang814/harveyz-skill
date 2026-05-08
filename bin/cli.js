#!/usr/bin/env node
import { checkbox } from '@inquirer/prompts'
import chalk from 'chalk'
import {
  buildAllChoices, getAllSkillItems, getAllToolItems,
  resolveSkills, resolveTools,
  TOOL_BUNDLE_CHOICES,
} from '../lib/bundles.js'
import { TARGET_CHOICES, resolveTargets, TARGETS } from '../lib/targets.js'
import { installSkills, installTools } from '../lib/installer.js'

const args = process.argv.slice(2)
const forceFlag = args.includes('--force')
const bundleIdx = args.indexOf('--bundle')
const targetIdx = args.indexOf('--target')
const bundleArg = bundleIdx !== -1 ? args[bundleIdx + 1] : undefined
const targetArg = targetIdx !== -1 ? args[targetIdx + 1] : undefined

// list 子命令
if (args[0] === 'list') {
  const { createRequire } = await import('module')
  const require = createRequire(import.meta.url)
  const { bundleMeta, skills, toolBundleMeta = {}, tools = [] } = require('../skills-index.json')
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

const TOOL_BUNDLE_VALUES = new Set(TOOL_BUNDLE_CHOICES.map(c => c.value))

// 交互式选择列表：单个 skill + shell tools + all
function buildInteractiveChoices() {
  const toolItems = getAllToolItems()
  return [
    ...buildAllChoices(),
    ...(toolItems.length > 0
      ? [
          { type: 'separator', separator: '── shell tools ──' },
          ...toolItems.map(t => ({ name: t.toolName, value: t })),
        ]
      : []),
    { type: 'separator', separator: '────────────────' },
    { name: 'all skills', value: 'all' },
  ]
}

try {
  let skillItems = []  // [{ kind:'skill', skillName, srcPath }]
  let toolItems  = []  // [{ kind:'tool',  toolName,  srcPath }]

  if (bundleArg) {
    // --bundle 保持 bundle 粒度，自动路由 skill vs tool
    const bundles = bundleArg.split(',').map(s => s.trim()).filter(Boolean)
    const skillBundles = bundles.filter(b => !TOOL_BUNDLE_VALUES.has(b))
    const toolBundles  = bundles.filter(b =>  TOOL_BUNDLE_VALUES.has(b))
    if (skillBundles.length) skillItems = resolveSkills(skillBundles).map(s => ({ kind: 'skill', ...s }))
    if (toolBundles.length)  toolItems  = resolveTools(toolBundles).map(t => ({ kind: 'tool', ...t }))
  } else {
    const selected = await checkbox({
      message: '选择要安装的内容（空格多选）:',
      choices: buildInteractiveChoices(),
    })

    if (!selected.length) {
      console.log(chalk.yellow('  未选择任何内容，退出。'))
      process.exit(0)
    }

    const hasAll = selected.includes('all')
    const items  = selected.filter(s => s !== 'all')

    // 展开 all → 全部 skill（不含 tools）
    const selectedSkills = hasAll ? getAllSkillItems() : items.filter(s => s.kind === 'skill')
    toolItems = items.filter(s => s.kind === 'tool')

    // 去重
    const seen = new Set()
    skillItems = selectedSkills.filter(s => {
      if (seen.has(s.skillName)) return false
      seen.add(s.skillName); return true
    })
  }

  if (!skillItems.length && !toolItems.length) {
    console.log(chalk.yellow('  未选择任何内容，退出。'))
    process.exit(0)
  }

  // ── 安装 skills ─────────────────────────────────────────────────────────────
  if (skillItems.length > 0) {
    let selectedTargets
    if (targetArg) {
      selectedTargets = targetArg === 'all' ? Object.keys(TARGETS) : [targetArg]
    } else {
      selectedTargets = await checkbox({
        message: '安装到哪些工具（空格多选）:',
        choices: [
          ...TARGET_CHOICES,
          { name: 'all      — 全部工具', value: 'all' },
        ],
      })
    }

    if (selectedTargets.length > 0) {
      const targets = resolveTargets(selectedTargets)
      console.log('')
      const summary = await installSkills(skillItems, targets, forceFlag)
      console.log('')
      if (Object.keys(summary).length === 0) {
        console.log(chalk.yellow('  没有 skill 被安装。'))
      } else {
        console.log(chalk.green('✔ Skills 安装完成：'))
        for (const [target, names] of Object.entries(summary)) {
          console.log(`  ${chalk.bold(target)} ← ${names.join(', ')}`)
        }
      }
    }
  }

  // ── 安装 shell tools ────────────────────────────────────────────────────────
  if (toolItems.length > 0) {
    console.log('')
    const installed = await installTools(
      toolItems.map(t => ({ toolName: t.toolName, srcPath: t.srcPath })),
      TARGETS.shell,
      forceFlag,
    )
    console.log('')
    if (installed.length === 0) {
      console.log(chalk.yellow('  没有 shell 工具被安装。'))
    } else {
      console.log(chalk.green('✔ Shell 工具安装完成：'))
      for (const name of installed) {
        console.log(`  ${chalk.bold('~/.local/bin')} ← ${name}`)
      }
      console.log('')
      console.log(chalk.bold.yellow('  ⚡ 运行以下命令使配置立即生效：'))
      console.log('')
      console.log(`     ${chalk.bold.cyan('source ~/.zshrc')}`)
      console.log('')
    }
  }
} catch (err) {
  console.error(chalk.red('Error: ' + err.message))
  process.exit(1)
}
