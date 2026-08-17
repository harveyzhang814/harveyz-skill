import { PHASE1_PLATFORMS, MODES } from './select.js'
import { PROFILES } from './profiles.js'
import { modelMismatchLines, unavailableFieldLines } from './attribution.js'

const COMBOS = PHASE1_PLATFORMS.flatMap(p => MODES.map(m => ({ platform: p, mode: m })))
const COL = 12

const LABEL = {
  pass: 'pass', fail: 'fail', unavailable: 'unavail',
  unstable: '~', 'declared-na': 'n/a', 'blocked-upstream': '.', 'not-run': '',
}

// --repeat > 1 时同一个 (skill, platform, mode) 下有多条 record（每个 repeat 一条）。
// upstream 这一行没有 repeat 维度可画，只能收敛成一个格子——不能像 .find 那样
// 任取命中的第一条（等于随机拿一个 repeat 的结果代表全部），否则某个 repeat
// 真的跑挂了会被别的 repeat 的成功悄悄盖过去。收敛规则是"任一 repeat 失败即算
// 失败"：与 variance.js 的"不稳不取多数决"同一个哲学——不确定的东西不该被
// 平滑成一个好看的结论。
export function upstreamStatus(skill, platform, mode, records) {
  const matches = records.filter(r => r.skill === skill && r.platform === platform && r.mode === mode)
  if (!matches.length) return 'not-run'
  const failed = matches.some(r => r.exitCode !== 0 || r.reply === null || r.reply === undefined)
  return failed ? 'fail' : 'pass'
}

function assertionState({ skill, platform, mode, evalId, assertionId, assertion, verdicts, upstream }) {
  if (assertion.na_platforms?.includes(platform)) return 'declared-na'
  if (upstream !== 'pass') return upstream === 'not-run' ? 'not-run' : 'blocked-upstream'
  const v = verdicts.find(x =>
    x.skill === skill && x.platform === platform && x.mode === mode &&
    x.evalId === evalId && x.assertionId === assertionId)
  if (!v) return 'not-run'
  return v.unstable ? 'unstable' : v.verdict
}

export function renderQualityReport({ records, declarations, verdicts, allSkills, graderModel, subjectModel }) {
  const lines = []
  const graded = [...declarations.keys()].filter(s => allSkills.includes(s))
  const width = Math.max(24, ...graded.map(s => s.length + 4)) + 2

  lines.push(`grader: model=${graderModel}  subject=${subjectModel}`)
  if (graderModel === subjectModel) {
    lines.push('!! 量具与被测物同模型，差异可能是自指伪影，结论不可直接引用')
  }

  const unfrozen = graded.filter(s => (declarations.get(s).evals ?? []).some(e => !e.frozen))
  if (unfrozen.length) {
    lines.push(`!! 声明尚未 review（未冻结）：${unfrozen.join(', ')} —— 其平台结论不可引用`)
  }

  lines.push('')
  lines.push('skill / assertion'.padEnd(width) + COMBOS.map(c => `${c.platform}/${c.mode[0]}`.padEnd(COL)).join(''))

  const counts = { pass: 0, fail: 0, unavailable: 0, unstable: 0, 'declared-na': 0, 'not-run': 0 }
  const blocked = new Set()

  for (const skill of graded) {
    lines.push(skill)
    const ups = COMBOS.map(({ platform, mode }) => upstreamStatus(skill, platform, mode, records))
    lines.push('  [upstream]'.padEnd(width) + ups.map(s => (LABEL[s] ?? s).padEnd(COL)).join(''))

    for (const ev of declarations.get(skill).evals ?? []) {
      for (const a of ev.assertions ?? []) {
        const cols = COMBOS.map(({ platform, mode }, i) => {
          const state = assertionState({
            skill, platform, mode, evalId: ev.id, assertionId: a.id,
            assertion: a, verdicts, upstream: ups[i],
          })
          if (state === 'blocked-upstream') blocked.add(`${skill}|${platform}|${mode}`)
          else counts[state] = (counts[state] ?? 0) + 1
          return LABEL[state].padEnd(COL)
        })
        lines.push(`  ${a.id}`.padEnd(width) + cols.join(''))
      }
    }
  }

  lines.push('')
  lines.push('legend: .  = blocked-upstream, 见本组 [upstream] 行')
  lines.push('        (空) = not-run    n/a = 声明排除    unavail = 判不了    ~ = unstable')
  lines.push('')
  // 只打各态计数，不打任何合成比率——比率的分母里藏着「排除了多少 unavailable、
  // 多少 blocked」这些恰恰最该被看见的东西。
  lines.push(
    `pass: ${counts.pass}  fail: ${counts.fail}  unavailable: ${counts.unavailable}  ` +
    `unstable: ${counts.unstable}  declared-na: ${counts['declared-na']}  ` +
    `not-run: ${counts['not-run']}  blocked-upstream: ${blocked.size}`,
  )

  const unstableList = verdicts.filter(v => v.unstable)
  if (unstableList.length) {
    lines.push('')
    lines.push(`unstable assertions (${unstableList.length}):`)
    for (const v of unstableList) lines.push(`  ${v.skill}/${v.assertionId}@${v.platform}/${v.mode}`)
  }

  // 稀疏矩阵最大的风险是把「没测」静默渲染成「没问题」。
  const noDecl = allSkills.filter(s => !declarations.has(s))
  lines.push('')
  lines.push(`无声明 skill (${noDecl.length}): ${noDecl.join(', ')}`)

  lines.push(...modelMismatchLines(records))
  lines.push(...unavailableFieldLines(records))

  const harv = records.filter(r => r.harvestErrors?.length || r.transcriptTruncated)
  if (harv.length) {
    lines.push('')
    lines.push('harvest issues:')
    for (const r of harv) {
      const bits = [...(r.harvestErrors ?? [])]
      if (r.transcriptTruncated) bits.push('transcript truncated')
      lines.push(`  ${r.skill}@${r.platform}/${r.mode}: ${bits.join('; ')}`)
    }
  }

  lines.push('')
  lines.push(`builtinSkillFloor: ${PROFILES.map(p => `${p.id}=${p.builtinSkillFloor}`).join(' ')} — 触发失败先归因到这一格`)
  lines.push('')
  lines.push('platform notes:')
  for (const p of PROFILES) {
    const chan = p.processChannel === 'collect' ? '过程数据走 collect 通道' : '过程数据在 stdout 内联'
    lines.push(`  ${p.id}: ${chan}；产出物通道 ${p.artifactChannel}`)
  }

  return lines.join('\n')
}
