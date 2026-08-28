import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import crypto from 'node:crypto'
import { spawn } from 'node:child_process'
import { claudeAdapter } from './adapters/claude.js'
import { piAdapter } from './adapters/pi.js'
import { hermesAdapter } from './adapters/hermes.js'
import { buildPrompt } from './prompt.js'
import { makeRecord } from './record.js'
import { createJail, redactEnv } from './jail.js'
import { snapshot, diffSnapshots, harvestCell, cellDirName, mergeHarvest } from './harvest.js'

export const ADAPTERS = { claude: claudeAdapter, pi: piAdapter, hermes: hermesAdapter }

const BIN = { claude: 'claude', pi: 'pi', hermes: 'hermes' }

// 打了 code: 'SKILL_NOT_FOUND' 的判据，让 runMatrix 的 worker 能只兜底这一种错误——
// 别的异常（我们自己代码里的真 bug）必须原样冒出去，不能被读成"这格测试失败了"。
export function skillNotFoundError(skill) {
  const err = new Error(`no skill entry for "${skill}" in ctx.skills — refusing to fall back to the probe`)
  err.code = 'SKILL_NOT_FOUND'
  return err
}

export function runId() {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
  return `${stamp}-${crypto.randomBytes(2).toString('hex')}`
}

export function artifactDir(id) {
  return path.join(os.homedir(), '.hskill/skill-harness', id)
}

// 纯函数。dry-run 直接消费它，因此不许有任何副作用。
export function planCell(cell, ctx) {
  if (!ctx.model) throw new Error('model is required — refusing to fall back to the platform default, which would confound platform with model')
  const entry = ctx.skills?.get(cell.skill)
  if (!entry) throw skillNotFoundError(cell.skill)
  const adapter = ADAPTERS[cell.platform]
  // cell.task 优先——每个 eval 场景带着自己的 prompt；ctx.task 只是没有
  // cell.task 时的兜底（探针格子、老测试手搭的 cell）。
  const { systemAppend, positional } = buildPrompt({
    mode: cell.mode,
    injection: adapter.profile.injection,
    skillBody: entry.skillBody,
    skillDir: entry.skillDir,
    compensation: adapter.compensation,
    task: cell.task ?? ctx.task,
  })

  const env = adapter.jailEnv({
    jailDir: ctx.jailDir, source: ctx.source,
    oauthToken: ctx.oauthToken, baseUrl: ctx.baseUrl, apiKey: ctx.apiKey,
  })

  const argv = adapter.args({
    model: ctx.model, provider: ctx.provider,
    systemAppend, positional,
    jailDir: ctx.jailDir, sessionId: ctx.sessionId,
  })

  return { argv, env, redactedEnv: redactEnv(env), systemAppend, positional }
}

// 纯函数。矩阵跑全量时每个 skill 有自己的 contentHash，不能用单个 run-wide 值——
// 否则 coverage.js 的 staleness 判定永远拿不到匹配值，每格都会被判成过期。
export function resolveContentHash(ctx, skill) {
  return ctx.contentHashMap?.get(skill) ?? null
}

// `pi` (v0.82.1) hangs indefinitely when its stdout/stderr are plain OS pipes
// (Node's default child_process stdio) — confirmed by direct reproduction.
// Redirecting to real files instead of pipes sidesteps the hang, so every
// platform's subprocess goes through this file-backed capture uniformly.
// Files are read back only once, after the process has already exited, so
// there's no unbounded-memory-while-still-running risk the way pipe
// buffering had — the old `maxBuffer` cap is no longer needed.
function runCaptured(bin, argv, { cwd, env, timeoutMs, outPath, errPath }) {
  return new Promise(resolve => {
    let outFd
    let errFd
    try {
      outFd = fs.openSync(outPath, 'w')
      errFd = fs.openSync(errPath, 'w')
    } catch (err) {
      resolve({ stdout: '', stderr: String(err.message), code: 1 })
      return
    }

    const spawnOpts = { cwd, env, stdio: ['ignore', outFd, errFd] }
    if (timeoutMs != null) {
      spawnOpts.timeout = timeoutMs
      spawnOpts.killSignal = 'SIGTERM'
    }
    const child = spawn(bin, argv, spawnOpts)

    let settled = false
    const finish = (code, errMessage) => {
      if (settled) return
      settled = true
      try { fs.closeSync(outFd) } catch { /* already closed */ }
      try { fs.closeSync(errFd) } catch { /* already closed */ }
      let stdout = ''
      let stderr = ''
      try { stdout = fs.readFileSync(outPath, 'utf8') } catch { /* nothing written */ }
      try { stderr = fs.readFileSync(errPath, 'utf8') } catch { /* nothing written */ }
      resolve({ stdout, stderr: errMessage ?? stderr, code: code ?? 1 })
    }
    // 'close' fires after the stdio streams (our file fds) have finished —
    // safer than 'exit' for making sure the file writes are flushed.
    child.on('close', code => finish(code))
    child.on('error', err => finish(1, String(err.message)))
  })
}

