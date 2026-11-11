import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)

test('handoff version and index hash are updated', async () => {
  const body = await read('skills/coding/handoff/SKILL.md')
  const entry = JSON.parse(await read('skills-index.json')).skills.find(s => s.path === 'coding/handoff')
  assert.match(body, /^version: ["']?1\.19\.0["']?$/m)
  assert.equal(entry.contentVersion, '1.19.0')
  assert.equal(entry.contentHash, hash(body))
})

test('handoff delegates worktree handling to manage-worktree', async () => {
  const body = await read('skills/coding/handoff/SKILL.md')
  for (const phrase of [
    '接手方是另一个会话、需要被指到一个确定的工作区时做',
    '调用 `manage-worktree` 的「准备」', '调用 `manage-worktree` 的「进入」', '调用 `manage-worktree` 的「离开」',
    '两种模式都必须填 `branch` 与 `worktree`',
    '需要安装 `devflow` bundle 中的 manage-worktree',
  ]) assert.ok(body.includes(phrase), phrase)
  for (const gone of ['EnterWorktree(path', 'codex -C', '接手方会在**另一条分支**上开工时才做', '.claude/worktrees/']) {
    assert.ok(!body.includes(gone), gone)
  }
})

test('author commits before running the integrity gate', async () => {
  const body = await read('skills/coding/handoff/SKILL.md')
  const commit = body.indexOf('7. **落库**')
  const gate = body.indexOf('8. **跑完整性门禁**')
  assert.ok(commit > 0 && gate > commit)
})

test('handoff template marks branch and worktree as required with workspace_mode', async () => {
  const tpl = await read('skills/coding/handoff/assets/handoff-template.md')
  assert.equal((tpl.match(/workspace_mode 存在时必填/g) || []).length, 2)
})
