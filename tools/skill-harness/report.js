import { PHASE1_PLATFORMS } from './select.js'
import { PROFILES } from './profiles.js'

// 三态：pass/fail 是真跑了；declared-na 是声明排除；not-run 是本次没覆盖。
// not-run 永远不得折叠进 pass，也不得从矩阵里省略行列——
// 这是 QM residual 那条纪律的直接应用：没有 residual 的归因表一定在撒谎。
function cellLabel(cell, records) {
  if (cell.state === 'declared-na') return 'n/a'
  if (cell.state === 'not-run') return ''
  const rec = records.find(r => r.skill === cell.skill && r.platform === cell.platform && r.mode === cell.mode)
  if (!rec) return ''
  return rec.exitCode === 0 ? 'pass' : 'fail'
}

export function renderReport({ cells, records, model, provider }) {
  const skills = [...new Set(cells.map(c => c.skill))]
  const width = Math.max(24, ...skills.map(s => s.length)) + 2

  const lines = []
  lines.push(`model:    ${model}`)
  lines.push(`provider: ${provider}`)
  lines.push('')
  lines.push('skill'.padEnd(width) + PHASE1_PLATFORMS.map(p => p.padEnd(12)).join(''))

  for (const skill of skills) {
    const cols = PHASE1_PLATFORMS.map(platform => {
      const c = cells.find(x => x.skill === skill && x.platform === platform)
      return (c ? cellLabel(c, records) : '').padEnd(12)
    })
    lines.push(skill.padEnd(width) + cols.join(''))
  }

  const counts = { pass: 0, fail: 0, 'declared-na': 0, 'not-run': 0 }
  for (const c of cells) {
    if (c.state === 'declared-na') counts['declared-na']++
    else if (c.state === 'not-run') counts['not-run']++
    else {
      const rec = records.find(r => r.skill === c.skill && r.platform === c.platform && r.mode === c.mode)
      if (!rec) counts['not-run']++
      else if (rec.exitCode === 0) counts.pass++
      else counts.fail++
    }
  }
  lines.push('')
  lines.push(`pass: ${counts.pass}  fail: ${counts.fail}  declared-na: ${counts['declared-na']}  not-run: ${counts['not-run']}`)

  const mism = records.filter(r => r.modelMismatch)
  if (mism.length) {
    lines.push('')
    lines.push(`model mismatch (${mism.length}): ${mism.map(r => `${r.skill}@${r.platform}`).join(', ')}`)
  }

  const un = records.filter(r => r.unavailable?.length)
  if (un.length) {
    lines.push('')
    lines.push('unavailable fields:')
    for (const r of un) lines.push(`  ${r.skill}@${r.platform}/${r.mode}: ${r.unavailable.join(', ')}`)
  }

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
