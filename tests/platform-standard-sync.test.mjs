import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import test from 'node:test'

const script = resolve(import.meta.dirname, '../scripts/sync-skill-platform-standard.mjs')
const sourcePath = 'docs/reference/skill-platform-adaptation.md'
const consumers = ['init-skill', 'contribute-skill']

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), 'platform-standard-'))
  const source = '# Stable standard\n\nA rule.\n'
  const files = [sourcePath]
  for (const name of consumers) {
    files.push(`skills/mint/${name}/SKILL.md`, `skills/mint/${name}/references/platform-adaptation.md`)
  }
  for (const file of files) await mkdir(dirname(join(root, file)), { recursive: true })
  await writeFile(join(root, sourcePath), source)
  for (const name of consumers) {
    await writeFile(join(root, `skills/mint/${name}/SKILL.md`), `---\nname: ${name}\n---\n<!-- platform-standard-sha256: ${'0'.repeat(64)} -->\n`)
    await writeFile(join(root, `skills/mint/${name}/references/platform-adaptation.md`), 'old copy\n')
  }
  return { root, source, files }
}

async function snapshot(root, files) {
  return Promise.all(files.map(file => readFile(join(root, file))))
}

test('check is read-only; write updates both copies and markers; repeat write is idempotent', async t => {
  const { syncPlatformStandard } = await import(script)
  const { root, source, files } = await fixture()
  t.after(() => rm(root, { recursive: true, force: true }))
  const before = await snapshot(root, files)
  const drift = await syncPlatformStandard({ root, mode: 'check' })
  assert.equal(drift.ok, false)
  assert.equal(drift.drift.length, 4)
  assert.deepEqual(await snapshot(root, files), before)

  await syncPlatformStandard({ root, mode: 'write' })
  const digest = createHash('sha256').update(source).digest('hex')
  const expectedCopy = `<!-- Generated from ${sourcePath}; sha256: ${digest}. Do not edit. -->\n\n${source}`
  for (const name of consumers) {
    assert.equal(await readFile(join(root, `skills/mint/${name}/references/platform-adaptation.md`), 'utf8'), expectedCopy)
    assert.match(await readFile(join(root, `skills/mint/${name}/SKILL.md`), 'utf8'), new RegExp(`<!-- platform-standard-sha256: ${digest} -->`))
  }
  assert.deepEqual(await syncPlatformStandard({ root, mode: 'check' }), { ok: true, drift: [] })
  const written = await snapshot(root, files)
  await syncPlatformStandard({ root, mode: 'write' })
  assert.deepEqual(await snapshot(root, files), written)
})

test('a malformed marker stops before changing any target', async t => {
  const { syncPlatformStandard } = await import(script)
  const { root, files } = await fixture()
  t.after(() => rm(root, { recursive: true, force: true }))
  const file = join(root, 'skills/mint/init-skill/SKILL.md')
  await writeFile(file, 'no marker\n')
  const before = await snapshot(root, files)
  await assert.rejects(syncPlatformStandard({ root, mode: 'write' }), /exactly one.*marker/i)
  assert.deepEqual(await snapshot(root, files), before)
})

test('failed replacement restores every original target', async t => {
  const { syncPlatformStandard } = await import(script)
  const { root, files } = await fixture()
  t.after(() => rm(root, { recursive: true, force: true }))
  const before = await snapshot(root, files)
  const fsApi = await import('node:fs/promises')
  let replacements = 0
  const injected = {
    ...fsApi,
    async rename(from, to) {
      if (String(from).includes('.platform-standard-tmp-') && ++replacements === 3) throw new Error('injected rename failure')
      return fsApi.rename(from, to)
    },
  }
  await assert.rejects(syncPlatformStandard({ root, mode: 'write', fsApi: injected }), /injected rename failure/)
  assert.deepEqual(await snapshot(root, files), before)
})
