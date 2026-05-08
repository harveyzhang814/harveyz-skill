#!/usr/bin/env node
import { checkbox } from '@inquirer/prompts'
import chalk from 'chalk'
import { BUNDLE_CHOICES, resolveSkills, TOOL_BUNDLE_CHOICES, resolveTools } from '../lib/bundles.js'
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
    const byToolBundle = {}
    for (const t of tools) {
      if (!byToolBundle[t.bundle]) byToolBundle[t.bundle] = []
      byToolBundle[t.bundle].push(t.name)
    }
    for (const [name, names] of Object.entries(byToolBundle)) {
      console.log(chalk.bold(name) + ' — ' + (toolBundleMeta[name] ?? name))
      for (const n of names) console.log('  ' + n)
    }
  }
  process.exit(0)
}

// 统一选项：skills + tools 放在同一个列表
const ALL_CHOICES = [
  ...BUNDLE_CHOICES.filter(c => c.value !== 'all'),
  ...(TOOL_BUNDLE_CHOICES.length > 0
    ? [
        { type: 'separator', separator: '── shell tools ──' },
        ...TOOL_BUNDLE_CHOICES,
      ]
    : []),
  { name: `${'all'.padEnd(16)} — 全部 skill（不含 shell 工具）`, value: 'all' },
]

// 区分 tool bundles 与 skill bundles
const TOOL_BUNDLE_VALUES = new Set(TOOL_BUNDLE_CHOICES.map(c => c.value))

try {
  let selected
  if (bundleArg) {
    selected = bundleArg.split(',').map(s => s.trim()).filter(Boolean)
  } else {
    selected = await checkbox({
      message: '选择要安装的 bundle（空格多选）:',
      choices: ALL_CHOICES,
    })
  }

  if (!selected.length) {
    console.log(chalk.yellow('  未选择任何 bundle，退出。'))
    process.exit(0)
  }

  const skillBundles = selected.filter(b => !TOOL_BUNDLE_VALUES.has(b))
  const toolBundles  = selected.filter(b =>  TOOL_BUNDLE_VALUES.has(b))

  // ── Skills ──────────────────────────────────────────────────────────────
  if (skillBundles.length > 0) {
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
      const skills  = resolveSkills(skillBundles)
      const targets = resolveTargets(selectedTargets)
      console.log('')
      const summary = await installSkills(skills, targets, forceFlag)
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

  // ── Shell Tools ──────────────────────────────────────────────────────────
  if (toolBundles.length > 0) {
    const tools = resolveTools(toolBundles)
    console.log('')
    const installed = await installTools(tools, TARGETS.shell, forceFlag)
    console.log('')
    if (installed.length === 0) {
      console.log(chalk.yellow('  没有 shell 工具被安装。'))
    } else {
      console.log(chalk.green('✔ Shell 工具安装完成：'))
      for (const name of installed) {
        console.log(`  ${chalk.bold('~/.local/bin')} ← ${name}`)
      }
      console.log('')
      console.log(chalk.dim('  提示：确保 ~/.local/bin 已加入 PATH，然后可添加别名：alias p=p-launch'))
    }
  }
} catch (err) {
  console.error(chalk.red('Error: ' + err.message))
  process.exit(1)
}
