import { test } from 'node:test'
import assert from 'node:assert/strict'
import { aggregateVerdicts } from '../../tools/skill-harness/variance.js'

const g = (repeat, verdict) => ({
  skill: 'a/x', platform: 'pi', mode: 'native', evalId: 1, repeat,
  assertions: [{ id: 'a', verdict, evidence: 'e' }],
})

test('五次一致就是稳定，verdict 取那个一致值', () => {
  const out = aggregateVerdicts([g(0, 'pass'), g(1, 'pass'), g(2, 'pass'), g(3, 'pass'), g(4, 'pass')])
  assert.equal(out.length, 1)
  assert.equal(out[0].verdict, 'pass')
  assert.equal(out[0].unstable, false)
})

test('有分歧就标 unstable，不取多数——多数决会把"尺子在漂"粉饰成一个确定结论', () => {
  const out = aggregateVerdicts([g(0, 'pass'), g(1, 'pass'), g(2, 'pass'), g(3, 'pass'), g(4, 'fail')])
  assert.equal(out[0].verdict, 'unstable')
  assert.equal(out[0].unstable, true)
  assert.deepEqual(out[0].verdicts.sort(), ['fail', 'pass', 'pass', 'pass', 'pass'])
})

test('unavailable 与 pass 混合也算不稳——判得了和判不了之间的摇摆同样是尺子在漂', () => {
  const out = aggregateVerdicts([g(0, 'pass'), g(1, 'unavailable')])
  assert.equal(out[0].verdict, 'unstable')
})

test('跑一次也能聚合，结果就是那一次——标定不是使用的前提', () => {
  const out = aggregateVerdicts([g(0, 'fail')])
  assert.equal(out[0].verdict, 'fail')
  assert.equal(out[0].unstable, false)
})

test('不同平台不聚合到一起——聚合键必须含 platform 和 mode', () => {
  const out = aggregateVerdicts([
    { skill: 'a/x', platform: 'pi', mode: 'native', evalId: 1, repeat: 0, assertions: [{ id: 'a', verdict: 'pass' }] },
    { skill: 'a/x', platform: 'claude', mode: 'native', evalId: 1, repeat: 0, assertions: [{ id: 'a', verdict: 'fail' }] },
    { skill: 'a/x', platform: 'pi', mode: 'inject', evalId: 1, repeat: 0, assertions: [{ id: 'a', verdict: 'fail' }] },
  ])
  assert.equal(out.length, 3)
  assert.ok(out.every(x => x.unstable === false))
})
