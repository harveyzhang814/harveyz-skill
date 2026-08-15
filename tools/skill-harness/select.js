export const PHASE1_PLATFORMS = ['claude', 'pi', 'hermes']
export const MODES = ['native', 'inject']

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
