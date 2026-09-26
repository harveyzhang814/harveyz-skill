import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import test from 'node:test'

const root = resolve(import.meta.dirname, '..')
const skill = name => readFile(resolve(root, `skills/mint/${name}/SKILL.md`), 'utf8')

test('init-skill reads both installed standards and reports scope, fallback, and evidence', async () => {
  const body = await skill('init-skill')
  assert.match(body, /references\/skill-standard\.md/)
  assert.match(body, /references\/platform-adaptation\.md/)
  for (const field of ['目标宿主', '有意限定', '核心能力', '路径来源', '回退', '验证状态']) {
    assert.ok(body.includes(field), `missing ${field}`)
  }
  assert.match(body, /通过[／/]缺口[／/]不适用/)
  assert.match(body, /platforms\/SKILL\.<host>\.md/)
  assert.match(body, /不.*(?:生成|创建).*空.*适配器/)
  assert.doesNotMatch(body, /由 Claude 根据内容推断|用 Read 工具|用 Write 工具/)
})

test('init-skill creates an isolated staging-based worktree before any write', async () => {
  const body = await skill('init-skill')
  const create = body.indexOf('worktree add')
  const write = body.indexOf('写入新 skill')
  assert.ok(create > 0 && write > create, 'worktree creation must precede writing')
  assert.match(body, /git -C "\$REPO_ROOT" worktree add[^\n]*staging/)
  assert.match(body, /core\.hooksPath/)
  assert.match(body, /merge\.ff/)
  assert.match(body, /脏工作区.*停止/)
  assert.match(body, /目标路径.*已存在.*停止/)
  assert.match(body, /不能.*(?:绑定|指定).*基线.*(?:停止|回退)/)
  assert.doesNotMatch(body, /git checkout -b feature\/init/)
})

test('skill-standard distinguishes domain references from host adapters', async () => {
  const body = await readFile(resolve(root, 'skills/mint/init-skill/references/skill-standard.md'), 'utf8')
  assert.match(body, /references\/<dim>\//)
  assert.match(body, /platforms\/SKILL\.<host>\.md/)
  assert.match(body, /references\/platform-adaptation\.md/)
})
