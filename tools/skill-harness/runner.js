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
  if (!entry) throw new Error(`no skill entry for "${cell.skill}" in ctx.skills — refusing to fall back to the probe`)
  const adapter = ADAPTERS[cell.platform]
  const { systemAppend, positional } = buildPrompt({
    mode: cell.mode,
    injection: adapter.profile.injection,
    skillBody: entry.skillBody,
    skillDir: entry.skillDir,
    compensation: adapter.compensation,
    task: ctx.task,
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
  if (!entry) throw new Error(`no skill entry for "${cell.skill}" in ctx.skills — refusing to fall back to the probe`)
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
        changedFiles = diffSnapshots(before, after)
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
      task: ctx.task, repeat: cell.repeat ?? 0, mode: cell.mode,
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
      // runOne 抛出的错误（例如 ctx.skills 里查不到 cell.skill）不能让整轮 Promise.all
      // 崩掉——那样一个格子的问题会连累所有已经跑完/还没跑的格子。落成这一格自己的
      // 失败 record，错误信息点名 cell.skill，其余格子照常跑。
      try {
        records.push(await runOne(cell, ctx, dir))
      } catch (e) {
        records.push(makeRecord({
          platform: cell.platform, skill: cell.skill, skillName: null,
          contentHash: resolveContentHash(ctx, cell.skill),
          task: ctx.task, repeat: cell.repeat ?? 0, mode: cell.mode,
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
