import { test } from 'node:test'
import assert from 'node:assert/strict'
import { makeRecord, tailBytes, STDERR_LIMIT } from '../../tools/skill-harness/record.js'

const BASE = {
  platform: 'claude', skill: 'mint/learn-skill', contentHash: 'aaaa',
  task: 'do it', repeat: 0, mode: 'native',
  requestedModel: 'MiniMax-M2.7', durationMs: 1234, exitCode: 0, stderr: '',
  parsed: {
    sessionId: 's-1', model: 'MiniMax-M2.7', provider: null, reply: 'ok', triggered: true,
    toolCalls: [{ name: 'Read', args: {}, ok: true, seq: 0 }], turns: 2,
    usage: { input: 1, output: 2, cacheRead: 3, cacheWrite: 4, totalTokens: 10, costUsd: 0.5 },
    visibleSkills: ['mint/learn-skill', 'a', 'b'], isError: false,
  },
}

test('tailBytes: 短字符串原样返回', () => {
  assert.equal(tailBytes('abc', 10), 'abc')
})

test('tailBytes: 超长保留尾部而不是头部', () => {
  const s = 'x'.repeat(100) + 'TAIL'
  assert.ok(tailBytes(s, 10).endsWith('TAIL'))
  assert.equal(tailBytes(s, 10).length, 10)
})

test('STDERR_LIMIT 是 16KB', () => {
  assert.equal(STDERR_LIMIT, 16 * 1024)
})

test('makeRecord: 完整输入时 unavailable 为空', () => {
  const r = makeRecord(BASE)
  assert.deepEqual(r.unavailable, [])
  assert.equal(r.reply, 'ok')
  assert.equal(r.triggered, true)
  assert.equal(r.turns, 2)
})

test('makeRecord: 缺失字段进 unavailable，且值为 null 而非伪造', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, toolCalls: null, turns: null, usage: null } })
  assert.deepEqual(r.unavailable.sort(), ['toolCalls', 'turns', 'usage'])
  assert.equal(r.toolCalls, null)
  assert.equal(r.turns, null)
  assert.equal(r.usage, null)
})

test('makeRecord: triggered 为 null 时进 unavailable', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, triggered: null } })
  assert.ok(r.unavailable.includes('triggered'))
})

test('makeRecord: inject 模式 triggered 恒为 null 且不算缺失', () => {
  const r = makeRecord({ ...BASE, mode: 'inject', parsed: { ...BASE.parsed, triggered: false } })
  assert.equal(r.triggered, null)
  assert.ok(!r.unavailable.includes('triggered'))
})

test('makeRecord: model 一致时 modelMismatch 为 false', () => {
  assert.equal(makeRecord(BASE).modelMismatch, false)
})

test('makeRecord: model 不一致时 modelMismatch 为 true', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, model: 'claude-sonnet-5' } })
  assert.equal(r.modelMismatch, true)
})

test('makeRecord: model 为 null 时不判 mismatch，进 unavailable', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, model: null } })
  assert.equal(r.modelMismatch, false)
  assert.ok(r.unavailable.includes('model'))
})

test('makeRecord: builtinSkillFloor = visibleSkills 数减去被测 skill', () => {
  const r = makeRecord({ ...BASE, skillName: 'mint/learn-skill' })
  assert.equal(r.builtinSkillFloor, 2)
})

test('makeRecord: visibleSkills 为 null 时 builtinSkillFloor 为 null 并进 unavailable', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, visibleSkills: null } })
  assert.equal(r.builtinSkillFloor, null)
  assert.ok(r.unavailable.includes('builtinSkillFloor'))
})

test('makeRecord: stderr 截断到 16KB 尾部', () => {
  const r = makeRecord({ ...BASE, stderr: 'y'.repeat(STDERR_LIMIT + 500) + 'END' })
  assert.equal(r.stderr.length, STDERR_LIMIT)
  assert.ok(r.stderr.endsWith('END'))
})

test('makeRecord: 记录里不出现任何凭证字段', () => {
  const r = makeRecord(BASE)
  const json = JSON.stringify(r)
  assert.ok(!/OAUTH|API_KEY|AUTH_TOKEN/i.test(json))
})

test('makeRecord: contentHash 透传，coverage 的 stale 判定靠它', () => {
  assert.equal(makeRecord(BASE).contentHash, 'aaaa')
  assert.equal(makeRecord({ ...BASE, contentHash: undefined }).contentHash, null)
})

test('makeRecord: 字段集合固定，新增字段必须来这里登记', () => {
  assert.deepEqual(Object.keys(makeRecord(BASE)).sort(), [
    'builtinSkillFloor', 'contentHash', 'durationMs', 'exitCode', 'harvestErrors', 'mode',
    'model', 'modelMismatch', 'platform', 'provider', 'repeat', 'reply', 'sessionId', 'skill',
    'stderr', 'task', 'toolCalls', 'transcriptTruncated', 'triggered', 'turns', 'unavailable',
    'usage',
  ])
})

test('采集出错要进 record——采集故障若不记，会伪装成被测方的质量问题', () => {
  const rec = makeRecord({ ...BASE, harvest: { truncated: true, errors: ['artifact a.md: ENOENT'] } })
  assert.equal(rec.transcriptTruncated, true)
  assert.deepEqual(rec.harvestErrors, ['artifact a.md: ENOENT'])
})

test('没传 harvest 时字段有确定默认值，不是 undefined', () => {
  const rec = makeRecord(BASE)
  assert.equal(rec.transcriptTruncated, false)
  assert.deepEqual(rec.harvestErrors, [])
})
