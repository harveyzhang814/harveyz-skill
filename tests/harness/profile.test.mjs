import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PROFILES, piProfile } from '../../tools/skill-harness/profiles.js'

// 整表 deepEqual，不是三个独立 equal。失败时一次看到全表；
// 新增平台必然让这些断言变红，强制作者来这里登记。这是注册表守卫模式。

test('L1: id 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.id), ['claude', 'pi', 'hermes'])
})

test('L1: skillChannel 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.skillChannel), ['skill-dir', 'explicit-flag', 'skill-dir'])
})

test('L1: builtinSkillFloor 整表（2026-08-14 实测，变了必须重新实测再改）', () => {
  assert.deepEqual(PROFILES.map(p => p.builtinSkillFloor), [15, 0, 0])
})

test('L1: injection 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.injection), ['append-system-prompt', 'append-system-prompt', 'prompt-only'])
})

test('L1: processChannel 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.processChannel), ['inline', 'inline', 'collect'])
})

test('L1: transcriptFormat 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.transcriptFormat), ['claude-code-jsonl', 'pi-jsonl', 'claude-code-jsonl'])
})

test('L1: compensation 逐字整表', () => {
  assert.deepEqual(PROFILES.map(p => p.compensation), ['', '', ''])
})

test('L1: capabilities 整表', () => {
  assert.deepEqual(
    PROFILES.map(p => [...p.capabilities].sort()),
    [
      ['cost-cap', 'structured-output', 'system-prompt-append', 'tool-allowlist', 'tool-trace', 'usage'],
      ['structured-output', 'system-prompt-append', 'tool-allowlist', 'tool-trace', 'usage'],
      ['structured-output', 'tool-allowlist', 'tool-trace', 'usage'],
    ],
  )
})

test('L1: isolation 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.isolation), [
    ['HOME', 'CLAUDE_CONFIG_DIR', '--setting-sources user'],
    ['-ns', '-ne', '-np', '--no-themes', '-nc', '--session-dir'],
    ['HOME', '--safe-mode'],
  ])
})

test('每个 profile 的字段集合一致', () => {
  const keys = PROFILES.map(p => Object.keys(p).sort().join(','))
  assert.equal(new Set(keys).size, 1, `profiles have divergent field sets: ${keys.join(' | ')}`)
})

test('每个 profile 都要声明 artifactChannel——捞不捞得到产出物决定质量断言能不能判', () => {
  for (const p of PROFILES) {
    assert.ok(['jail', 'none'].includes(p.artifactChannel), `${p.id} 缺 artifactChannel`)
  }
})

test('pi 未重定向 HOME，故 artifactChannel 为 none——产出物类断言对 pi 只能判 unavailable', () => {
  assert.equal(piProfile.artifactChannel, 'none')
})
