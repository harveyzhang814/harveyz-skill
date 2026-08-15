import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { runMatrix } from '../../tools/skill-harness/runner.js'
import { stripFrontmatter } from '../../tools/skill-harness/prompt.js'
import { claudeOAuthToken, readEnvFile } from '../../tools/skill-harness/jail.js'

const ENABLED = process.env.SKILL_HARNESS_E2E === '1'
const MODEL = process.env.SKILL_HARNESS_MODEL ?? 'MiniMax-M2.7'
const PROVIDER = process.env.SKILL_HARNESS_PROVIDER ?? 'minimax-cn'
const BASE_URL = 'https://api.minimaxi.com/anthropic'

const SKILL_PATH = path.resolve('tools/skill-harness/probe/probe-anchor')

// claude 的 16 个内置 skill 不算宿主泄漏——jail 挡不住它们，这是已知不对称。
const CLAUDE_BUILTINS = new Set([
  'deep-research', 'design-sync', 'dataviz', 'update-config', 'verify', 'debug',
  'code-review', 'simplify', 'batch', 'fewer-permission-prompts', 'doctor',
  'loop', 'schedule', 'claude-api', 'run', 'run-skill-generator',
])

async function baseCtx() {
  return {
    model: MODEL,
    provider: PROVIDER,
    baseUrl: BASE_URL,
    apiKey: readEnvFile(path.join(os.homedir(), '.hermes/.env')).MINIMAX_CN_API_KEY,
    oauthToken: claudeOAuthToken(),
    task: 'run anchor probe',
    skillPath: SKILL_PATH,
    skillDir: SKILL_PATH,
    skillBody: stripFrontmatter(await fs.readFile(path.join(SKILL_PATH, 'SKILL.md'), 'utf8')),
    source: process.env,
    sessionId: '00000000-0000-0000-0000-000000000000',
    concurrency: 3,
  }
}

function cells(mode, task) {
  return ['claude', 'pi', 'hermes'].map(platform => ({
    skill: 'probe-anchor', platform, mode, state: 'run', repeat: 0, task,
  }))
}

test('E2E native: 三平台都读到 references/token.md', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('native'), await baseCtx())
  assert.equal(records.length, 3)
  for (const r of records) {
    assert.ok(r.reply.includes('ANCHOR-7F3A9C'), `${r.platform}: FILE unreachable — ${r.reply}`)
    assert.ok(r.reply.includes('BODY-4B21E8'), `${r.platform}: BODY missing`)
  }
})

test('E2E native: 三平台 triggered 都为 true', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('native'), await baseCtx())
  for (const r of records) assert.equal(r.triggered, true, `${r.platform}: skill not triggered`)
})

test('E2E inject: 带路径补偿行时三平台也都读到', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('inject'), await baseCtx())
  for (const r of records) {
    assert.ok(r.reply.includes('ANCHOR-7F3A9C'), `${r.platform}: compensation line failed to restore the anchor`)
  }
})

test('E2E native + 非触发 prompt: 三平台 triggered 都为 false', { skip: !ENABLED }, async () => {
  const ctx = { ...(await baseCtx()), task: 'what is 2+2? answer with just the number' }
  const { records } = await runMatrix(cells('native'), ctx)
  for (const r of records) assert.equal(r.triggered, false, `${r.platform}: skill fired on a non-matching prompt`)
})

test('E2E L3: 宿主 skill 不可见', { skip: !ENABLED }, async () => {
  const hostDirs = [
    path.join(os.homedir(), '.claude/skills'),
    path.join(os.homedir(), '.hermes/skills'),
    path.join(os.homedir(), '.pi/agent/skills'),
  ]
  const hostSkills = new Set()
  for (const d of hostDirs) {
    if (!await fs.pathExists(d)) continue
    for (const n of await fs.readdir(d)) if (!CLAUDE_BUILTINS.has(n)) hostSkills.add(n)
  }
  assert.ok(hostSkills.size > 0, 'expected the host to have skills installed, otherwise this assertion is vacuous')

  const { records } = await runMatrix(cells('native'), await baseCtx())
  for (const r of records) {
    const seen = new Set([...(r.toolCalls ?? []).map(t => JSON.stringify(t.args)), r.reply].join(' ').match(/[a-z0-9-]+/g) ?? [])
    for (const name of hostSkills) {
      assert.ok(!seen.has(name), `jail breach: ${r.platform} saw host skill '${name}'; the run's result is not attributable to the skill under test`)
    }
  }
})

test('E2E: claude 的 builtinSkillFloor 实测值仍是 16', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('native'), await baseCtx())
  const claude = records.find(r => r.platform === 'claude')
  assert.equal(claude.builtinSkillFloor, 16, 'upstream changed its builtin skill set — update profiles.js and the L1 snapshot')
})

test('E2E: 三平台实测 model 与请求一致', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('native'), await baseCtx())
  for (const r of records) {
    assert.equal(r.modelMismatch, false, `${r.platform}: requested ${MODEL}, got ${r.model}`)
  }
})
