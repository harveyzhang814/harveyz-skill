import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)
const INSTALL = '需要安装 `devflow` bundle 中的 manage-worktree'

async function checkIndexed(name, version) {
  const body = await read(`skills/devflow/${name}/SKILL.md`)
  const entry = JSON.parse(await read('skills-index.json')).skills.find(s => s.path === `devflow/${name}`)
  assert.match(body, new RegExp(`^version: ["']?${version.replace(/\./g, '\\.')}["']?$`, 'm'), name)
  assert.equal(entry.contentVersion, version, name)
  assert.equal(entry.contentHash, hash(body), name)
  return body
}

test('init-spec prepares the worktree before writing the decision record', async () => {
  const body = await checkIndexed('init-spec', '0.4.0')
  const prepare = body.indexOf('建档前调用 `manage-worktree` 的「准备」')
  assert.ok(prepare > 0)
  assert.ok(prepare < body.indexOf('**按摘要建档。**'))
  assert.ok(body.includes(INSTALL))
  assert.ok(body.includes('工作区根目录下'))
})

test('develop-plan reuses the spec worktree and defers execution mode to project instructions', async () => {
  const body = await checkIndexed('develop-plan', '0.5.0')
  assert.ok(body.includes('调用 `manage-worktree` 的「准备」'))
  assert.ok(body.includes('把已批准 Spec 的路径作为锚点传入'))
  assert.ok(body.includes('项目指令对计划确认后的执行方式另有规定时按项目指令，否则直接使用 `superpowers:subagent-driven-development` 执行'))
  assert.ok(body.includes(INSTALL))
  assert.ok(!body.includes('不询问执行方式'))
  assert.ok(!body.includes('using-git-worktrees'))
})
