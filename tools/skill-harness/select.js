export const PHASE1_PLATFORMS = ['claude', 'pi', 'hermes']
export const MODES = ['native', 'inject']

// --probe 模式下代表锚点探针的身份，绝不能与 skills-index.json 里任何真实 skill 的
// path 撞名——撞了就会让探针跑的记录顶替真实 skill 的账。
export const PROBE_SKILL = 'probe-anchor'

// 校验 matrix.json。返回错误信息数组，空数组表示合法。
// reason 必填是本模块唯一的硬约束：一条没有理由的排除，和忘了测无法区分。
export function validateMatrix(matrix) {
  const errors = []
  const overrides = matrix?.overrides ?? []
  overrides.forEach((o, i) => {
    const tag = `overrides[${i}]${o?.skill ? ` (${o.skill})` : ''}`
    if (!o?.skill) errors.push(`${tag}: "skill" is required`)
    if (!Array.isArray(o?.platforms)) errors.push(`${tag}: "platforms" must be an array`)
    if (!o?.reason || !String(o.reason).trim())
      errors.push(`${tag}: "reason" is required — an exclusion without a stated reason is indistinguishable from forgetting to test`)
  })
  return errors
}

// 纯函数。产出全矩阵每一格及其状态，被过滤掉的格子保留为 not-run 而非删除，
// 这样报告永远拿得到完整矩阵，"没跑"无法伪装成"通过"。
export function selectCells({ skills, matrix = { overrides: [] }, opts = {} }) {
  const declared = new Map((matrix.overrides ?? []).map(o => [o.skill, o]))
  const wantSkills = new Set(opts.skills ?? [])
  const wantBundles = new Set(opts.bundles ?? [])
  const wantPlatforms = new Set(opts.platforms ?? PHASE1_PLATFORMS)
  const wantModes = new Set(opts.modes ?? MODES)
  const explicitPlatform = Array.isArray(opts.platforms)
  const noSkillFilter = wantSkills.size === 0 && wantBundles.size === 0

  const cells = []
  for (const s of skills) {
    const override = declared.get(s.path)
    const skillSelected = noSkillFilter || wantSkills.has(s.path) || wantBundles.has(s.bundle)
    for (const platform of PHASE1_PLATFORMS) {
      const declaredOut = Boolean(override) && !override.platforms.includes(platform)
      for (const mode of MODES) {
        const cell = { skill: s.path, bundle: s.bundle, platform, mode, overridesDeclaration: false, reason: null }
        const cliSelected = skillSelected && wantPlatforms.has(platform) && wantModes.has(mode)
        if (declaredOut && explicitPlatform && wantPlatforms.has(platform) && skillSelected && wantModes.has(mode)) {
          cell.state = 'run'
          cell.overridesDeclaration = true
          cell.reason = override.reason
        } else if (declaredOut) {
          cell.state = 'declared-na'
          cell.reason = override.reason
        } else if (!cliSelected) {
          cell.state = 'not-run'
        } else {
          cell.state = 'run'
        }
        cells.push(cell)
      }
    }
  }
  return cells
}

// 纯函数。--probe：一期锚点探针冒烟用例，本质是单一探针身份 × 选中的
// platforms/modes——Phase 1 的冒烟用例一直就是 3 平台 × 2 模式 = 6 格，
// 不是套着探针外壳的、cell.skill 各不相同的 41 行真实 skill。
// 用 PROBE_SKILL 统一填 cell.skill，下游的 record/cells.json/contentHash
// 查表因此天然不会把探针的结果记成任何一个真实 skill 的。
export function selectProbeCells(opts = {}) {
  const wantPlatforms = new Set(opts.platforms ?? PHASE1_PLATFORMS)
  const wantModes = new Set(opts.modes ?? MODES)
  const cells = []
  for (const platform of PHASE1_PLATFORMS) {
    for (const mode of MODES) {
      cells.push({
        skill: PROBE_SKILL, bundle: 'probe', platform, mode,
        overridesDeclaration: false, reason: null,
        state: wantPlatforms.has(platform) && wantModes.has(mode) ? 'run' : 'not-run',
      })
    }
  }
  return cells
}
