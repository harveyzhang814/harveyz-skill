import { PHASE1_PLATFORMS, MODES } from './select.js'
import { PROFILES } from './profiles.js'
import { modelMismatchLines, unavailableFieldLines } from './attribution.js'

// 三态：pass/fail 是真跑了；declared-na 是声明排除；not-run 是本次没覆盖。
// not-run 永远不得折叠进 pass，也不得从矩阵里省略行列——
// 这是 QM residual 那条纪律的直接应用：没有 residual 的归因表一定在撒谎。
//
// pass/fail 判定还要防一种伪装：exitCode === 0 但 reply 缺失/unavailable，
// 说明这次运行虽然没崩，但我们其实没收集到任何可判读的结果——不能算 pass。
function cellStatus(cell, records) {
  if (cell.state === 'declared-na') return 'declared-na'
  if (cell.state === 'not-run') return 'not-run'
  const rec = records.find(r => r.skill === cell.skill && r.platform === cell.platform && r.mode === cell.mode)
  if (!rec) return 'not-run'
  if (rec.exitCode !== 0) return 'fail'
  if (rec.reply === null || rec.reply === undefined) return 'fail'
  return 'pass'
}

function cellLabel(cell, records) {
  const status = cellStatus(cell, records)
  if (status === 'declared-na') return 'n/a'
  if (status === 'not-run') return ''
  return status
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
    const cols = COMBOS.map(({ platform, mode }) => {
      const c = cells.find(x => x.skill === skill && x.platform === platform && x.mode === mode)
      return (c ? cellLabel(c, records) : '').padEnd(COL_WIDTH)
    })
    lines.push(skill.padEnd(width) + cols.join(''))
  }

  const counts = { pass: 0, fail: 0, 'declared-na': 0, 'not-run': 0 }
  for (const c of cells) counts[cellStatus(c, records)]++
  lines.push('')
  lines.push(`pass: ${counts.pass}  fail: ${counts.fail}  declared-na: ${counts['declared-na']}  not-run: ${counts['not-run']}`)

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
