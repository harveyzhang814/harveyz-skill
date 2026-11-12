import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const PATH = 'skills/coding/init-workflow/SKILL.md'
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)

test('init-workflow is 5.0.0 with matching index hash', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const index = JSON.parse(await readFile(resolve(root, 'skills-index.json'), 'utf8'))
  const entry = index.skills.find(s => s.path === 'coding/init-workflow')
  assert.match(body, /^name: init-workflow$/m)
  assert.match(body, /^version: ["']?5\.0\.0["']?$/m)
  assert.equal(entry.contentVersion, '5.0.0')
  assert.equal(entry.contentHash, hash(body))
})

test('init-workflow states single resolver, deploy and outputs', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  for (const phrase of [
    'deploy_artifacts.py',
    '.hskill/init-workflow/resolved.env',
    '<!-- BEGIN PROJECT NOTES -->',
    'merge.pre_checks',
    'commit-msg/merge-via',
    'pre-push/merge-via',
    'worktree.dir',
    'WARN',
  ]) assert.ok(body.includes(phrase), phrase)
})

test('init-workflow no longer tells the agent to parse config by hand for docs', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  assert.ok(!/render_docs\.py\s*\\?\s*\.hskill\/init-workflow\/workflow-config\.yml/.test(body))
})
