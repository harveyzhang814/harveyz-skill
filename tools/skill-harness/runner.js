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
import { snapshot, diffSnapshots, harvestCell, cellDirName } from './harvest.js'

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
  const adapter = ADAPTERS[cell.platform]
  const { systemAppend, positional } = buildPrompt({
    mode: cell.mode,
    injection: adapter.profile.injection,
    skillBody: ctx.skillBody,
    skillDir: ctx.skillDir,
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
  const { dir: jailDir, cleanup } = await createJail()
  const started = Date.now()
  try {
    if (cell.platform === 'hermes') {
      await adapter.seedJail({ jailDir, hermesHome: path.join(ctx.source.HOME ?? os.homedir(), '.hermes') })
    }
    const extraArgs = cell.mode === 'native'
      ? await adapter.install({ jailDir, skillPath: ctx.skillPath })
      : []

    const plan = planCell(cell, { ...ctx, jailDir })
    const argv = [...plan.argv, ...extraArgs]

    // 采集故障不得判成 fail：before-snapshot 失败就没有基准去做差集，
    // 直接记为 harvest 失败，subprocess 仍照常跑，不影响被测方的结果。
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

    // 采集故障不得判成 fail：after-snapshot 或 harvestCell 本身出错，
    // 不能让异常逃出 runOne 把整格判丢——记成 harvest 失败，格子仍正常产出 record。
    let harvest
    if (harvestError) {
      harvest = { truncated: false, errors: [harvestError.message] }
    } else {
      try {
        const after = await snapshot(jailDir)
        harvest = await harvestCell({
          jailDir,
          destDir: path.join(runDir, 'cells', cellDirName({ ...cell, repeat: cell.repeat ?? 0 })),
          raw,
          changedFiles: diffSnapshots(before, after),
        })
      } catch (e) {
        harvest = { truncated: false, errors: [e.message] }
      }
    }

    const parsed = adapter.parse(raw, { skillName: path.basename(ctx.skillPath), skillDir: ctx.skillDir })
    return makeRecord({
      platform: cell.platform, skill: cell.skill, skillName: path.basename(ctx.skillPath),
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
      records.push(await runOne(cell, ctx, dir))
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, todo.length) }, worker))

  await fs.writeJson(path.join(dir, 'records.json'), records, { spaces: 2 })
  await fs.writeJson(path.join(dir, 'cells.json'), cells, { spaces: 2 })
  return { runId: id, dir, records }
}