async function runOne(cell, ctx, runDir) {
  const adapter = ADAPTERS[cell.platform]
  // 查表放在建 jail 之前：查不到就没必要浪费一次 jail 创建，
  // 点名该 skill 抛出去，由 runMatrix 的 worker 兜底记成这一格的失败 record。
  const entry = ctx.skills?.get(cell.skill)
  if (!entry) throw skillNotFoundError(cell.skill)
  const { dir: jailDir, cleanup } = await createJail()
  const started = Date.now()
  try {
    if (cell.platform === 'hermes') {
      await adapter.seedJail({ jailDir, hermesHome: path.join(ctx.source.HOME ?? os.homedir(), '.hermes') })
    }
    const extraArgs = cell.mode === 'native'
      ? await adapter.install({ jailDir, skillPath: entry.skillPath })
      : []

    const plan = planCell(cell, { ...ctx, jailDir })
    const argv = [...plan.argv, ...extraArgs]

    // 采集故障不得判成 fail：before-snapshot 失败就没有基准去做差集，
    // 但 transcript 不依赖这个基准——错误信息留到下面并入 harvest.errors，
    // diff 步骤退化成空 changedFiles，subprocess 仍照常跑。
    let harvestError = null
    let before = new Map()
    try {
      before = await snapshot(jailDir)
    } catch (e) {
      harvestError = e
    }

    const r = await runCaptured(BIN[cell.platform], argv, {
      cwd: jailDir, env: plan.env, timeoutMs: ctx.timeoutMs ?? 300000,
      outPath: path.join(jailDir, 'stdout.log'), errPath: path.join(jailDir, 'stderr.log'),
    })
    const stdout = r.stdout
    const stderr = r.stderr
    const exitCode = r.code ?? 1

    let raw = stdout
    const collected = adapter.collect ? adapter.collect() : null
    if (collected === null && cell.platform === 'hermes') {
      const list = await runCaptured(BIN.hermes, ['sessions', 'list'], {
        cwd: jailDir, env: plan.env,
        outPath: path.join(jailDir, 'hermes-list-stdout.log'), errPath: path.join(jailDir, 'hermes-list-stderr.log'),
      })
      const sid = adapter.parseSessionId(list.stdout)
      if (sid) {
        const exp = await runCaptured(BIN.hermes, adapter.collectArgs(sid), {
          cwd: jailDir, env: plan.env,
          outPath: path.join(jailDir, 'hermes-export-stdout.log'), errPath: path.join(jailDir, 'hermes-export-stderr.log'),
        })
        raw = exp.stdout || stdout
      }
    }

    // transcript 是唯一花钱重跑模型也换不回来的证据，不能因为 snapshot 失败
    // 就连它一起丢掉：无论 before/after snapshot 是否成功，harvestCell 始终
    // 要被调用——它内部先写 transcript，再处理 changedFiles；snapshot 拿不到
    // 基准就退化成空 changedFiles（只丢差集，不丢 transcript），snapshot 的
    // 错误信息并入 harvest.errors，不让异常逃出 runOne 把整格判丢。
    const destDir = path.join(runDir, 'cells', cellDirName({ ...cell, repeat: cell.repeat ?? 0 }))
    const snapshotErrors = harvestError ? [harvestError.message] : []
    let changedFiles = []
    if (!harvestError) {
      try {
        const after = await snapshot(jailDir)
        changedFiles = diffSnapshots(before, after, cell.platform)
      } catch (e) {
        snapshotErrors.push(e.message)
      }
    }

    let harvest
    try {
      const result = await harvestCell({ jailDir, destDir, raw, changedFiles })
      harvest = mergeHarvest(snapshotErrors, result)
    } catch (e) {
      harvest = mergeHarvest(snapshotErrors, null, e.message)
    }

    const parsed = adapter.parse(raw, { skillName: path.basename(entry.skillPath), skillDir: entry.skillDir })
    return makeRecord({
      platform: cell.platform, skill: cell.skill, skillName: path.basename(entry.skillPath),
      contentHash: resolveContentHash(ctx, cell.skill),
      // task/evalId 来自 cell，不是 ctx：这一格实际收到的任务文案就是它自己
      // 的 eval prompt（或没有声明时的默认任务），record 必须如实记它，grade
      // 阶段拼 prompt 时才不用回头猜"当时到底给了什么任务"。
      task: cell.task ?? ctx.task, evalId: cell.evalId, repeat: cell.repeat ?? 0, mode: cell.mode,
      requestedModel: ctx.model, durationMs: Date.now() - started,
      exitCode, stderr, parsed, harvest,
    })
  } finally {
    await cleanup()
  }
}

export async function runMatrix(cells, ctx) {
  const todo = cells.filter(c => c.state === 'run')
  const limit = ctx.concurrency ?? 3
  const id = ctx.runId ?? runId()
  const dir = artifactDir(id)
  await fs.ensureDir(dir)

  const records = []
  let i = 0
  async function worker() {
    while (i < todo.length) {
      const cell = todo[i++]
      // 只兜底 SKILL_NOT_FOUND（例如 ctx.skills 里查不到 cell.skill）——那是一格
      // 自己的资格问题，落成这一格的失败 record，其余格子照常跑。别的异常必须
      // 原样冒出去：它们经过 createJail / adapter.seedJail / adapter.install /
      // harness 自身的 finally 清理，是我们代码里的真 bug，不是"这个平台跑这个
      // skill 失败了"——两者若被同一个 exitCode/stderr 表示，报告和 quality-report
      // 就无法区分，等于把本任务要修的缺陷换了个地方重犯。
      try {
        records.push(await runOne(cell, ctx, dir))
      } catch (e) {
        if (e.code !== 'SKILL_NOT_FOUND') throw e
        records.push(makeRecord({
          platform: cell.platform, skill: cell.skill, skillName: null,
          contentHash: resolveContentHash(ctx, cell.skill),
          task: cell.task ?? ctx.task, evalId: cell.evalId, repeat: cell.repeat ?? 0, mode: cell.mode,
          requestedModel: ctx.model, durationMs: 0,
          exitCode: 1, stderr: e.message, parsed: null, harvest: null,
        }))
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, todo.length) }, worker))

  await fs.writeJson(path.join(dir, 'records.json'), records, { spaces: 2 })
  await fs.writeJson(path.join(dir, 'cells.json'), cells, { spaces: 2 })
  return { runId: id, dir, records }
}
