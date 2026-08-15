import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseClaudeCodeJsonl } from '../../tools/skill-harness/parse/claude-code-jsonl.js'
import { parsePiJsonl } from '../../tools/skill-harness/parse/pi-jsonl.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const CLAUDE_FIXTURES = path.join(here, 'fixtures/claude')

function fixture(name) {
  return fs.readFileSync(path.join(CLAUDE_FIXTURES, name), 'utf8')
}

test('空集合保险：claude fixture 目录非空', () => {
  const files = fs.readdirSync(CLAUDE_FIXTURES).filter(f => f.endsWith('.jsonl'))
  assert.ok(files.length > 0, 'expected at least one claude fixture')
})

test('claude: 解析出 sessionId 与 model', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.match(r.sessionId, /^[0-9a-f-]{36}$/)
  assert.equal(r.model, 'claude-sonnet-5')
})

test('claude: reply 取 result 行的 result 字段', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.reply, 'BODY=BODY-4B21E8\nFILE=ANCHOR-7F3A9C')
})

test('claude: triggered 判据是 Skill 工具且 input.skill 匹配', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.triggered, true)
})

test('claude: skillName 不匹配时 triggered 为 false（负向）', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'some-other-skill' })
  assert.equal(r.triggered, false)
})

test('claude: toolCalls 按出现顺序编号，含 Skill 与 Read', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.deepEqual(r.toolCalls.map(t => t.name), ['Skill', 'Read'])
  assert.deepEqual(r.toolCalls.map(t => t.seq), [0, 1])
  assert.equal(r.toolCalls[0].args.skill, 'probe-anchor')
})

test('claude: turns 取 num_turns', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.turns, 4)
})

test('claude: usage 归一化字段名', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.usage.input, 5)
  assert.equal(r.usage.output, 222)
  assert.equal(r.usage.cacheRead, 95002)
  assert.equal(r.usage.cacheWrite, 3512)
  assert.equal(r.usage.totalTokens, 5 + 222 + 95002 + 3512)
  assert.ok(r.usage.costUsd > 0)
})

test('claude: visibleSkills 来自 system 行，是 builtinSkillFloor 的 ground truth', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.ok(Array.isArray(r.visibleSkills))
  assert.equal(r.visibleSkills.length, 17)
  assert.ok(r.visibleSkills.includes('probe-anchor'))
})

test('claude: provider 恒为 null，与 pi 解析器形状一致', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.provider, null)
})

test('claude: isError 取 result 行的 is_error', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.isError, false)
})

test('claude: 空输入不抛错，字段全 null', () => {
  const r = parseClaudeCodeJsonl('', { skillName: 'x' })
  assert.equal(r.reply, null)
  assert.equal(r.sessionId, null)
  assert.equal(r.usage, null)
  assert.equal(r.toolCalls, null)
})

test('claude: 非法 JSON 行被跳过而不是让整个解析崩掉', () => {
  const raw = 'not json\n' + fixture('probe-anchor-native.jsonl')
  const r = parseClaudeCodeJsonl(raw, { skillName: 'probe-anchor' })
  assert.equal(r.reply, 'BODY=BODY-4B21E8\nFILE=ANCHOR-7F3A9C')
})

test('parse 是纯函数：同一输入两次调用结果 deepEqual', () => {
  const raw = fixture('probe-anchor-native.jsonl')
  const a = parseClaudeCodeJsonl(raw, { skillName: 'probe-anchor' })
  const b = parseClaudeCodeJsonl(raw, { skillName: 'probe-anchor' })
  assert.deepEqual(a, b)
})

const PI_FIXTURES = path.join(here, 'fixtures/pi')
const PROBE_DIR = '/private/tmp/claude-501/-Users-harveyzhang96-Projects-harveyz-skill/aa316c5f-1656-4440-98b6-368ccbffcced/scratchpad/probe/probe-anchor'

function piFixture(name) {
  return fs.readFileSync(path.join(PI_FIXTURES, name), 'utf8')
}

test('空集合保险：pi fixture 目录非空', () => {
  const files = fs.readdirSync(PI_FIXTURES).filter(f => f.endsWith('.jsonl'))
  assert.ok(files.length > 0, 'expected at least one pi fixture')
})

test('pi: 解析出 sessionId', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.match(r.sessionId, /^[0-9a-f-]{36}$/)
})

test('pi: model 与 provider 从 message_end 读', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.model, 'MiniMax-M2.7')
  assert.equal(r.provider, 'minimax-cn')
})

test('pi: reply 取最后一条 assistant 消息的 text 块', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.ok(r.reply.includes('BODY=BODY-4B21E8'))
  assert.ok(r.reply.includes('FILE=ANCHOR-7F3A9C'))
})

test('pi: reply 不含 thinking 块', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.ok(!r.reply.includes('Now I need to print'))
})

test('pi: triggered 判据是 read 了该 skill 的 SKILL.md', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.triggered, true)
})

test('pi: skillDir 不匹配时 triggered 为 false（负向）', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: '/some/other/skill' })
  assert.equal(r.triggered, false)
})

test('pi: toolCalls 来自 tool_execution_start，ok 来自 tool_execution_end.isError', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.deepEqual(r.toolCalls.map(t => t.name), ['read', 'read'])
  assert.deepEqual(r.toolCalls.map(t => t.seq), [0, 1])
  assert.ok(r.toolCalls.every(t => t.ok === true))
  assert.ok(r.toolCalls[0].args.path.endsWith('SKILL.md'))
  assert.ok(r.toolCalls[1].args.path.endsWith('references/token.md'))
})

