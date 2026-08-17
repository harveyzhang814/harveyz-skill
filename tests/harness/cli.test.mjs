import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseArgs, renderDryRun, buildSkillMap, buildProbeMap } from '../../tools/skill-harness/cli.js'

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
    model: 'M', provider: 'P', task: 'go',
    skills: new Map([['probe-anchor', { skillBody: 'BODY', skillDir: '/abs/probe-anchor', skillPath: '/abs/probe-anchor' }]]),
    source: { PATH: '/usr/bin' }, oauthToken: 'SECRET',
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
  const ctx = {
    model: 'M', provider: 'P', task: 'go',
    skills: new Map([['probe-anchor', { skillBody: 'BODYTEXT', skillDir: '/d', skillPath: '/d' }]]),
    source: {}, jailDir: '/tmp/skill-harness-x', sessionId: 's',
  }
  const out = renderDryRun(cells, ctx)
  assert.ok(!out.includes('BODYTEXT'))
  assert.ok(/loaded natively/i.test(out))
})

test('renderDryRun: 只渲染 state 为 run 的格子', () => {
  const cells = [
    { skill: 'a', platform: 'claude', mode: 'native', state: 'not-run' },
    { skill: 'b', platform: 'pi', mode: 'native', state: 'run' },
  ]
  const ctx = {
    model: 'M', provider: 'P', task: 'go',
    skills: new Map([['b', { skillBody: 'B', skillDir: '/d', skillPath: '/d' }]]),
    source: {}, jailDir: '/tmp/skill-harness-x', sessionId: 's',
  }
  const out = renderDryRun(cells, ctx)
  assert.ok(out.includes('pi/native'))
  assert.ok(!out.includes('claude/native'))
})

test('renderDryRun: 两个不同 skill 的 dry-run 输出——路径（native）与正文（inject）都不同', () => {
  const cells = [
    { skill: 'mint/learn-skill', platform: 'claude', mode: 'native', state: 'run' },
    { skill: 'mint/learn-skill', platform: 'claude', mode: 'inject', state: 'run' },
    { skill: 'research/capture-todo', platform: 'claude', mode: 'native', state: 'run' },
    { skill: 'research/capture-todo', platform: 'claude', mode: 'inject', state: 'run' },
  ]
  const ctx = {
    model: 'M', provider: 'P', task: 'go',
    skills: new Map([
      ['mint/learn-skill', { skillBody: 'LEARN-SKILL BODY', skillDir: '/repo/skills/mint/learn-skill', skillPath: '/repo/skills/mint/learn-skill' }],
      ['research/capture-todo', { skillBody: 'CAPTURE-TODO BODY', skillDir: '/repo/skills/research/capture-todo', skillPath: '/repo/skills/research/capture-todo' }],
    ]),
    source: {}, jailDir: '/tmp/skill-harness-x', sessionId: 's',
  }
  const out = renderDryRun(cells, ctx)
  assert.ok(out.includes('/tmp/skill-harness-x/.claude/skills/learn-skill'))
  assert.ok(out.includes('/tmp/skill-harness-x/.claude/skills/capture-todo'))
  assert.ok(out.includes('LEARN-SKILL BODY'))
  assert.ok(out.includes('CAPTURE-TODO BODY'))
})

test('grade 缺 --grader-model 直接报错——不 pin 量具，跨平台差异就是平台⊗模型混合效应', () => {
  assert.throws(() => parseArgs(['grade', '20260817-120000-abcd']), /grader-model/)
})

test('grade 认得 runId 与 --only', () => {
  const { command, opts } = parseArgs(['grade', '20260817-120000-abcd', '--grader-model', 'm', '--only', 'a/x'])
  assert.equal(command, 'grade')
  assert.equal(opts.runId, '20260817-120000-abcd')
  assert.equal(opts.graderModel, 'm')
  assert.deepEqual(opts.only, ['a/x'])
})

test('parseArgs: --probe 是布尔旗标，不吃下一个 token', () => {
  const { opts } = parseArgs(['run', '--model', 'M', '--probe', '--platform', 'pi'])
  assert.equal(opts.probe, true)
  assert.deepEqual(opts.platforms, ['pi'])
})

