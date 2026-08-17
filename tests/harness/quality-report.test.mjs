import { test } from 'node:test'
import assert from 'node:assert/strict'
import { renderQualityReport, upstreamStatus } from '../../tools/skill-harness/quality-report.js'

const DECL = {
  skill_name: 'x',
  evals: [{ id: 1, frozen: '2026-08-17', assertions: [
    { id: 'aa', text: 'A' }, { id: 'bb', text: 'B' },
  ] }],
}

const RECORDS = [
  { skill: 'a/x', platform: 'claude', mode: 'native', exitCode: 0, reply: 'ok', model: 'subj-m', unavailable: [], modelMismatch: false },
  { skill: 'a/x', platform: 'claude', mode: 'inject', exitCode: 0, reply: 'ok', model: 'subj-m', unavailable: [], modelMismatch: false },
  { skill: 'a/x', platform: 'hermes', mode: 'native', exitCode: 1, reply: null, model: 'subj-m', unavailable: [], modelMismatch: false },
]

const VERDICTS = [
  { skill: 'a/x', platform: 'claude', mode: 'native', evalId: 1, assertionId: 'aa', verdict: 'pass', unstable: false },
  { skill: 'a/x', platform: 'claude', mode: 'native', evalId: 1, assertionId: 'bb', verdict: 'fail', unstable: false },
  { skill: 'a/x', platform: 'claude', mode: 'inject', evalId: 1, assertionId: 'aa', verdict: 'unavailable', unstable: false },
  { skill: 'a/x', platform: 'claude', mode: 'inject', evalId: 1, assertionId: 'bb', verdict: 'unstable', unstable: true },
]

const BASE = {
  records: RECORDS, declarations: new Map([['a/x', DECL]]), verdicts: VERDICTS,
  allSkills: ['a/x', 'a/y', 'a/z'], graderModel: 'grader-m', subjectModel: 'subj-m',
}

test('upstream 行就是第一期矩阵——降级成前置检查，不是删掉', () => {
  const out = renderQualityReport(BASE)
  assert.ok(out.includes('[upstream]'))
  assert.equal(upstreamStatus('a/x', 'claude', 'native', RECORDS), 'pass')
  assert.equal(upstreamStatus('a/x', 'hermes', 'native', RECORDS), 'fail')
  assert.equal(upstreamStatus('a/x', 'pi', 'native', RECORDS), 'not-run')
})

test('上游 fail 时断言行填 . 而不是 fail——一次安装失败不得放大成 N 条质量失败', () => {
  const out = renderQualityReport(BASE)
  const row = out.split('\n').find(l => l.trim().startsWith('aa'))
  assert.ok(row.includes('.'))
  assert.ok(!/\bfail\b.*\bfail\b.*\bfail\b/.test(row))
})

test('blocked-upstream 按 (skill,platform,mode) 计一次——按断言条数计会让平台差异变成断言条数的函数', () => {
  const out = renderQualityReport(BASE)
  // a/x 在 hermes/native 上游 fail，该 skill 有 2 条断言，只能计 1
  assert.ok(out.includes('blocked-upstream: 1'), out)
})

test('不打 pass_rate——合成比率会把三态压平，且太容易被单独摘出去引用', () => {
  const out = renderQualityReport(BASE)
  assert.ok(!/pass_rate/.test(out))
  assert.ok(!/通过率/.test(out))
  assert.ok(!/%/.test(out))
})

test('unavailable 格子只能是 unavail 本身——判不了的格子不能读成通过或零', () => {
  const out = renderQualityReport(BASE)
  const row = out.split('\n').find(l => l.trim().startsWith('aa'))
  // 列宽 12，前缀宽 26（BASE 里只有 a/x 一个 skill，width = max(24, 3+4)+2 = 26），
  // 6 列顺序 = COMBOS：claude/native claude/inject pi/native pi/inject hermes/native hermes/inject
  const col = i => row.slice(26 + i * 12, 26 + (i + 1) * 12).trim()
  assert.equal(col(0), 'pass')
  assert.equal(col(1), 'unavail') // claude/inject 的 aa：这一格是本测试要守的对象
  assert.equal(col(2), '')
  assert.equal(col(3), '')
  assert.equal(col(4), '.')
  assert.equal(col(5), '')
  for (let i = 0; i < 6; i++) {
    assert.notEqual(col(i), '0')
    assert.notEqual(col(i), '✓')
  }
})

test('[upstream] 行同样按固定列宽切片——列错位会让整行的判定挂到错误平台头上', () => {
  const out = renderQualityReport(BASE)
  const row = out.split('\n').find(l => l.trim().startsWith('[upstream]'))
  const col = i => row.slice(26 + i * 12, 26 + (i + 1) * 12).trim()
  assert.equal(col(0), 'pass')   // claude/native
  assert.equal(col(1), 'pass')   // claude/inject
  assert.equal(col(2), '')       // pi/native：未跑
  assert.equal(col(3), '')       // pi/inject：未跑
  assert.equal(col(4), 'fail')   // hermes/native：exitCode 1
  assert.equal(col(5), '')       // hermes/inject：未跑
})

test('unstable 渲染成 ~，不算 pass 也不算 fail', () => {
  const out = renderQualityReport(BASE)
  assert.ok(/~/.test(out))
  assert.ok(out.includes('unstable: 1'))
})

test('无声明 skill 必须显式列出——稀疏矩阵最大的风险是把"没测"渲染成"没问题"', () => {
  const out = renderQualityReport(BASE)
  assert.ok(out.includes('无声明 skill (2)'))
  assert.ok(out.includes('a/y'))
  assert.ok(out.includes('a/z'))
})

test('第一期的归因段落全部保留——降级的是矩阵层，不是归因层', () => {
  const out = renderQualityReport(BASE)
  assert.ok(out.includes('builtinSkillFloor'))
  assert.ok(out.includes('platform notes'))
})

test('量具与被测物同模型要打警告——否则差异可能只是自指伪影', () => {
  const same = renderQualityReport({ ...BASE, graderModel: 'subj-m' })
  assert.ok(/自指/.test(same))
  const diff = renderQualityReport(BASE)
  assert.ok(!/自指/.test(diff))
})

test('upstreamStatus: --repeat > 1 时任一 repeat 上游失败即整格判 fail——不能被别的 repeat 的成功盖过去', () => {
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' },
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 1, exitCode: 1, reply: null },
  ]
  assert.equal(upstreamStatus('a/x', 'claude', 'native', records), 'fail')
})

test('未冻结的声明要警告——冻结前不得据其下平台结论', () => {
  const unfrozen = new Map([['a/x', { ...DECL, evals: [{ id: 1, assertions: DECL.evals[0].assertions }] }]])
  const out = renderQualityReport({ ...BASE, declarations: unfrozen })
  assert.ok(/尚未 review/.test(out))
})
