import { test } from 'node:test'
import assert from 'node:assert/strict'
import { selectCells, selectProbeCells, validateMatrix, PHASE1_PLATFORMS, MODES, PROBE_SKILL } from '../../tools/skill-harness/select.js'
import { aggregateVerdicts } from '../../tools/skill-harness/variance.js'

const SKILLS = [
  { path: 'mint/learn-skill', bundle: 'mint' },
  { path: 'research/extract-url', bundle: 'research' },
  { path: 'mint/runby-opencode', bundle: 'mint' },
]

const EMPTY = { overrides: [] }

test('默认：全部 skill × 3 平台 × 2 模式，全部 run', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY })
  assert.equal(cells.length, 3 * PHASE1_PLATFORMS.length * MODES.length)
  assert.ok(cells.every(c => c.state === 'run'))
})

test('声明 platforms: [] 使该 skill 全部平台变 declared-na 并带 reason', () => {
  const matrix = { overrides: [{ skill: 'mint/runby-opencode', platforms: [], reason: '它驱动的是 opencode' }] }
  const cells = selectCells({ skills: SKILLS, matrix })
  const mine = cells.filter(c => c.skill === 'mint/runby-opencode')
  assert.equal(mine.length, PHASE1_PLATFORMS.length * MODES.length)
  assert.ok(mine.every(c => c.state === 'declared-na'))
  assert.ok(mine.every(c => c.reason === '它驱动的是 opencode'))
})

test('声明 platforms 白名单：表内平台 run，表外 declared-na', () => {
  const matrix = { overrides: [{ skill: 'research/extract-url', platforms: ['claude'], reason: '依赖 claude 后台通道' }] }
  const cells = selectCells({ skills: SKILLS, matrix })
  const mine = cells.filter(c => c.skill === 'research/extract-url')
  assert.ok(mine.filter(c => c.platform === 'claude').every(c => c.state === 'run'))
  assert.ok(mine.filter(c => c.platform !== 'claude').every(c => c.state === 'declared-na'))
})

test('--skill 过滤：未选中的格子是 not-run，不是被删掉', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { skills: ['mint/learn-skill'] } })
  assert.equal(cells.length, 3 * PHASE1_PLATFORMS.length * MODES.length)
  assert.ok(cells.filter(c => c.skill === 'mint/learn-skill').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => c.skill !== 'mint/learn-skill').every(c => c.state === 'not-run'))
})

test('--bundle 过滤复用 skills-index.json 的 bundle 字段', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { bundles: ['research'] } })
  assert.ok(cells.filter(c => c.bundle === 'research').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => c.bundle !== 'research').every(c => c.state === 'not-run'))
})

test('--platform 过滤', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { platforms: ['pi'] } })
  assert.ok(cells.filter(c => c.platform === 'pi').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => c.platform !== 'pi').every(c => c.state === 'not-run'))
})

test('--mode 过滤', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { modes: ['native'] } })
  assert.ok(cells.filter(c => c.mode === 'native').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => c.mode === 'inject').every(c => c.state === 'not-run'))
})

test('CLI 显式指定平台可覆盖声明，但打 overridesDeclaration 标记', () => {
  const matrix = { overrides: [{ skill: 'mint/runby-opencode', platforms: [], reason: 'r' }] }
  const cells = selectCells({ skills: SKILLS, matrix, opts: { platforms: ['claude'] } })
  const mine = cells.filter(c => c.skill === 'mint/runby-opencode' && c.platform === 'claude')
  assert.ok(mine.every(c => c.state === 'run'))
  assert.ok(mine.every(c => c.overridesDeclaration === true))
})

test('validateMatrix: reason 缺失或空白即报错', () => {
  assert.deepEqual(validateMatrix({ overrides: [] }), [])
  const bad = { overrides: [{ skill: 'a/b', platforms: [] }] }
  assert.equal(validateMatrix(bad).length, 1)
  assert.match(validateMatrix(bad)[0], /reason/)
  const blank = { overrides: [{ skill: 'a/b', platforms: [], reason: '   ' }] }
  assert.equal(validateMatrix(blank).length, 1)
})

test('validateMatrix: platforms 必须是数组', () => {
  const bad = { overrides: [{ skill: 'a/b', platforms: 'claude', reason: 'r' }] }
  assert.ok(validateMatrix(bad).some(e => /platforms/.test(e)))
})

test('仓库自带的 matrix.json 合法', async () => {
  const { default: matrix } = await import('../../tools/skill-harness/matrix.json', { with: { type: 'json' } })
  assert.deepEqual(validateMatrix(matrix), [])
})

