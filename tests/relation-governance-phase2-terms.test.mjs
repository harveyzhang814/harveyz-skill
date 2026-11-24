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

// 逐行扫描：命中旧说法的行，若同一行带有否定或退役词（退役/拒/不），视为在说明「已不成立」，跳过。
// 没有这类词的命中才算残留的一期说法。
const NEGATED = /退役|拒|不/

const RULES = [
  { name: 'spawns 作为现行类型', hit: l => /spawns/.test(l) && !NEGATED.test(l) },
  { name: '子节点（一期「子节点不弹审批」等）', hit: l => /子节点/.test(l) },
  { name: 'spawns/hands-off-to', hit: l => /spawns\/hands-off-to/.test(l) },
  { name: '会话间 depends-on 的建议', hit: l => /depends-on/.test(l) && !NEGATED.test(l) },
  { name: 'lineage 说成 spawns 链', hit: l => /lineage/.test(l) && /spawns/.test(l) },
]

test('five skills drop phase-1 relation wording', async () => {
  const found = []
  for (const dir of SKILLS) {
    const lines = (await readSkill(`${dir}/SKILL.md`)).split('\n')
    lines.forEach((line, i) => {
      for (const r of RULES) if (r.hit(line)) found.push(`${dir}:${i + 1} [${r.name}] ${line.trim()}`)
    })
  }
  assert.deepEqual(found, [])
})
