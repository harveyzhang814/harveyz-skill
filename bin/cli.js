#!/usr/bin/env node
import { checkbox } from '@inquirer/prompts'
import chalk from 'chalk'
import { BUNDLE_CHOICES, resolveSkills } from '../lib/bundles.js'
import { TARGET_CHOICES, resolveTargets, TARGETS } from '../lib/targets.js'
import { installSkills } from '../lib/installer.js'

const args = process.argv.slice(2)
const forceFlag = args.includes('--force')
const bundleIdx = args.indexOf('--bundle')
const targetIdx = args.indexOf('--target')
const bundleArg = bundleIdx !== -1 ? args[bundleIdx + 1] : undefined
const targetArg = targetIdx !== -1 ? args[targetIdx + 1] : undefined

// list 子命令
if (args[0] === 'list') {
  const { createRequire } = await import('module')
  const { fileURLToPath } = await import('url')
  const path = await import('path')
  const require = createRequire(import.meta.url)
  const bundles = require('../bundles.json')
  for (const b of bundles) {
    console.log(chalk.bold(b.name) + ' — ' + b.description)
    for (const s of b.skills) console.log('  ' + s)
  }
  process.exit(0)
}

// 解析 bundle 选择
let selectedBundles
if (bundleArg) {
  selectedBundles = [bundleArg]
} else {
  selectedBundles = await checkbox({
    message: '选择要安装的 bundle（空格多选）:',
    choices: BUNDLE_CHOICES,
  })
}

if (!selectedBundles.length) {
  console.log(chalk.red('未选择任何 bundle，退出。'))
  process.exit(1)
}

// 解析 target 选择
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

if (!selectedTargets.length) {
  console.log(chalk.red('未选择任何目标工具，退出。'))
  process.exit(1)
}

const skills = resolveSkills(selectedBundles)
const targets = resolveTargets(selectedTargets)

console.log('')
const summary = await installSkills(skills, targets, forceFlag)

console.log('')
if (Object.keys(summary).length === 0) {
  console.log(chalk.yellow('  没有 skill 被安装。'))
} else {
  console.log(chalk.green('✔ 安装完成：'))
  for (const [target, names] of Object.entries(summary)) {
    console.log(`  ${chalk.bold(target)} ← ${names.join(', ')}`)
  }
}