test('pi: usage 字段名已与规范一致，直接取末条 message_end', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.usage.input, 466)
  assert.equal(r.usage.output, 61)
  assert.equal(r.usage.cacheRead, 10720)
  assert.equal(r.usage.cacheWrite, 0)
  assert.equal(r.usage.totalTokens, 11247)
  assert.ok(r.usage.costUsd > 0)
})

test('pi: turns 取 turn_start 计数', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.turns, 3)
})

test('pi: visibleSkills 恒为 null——该平台不暴露这个信息', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.visibleSkills, null)
})

test('pi: message_update 流式增量被跳过，不产生额外 toolCalls', () => {
  const raw = piFixture('probe-anchor-native.jsonl')
  assert.ok(raw.includes('"message_update"'), 'fixture 应保留至少一条 message_update 以验证跳过逻辑')
  const r = parsePiJsonl(raw, { skillDir: PROBE_DIR })
  assert.equal(r.toolCalls.length, 2)
})

test('pi: 空输入不抛错', () => {
  const r = parsePiJsonl('', { skillDir: '/x' })
  assert.equal(r.reply, null)
  assert.equal(r.toolCalls, null)
})

test('pi parse 是纯函数：同一输入两次调用 deepEqual', () => {
  const raw = piFixture('probe-anchor-native.jsonl')
  assert.deepEqual(parsePiJsonl(raw, { skillDir: PROBE_DIR }), parsePiJsonl(raw, { skillDir: PROBE_DIR }))
})

const HERMES_FIXTURES = path.join(here, 'fixtures/hermes')

function hermesFixture(name) {
  return fs.readFileSync(path.join(HERMES_FIXTURES, name), 'utf8')
}

test('空集合保险：hermes fixture 目录非空', () => {
  const files = fs.readdirSync(HERMES_FIXTURES).filter(f => f.endsWith('.jsonl'))
  assert.ok(files.length > 0, 'expected at least one hermes fixture')
})

// hermes 真实抓取（2026-08-15，HOME=jail + --safe-mode + --yolo，
// MiniMax-M2.7 / minimax-cn）：hermes 的 trace 里没有 claude 的
// system/result 事件类型，所以 sessionId/reply/turns/usage/visibleSkills/
// isError 全部合法地是 null——不是解析失败，是这个格式本来就不带这些信息。
// model 例外：它从 assistant 事件的 message.model 回退拿到（见下方专门测试）。
// triggered 能算出 true，靠的正是本次修的 skill_view 判据。

test('hermes: triggered 判据是 skill_view 工具且 args.name 匹配（真实抓取，证明 bugfix）', () => {
  const r = parseClaudeCodeJsonl(hermesFixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.triggered, true)
})

test('hermes: skillName 不匹配时 triggered 为 false（负向）', () => {
  const r = parseClaudeCodeJsonl(hermesFixture('probe-anchor-native.jsonl'), { skillName: 'some-other-skill' })
  assert.equal(r.triggered, false)
})

test('hermes: toolCalls 是 skill_view 与 read_file，按出现顺序编号', () => {
  const r = parseClaudeCodeJsonl(hermesFixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.deepEqual(r.toolCalls.map(t => t.name), ['skill_view', 'read_file'])
  assert.deepEqual(r.toolCalls.map(t => t.seq), [0, 1])
  assert.equal(r.toolCalls[0].args.name, 'probe-anchor')
  assert.ok(r.toolCalls[1].args.path.endsWith('references/token.md'))
})

test('hermes: sessionId/turns/usage/visibleSkills/isError 真实均为 null——trace 无 system/result 事件', () => {
  const r = parseClaudeCodeJsonl(hermesFixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.sessionId, null)
  assert.equal(r.turns, null)
  assert.equal(r.usage, null)
  assert.equal(r.visibleSkills, null)
  assert.equal(r.isError, null)
})

// 2026-08-15 真实 E2E 抓取确认：trace 没有 `system` 事件，model 靠回退到
// 最后一条 assistant 事件的 message.model 字段（见 claude-code-jsonl.js 的
// fallbackModel 注释）——与 reply 的 fallbackReply 是同一类修复。
test('hermes: model 无 system 事件时回退到 assistant 事件的 message.model', () => {
  const r = parseClaudeCodeJsonl(hermesFixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.model, 'MiniMax-M2.7')
})

// 2026-08-15 真实 E2E 抓取确认：trace 没有 `result` 事件，reply 靠回退到最后一条
// assistant 事件的文本块拼接（见 claude-code-jsonl.js 的 fallbackReply 注释）。
test('hermes: reply 无 result 事件时回退到最后一条 assistant 事件的文本块', () => {
  const r = parseClaudeCodeJsonl(hermesFixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.reply, 'BODY=BODY-4B21E8\nFILE=ANCHOR-7F3A9C')
})

test('hermes: provider 恒为 null，与 claude/pi 解析器形状一致', () => {
  const r = parseClaudeCodeJsonl(hermesFixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.provider, null)
})

test('hermes parse 是纯函数：同一输入两次调用结果 deepEqual', () => {
  const raw = hermesFixture('probe-anchor-native.jsonl')
  assert.deepEqual(parseClaudeCodeJsonl(raw, { skillName: 'probe-anchor' }), parseClaudeCodeJsonl(raw, { skillName: 'probe-anchor' }))
})