test('selectProbeCells: 默认 3 平台 × 2 模式 = 6 格，全部 run，skill 字段是探针身份——Phase 1 的冒烟用例本来就是六格，不是套着探针外壳的 41 行真实 skill', () => {
  const cells = selectProbeCells()
  assert.equal(cells.length, PHASE1_PLATFORMS.length * MODES.length)
  assert.ok(cells.every(c => c.state === 'run'))
  assert.ok(cells.every(c => c.skill === PROBE_SKILL))
})

test('selectProbeCells: 遵守 --platform/--mode 过滤，未选中的格子是 not-run', () => {
  const cells = selectProbeCells({ platforms: ['pi'], modes: ['native'] })
  assert.ok(cells.filter(c => c.platform === 'pi' && c.mode === 'native').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => !(c.platform === 'pi' && c.mode === 'native')).every(c => c.state === 'not-run'))
})

// --- --repeat 展开：defect 是 --repeat 解析后从未传给 selectCells，导致
// variance.js 的 aggregateVerdicts 永远只能拿到每组一条 grading，unstable
// 结构性地恒为 false。以下测试锁定修复后的行为。

test('--repeat 缺省为 1：每个组合仍然只有一格，repeat 字段为 0——今天的行为原样保留', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY })
  assert.equal(cells.length, 3 * PHASE1_PLATFORMS.length * MODES.length)
  assert.ok(cells.every(c => c.repeat === 0))
})

test('--repeat N 把每个会跑的组合展开成 N 格，编号 0..N-1', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { repeat: 3 } })
  assert.equal(cells.length, 3 * PHASE1_PLATFORMS.length * MODES.length * 3)
  const mine = cells.filter(c => c.skill === 'mint/learn-skill' && c.platform === 'claude' && c.mode === 'native')
  assert.equal(mine.length, 3)
  assert.deepEqual(mine.map(c => c.repeat).sort(), [0, 1, 2])
})

test('declared-na / not-run 的格子不被 --repeat 放大——重复没跑过的东西是矩阵里的纯噪声', () => {
  const matrix = { overrides: [{ skill: 'mint/runby-opencode', platforms: [], reason: 'r' }] }
  const cells = selectCells({ skills: SKILLS, matrix, opts: { repeat: 5, skills: ['mint/learn-skill'] } })

  const na = cells.filter(c => c.skill === 'mint/runby-opencode')
  assert.equal(na.length, PHASE1_PLATFORMS.length * MODES.length, 'declared-na 格子数量不受 repeat 影响')
  assert.ok(na.every(c => c.state === 'declared-na' && c.repeat === 0))

  const notRun = cells.filter(c => c.skill === 'research/extract-url')
  assert.equal(notRun.length, PHASE1_PLATFORMS.length * MODES.length, 'not-run 格子数量不受 repeat 影响')
  assert.ok(notRun.every(c => c.state === 'not-run' && c.repeat === 0))

  const run = cells.filter(c => c.skill === 'mint/learn-skill')
  assert.equal(run.length, PHASE1_PLATFORMS.length * MODES.length * 5, '只有真的要跑的格子按 repeat 展开')
})

test('selectProbeCells 同样遵守 --repeat：run 的格子按 repeat 展开，not-run 的格子不受影响', () => {
  const cells = selectProbeCells({ platforms: ['pi'], modes: ['native'], repeat: 4 })
  const run = cells.filter(c => c.state === 'run')
  assert.equal(run.length, 4)
  assert.deepEqual(run.map(c => c.repeat).sort(), [0, 1, 2, 3])
  const notRun = cells.filter(c => c.state === 'not-run')
  assert.ok(notRun.every(c => c.repeat === 0))
})

test('payoff：--repeat 展开出的 cells 能喂给 aggregateVerdicts 并真的测出 grader 判定不稳——修复前这条能力从 CLI 不可达', () => {
  const cells = selectCells({
    skills: SKILLS, matrix: EMPTY,
    opts: { repeat: 5, skills: ['mint/learn-skill'], platforms: ['pi'], modes: ['native'] },
  })
  const runCells = cells.filter(c => c.state === 'run')
  assert.equal(runCells.length, 5)

  // 模拟每个 repeat 格子跑完后 grader 给出的 grading：前 4 次判 pass，
  // 第 5 次判 fail——真实世界里这就是"量具在漂"的信号。
  const gradings = runCells.map(cell => ({
    skill: cell.skill, platform: cell.platform, mode: cell.mode, evalId: 1, repeat: cell.repeat,
    assertions: [{ id: 'a', verdict: cell.repeat === 4 ? 'fail' : 'pass' }],
  }))

  const verdicts = aggregateVerdicts(gradings)
  assert.equal(verdicts.length, 1)
  assert.equal(verdicts[0].unstable, true, '5 次里有 1 次分歧必须被判定为 unstable——这正是 --repeat 存在的意义')
})
