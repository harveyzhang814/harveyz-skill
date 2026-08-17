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
  const row = out.split('\n').find(l => l.trim().startsWith('bb'))
  const col = i => row.slice(26 + i * 12, 26 + (i + 1) * 12).trim()
  assert.equal(col(1), '~') // claude/inject 的 bb：VERDICTS 里标为 unstable，这才是本测试真正要守的格子
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

test('upstreamStatus: --repeat > 1 时部分 repeat 上游失败要返回 partial，不是 fail——"4/5 装成了"和"5/5 全挂"是不同的事实', () => {
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' },
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 1, exitCode: 1, reply: null },
  ]
  assert.equal(upstreamStatus('a/x', 'claude', 'native', records), 'partial')
})

test('upstreamStatus: 全部 repeat 上游都失败才是 fail', () => {
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 1, reply: null },
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 1, exitCode: 1, reply: null },
  ]
  assert.equal(upstreamStatus('a/x', 'claude', 'native', records), 'fail')
})

test('审阅场景：一个 repeat 通过并被判 pass，另一个 repeat 上游失败——已算出的 pass 必须照常渲染和计数，[upstream] 显示 partial 而不是 fail', () => {
  const decl = {
    skill_name: 'x',
    evals: [{ id: 1, frozen: '2026-08-17', assertions: [{ id: 'aa', text: 'A' }] }],
  }
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', model: 'subj-m', unavailable: [], modelMismatch: false },
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 1, exitCode: 1, reply: null, model: 'subj-m', unavailable: [], modelMismatch: false },
  ]
  const verdicts = [
    { skill: 'a/x', platform: 'claude', mode: 'native', evalId: 1, assertionId: 'aa', verdict: 'pass', unstable: false },
  ]
  const out = renderQualityReport({
    records, declarations: new Map([['a/x', decl]]), verdicts,
    allSkills: ['a/x'], graderModel: 'grader-m', subjectModel: 'subj-m',
  })

  // width = max(24, 3+4)+2 = 26；只有 a/x 一个 skill，与 BASE 场景相同的列宽算法
  const upRow = out.split('\n').find(l => l.trim().startsWith('[upstream]'))
  const aaRow = out.split('\n').find(l => l.trim().startsWith('aa'))
  const col = (row, i) => row.slice(26 + i * 12, 26 + (i + 1) * 12).trim()

  assert.equal(col(upRow, 0), 'partial', '[upstream] 必须显示 partial，不能显示 fail——另一个 repeat 是真的跑通了的')
  assert.equal(col(aaRow, 0), 'pass', '已经算出来的 verdict 必须照常渲染，不能被折叠后的 upstream 状态吞掉')
  assert.ok(out.includes('pass: 1'), '计数必须反映这条真实算出的 pass，不能被折进 blocked-upstream')
  assert.ok(out.includes('blocked-upstream: 0'))
})

test('全部 repeat 上游都失败时行为不变：整格仍是 fail，断言行仍是 .（blocked-upstream）', () => {
  const decl = {
    skill_name: 'x',
    evals: [{ id: 1, frozen: '2026-08-17', assertions: [{ id: 'aa', text: 'A' }] }],
  }
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 1, reply: null, model: 'subj-m', unavailable: [], modelMismatch: false },
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 1, exitCode: 1, reply: null, model: 'subj-m', unavailable: [], modelMismatch: false },
  ]
  const out = renderQualityReport({
    records, declarations: new Map([['a/x', decl]]), verdicts: [],
    allSkills: ['a/x'], graderModel: 'grader-m', subjectModel: 'subj-m',
  })

  const upRow = out.split('\n').find(l => l.trim().startsWith('[upstream]'))
  const aaRow = out.split('\n').find(l => l.trim().startsWith('aa'))
  const col = (row, i) => row.slice(26 + i * 12, 26 + (i + 1) * 12).trim()

  assert.equal(col(upRow, 0), 'fail')
  assert.equal(col(aaRow, 0), '.')
  assert.ok(out.includes('blocked-upstream: 1'))
})

test('未冻结的声明要警告——冻结前不得据其下平台结论', () => {
  const unfrozen = new Map([['a/x', { ...DECL, evals: [{ id: 1, assertions: DECL.evals[0].assertions }] }]])
  const out = renderQualityReport({ ...BASE, declarations: unfrozen })
  assert.ok(/尚未 review/.test(out))
})
