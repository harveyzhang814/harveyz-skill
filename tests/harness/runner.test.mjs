import { test } from 'node:test'
import assert from 'node:assert/strict'
import os from 'node:os'
import path from 'node:path'
import { ADAPTERS, planCell, runId, artifactDir } from '../../tools/skill-harness/runner.js'

const CTX = {
  model: 'MiniMax-M2.7',
  provider: 'minimax-cn',
  task: 'run anchor probe',
  skillBody: 'BODY TEXT',
  skillDir: '/abs/probe-anchor',
  source: { PATH: '/usr/bin' },
  oauthToken: 'tok',
  jailDir: '/tmp/skill-harness-x',
  sessionId: '11111111-1111-1111-1111-111111111111',
}

test('ADAPTERS 有且只有三个平台，键与 profile.id 一致', () => {
  assert.deepEqual(Object.keys(ADAPTERS).sort(), ['claude', 'hermes', 'pi'])
  for (const [k, a] of Object.entries(ADAPTERS)) assert.equal(a.profile.id, k)
})

test('planCell: claude native 的 argv 不含 skill 正文', () => {
  const { argv } = planCell({ platform: 'claude', mode: 'native', skill: 'probe-anchor' }, CTX)
  assert.ok(!argv.some(a => String(a).includes('BODY TEXT')))
  assert.ok(argv.includes('--setting-sources'))
})

test('planCell: claude inject 的 argv 含正文与路径补偿行', () => {
  const { argv } = planCell({ platform: 'claude', mode: 'inject', skill: 'probe-anchor' }, CTX)
  const sys = argv[argv.indexOf('--append-system-prompt') + 1]
  assert.ok(sys.includes('BODY TEXT'))
  assert.ok(sys.includes('This skill directory is: /abs/probe-anchor'))
})

test('planCell: hermes inject 把一切拼进 -z，不产生 --append-system-prompt', () => {
  const { argv } = planCell({ platform: 'hermes', mode: 'inject', skill: 'probe-anchor' }, CTX)
  assert.ok(!argv.includes('--append-system-prompt'))
  const z = argv[argv.indexOf('-z') + 1]
  assert.ok(z.includes('BODY TEXT'))
  assert.ok(z.includes('This skill directory is: /abs/probe-anchor'))
  assert.ok(z.trimEnd().endsWith('run anchor probe'))
})

test('planCell: pi native 的 argv 含 -ns，且不含正文', () => {
  const { argv } = planCell({ platform: 'pi', mode: 'native', skill: 'probe-anchor' }, CTX)
  assert.ok(argv.includes('-ns'))
  assert.ok(!argv.some(a => String(a).includes('BODY TEXT')))
})

test('planCell: env 里凭证存在但 redacted 版本已打码', () => {
  const { env, redactedEnv } = planCell({ platform: 'claude', mode: 'native', skill: 'probe-anchor' }, CTX)
  assert.equal(env.CLAUDE_CODE_OAUTH_TOKEN, 'tok')
  assert.equal(redactedEnv.CLAUDE_CODE_OAUTH_TOKEN, '***')
})

test('planCell: 模型缺失时抛错，不静默用平台默认值', () => {
  assert.throws(
    () => planCell({ platform: 'claude', mode: 'native', skill: 'probe-anchor' }, { ...CTX, model: undefined }),
    /model/,
  )
})

test('planCell 是纯函数：两次调用 argv deepEqual', () => {
  const cell = { platform: 'pi', mode: 'inject', skill: 'probe-anchor' }
  assert.deepEqual(planCell(cell, CTX).argv, planCell(cell, CTX).argv)
})

test('runId: 形如 YYYYMMDD-HHMMSS-<4 hex>', () => {
  assert.match(runId(), /^\d{8}-\d{6}-[0-9a-f]{4}$/)
})

test('artifactDir: 落在 $HOME/.hskill/skill-harness/ 下', () => {
  const d = artifactDir('20260815-101112-abcd')
  assert.equal(d, path.join(os.homedir(), '.hskill/skill-harness/20260815-101112-abcd'))
})
