import { PHASE1_PLATFORMS, MODES } from './select.js'
import { PROFILES } from './profiles.js'
import { modelMismatchLines, unavailableFieldLines } from './attribution.js'
import { upstreamStatus } from './quality-report.js'

// 一个 (skill, platform, mode) 组合下可能有多个 cell（--repeat 展开、eval 轴展开），
// 这一行没有 repeat/eval 维度可画，只能收敛成一个结果——复用 quality-report.js
// 已经验证过的三态收敛逻辑（pass/fail/partial），不要在这里另起一套只看 cells.find
// 抓到的那一个 cell 的逻辑，那套逻辑在 --repeat 或多 eval 场景下和 counts 对不上。
function comboStatus(skill, platform, mode, cells, records) {
  const matches = cells.filter(c => c.skill === skill && c.platform === platform && c.mode === mode)
  if (!matches.length || matches[0].state === 'not-run') return 'not-run'
  if (matches[0].state === 'declared-na') return 'declared-na'
  return upstreamStatus(skill, platform, mode, records)
}

function comboLabel(status) {
  if (status === 'declared-na') return 'n/a'
  if (status === 'not-run') return ''
  return status // pass / fail / partial
}

// 每个 skill × platform 有两种 mode（native/inject），矩阵必须把两者都画出来——
// 否则 native 和 inject 的结果会被 cells.find 的"取第一个"悄悄合并成一格。
const COL_WIDTH = 16
const COMBOS = PHASE1_PLATFORMS.flatMap(platform => MODES.map(mode => ({ platform, mode })))

export function renderReport({ cells, records, model, provider }) {
  const skills = [...new Set(cells.map(c => c.skill))]
  const width = Math.max(24, ...skills.map(s => s.length)) + 2

  const lines = []
  lines.push(`model:    ${model}`)
  lines.push(`provider: ${provider}`)
  lines.push('')
  lines.push('skill'.padEnd(width) + COMBOS.map(c => `${c.platform}/${c.mode}`.padEnd(COL_WIDTH)).join(''))

  for (const skill of skills) {
    const cols = COMBOS.map(({ platform, mode }) => comboLabel(comboStatus(skill, platform, mode, cells, records)).padEnd(COL_WIDTH))
    lines.push(skill.padEnd(width) + cols.join(''))
  }

  const counts = { pass: 0, fail: 0, partial: 0, 'declared-na': 0, 'not-run': 0 }
  for (const skill of skills) {
    for (const { platform, mode } of COMBOS) {
      counts[comboStatus(skill, platform, mode, cells, records)]++
    }
  }
  lines.push('')
  lines.push(`pass: ${counts.pass}  fail: ${counts.fail}  partial: ${counts.partial}  declared-na: ${counts['declared-na']}  not-run: ${counts['not-run']}`)

  lines.push(...modelMismatchLines(records))
  lines.push(...unavailableFieldLines(records))

  const na = cells.filter(c => c.state === 'declared-na')
  if (na.length) {
    lines.push('')
    lines.push('declared n/a:')
    const seen = new Set()
    for (const c of na) {
      const key = `${c.skill}@${c.platform}`
      if (seen.has(key)) continue
      seen.add(key)
      lines.push(`  ${key}: ${c.reason}`)
    }
  }

  // capabilities 与 profile 必须有生产消费者，否则会腐烂成谎言（spec 风险 1）：
  // 表靠一条测试守着、而那条测试断言的正是声明本身，就是自己证明自己。
  // 让表错了体现在给人看的输出里，才有代价。
  const floors = PROFILES.map(p => `${p.id}=${p.builtinSkillFloor}`).join(' ')
  lines.push('')
  lines.push(`builtinSkillFloor: ${floors} — 触发失败先归因到这一格，各平台候选数不同`)

  lines.push('')
  lines.push('platform notes:')
  const ALL_CAPS = ['tool-trace', 'usage', 'cost-cap', 'tool-allowlist', 'structured-output', 'system-prompt-append']
  for (const p of PROFILES) {
    const missing = ALL_CAPS.filter(c => !p.capabilities.has(c))
    const chan = p.processChannel === 'collect' ? '过程数据走 collect 通道，导出失败则 toolCalls 缺失' : '过程数据在 stdout 内联'
    lines.push(`  ${p.id}: ${chan}${missing.length ? `；缺能力 ${missing.join(', ')}` : ''}`)
  }

  return lines.join('\n')
}
