import { test } from 'node:test'
import assert from 'node:assert/strict'
import { selectCells, selectProbeCells, validateMatrix, PHASE1_PLATFORMS, MODES, PROBE_SKILL } from '../../tools/skill-harness/select.js'

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
