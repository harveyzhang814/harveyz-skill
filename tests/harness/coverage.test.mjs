import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildCoverage, renderCoverage } from '../../tools/skill-harness/coverage.js'

const SKILLS = [
  { path: 'mint/learn-skill', contentHash: 'aaaa' },
  { path: 'research/extract-url', contentHash: 'bbbb' },
]

const NOW = new Date('2026-08-15T00:00:00Z')

const RUNS = [
  {
    runId: '20260812-100000-0001',
    at: new Date('2026-08-12T00:00:00Z'),
    records: [
      { skill: 'mint/learn-skill', platform: 'claude', contentHash: 'aaaa' },
      { skill: 'mint/learn-skill', platform: 'pi', contentHash: 'aaaa' },
      { skill: 'research/extract-url', platform: 'claude', contentHash: 'OLD' },
    ],
  },
]

test('从未跑过的格子是 never', () => {
  const cells = buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW })
  const c = cells.find(x => x.skill === 'mint/learn-skill' && x.platform === 'hermes')
  assert.equal(c.state, 'never')
  assert.equal(c.lastRunAt, null)
})

test('跑过且 contentHash 一致的格子是 fresh', () => {
  const cells = buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW })
  const c = cells.find(x => x.skill === 'mint/learn-skill' && x.platform === 'claude')
  assert.equal(c.state, 'fresh')
  assert.equal(c.ageDays, 3)
})

test('contentHash 变过的格子是 stale——结论已过期', () => {
  const cells = buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW })
  const c = cells.find(x => x.skill === 'research/extract-url' && x.platform === 'claude')
  assert.equal(c.state, 'stale')
  assert.equal(c.stale, true)
})

test('矩阵是完整的：skill 数 × 平台数', () => {
  const cells = buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW })
  assert.equal(cells.length, 2 * 3)
})

test('多次运行取最近一次', () => {
  const runs = [
    ...RUNS,
    { runId: '20260814-100000-0002', at: new Date('2026-08-14T00:00:00Z'), records: [{ skill: 'mint/learn-skill', platform: 'claude', contentHash: 'aaaa' }] },
  ]
  const c = buildCoverage({ runs, skills: SKILLS, now: NOW }).find(x => x.skill === 'mint/learn-skill' && x.platform === 'claude')
  assert.equal(c.ageDays, 1)
})

test('renderCoverage: never 渲染成 never，不是对勾', () => {
  const out = renderCoverage(buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW }))
  assert.ok(out.includes('never'))
  assert.ok(!out.includes('✓'))
})

test('renderCoverage: stale 带标记', () => {
  const out = renderCoverage(buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW }))
  assert.ok(/3d ago/.test(out))
  assert.ok(/陈/.test(out))
})

test('renderCoverage: 表头含三个平台名', () => {
  const out = renderCoverage(buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW }))
  for (const p of ['claude', 'pi', 'hermes']) assert.ok(out.includes(p))
})
