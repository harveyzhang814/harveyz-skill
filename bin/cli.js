#!/usr/bin/env node
import { checkbox } from '@inquirer/prompts'
import chalk from 'chalk'
import {
  buildAllChoices, getAllSkillItems, getAllToolItems,
  resolveSkills, resolveSkillsByName, resolveTools, resolveToolsByName,
  TOOL_BUNDLE_CHOICES,
} from '../lib/bundles.js'
import { TARGET_CHOICES, resolveTargets, TARGETS } from '../lib/targets.js'
import { installSkills, installTools } from '../lib/installer.js'

const args = process.argv.slice(2)
const forceFlag = args.includes('--force')
const bundleIdx = args.indexOf('--bundle')
const targetIdx = args.indexOf('--target')
const toolIdx   = args.indexOf('--tool')
const skillIdx  = args.indexOf('--skill')
const bundleArg = bundleIdx !== -1 ? args[bundleIdx + 1] : undefined
const targetArg = targetIdx !== -1 ? args[targetIdx + 1] : undefined
const toolArg   = toolIdx   !== -1 ? args[toolIdx   + 1] : undefined
const skillArg  = skillIdx  !== -1 ? args[skillIdx  + 1] : undefined

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
    const selected = await checkbox({
      message: 'Select items to install (space to select, enter to confirm):',
      choices: buildInteractiveChoices(),
    })

    if (!selected.length) {
      console.log(chalk.dim('  · Nothing selected, exiting'))
      process.exit(0)
    }

    const hasAll = selected.includes('all')
    const items  = selected.filter(s => s !== 'all')

    const selectedSkills = hasAll ? getAllSkillItems() : items.filter(s => s.kind === 'skill')
    toolItems = items.filter(s => s.kind === 'tool')

    const seen = new Set()
    skillItems = selectedSkills.filter(s => {
      if (seen.has(s.skillName)) return false
      seen.add(s.skillName); return true
    })
  }

  if (!skillItems.length && !toolItems.length) {
    console.log(chalk.dim('  · Nothing selected, exiting'))
    process.exit(0)
  }

  // ── Install skills ───────────────────────────────────────────────────────────
  if (skillItems.length > 0) {
    let selectedTargets
    if (targetArg) {
      selectedTargets = targetArg === 'all' ? Object.keys(TARGETS) : [targetArg]
    } else {
      selectedTargets = await checkbox({
        message: 'Install to which tools (space to select, enter to confirm):',
        choices: [
          ...TARGET_CHOICES,
          { name: 'all      — all tools', value: 'all' },
        ],
      })
    }

    if (selectedTargets.length > 0) {
      const targets = resolveTargets(selectedTargets)
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

  // ── Install shell tools ──────────────────────────────────────────────────────
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
