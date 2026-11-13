import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')

// step6 = SKILL.md 中 '6. **建执行节点**' 到 '7. **落库**' 之间的文本
async function step6() {
  const body = await read('skills/coding/handoff/SKILL.md')
  const start = body.indexOf('6. **建执行节点**')
  const end = body.indexOf('7. **落库**')
  assert.ok(start > 0 && end > start, 'step 6 boundaries found')
  return body.slice(start, end)
}

test('author step 6 creates the receiver node through the routing engine', async () => {
  const s = await step6()
  const order = ['list-node-route-categories', 'describe-node-route-category develop', 'create-routed-pty-node', '--category develop']
  let last = -1
  for (const phrase of order) {
    const at = s.indexOf(phrase)
    assert.ok(at >= 0, `missing: ${phrase}`)
    assert.ok(at > last, `out of order: ${phrase}`)
    last = at
  }
})

test('step 6 keeps create-pty-node only as the fallback', async () => {
  const s = await step6()
  const routed = s.indexOf('create-routed-pty-node')
  const direct = s.indexOf('create-pty-node')
  assert.ok(routed >= 0 && direct > routed, 'create-pty-node first appears after create-routed-pty-node')
  for (const phrase of ['未知子命令', 'PRECONDITION_FAILED', 'INVALID_ARGUMENT', '--task-type execute']) {
    assert.ok(s.includes(phrase), phrase)
  }
})

test('handoff body does not copy routing field standards', async () => {
  const body = await read('skills/coding/handoff/SKILL.md')
  for (const term of [
    'openDecisions', 'precedent', 'detailDifficulty', 'impact', 'scale',
    'openness', 'informationGap', 'reasoningDepth', '## 目标', '## 问题',
  ]) assert.ok(!body.includes(term), term)
})

test('dispatch message in step 9 stays addressing-only', async () => {
  const body = await read('skills/coding/handoff/SKILL.md')
  const start = body.indexOf('9. **派发**')
  assert.ok(start > 0)
  assert.ok(body.slice(start).includes('只放寻址信息，不放文档内容摘要'))
})

test('step 6 supports a named model and bounds the INVALID_ARGUMENT retry', async () => {
  const s = await step6()
  assert.ok(s.includes('--model'), '--model')
  assert.ok(s.includes('最多重试两次'), 'retry limit')
})

test('step 6 reads help only on error and spells out the routed flags', async () => {
  const s = await step6()
  assert.ok(s.includes('报错时再查 `agent-canvas-ctl help <命令>`'), 'help only on error')
  assert.ok(!s.includes('命令用法以 `agent-canvas-ctl help <命令>` 为准'), 'old help-first wording gone')
  for (const phrase of ['--params 字段=级别', '--evidence 名称=路径', '`## <段名>`']) assert.ok(s.includes(phrase), phrase)
})
