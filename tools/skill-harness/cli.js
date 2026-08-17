#!/usr/bin/env node
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { selectCells, selectProbeCells, validateMatrix, PHASE1_PLATFORMS, MODES } from './select.js'
import { planCell, runMatrix, ADAPTERS } from './runner.js'
import { loadRuns, buildCoverage, renderCoverage } from './coverage.js'
import { renderReport } from './report.js'
import { stripFrontmatter } from './prompt.js'
import { claudeOAuthToken } from './jail.js'
import { runGrade, invokeClaudeGrader } from './grade/index.js'
import { loadDeclaration } from './declarations.js'
import { aggregateVerdicts } from './variance.js'
import { renderQualityReport } from './quality-report.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(here, '../..')

const COMMANDS = new Set(['run', 'dry-run', 'report', 'coverage', 'grade'])
const REPEATABLE = { '--skill': 'skills', '--platform': 'platforms', '--bundle': 'bundles', '--only': 'only' }

export function parseArgs(argv) {
  const command = argv[0]
  if (!COMMANDS.has(command)) throw new Error(`unknown command: ${command} (expected one of ${[...COMMANDS].join(', ')})`)

  const opts = { modes: [...MODES], repeat: 1 }
  // grade 的第一个位置参数是 runId，不是旗标
  let start = 1
  if (command === 'grade' && argv[1] && !argv[1].startsWith('--')) {
    opts.runId = argv[1]
    start = 2
  }
  for (let i = start; i < argv.length; i++) {
    const flag = argv[i]
    if (flag === '--probe') { opts.probe = true; continue }
    const value = argv[++i]
    if (REPEATABLE[flag]) {
      const key = REPEATABLE[flag]
      opts[key] = [...(opts[key] ?? []), value]
    } else if (flag === '--mode') {
      opts.modes = value === 'both' ? [...MODES] : [value]
    } else if (flag === '--model') opts.model = value
    else if (flag === '--provider') opts.provider = value
    else if (flag === '--base-url') opts.baseUrl = value
    else if (flag === '--task') opts.task = value
    else if (flag === '--repeat') opts.repeat = Number(value)
    else if (flag === '--grader-model') opts.graderModel = value
    else throw new Error(`unknown flag: ${flag}`)
  }

  for (const p of opts.platforms ?? []) {
    if (!PHASE1_PLATFORMS.includes(p)) throw new Error(`unknown platform: ${p} (phase 1 supports ${PHASE1_PLATFORMS.join(', ')})`)
  }
  for (const m of opts.modes) {
    if (!MODES.includes(m)) throw new Error(`unknown mode: ${m}`)
  }
  if ((command === 'run' || command === 'dry-run') && !opts.model) {
    throw new Error('--model is required — falling back to each platform default would confound platform with model')
  }
  if (opts.probe && (opts.skills?.length ?? 0) > 0) {
    throw new Error('--probe and --skill are mutually exclusive — say which one you mean, guessing recreates the defect this flag exists to fix')
  }
  if (command === 'grade') {
    if (!opts.runId) throw new Error('grade requires a runId: skill-harness grade <runId> --grader-model <model>')
    if (!opts.graderModel) throw new Error('--grader-model is required — an unpinned grader confounds the measuring stick with the thing measured')
  }
  return { command, opts }
}

export function renderDryRun(cells, ctx) {
  const out = []
  for (const cell of cells) {
    if (cell.state !== 'run') continue
    const adapter = ADAPTERS[cell.platform]
    const plan = planCell(cell, ctx)
    const entry = ctx.skills.get(cell.skill)
    out.push(`=== ${cell.platform}/${cell.mode} · ${cell.skill} ===`)
    out.push('argv:')
    out.push(plan.argv.map(a => `  ${a}`).join('\n'))
    out.push('env (redacted):')
    out.push(Object.entries(plan.redactedEnv).map(([k, v]) => `  ${k}=${v}`).join('\n'))
    if (cell.mode === 'native') {
      const dest = adapter.profile.skillChannel === 'skill-dir'
        ? path.join(ctx.jailDir, cell.platform === 'claude' ? '.claude/skills' : '.hermes/skills', path.basename(entry.skillPath))
        : '(none — loaded via explicit flag)'
      out.push(`jail writes: ${dest}`)
      out.push('skill body: not in the prompt — loaded natively by the platform')
    }
    out.push('systemAppend:')
    out.push(plan.systemAppend ?? '  (none)')
    out.push('positional:')
    out.push(plan.positional)
    out.push('')
  }
  return out.join('\n')
}

// 纯函数（readBody 注入，测试不必读真盘）。只为 cells 里实际要跑（state === 'run'）
// 的 skill 建条目——不把全仓库 41 个 SKILL.md 都读进来。键是 cell.skill，
// 即 skills-index.json 里的 path（如 'mint/learn-skill'）。
export async function buildSkillMap(repoRoot, cells, readBody) {
  const skills = new Map()
  for (const cell of cells) {
    if (cell.state !== 'run') continue
    if (skills.has(cell.skill)) continue
    const skillPath = path.join(repoRoot, 'skills', cell.skill)
    const skillBody = stripFrontmatter(await readBody(path.join(skillPath, 'SKILL.md')))
    skills.set(cell.skill, { skillPath, skillDir: skillPath, skillBody })
  }
  return skills
}

