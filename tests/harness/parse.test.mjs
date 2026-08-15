import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseClaudeCodeJsonl } from '../../tools/skill-harness/parse/claude-code-jsonl.js'

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
  assert.deepEqual(r.toolCalls, [])
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
