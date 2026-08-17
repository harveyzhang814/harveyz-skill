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

test('assertion id 含 | 分隔符不能与其他 id 意外合并——聚合键不安全会制造假的分歧', () => {
  // 在 JSON.stringify 之前，id 'a|b' 和这样的 evalId 布局会产生冲突
  // 比如 evalId 1, id 'a|b' vs evalId 'a', id 'b' 在字符串拼接中会变成相同字符串
  // JSON.stringify 确保任何字符都能安全区分
  const out = aggregateVerdicts([
    { skill: 'x', platform: 'pi', mode: 'native', evalId: 1, repeat: 0, assertions: [{ id: 'a|b', verdict: 'pass' }] },
    { skill: 'x', platform: 'pi', mode: 'native', evalId: 'a', repeat: 0, assertions: [{ id: 'b', verdict: 'fail' }] },
  ])
  assert.equal(out.length, 2)
  assert.equal(out[0].unstable, false)
  assert.equal(out[1].unstable, false)
})

test('空 gradings 数组返回空数组', () => {
  const out = aggregateVerdicts([])
  assert.deepEqual(out, [])
})

test('空 assertions 数组的 grading 不贡献任何组', () => {
  const out = aggregateVerdicts([
    { skill: 'x', platform: 'pi', mode: 'native', evalId: 1, repeat: 0, assertions: [] },
  ])
  assert.deepEqual(out, [])
})

test('没有 assertions 键的 grading 不抛错', () => {
  const out = aggregateVerdicts([
    { skill: 'x', platform: 'pi', mode: 'native', evalId: 1, repeat: 0 },
  ])
  assert.deepEqual(out, [])
})
