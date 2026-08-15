import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseArgs, renderDryRun } from '../../tools/skill-harness/cli.js'

test('parseArgs: 子命令识别', () => {
  assert.equal(parseArgs(['run', '--model', 'M']).command, 'run')
  assert.equal(parseArgs(['dry-run', '--model', 'M']).command, 'dry-run')
  assert.equal(parseArgs(['coverage']).command, 'coverage')
  assert.equal(parseArgs(['report']).command, 'report')
})

test('parseArgs: --skill 可重复', () => {
  const { opts } = parseArgs(['run', '--model', 'M', '--skill', 'a/b', '--skill', 'c/d'])
  assert.deepEqual(opts.skills, ['a/b', 'c/d'])
})

test('parseArgs: --platform 可重复', () => {
  const { opts } = parseArgs(['run', '--model', 'M', '--platform', 'pi', '--platform', 'claude'])
  assert.deepEqual(opts.platforms, ['pi', 'claude'])
})

test('parseArgs: --bundle 可重复', () => {
  const { opts } = parseArgs(['run', '--model', 'M', '--bundle', 'research'])
  assert.deepEqual(opts.bundles, ['research'])
})

test('parseArgs: --mode both 展开成两种模式', () => {
  assert.deepEqual(parseArgs(['run', '--model', 'M', '--mode', 'both']).opts.modes, ['native', 'inject'])
  assert.deepEqual(parseArgs(['run', '--model', 'M', '--mode', 'native']).opts.modes, ['native'])
})

test('parseArgs: --mode 缺省即 both', () => {
  assert.deepEqual(parseArgs(['run', '--model', 'M']).opts.modes, ['native', 'inject'])
})

test('parseArgs: --repeat 转成数字，缺省为 1', () => {
  assert.equal(parseArgs(['run', '--model', 'M', '--repeat', '5']).opts.repeat, 5)
  assert.equal(parseArgs(['run', '--model', 'M']).opts.repeat, 1)
})

test('parseArgs: run 缺 --model 抛错，不静默用平台默认值', () => {
  assert.throws(() => parseArgs(['run']), /--model is required/)
})

test('parseArgs: coverage 不要求 --model', () => {
  assert.doesNotThrow(() => parseArgs(['coverage']))
})

test('parseArgs: 未知平台名抛错', () => {
  assert.throws(() => parseArgs(['run', '--model', 'M', '--platform', 'cursor']), /cursor/)
})

test('renderDryRun: 打印 argv、prompt、env（打码）与 jail 写入清单', () => {
  const cells = [{ skill: 'probe-anchor', platform: 'claude', mode: 'native', state: 'run' }]
  const ctx = {
    model: 'M', provider: 'P', task: 'go', skillBody: 'BODY', skillDir: '/abs/probe-anchor',
    skillPath: '/abs/probe-anchor', source: { PATH: '/usr/bin' }, oauthToken: 'SECRET',
    jailDir: '/tmp/skill-harness-x', sessionId: '11111111-1111-1111-1111-111111111111',
  }
  const out = renderDryRun(cells, ctx)
  assert.ok(out.includes('claude/native'))
  assert.ok(out.includes('--setting-sources'))
  assert.ok(out.includes('/tmp/skill-harness-x/.claude/skills/probe-anchor'))
  assert.ok(out.includes('***'))
  assert.ok(!out.includes('SECRET'))
})

test('renderDryRun: native 模式明确标出正文不在 prompt 里', () => {
  const cells = [{ skill: 'probe-anchor', platform: 'claude', mode: 'native', state: 'run' }]
  const ctx = { model: 'M', provider: 'P', task: 'go', skillBody: 'BODYTEXT', skillDir: '/d', skillPath: '/d', source: {}, jailDir: '/tmp/skill-harness-x', sessionId: 's' }
  const out = renderDryRun(cells, ctx)
  assert.ok(!out.includes('BODYTEXT'))
  assert.ok(/loaded natively/i.test(out))
})

test('renderDryRun: 只渲染 state 为 run 的格子', () => {
  const cells = [
    { skill: 'a', platform: 'claude', mode: 'native', state: 'not-run' },
    { skill: 'b', platform: 'pi', mode: 'native', state: 'run' },
  ]
  const ctx = { model: 'M', provider: 'P', task: 'go', skillBody: 'B', skillDir: '/d', skillPath: '/d', source: {}, jailDir: '/tmp/skill-harness-x', sessionId: 's' }
  const out = renderDryRun(cells, ctx)
  assert.ok(out.includes('pi/native'))
  assert.ok(!out.includes('claude/native'))
})
