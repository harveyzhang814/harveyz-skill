import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')

test('handoff template makes the author choose workspace_mode instead of copying a default', async () => {
  const tpl = await read('skills/coding/handoff/assets/handoff-template.md')
  assert.match(tpl, /^workspace_mode: <same-workspace\|shared-worktree>/m)
  assert.doesNotMatch(tpl, /^workspace_mode: shared-worktree/m)
})

test('handoff config schema sends workspace entry to manage-worktree', async () => {
  const schema = await read('skills/coding/handoff/references/config-schema.md')
  assert.ok(schema.includes('manage-worktree'))
  assert.ok(!schema.includes('分别写 Claude Code、Codex 与通用兜底'))
})

test('CLAUDE.md does not credit manage-worktree with the pre-merge check', async () => {
  const body = await read('CLAUDE.md')
  assert.ok(!body.includes('它替你守住三条硬约束'))
  assert.ok(!body.includes('进入后补上 `git config core.hooksPath .githooks && git config merge.ff false`。'))
})
