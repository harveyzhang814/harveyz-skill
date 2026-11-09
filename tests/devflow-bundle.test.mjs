import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const SKILLS = ['question-me', 'init-spec', 'develop-plan']

test('superpowers-rewrite directory is gone and skills live under devflow', () => {
  assert.equal(existsSync(resolve(root, 'skills/superpowers-rewrite')), false)
  for (const s of SKILLS) assert.ok(existsSync(resolve(root, `skills/devflow/${s}/SKILL.md`)), s)
})

test('skills-index registers the three skills under the devflow bundle', async () => {
  const index = JSON.parse(await read('skills-index.json'))
  assert.equal(index.bundleMeta['superpowers-rewrite'], undefined)
  assert.match(index.bundleMeta.devflow, /manage-worktree/)
  for (const s of SKILLS) {
    const entry = index.skills.find(x => x.path === `devflow/${s}`)
    assert.ok(entry, s)
    assert.equal(entry.bundle, 'devflow', s)
  }
})

test('no shipped file still names the old bundle', async () => {
  for (const f of ['skills-index.json', 'package.json', 'tests/skill-portability.test.mjs', 'docs/product/PRD.md', 'skills/devflow/init-spec/SKILL.md']) {
    assert.doesNotMatch(await read(f), /superpowers-rewrite/, f)
  }
  assert.match(await read('skills/devflow/init-spec/SKILL.md'), /调用本 `devflow` bundle 的 `develop-plan` 技能/)
})
