import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import crypto from 'node:crypto'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { claudeAdapter } from './adapters/claude.js'
import { piAdapter } from './adapters/pi.js'
import { hermesAdapter } from './adapters/hermes.js'
import { buildPrompt } from './prompt.js'
import { makeRecord } from './record.js'
import { createJail, redactEnv } from './jail.js'

const execFileAsync = promisify(execFile)

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

async function runOne(cell, ctx) {
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

    let stdout = ''
    let stderr = ''
    let exitCode = 0
    try {
      const r = await execFileAsync(BIN[cell.platform], argv, {
        cwd: jailDir, env: plan.env, maxBuffer: 64 * 1024 * 1024, timeout: ctx.timeoutMs ?? 300000,
      })
      stdout = r.stdout
      stderr = r.stderr
    } catch (e) {
      stdout = e.stdout ?? ''
      stderr = e.stderr ?? String(e.message)
      exitCode = e.code ?? 1
    }

    let raw = stdout
    const collected = adapter.collect ? adapter.collect() : null
    if (collected === null && cell.platform === 'hermes') {
      const list = await execFileAsync(BIN.hermes, ['sessions', 'list'], { cwd: jailDir, env: plan.env }).catch(() => ({ stdout: '' }))
      const sid = adapter.parseSessionId(list.stdout)
      if (sid) {
        const exp = await execFileAsync(BIN.hermes, adapter.collectArgs(sid), { cwd: jailDir, env: plan.env, maxBuffer: 64 * 1024 * 1024 }).catch(() => ({ stdout: '' }))
        raw = exp.stdout || stdout
      }
    }

    const parsed = adapter.parse(raw, { skillName: path.basename(ctx.skillPath), skillDir: ctx.skillDir })
    return makeRecord({
      platform: cell.platform, skill: cell.skill, skillName: path.basename(ctx.skillPath),
      contentHash: resolveContentHash(ctx, cell.skill),
      task: ctx.task, repeat: cell.repeat ?? 0, mode: cell.mode,
      requestedModel: ctx.model, durationMs: Date.now() - started,
      exitCode, stderr, parsed,
    })
  } finally {
    await cleanup()
  }
}

export async function runMatrix(cells, ctx) {
  const todo = cells.filter(c => c.state === 'run')
  const limit = ctx.concurrency ?? 3
  const records = []
  let i = 0
  async function worker() {
    while (i < todo.length) {
      const cell = todo[i++]
      records.push(await runOne(cell, ctx))
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, todo.length) }, worker))

  const id = ctx.runId ?? runId()
  const dir = artifactDir(id)
  await fs.ensureDir(dir)
  await fs.writeJson(path.join(dir, 'records.json'), records, { spaces: 2 })
  await fs.writeJson(path.join(dir, 'cells.json'), cells, { spaces: 2 })
  return { runId: id, dir, records }
}