test('parseArgs: --probe 与 --skill 同时给出必须报错——不猜用户想要哪个', () => {
  assert.throws(
    () => parseArgs(['run', '--model', 'M', '--probe', '--skill', 'mint/learn-skill']),
    /--probe and --skill/,
  )
})

test('buildSkillMap: 两个不同 cell.skill 解析出不同的 skillPath，且都不是探针路径——这是缺陷的直接回归测试', async () => {
  const cells = [
    { skill: 'mint/learn-skill', state: 'run' },
    { skill: 'research/capture-todo', state: 'run' },
  ]
  const reads = []
  const readBody = async p => { reads.push(p); return '---\nfrontmatter: yes\n---\nBODY for ' + p }
  const skills = await buildSkillMap('/repo', cells, readBody)

  const a = skills.get('mint/learn-skill')
  const b = skills.get('research/capture-todo')
  assert.notEqual(a.skillPath, b.skillPath)
  assert.ok(!a.skillPath.includes('probe-anchor'))
  assert.ok(!b.skillPath.includes('probe-anchor'))
  assert.equal(a.skillPath, '/repo/skills/mint/learn-skill')
  assert.equal(b.skillPath, '/repo/skills/research/capture-todo')
  assert.notEqual(a.skillBody, b.skillBody)
})

test('buildSkillMap: skillBody 经 stripFrontmatter 处理，不含 --- 分隔符', async () => {
  const cells = [{ skill: 'mint/learn-skill', state: 'run' }]
  const readBody = async () => '---\nname: x\n---\nPLAIN BODY'
  const skills = await buildSkillMap('/repo', cells, readBody)
  assert.equal(skills.get('mint/learn-skill').skillBody, 'PLAIN BODY')
})

test('buildSkillMap: 只为 state === "run" 的 cell 预读，not-run 的格子不产生 I/O', async () => {
  const cells = [
    { skill: 'mint/learn-skill', state: 'run' },
    { skill: 'research/capture-todo', state: 'not-run' },
  ]
  const reads = []
  const readBody = async p => { reads.push(p); return 'BODY' }
  const skills = await buildSkillMap('/repo', cells, readBody)
  assert.equal(reads.length, 1)
  assert.ok(!skills.has('research/capture-todo'))
})

test('buildSkillMap: 同一个 skill 出现在多个 cell（不同平台/模式）里只读一次', async () => {
  const cells = [
    { skill: 'mint/learn-skill', platform: 'claude', mode: 'native', state: 'run' },
    { skill: 'mint/learn-skill', platform: 'pi', mode: 'inject', state: 'run' },
  ]
  let reads = 0
  const readBody = async () => { reads++; return 'BODY' }
  await buildSkillMap('/repo', cells, readBody)
  assert.equal(reads, 1)
})

test('buildProbeMap: --probe 模式下所有 cell（无论 cell.skill 是什么）都解析到同一个探针路径', async () => {
  const cells = [
    { skill: 'mint/learn-skill', state: 'run' },
    { skill: 'creative/capture-todo', state: 'run' },
  ]
  const readBody = async () => 'PROBE BODY'
  const skills = await buildProbeMap('/repo', cells, readBody)
  const a = skills.get('mint/learn-skill')
  const b = skills.get('creative/capture-todo')
  assert.equal(a.skillPath, '/repo/tools/skill-harness/probe/probe-anchor')
  assert.equal(b.skillPath, '/repo/tools/skill-harness/probe/probe-anchor')
  assert.equal(a.skillBody, 'PROBE BODY')
})

test('buildProbeMap: 只为探针文件读一次盘，不管选中了多少格子', async () => {
  const cells = [
    { skill: 'a', state: 'run' },
    { skill: 'b', state: 'run' },
    { skill: 'c', state: 'run' },
  ]
  let reads = 0
  const readBody = async () => { reads++; return 'BODY' }
  await buildProbeMap('/repo', cells, readBody)
  assert.equal(reads, 1)
})
