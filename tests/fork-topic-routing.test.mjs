import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)
const SKILL = 'skills/coding/fork-topic/SKILL.md'

test('fork-topic version and index hash are 1.1.1', async () => {
  const body = await read(SKILL)
  const entry = JSON.parse(await read('skills-index.json')).skills.find(s => s.path === 'coding/fork-topic')
  assert.match(body, /^version: ["']?1\.1\.1["']?$/m)
  assert.equal(entry.contentVersion, '1.1.1')
  assert.equal(entry.contentHash, hash(body))
})

test('fork-topic routes a think node when inside a canvas node', async () => {
  const body = await read(SKILL)
  const order = ['agent-canvas-ctl whoami', 'list-node-route-categories', 'describe-node-route-category think', 'create-routed-pty-node', '--category think']
  let last = -1
  for (const phrase of order) {
    const at = body.indexOf(phrase)
    assert.ok(at >= 0, `missing: ${phrase}`)
    assert.ok(at > last, `out of order: ${phrase}`)
    last = at
  }
  assert.ok(body.split(/^---$/m).slice(2).join('---').includes('agent-canvas-ctl send'), 'agent-canvas-ctl send')
  assert.ok(body.includes('--file'), '--file')
})

test('fork-topic keeps the fallback and named-model rules', async () => {
  const body = await read(SKILL)
  for (const phrase of ['未知子命令', 'PRECONDITION_FAILED', 'INVALID_ARGUMENT', '--task-type plan']) {
    assert.ok(body.includes(phrase), phrase)
  }
  const routed = body.indexOf('create-routed-pty-node')
  const direct = body.indexOf('create-pty-node')
  assert.ok(routed >= 0 && direct > routed, 'create-pty-node first appears after create-routed-pty-node')
})

test('fork-topic never links nodes or copies routing field standards', async () => {
  const body = await read(SKILL)
  for (const term of [
    'link-nodes', '--expect-reply',
    'openDecisions', 'precedent', 'detailDifficulty', 'impact', 'scale',
    'openness', 'informationGap', 'reasoningDepth', '## 目标', '## 问题',
  ]) assert.ok(!body.includes(term), term)
})

test('fork-topic description no longer claims text-only everywhere', async () => {
  const body = await read(SKILL)
  const description = body.match(/^description: (.*)$/m)[1]
  assert.ok(!description.includes('Text only: no files, branches, or acceptance.'))
  assert.ok(description.includes('outside a canvas node'))
})

test('fork-topic design doc limits no-dispatch to outside the canvas', async () => {
  const doc = await read('docs/superpowers/specs/2026-10-11-fork-topic-design.md')
  const start = doc.indexOf('## 边界')
  assert.ok(start >= 0)
  const next = doc.indexOf('\n## ', start + 1)
  const section = doc.slice(start, next < 0 ? undefined : next)
  assert.ok(!section.includes('不替用户派给其他 agent——只输出文本，用户自己贴'))
  assert.ok(section.includes('画布'))
})

test('fork-topic reads help only on error and spells out the routed flags', async () => {
  const body = await read(SKILL)
  assert.ok(body.includes('报错时再查 `agent-canvas-ctl help <命令>`'), 'help only on error')
  assert.ok(!body.includes('命令用法以 `agent-canvas-ctl help <命令>` 为准'), 'old help-first wording gone')
  for (const phrase of ['--params 字段=级别', '--evidence 名称=路径', '`## <段名>`']) assert.ok(body.includes(phrase), phrase)
})
