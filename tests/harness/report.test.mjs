import { test } from 'node:test'
import assert from 'node:assert/strict'
import { renderReport } from '../../tools/skill-harness/report.js'

const CELLS = [
  { skill: 'a/x', platform: 'claude', mode: 'native', state: 'run' },
  { skill: 'a/x', platform: 'pi', mode: 'native', state: 'not-run' },
  { skill: 'a/x', platform: 'hermes', mode: 'native', state: 'declared-na', reason: '无等价机制' },
]

const RECORDS = [
  { skill: 'a/x', platform: 'claude', mode: 'native', exitCode: 0, triggered: true, modelMismatch: false, unavailable: [], reply: 'ok' },
]

test('页眉打印模型——没写模型的跨平台报告不可解读', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'MiniMax-M2.7', provider: 'minimax-cn' })
  assert.ok(out.includes('MiniMax-M2.7'))
  assert.ok(out.includes('minimax-cn'))
})

test('not-run 渲染成空格，绝不是对勾', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(!out.includes('✓'), 'not-run must never render as a checkmark')
  const row = out.split('\n').find(l => l.startsWith('a/x'))
  // 列宽 12：claude 列是 'pass'，pi 列必须整列空白，hermes 列是 'n/a'
  const cols = [0, 1, 2].map(i => row.slice(26 + i * 12, 26 + (i + 1) * 12))
  assert.equal(cols[0].trim(), 'pass')
  assert.equal(cols[1].trim(), '')
  assert.equal(cols[2].trim(), 'n/a')
  assert.ok(out.includes('not-run: 1'))
})

test('capabilities 表有生产消费者——报告读它说明各平台拿不到什么', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(/hermes/.test(out))
  assert.ok(/collect/.test(out), '报告须说明 hermes 的过程数据走 collect 通道')
  assert.ok(/cost-cap/.test(out), '报告须说明只有 claude 有成本上限能力')
})

test('declared-na 渲染成 n/a 并在脚注给出 reason', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(out.includes('n/a'))
  assert.ok(out.includes('无等价机制'))
})

test('跑过并成功的格子渲染成 pass', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(out.includes('pass'))
})

test('exitCode 非零渲染成 fail', () => {
  const bad = [{ ...RECORDS[0], exitCode: 1 }]
  const out = renderReport({ cells: CELLS, records: bad, model: 'M', provider: 'P' })
  assert.ok(out.includes('fail'))
})

test('modelMismatch 单列，不混进普通失败', () => {
  const mism = [{ ...RECORDS[0], modelMismatch: true }]
  const out = renderReport({ cells: CELLS, records: mism, model: 'M', provider: 'P' })
  assert.ok(/model mismatch/i.test(out))
})

test('unavailable 字段在报告里显式说明，不静默省略', () => {
  const un = [{ ...RECORDS[0], unavailable: ['toolCalls', 'triggered'] }]
  const out = renderReport({ cells: CELLS, records: un, model: 'M', provider: 'P' })
  assert.ok(out.includes('toolCalls'))
  assert.ok(out.includes('triggered'))
})

test('builtinSkillFloor 不对称在报告里给出归因提示', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(/builtinSkillFloor/.test(out))
  assert.ok(/16/.test(out))
})

test('矩阵行数等于 skill 数，不省略任何行列', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.equal(out.split('\n').filter(l => l.startsWith('a/x')).length, 1)
})
