import test from 'node:test'
import assert from 'node:assert/strict'
import { readSkill, indexEntry, contentHash } from './helpers/skillIndex.mjs'

const SKILL = 'skills/agent-canvas/relate-node/SKILL.md'
const split = body => {
  const [, front, ...rest] = body.split(/^---$/m)
  return { front, text: rest.join('---') }
}

test('relate-node version and index hash are 1.1.0', async () => {
  const body = await readSkill(SKILL)
  const entry = await indexEntry('agent-canvas/relate-node')
  assert.match(body, /^version: ["']?1\.1\.0["']?$/m)
  assert.equal(entry.contentVersion, '1.1.0')
  assert.equal(entry.contentHash, contentHash(body))
})

test('relate-node reads the phase-2 guide fields', async () => {
  const body = await readSkill(SKILL)
  for (const phrase of ['rules', 'selection', 'waitingOn', 'created-from', 'relation-guide --from', 'resolve-wait']) {
    assert.ok(body.includes(phrase), phrase)
  }
})

test('relate-node skips explores and session depends-on', async () => {
  const { front, text } = split(await readSkill(SKILL))
  assert.ok(text.includes('不核对 `explores`'))
  assert.ok(!text.includes('depends-on（已知的阻塞）'))
  assert.ok(!text.includes('`depends-on`（补漏）'))
  assert.ok(!/description:.*depends-on/.test(front), 'description 不含 depends-on')
})

test('relate-node no longer calls spawns the system type', async () => {
  const body = await readSkill(SKILL)
  assert.ok(!body.includes('是系统专属'))
  assert.ok(!body.includes('spawns/hands-off-to 血缘链'))
  assert.ok(!body.includes('`spawns`——'))
})
