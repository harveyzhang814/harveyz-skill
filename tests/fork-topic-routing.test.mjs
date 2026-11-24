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

test('fork-topic version and index hash are 1.2.0', async () => {
  const body = await read(SKILL)
  const entry = JSON.parse(await read('skills-index.json')).skills.find(s => s.path === 'coding/fork-topic')
  assert.match(body, /^version: ["']?1\.2\.0["']?$/m)
  assert.equal(entry.contentVersion, '1.2.0')
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

test('fork-topic never uses expect-reply or copies routing field standards', async () => {
  const body = await read(SKILL)
  for (const term of [
    '--expect-reply',
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

test('fork-topic links waits-for before send only when a return is requested', async () => {
  const body = await read(SKILL)
  const link = body.indexOf('--type waits-for')
  const send = body.indexOf('agent-canvas-ctl send')
  assert.ok(link >= 0, '--type waits-for')
  assert.ok(send >= 0, 'agent-canvas-ctl send')
  assert.ok(link < send, 'waits-for link comes before send')
  const paragraphs = body.split(/\n\s*\n/)
  assert.ok(paragraphs.some(p => p.includes('交回要求') && p.includes('waits-for')), '交回要求 and waits-for in one paragraph')
  assert.ok(body.includes('没有交回要求就不连边'), 'no link without a return request')
  assert.ok(body.includes('记下返回的 `relationId`'), 'records relationId')
})

test('fork-topic handles a refused send', async () => {
  const body = await read(SKILL)
  for (const phrase of ['APPROVAL_DENIED', 'APPROVAL_TIMEOUT', '消息未发出', '可粘贴 prompt', '不重试']) {
    assert.ok(body.includes(phrase), phrase)
  }
  assert.ok(body.includes('不得声称消息已发出'), 'no claim of delivery')
  assert.ok(body.includes('不得给出 `messageId`'), 'no messageId when refused')
  assert.ok(body.includes('仅 `send` 成功时'), 'step 6 only on success')
  assert.ok(body.includes('等待边已保留'), 'wait edge kept after refusal')
  assert.ok(body.includes('未成功'), 'unified send-failed branch')
  assert.ok(body.includes('以 stderr 文本为准'), 'classify by stderr text, codes are supplementary')
  const lines = body.split('\n')
  const notExecuted = lines.find(l => l.includes('明确未执行') && l.includes('请勿重试'))
  assert.ok(notExecuted, 'not-executed class line keyed on 请勿重试')
  for (const phrase of ['被用户拒绝', '审批超时', '被策略规则', 'INVALID_ARGUMENT', 'PRECONDITION_FAILED', 'NOT_APPLICABLE', 'TARGET_NOT_FOUND', '节点已建、消息未发出', '贴进新节点']) {
    assert.ok(notExecuted.includes(phrase), `not-executed class: ${phrase}`)
  }
  const unknown = lines.find(l => l.includes('OUTCOME_UNKNOWN') && l.includes('结果不明'))
  assert.ok(unknown, 'unknown-outcome class line')
  for (const phrase of ['EXECUTION_FAILED', '看不出类别', '结果未知', '先到新节点核对', '确认没收到再贴', '不自动重发']) {
    assert.ok(unknown.includes(phrase), `unknown-outcome class: ${phrase}`)
  }
  assert.ok(unknown.includes('代码块外') && unknown.includes('不写进 prompt'), '确认没收到再贴 lives outside the paste-ready prompt')
  assert.ok(!notExecuted.includes('EXECUTION_FAILED'), 'EXECUTION_FAILED is not "not executed"')
  assert.ok(!notExecuted.includes('OUTCOME_UNKNOWN'), 'OUTCOME_UNKNOWN is not "not executed"')
  assert.ok(body.includes('结果不明时先确认没收到'), 'wait-edge hint is conditional')
})

test('fork-topic mentions resolve-wait', async () => {
  const body = await read(SKILL)
  assert.ok(body.includes('resolve-wait'))
  assert.ok(body.includes('不自动解除'), 'never auto-resolves')
  assert.ok(body.includes('经用户同意'), 'needs user consent')
  assert.ok(!/resolve-wait\s+<[^>]+>/.test(body), 'no angle-bracket placeholder after resolve-wait')
})
