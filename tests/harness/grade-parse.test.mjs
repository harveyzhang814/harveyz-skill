import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseGraderOutput, extractJson, VERDICTS, EVIDENCE_LIMIT } from '../../tools/skill-harness/grade/parse.js'

const ASSERTIONS = [{ id: 'a', text: 'A' }, { id: 'b', text: 'B' }]

test('三态齐全——只有 pass/fail 的话 unavailable 无处安放，必然被压成其中之一', () => {
  assert.deepEqual([...VERDICTS].sort(), ['fail', 'pass', 'unavailable'])
})

test('围栏包裹的 JSON 要能取出来——grader 常自作主张加 ```json', () => {
  assert.equal(extractJson('前言\n```json\n{"a":1}\n```\n后记').trim(), '{"a":1}')
  assert.equal(extractJson('{"b":2}'), '{"b":2}')
  assert.equal(extractJson('废话 {"c":{"d":3}} 废话'), '{"c":{"d":3}}')
  assert.equal(extractJson('```json\n{"x":"y","nested":{"z":123}}\n```'), '{"x":"y","nested":{"z":123}}')
})

test('JSON 不存在时必须抛错——找不到 { 不能静默返回空', () => {
  assert.throws(() => extractJson('no json here'), /JSON object found/)
  assert.throws(() => extractJson(''), /JSON object found/)
})

test('解析失败必须全判 unavailable——静默算 fail 会把量具故障伪装成平台质量问题', () => {
  const r = parseGraderOutput('模型今天不想输出 JSON', ASSERTIONS)
  assert.equal(r.ok, false)
  assert.equal(r.assertions.length, 2)
  for (const a of r.assertions) {
    assert.equal(a.verdict, 'unavailable')
    assert.match(a.evidence, /unparseable/)
  }
})

test('grader 漏判某条，那条判 unavailable，不牵连已判的条目', () => {
  const raw = '{"assertions":[{"id":"a","verdict":"pass","evidence":"原文 X"}]}'
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.equal(r.ok, true)
  assert.equal(r.assertions[0].verdict, 'pass')
  assert.equal(r.assertions[0].evidence, '原文 X')
  assert.equal(r.assertions[1].verdict, 'unavailable')
  assert.match(r.assertions[1].evidence, /未给出/)
})

test('verdict 取值非法当作没判——"partially" 这种自造值不能悄悄当成 pass', () => {
  const raw = '{"assertions":[{"id":"a","verdict":"partially","evidence":"e"},{"id":"b","verdict":"fail","evidence":"f"}]}'
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.equal(r.assertions[0].verdict, 'unavailable')
  assert.equal(r.assertions[1].verdict, 'fail')
})

test('输出顺序按声明顺序，不按 grader 返回顺序——矩阵的行顺序必须稳定', () => {
  const raw = '{"assertions":[{"id":"b","verdict":"fail","evidence":"f"},{"id":"a","verdict":"pass","evidence":"p"}]}'
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.deepEqual(r.assertions.map(x => x.id), ['a', 'b'])
})

test('grader 编出声明里没有的断言 id，直接丢弃——不许它自己加行', () => {
  const raw = '{"assertions":[{"id":"a","verdict":"pass","evidence":"p"},{"id":"ghost","verdict":"pass","evidence":"x"}]}'
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.equal(r.assertions.length, 2)
  assert.ok(!r.assertions.some(x => x.id === 'ghost'))
})

test('evidence 过长要截断至头部——保留引用源的开头，限制文件体积', () => {
  const longEvidence = 'x'.repeat(EVIDENCE_LIMIT + 1000)
  const raw = `{"assertions":[{"id":"a","verdict":"pass","evidence":"${longEvidence}"}]}`
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.equal(r.assertions[0].evidence.length, EVIDENCE_LIMIT)
  assert.ok(r.assertions[0].evidence.startsWith('x'))
})
