import test from 'node:test'
import assert from 'node:assert/strict'
import { readSkill, indexEntry, contentHash } from './helpers/skillIndex.mjs'

const SKILL = 'skills/agent-canvas/capture-requirement/SKILL.md'

test('capture-requirement version and index hash are 2.2.0', async () => {
  const body = await readSkill(SKILL)
  const entry = await indexEntry('agent-canvas/capture-requirement')
  assert.match(body, /^version: ["']?2\.2\.0["']?$/m)
  assert.equal(entry.contentVersion, '2.2.0')
  assert.equal(entry.contentHash, contentHash(body))
})

test('capture-requirement checks implements before drafting', async () => {
  const body = await readSkill(SKILL)
  const draft = body.indexOf('draft-requirement')
  assert.ok(body.indexOf('node-relations') >= 0 && body.indexOf('node-relations') < draft)
  assert.ok(body.indexOf('--type implements') >= 0 && body.indexOf('--type implements') < draft)
  assert.ok(body.includes('claim-requirement'))
  assert.ok(body.includes('--acceptance-spec'))
  assert.ok(body.includes('用户指定'))
})

test('capture-requirement reports existing acceptance items and gates replace', async () => {
  const body = await readSkill(SKILL)
  for (const phrase of ['existingItemCount', 'acceptanceWritten', '未覆盖', '--replace-acceptance', '明确要求']) {
    assert.ok(body.includes(phrase), phrase)
  }
})

test('capture-requirement stops when the claim is refused', async () => {
  const body = await readSkill(SKILL)
  for (const phrase of ['open', 'in_progress', '停下', '不新建', '不重试']) {
    assert.ok(body.includes(phrase), phrase)
  }
})

test('capture-requirement does not write realizes', async () => {
  const body = await readSkill(SKILL)
  assert.ok(!/link-nodes[^\n]*realizes/.test(body))
  assert.ok(body.includes('不写 `realizes`'))
})

test('capture-requirement old refusal wording is replaced', async () => {
  const body = await readSkill(SKILL)
  assert.ok(!body.includes('第 1 步会直接拒绝'))
  assert.ok(body.includes('不该走到第 1 步'))
})
