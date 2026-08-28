export const PHASE1_PLATFORMS = ['claude', 'pi', 'hermes']
export const MODES = ['native', 'inject']

// 没有声明的 skill（或没传 --task）时，被测方收到的任务文案。与 cli.js 的
// ctx.task 缺省值共用同一个常量，避免两处各写一份、随时间悄悄分岔。
export const DEFAULT_TASK = 'run skill'

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
//
// eval 轴：一个 skill 的声明（declarations.get(s.path)）可能含多个 evals[]，
// 每条是独立场景、有自己的 prompt。有声明的 skill 按声明的 eval 数量展开
// cell，每个 cell 带自己的 evalId 与 task（= evalDef.prompt）——这是本任务
// 要修的缺陷本身：过去 run 阶段没有 eval 维度，四个场景的断言全部扣到同一次
// `run skill` 通用任务的运行结果上。没有声明的 skill 退化成过去的单格行为，
// evalId 为 null，task 取 opts.task ?? DEFAULT_TASK——它们永远不会被
// selectGradeCells 选中（要求声明存在），稀疏覆盖是有意的（见 brief 第 6 条）。
export function selectCells({ skills, matrix = { overrides: [] }, opts = {}, declarations = new Map() }) {
  const declared = new Map((matrix.overrides ?? []).map(o => [o.skill, o]))
  const wantSkills = new Set(opts.skills ?? [])
  const wantBundles = new Set(opts.bundles ?? [])
  const wantPlatforms = new Set(opts.platforms ?? PHASE1_PLATFORMS)
  const wantModes = new Set(opts.modes ?? MODES)
  const explicitPlatform = Array.isArray(opts.platforms)
  const noSkillFilter = wantSkills.size === 0 && wantBundles.size === 0
  // --repeat 缺省为 1：今天的行为——每个组合一格，repeat: 0。
  const repeat = opts.repeat ?? 1

  const cells = []
  for (const s of skills) {
    const override = declared.get(s.path)
    const skillSelected = noSkillFilter || wantSkills.has(s.path) || wantBundles.has(s.bundle)
    const decl = declarations.get(s.path)
    // [null] 占位：没有声明或声明里 evals 为空时，仍然只产出过去那样的单格。
    const evalDefs = decl?.evals?.length ? decl.evals : [null]
    for (const platform of PHASE1_PLATFORMS) {
      const declaredOut = Boolean(override) && !override.platforms.includes(platform)
      for (const mode of MODES) {
        for (const evalDef of evalDefs) {
          const cell = {
            skill: s.path, bundle: s.bundle, platform, mode,
            evalId: evalDef ? evalDef.id : null,
            // --task 只对没有声明的 skill 生效——一个 skill 一旦声明了 eval
            // 场景，每个场景的 prompt 就是它自己的任务，--task 不会静默盖过它，
            // 也不会因为选中了别的 skill 就报错，直接被这条 skill 的 cell 忽略。
            task: evalDef ? evalDef.prompt : (opts.task ?? DEFAULT_TASK),
            overridesDeclaration: false, reason: null,
          }
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
          // 只有真的会跑的格子才按 --repeat 展开——declared-na/not-run 重复是纯噪声，
          // 会在矩阵里制造从未执行过的"格子"。repeat 轴叠在 eval 轴之上：
          // 每个 (skill, platform, mode, evalId) 组合各自展开 N 份。
          if (cell.state === 'run') {
            for (let r = 0; r < repeat; r++) cells.push({ ...cell, repeat: r })
          } else {
            cells.push({ ...cell, repeat: 0 })
          }
        }
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
  const repeat = opts.repeat ?? 1
  const cells = []
  for (const platform of PHASE1_PLATFORMS) {
    for (const mode of MODES) {
      const base = { skill: PROBE_SKILL, bundle: 'probe', platform, mode, overridesDeclaration: false, reason: null }
      if (wantPlatforms.has(platform) && wantModes.has(mode)) {
        for (let r = 0; r < repeat; r++) cells.push({ ...base, state: 'run', repeat: r })
      } else {
        cells.push({ ...base, state: 'not-run', repeat: 0 })
      }
    }
  }
  return cells
}
