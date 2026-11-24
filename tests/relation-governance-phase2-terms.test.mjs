import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readSkill } from './helpers/skillIndex.mjs'

const SKILLS = [
  'skills/agent-canvas/relate-node',
  'skills/agent-canvas/capture-requirement',
  'skills/coding/fork-topic',
  'skills/agent-canvas/relation-review',
  'skills/agent-canvas/dispatch-agent',
]

// 显式白名单：只有「文件 + 行文本片段」都匹配的行才豁免，不按语境猜。
// 每项必须在本次扫描中至少豁免一行命中，否则判失败（防止白名单烂掉）。
const ALLOW = [
  {
    file: 'skills/agent-canvas/relate-node',
    snippet: '`spawns`、`originates-from` 已退役',
    reason: '明确声明 spawns 与 originates-from 已退役，不是推荐用法',
  },
  {
    file: 'skills/agent-canvas/relate-node',
    snippet: '想连会话之间的 `depends-on`：App 会拒绝',
    reason: '说明会话之间的 depends-on 会被 App 拒绝；需求之间的 depends-on 另有归属',
  },
]

const RULES = [
  { name: 'spawns 出现', hit: l => /spawns/.test(l) },
  { name: '子节点', hit: l => /子节点/.test(l) },
  { name: 'spawns/hands-off-to', hit: l => /spawns\s*[/、,，]\s*hands-off-to/.test(l) },
  { name: '血缘', hit: l => /血缘/.test(l) },
  { name: 'depends-on 出现', hit: l => /depends-on/.test(l) },
]

/** 扫描一份正文，返回 { hits, lineageHits }；hits 里带行号与规则名。 */
function scan(file, body) {
  const hits = []
  body.split('\n').forEach((line, i) => {
    for (const r of RULES) if (r.hit(line)) hits.push({ file, no: i + 1, rule: r.name, line: line.trim() })
  })
  // lineage 规则：同一段（空行之间）里 lineage 与 spawns 不能同时出现；
  // 已在白名单里豁免的行（如「spawns 已退役」）不算 spawns 出现，否则同段的合法声明会误报。
  const lineageHits = []
  for (const para of body.split(/\n\s*\n/)) {
    const spawnsLeft = para.split('\n').some(l => /spawns/.test(l) && !ALLOW.some(a => a.file === file && l.includes(a.snippet)))
    if (/lineage/.test(para) && spawnsLeft) lineageHits.push(`${file} [lineage 与 spawns 同段] ${para.trim().slice(0, 80)}`)
  }
  return { hits, lineageHits }
}

function split(hits) {
  const used = new Set()
  const violations = []
  const allowed = []
  for (const h of hits) {
    const idx = ALLOW.findIndex(a => a.file === h.file && h.line.includes(a.snippet))
    if (idx >= 0) { used.add(idx); allowed.push({ ...h, reason: ALLOW[idx].reason }) } else violations.push(h)
  }
  return { used, violations, allowed }
}

test('five skills drop phase-1 relation wording', async t => {
  const hits = []
  const lineage = []
  for (const dir of SKILLS) {
    const r = scan(dir, await readSkill(`${dir}/SKILL.md`))
    hits.push(...r.hits)
    lineage.push(...r.lineageHits)
  }
  const { used, violations, allowed } = split(hits)
  const stale = ALLOW.filter((_, i) => !used.has(i)).map(a => `白名单项匹配不到任何行：${a.file} ${a.snippet}`)
  assert.deepEqual(
    [...violations.map(v => `${v.file}:${v.no} [${v.rule}] ${v.line}`), ...lineage, ...stale],
    [],
  )
  for (const a of allowed) t.diagnostic(`豁免 ${a.file}:${a.no} [${a.rule}] ${a.reason} | ${a.line}`)
})

test('scan catches a reworded phase-1 claim that the old context rule would skip', () => {
  const body = 'spawns 不需要你建\n\nlineage 是 spawns 链\n\n会话间 depends-on 不用管'
  const { hits, lineageHits } = scan('tmp/skill', body)
  const { violations } = split(hits)
  assert.equal(violations.length, 3)
  assert.equal(lineageHits.length, 1)
})