// 纯函数（readBody 注入），与 buildSkillMap 对称。--probe：一期锚点探针冒烟用例，
// 所有 state === 'run' 的格子显式指向同一个探针目录，而不是按 cell.skill 解析。
export async function buildProbeMap(repoRoot, cells, readBody) {
  const probePath = path.join(repoRoot, 'tools/skill-harness/probe/probe-anchor')
  const skillBody = stripFrontmatter(await readBody(path.join(probePath, 'SKILL.md')))
  const entry = { skillPath: probePath, skillDir: probePath, skillBody }
  const skills = new Map()
  for (const cell of cells) {
    if (cell.state !== 'run') continue
    skills.set(cell.skill, entry)
  }
  return skills
}

async function main() {
  const { command, opts } = parseArgs(process.argv.slice(2))
  const index = await fs.readJson(path.join(REPO_ROOT, 'skills-index.json'))
  const matrix = await fs.readJson(path.join(here, 'matrix.json'))

  const errors = validateMatrix(matrix)
  if (errors.length) {
    console.error(errors.join('\n'))
    process.exit(1)
  }

  if (command === 'grade') {
    const runDir = path.join(os.homedir(), '.hskill/skill-harness', opts.runId)
    const declarations = new Map()
    for (const s of index.skills) {
      const decl = await loadDeclaration(REPO_ROOT, s.path)
      if (decl) declarations.set(s.path, decl)
    }
    const out = await runGrade({
      runDir, graderModel: opts.graderModel, only: opts.only, declarations,
      invoke: (prompt, model) => invokeClaudeGrader(prompt, model, {
        source: process.env,
        oauthToken: opts.baseUrl ? undefined : claudeOAuthToken(),
        baseUrl: opts.baseUrl,
        apiKey: opts.baseUrl ? process.env.MINIMAX_CN_API_KEY : undefined,
      }),
    })
    const verdicts = aggregateVerdicts(out.gradings)
    console.log(renderQualityReport({
      records: await fs.readJson(path.join(runDir, 'records.json')),
      declarations, verdicts,
      allSkills: index.skills.map(s => s.path),
      graderModel: out.graderModel, subjectModel: out.subjectModel,
    }))
    return
  }

  if (command === 'coverage') {
    const runs = await loadRuns(path.join(os.homedir(), '.hskill/skill-harness'))
    console.log(renderCoverage(buildCoverage({ runs, skills: index.skills })))
    return
  }

  // --probe：单一探针身份 × 选中的 platforms/modes（3×2=6 格），不是套着探针外壳的
  // 41 行真实 skill——cell.skill 本身就是探针身份，record/cells.json 因此天然带着
  // 正确的身份，不会被下游（coverage 的 staleness 判定等）当成真实 skill 跑过。
  // 不带 --probe：按 cell.skill 逐格解析，被测 skill 由 --skill 真正决定——
  // 这是本任务要修的缺陷：过去这里无论 --skill 传什么都硬编码成探针。
  const cells = opts.probe ? selectProbeCells(opts) : selectCells({ skills: index.skills, matrix, opts })

  const readBody = p => fs.readFile(p, 'utf8')
  const skills = opts.probe
    ? await buildProbeMap(REPO_ROOT, cells, readBody)
    : await buildSkillMap(REPO_ROOT, cells, readBody)

  const ctx = {
    model: opts.model,
    provider: opts.provider,
    baseUrl: opts.baseUrl,
    apiKey: opts.baseUrl ? process.env.MINIMAX_CN_API_KEY : undefined,
    task: opts.task ?? (opts.probe ? 'run anchor probe' : 'run skill'),
    skills,
    // 每个 skill 有自己的 contentHash——全量跑时 opts.skills 是 undefined，
    // 单个值在这里没有意义，必须查表；查表逻辑在 runner.js 的 resolveContentHash。
    contentHashMap: new Map(index.skills.map(s => [s.path, s.contentHash])),
    source: process.env,
    jailDir: '<created at run time>',
    sessionId: '00000000-0000-0000-0000-000000000000',
  }

  // claudeAdapter.jailEnv 重定向 HOME 后 claude 读不到 keychain/配置，必须显式传 token。
  // 只在 run/dry-run 才取，coverage/report 不碰 adapter，不该在没有 keychain 的机器上报错。
  if (!opts.baseUrl && command === 'run') {
    ctx.oauthToken = claudeOAuthToken()
  } else if (!opts.baseUrl && command === 'dry-run') {
    try {
      ctx.oauthToken = claudeOAuthToken()
    } catch {
      // dry-run 只是打印计划，机器上没有 keychain 条目时不该因此失败——留空即可，
      // redactEnv 输出里这一项就是缺失，而不是伪造一个假 token。
    }
  }

  if (command === 'dry-run') {
    console.log(renderDryRun(cells, ctx))
    return
  }

  if (command === 'run') {
    const { records } = await runMatrix(cells, ctx)
    console.log(renderReport({ cells, records, model: opts.model, provider: opts.provider }))
    return
  }

  if (command === 'report') {
    const runs = await loadRuns(path.join(os.homedir(), '.hskill/skill-harness'))
    const last = runs[runs.length - 1]
    if (!last) {
      console.error('no runs found')
      process.exit(1)
    }
    console.log(renderReport({ cells, records: last.records, model: opts.model, provider: opts.provider }))
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(e => {
    console.error(e.message)
    process.exit(1)
  })
}
