import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildPrompt, stripFrontmatter, anchorLine } from '../../tools/skill-harness/prompt.js'

const MD = `---
name: probe-anchor
description: "d"
---

# Anchor Probe

body text here
`

test('stripFrontmatter: 去掉 YAML frontmatter，保留正文', () => {
  const body = stripFrontmatter(MD)
  assert.ok(body.includes('# Anchor Probe'))
  assert.ok(body.includes('body text here'))
  assert.ok(!body.includes('name: probe-anchor'))
  assert.ok(!body.includes('---'))
})

test('stripFrontmatter: 无 frontmatter 时原样返回', () => {
  assert.equal(stripFrontmatter('# Just A Title\n').trim(), '# Just A Title')
})

test('anchorLine: 输出绝对路径', () => {
  assert.equal(anchorLine('/tmp/x/probe-anchor'), 'This skill directory is: /tmp/x/probe-anchor')
})

test('native: systemAppend 只含 compensation，不含正文', () => {
  const { systemAppend, positional } = buildPrompt({
    mode: 'native', injection: 'append-system-prompt',
    skillBody: stripFrontmatter(MD), skillDir: '/tmp/x/probe-anchor',
    compensation: 'COMP', task: 'run anchor probe',
  })
  assert.equal(systemAppend, 'COMP')
  assert.equal(positional, 'run anchor probe')
  assert.ok(!systemAppend.includes('body text here'))
})

test('native: compensation 为空时 systemAppend 为 null', () => {
  const { systemAppend } = buildPrompt({
    mode: 'native', injection: 'append-system-prompt',
    skillBody: 'x', skillDir: '/d', compensation: '', task: 't',
  })
  assert.equal(systemAppend, null)
})

test('native + prompt-only: 正文不进 positional', () => {
  const { systemAppend, positional } = buildPrompt({
    mode: 'native', injection: 'prompt-only',
    skillBody: stripFrontmatter(MD), skillDir: '/d', compensation: 'COMP', task: 'do it',
  })
  assert.equal(systemAppend, null)
  assert.equal(positional, 'COMP\n\ndo it')
  assert.ok(!positional.includes('body text here'))
})

test('inject + append-system-prompt: 补偿行 + 正文进 system，任务进 positional', () => {
  const { systemAppend, positional } = buildPrompt({
    mode: 'inject', injection: 'append-system-prompt',
    skillBody: stripFrontmatter(MD), skillDir: '/tmp/x/probe-anchor',
    compensation: 'COMP', task: 'run anchor probe',
  })
  assert.ok(systemAppend.includes('COMP'))
  assert.ok(systemAppend.includes('This skill directory is: /tmp/x/probe-anchor'))
  assert.ok(systemAppend.includes('body text here'))
  assert.equal(positional, 'run anchor probe')
})

test('inject: 路径补偿行必须存在——缺了它三平台一律断锚', () => {
  const { systemAppend } = buildPrompt({
    mode: 'inject', injection: 'append-system-prompt',
    skillBody: 'b', skillDir: '/abs/dir', compensation: '', task: 't',
  })
  assert.ok(systemAppend.includes('This skill directory is: /abs/dir'))
})

test('inject + prompt-only: 全部拼进 positional，用 --- 分隔任务', () => {
  const { systemAppend, positional } = buildPrompt({
    mode: 'inject', injection: 'prompt-only',
    skillBody: 'BODY', skillDir: '/abs/dir', compensation: 'COMP', task: 'TASK',
  })
  assert.equal(systemAppend, null)
  assert.ok(positional.startsWith('COMP'))
  assert.ok(positional.includes('This skill directory is: /abs/dir'))
  assert.ok(positional.includes('BODY'))
  assert.ok(positional.endsWith('TASK'))
  assert.ok(positional.includes('\n---\n'))
})

test('未知 mode 抛错', () => {
  assert.throws(() => buildPrompt({ mode: 'bogus', injection: 'prompt-only', skillBody: 'b', skillDir: '/d', compensation: '', task: 't' }), /bogus/)
})
