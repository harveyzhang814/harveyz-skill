import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const index = JSON.parse(readFileSync(join(root, 'skills-index.json'), 'utf8'))
const pkg = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'))
const body = readFileSync(join(root, 'skills/devflow/compose-agentsmd/SKILL.md'), 'utf8')

// publish-skill F8：version 行换成占位符后取 sha256 前 16 位
const hash = text => createHash('sha256')
  .update(text.replace(/^version:.*$/gm, 'version: __HASH_PLACEHOLDER__'))
  .digest('hex').slice(0, 16)

const walk = dir => readdirSync(dir).flatMap(name => {
  const p = join(dir, name)
  return statSync(p).isDirectory() ? walk(p) : [p]
})

test('compose-agentsmd is registered in devflow with matching version and hash', async () => {
  const entry = index.skills.find(s => s.path === 'devflow/compose-agentsmd')
  assert.equal(entry.bundle, 'devflow'); assert.equal(entry.installScope, 'global')
  assert.equal(entry.contentVersion, '0.2.1'); assert.equal(entry.contentHash, hash(body))
  assert.match(index.bundleMeta.devflow, /compose-agentsmd/)
  assert.ok(pkg.files.includes('skills/devflow/compose-agentsmd/'))
})
test('SKILL.md states the actions, boundaries and portable script path', () => {
  for (const p of ['## 初始化', '## 生成 / 升级', '## 本地包', '## 检查', '## 边界',
                   'scripts/compose-agentsmd.mjs', '--force', 'slot_packs', '不提交 git'])
    assert.ok(body.includes(p), p)
  assert.ok(!body.includes('~/.claude/skills'))
})
test('V8 hskill install copies pack files byte-for-byte', () => {
  const home = mkdtempSync(join(tmpdir(), 'hs-'))
  mkdirSync(join(home, '.claude/skills'), { recursive: true })
  const r = spawnSync(process.execPath, ['bin/cli.js', 'install', '--skill', 'compose-agentsmd', '--target', 'claude', '--scope', 'user', '--force'], { cwd: root, env: { ...process.env, HOME: home }, encoding: 'utf8' })
  assert.equal(r.status, 0, r.stderr)
  for (const f of walk(join(root, 'skills/devflow/compose-agentsmd/assets/packs')))
    assert.ok(readFileSync(f).equals(readFileSync(f.replace(join(root, 'skills/devflow'), join(home, '.claude/skills')))), f)
})
