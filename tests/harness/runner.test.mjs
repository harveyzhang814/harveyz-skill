import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { ADAPTERS, planCell, runId, artifactDir, resolveContentHash, runMatrix } from '../../tools/skill-harness/runner.js'
import { selectProbeCells, PROBE_SKILL } from '../../tools/skill-harness/select.js'

const CTX = {
  model: 'MiniMax-M2.7',
  provider: 'minimax-cn',
  task: 'run anchor probe',
  skills: new Map([['probe-anchor', { skillPath: '/abs/probe-anchor', skillDir: '/abs/probe-anchor', skillBody: 'BODY TEXT' }]]),
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

test('planCell: cell.skill 在 ctx.skills 里查不到时点名抛错，不回落到探针，且带 SKILL_NOT_FOUND 判据', () => {
  assert.throws(
    () => planCell({ platform: 'claude', mode: 'native', skill: 'mint/does-not-exist' }, CTX),
    err => /mint\/does-not-exist/.test(err.message) && err.code === 'SKILL_NOT_FOUND',
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

test('resolveContentHash: 按 skill 从 contentHashMap 里查，不是全局单值', () => {
  const map = new Map([['a/b', 'hash-a'], ['c/d', 'hash-c']])
  assert.equal(resolveContentHash({ contentHashMap: map }, 'a/b'), 'hash-a')
  assert.equal(resolveContentHash({ contentHashMap: map }, 'c/d'), 'hash-c')
})

test('resolveContentHash: 查不到的 skill 或缺失的 map 给 null 而非伪造', () => {
  const map = new Map([['a/b', 'hash-a']])
  assert.equal(resolveContentHash({ contentHashMap: map }, 'unknown/skill'), null)
  assert.equal(resolveContentHash({}, 'a/b'), null)
})

test('runMatrix: 非 SKILL_NOT_FOUND 的错误（我们代码里的真 bug）必须冒出 runMatrix，不能被 worker 吞成这一格的失败 record——否则一个 TypeError 会被读成"这个平台跑这个 skill 失败了"', async () => {
  const runIdForTest = 'test-runmatrix-real-bug-propagates'
  const cells = [{ skill: 'probe-anchor', platform: 'hermes', mode: 'native', state: 'run', repeat: 0 }]
  const ctx = {
    model: 'M',
    task: 'go',
    skills: new Map([['probe-anchor', { skillPath: '/abs/probe-anchor', skillDir: '/abs/probe-anchor', skillBody: 'B' }]]),
    // 故意不给 ctx.source：hermes 的 seedJail 会在 `ctx.source.HOME` 上抛 TypeError——
    // 这是我们自己代码的 bug，不是 SKILL_NOT_FOUND，必须原样冒出去。
    runId: runIdForTest,
  }
  try {
    await assert.rejects(() => runMatrix(cells, ctx), TypeError)
  } finally {
    await fs.remove(artifactDir(runIdForTest))
  }
})

test('probe 模式：cells 的 skill 字段是探针身份，contentHash 解析永远是 null——不能让探针跑的记录顶替任何真实 skill 的账，这正是本任务要移除的谎言在持久化状态里的翻版', () => {
  const cells = selectProbeCells({})
  assert.equal(cells.length, 6) // 3 平台 × 2 模式
  assert.ok(cells.every(c => c.skill === PROBE_SKILL))
  assert.ok(cells.every(c => c.skill !== 'mint/learn-skill' && c.skill !== 'creative/capture-todo'))

  // 模拟 cli.js 里 ctx.contentHashMap 的构造方式：整张真实 skills-index.json 的表。
  const fakeIndexSkills = [
    { path: 'mint/learn-skill', contentHash: 'hash-a' },
    { path: 'creative/capture-todo', contentHash: 'hash-b' },
  ]
  const contentHashMap = new Map(fakeIndexSkills.map(s => [s.path, s.contentHash]))
  for (const c of cells) {
    assert.equal(resolveContentHash({ contentHashMap }, c.skill), null)
  }
})
