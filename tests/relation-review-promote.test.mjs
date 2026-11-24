import test from 'node:test'
import assert from 'node:assert/strict'
import { readSkill, indexEntry, contentHash } from './helpers/skillIndex.mjs'

const SKILL = 'skills/agent-canvas/relation-review/SKILL.md'

test('relation-review version and index hash are 1.2.0', async () => {
  const body = await readSkill(SKILL)
  const entry = await indexEntry('agent-canvas/relation-review')
  assert.match(body, /^version: ["']?1\.2\.0["']?$/m)
  assert.equal(entry.contentVersion, '1.2.0')
  assert.equal(entry.contentHash, contentHash(body))
})

test('relation-review promote example carries tier and selection fields', async () => {
  const body = await readSkill(SKILL)
  const lines = body.split('\n')
  const block = body.match(/relation_promote \{[\s\S]*?\n\}/)
  assert.ok(block, 'relation_promote 示例块存在')
  for (const f of ['tier:', 'useWhen:', 'notFor:', 'versus']) {
    assert.ok(block[0].includes(f), `示例块含 ${f}`)
  }
  assert.ok(/tier:.*role.*collaboration.*structure/.test(block[0]), 'tier 行列出三个取值')
  assert.ok(lines.some(l => l.includes('versus') && l.includes('可选')), 'versus 标为可选')
  assert.ok(lines.some(l => l.includes('tier') && l.includes('origin') && l.includes('unclassified')), 'tier 禁用 origin/unclassified 同行说明')
  assert.ok(lines.some(l => l.includes('缺') && l.includes('整次') && l.includes('什么都不写')), '缺项整次被拒')
  assert.ok(lines.some(l => l.includes('role') && l.includes('会话→对象')), 'role 层端点组合')
  assert.ok(lines.some(l => l.includes('collaboration') && l.includes('会话↔会话')), 'collaboration 层端点组合')
  assert.ok(lines.some(l => l.includes('structure') && l.includes('对象↔对象')), 'structure 层端点组合')
})

test('relation-review gates feed useWhen/notFor/versus and cite selection.byType', async () => {
  const lines = (await readSkill(SKILL)).split('\n')
  assert.ok(lines.some(l => l.includes('关卡一') && l.includes('useWhen') && l.includes('notFor')), '关卡一结论对应 useWhen/notFor')
  assert.ok(lines.some(l => l.includes('关卡三') && l.includes('versus')), '关卡三结论对应 versus')
  assert.ok(lines.some(l => l.includes('selection.byType') && l.includes('relationId')), 'selection.byType 引用且仍须真实 relationId')
})

test('relation-review codePinned examples match the current pinned set', async () => {
  const body = await readSkill(SKILL)
  const lines = body.split('\n').filter(l => l.includes('codePinned'))
  assert.ok(lines.length > 0)
  for (const l of lines) {
    assert.ok(!l.includes('spawns'), l)
    for (const t of ['implements', 'waits-for', 'unspecified']) assert.ok(l.includes(t), `${t} in: ${l}`)
  }
  assert.ok(!body.includes('spawns'), '正文不再出现 spawns')
})
