import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, cpSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { ConfigError, loadSkeleton, loadPacks, resolveConfig } from '../skills/devflow/compose-agentsmd/scripts/lib/config.mjs'

const packsDir = fileURLToPath(new URL('./fixtures/compose-agentsmd/packs', import.meta.url))
const tmpRoots = []
const tmp = () => { const d = mkdtempSync(join(tmpdir(), 'compose-agentsmd-')); tmpRoots.push(d); return d }
after(() => tmpRoots.forEach(d => rmSync(d, { recursive: true, force: true })))

// 在 root 下写一个本地包：manifest 为 pack.json 内容，files 为 { 文件名: 内容 }
function writePack(root, manifest, files) {
  const dir = join(root, manifest.name)
  mkdirSync(dir, { recursive: true })
  writeFileSync(join(dir, 'pack.json'), JSON.stringify(manifest))
  for (const [f, text] of Object.entries(files)) writeFileSync(join(dir, f), text)
}

const skeleton = loadSkeleton()
const dirs = { packsDir, localPacksDir: tmp() }
const packs = loadPacks(dirs)

const dupDir = tmp()
cpSync(join(packsDir, 'alpha'), join(dupDir, 'alpha'), { recursive: true })

const badParamDir = tmp()
writePack(badParamDir, { name: 'gamma', slots: ['flow-steps'], params: {} }, { 'flow-steps.md': '## G @{undeclared}\n' })

const deltaDir = tmp()
writePack(deltaDir, { name: 'delta', slots: ['platform-fallbacks'], params: { branch: { type: 'boolean', required: true } } },
  { 'platform-fallbacks.md': '## Delta\n' })
const withDelta = loadPacks({ packsDir, localPacksDir: deltaDir })
const useDelta = { slot_packs: { 'platform-fallbacks': 'delta' } }

const epsilonDir = tmp()
writePack(epsilonDir, { name: 'epsilon', slots: ['flow-summary'], params: { spec_dir: { type: 'string', default: 'docs/superpowers/specs' } } },
  { 'flow-summary.md': '## E @{spec_dir}\n' })
const withEpsilon = loadPacks({ packsDir, localPacksDir: epsilonDir })

const base = { title: 'T', pack: 'alpha', branch: 'main' }
test('skeleton has the 10 slots in spec order', () => {
  assert.deepEqual(loadSkeleton().map(s => s.id), ['overview','flow-summary','principles','instruction-sources','platform-fallbacks','platform-adaptation','repo-env','flow-steps','release-acceptance','other'])
})
test('resolves slots from the main pack and applies param defaults', () => {
  const r = resolveConfig({ config: base, skeleton, packs: loadPacks(dirs) })
  assert.equal(r.slots.find(s => s.id === 'flow-steps').pack, 'alpha')
  assert.equal(r.slots.find(s => s.id === 'instruction-sources').pack, 'alpha')
  assert.equal(r.slots.find(s => s.id === 'platform-fallbacks').pack, null)
  assert.equal(r.params.extra, '')
  assert.equal(r.params.agent_canvas, false)
})
test('missing required param is rejected', () => {
  assert.throws(() => resolveConfig({ config: { title: 'T', pack: 'alpha' }, skeleton, packs }), /branch/)
})
test('unknown field is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, bogus: 1 }, skeleton, packs }), /bogus/)
})
test('wrong type is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, agent_canvas: 'yes' }, skeleton, packs }), /agent_canvas/)
})
test('slot_packs splitting a linked group is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, slot_packs: { 'flow-steps': 'beta' } }, skeleton, packs }), /linked|联动/)
})
test('slot_packs to a pack that does not declare the slot is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, slot_packs: { 'flow-summary': 'beta' } }, skeleton, packs }), /beta/)
})
test('disabling only part of a linked group is rejected; whole group is allowed', () => {
  assert.throws(() => resolveConfig({ config: { ...base, disabled_slots: ['flow-summary'] }, skeleton, packs }), ConfigError)
  const r = resolveConfig({ config: { ...base, disabled_slots: ['flow-summary', 'flow-steps'] }, skeleton, packs })
  assert.equal(r.slots.find(s => s.id === 'flow-steps').pack, null)
})
test('disabled_slots naming a description slot is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, disabled_slots: ['other'] }, skeleton, packs }), /other/)
})
test('same pack name in shipped and local dirs is rejected', () => {
  assert.throws(() => loadPacks({ packsDir, localPacksDir: dupDir }), /alpha/)
})
test('template referencing an undeclared param is rejected', () => {
  assert.throws(() => loadPacks({ packsDir, localPacksDir: badParamDir }), /undeclared/)
})
test('conflicting declarations of the same param across used packs are rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, ...useDelta }, skeleton, packs: withDelta }), /branch/)
})
test('agent_canvas true with spec_dir outside docs/superpowers/specs is rejected', () => {
  assert.throws(() => resolveConfig({ config: { title: 'T', pack: 'epsilon', agent_canvas: true, spec_dir: 'docs/specs' }, skeleton, packs: withEpsilon }), /spec_dir/)
})
