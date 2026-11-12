import test, { after, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, appendFileSync, existsSync, rmSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { runInit, runGenerate, runCheck, parseHeader } from '../skills/devflow/compose-agentsmd/scripts/lib/compose.mjs'

const packsDir = fileURLToPath(new URL('./fixtures/compose-agentsmd/packs', import.meta.url))
const CLI = fileURLToPath(new URL('../skills/devflow/compose-agentsmd/scripts/compose-agentsmd.mjs', import.meta.url))
const tmpRoots = []
const tmp = () => { const d = mkdtempSync(join(tmpdir(), 'compose-agentsmd-')); tmpRoots.push(d); return d }
after(() => tmpRoots.forEach(d => rmSync(d, { recursive: true, force: true })))

const cfgDir = r => join(r, '.hskill/compose-agentsmd')
const writeConfig = (r, extra = {}) => {
  mkdirSync(join(cfgDir(r), 'slots'), { recursive: true })
  writeFileSync(join(cfgDir(r), 'config.json'), JSON.stringify({ title: 'T', pack: 'alpha', branch: 'main', ...extra }))
}
const writeSlot = (r, id, text) => writeFileSync(join(cfgDir(r), 'slots', `${id}.md`), text)
const freshRoot = () => { const r = tmp(); writeConfig(r); return r }

// 本地包 local-a 只声明非联动槽 instruction-sources；config 的 slot_packs 指向它
function addLocalPack(r, template = '## Local sources\n\nLOCAL-A BODY\n') {
  const dir = join(cfgDir(r), 'packs/local-a')
  mkdirSync(dir, { recursive: true })
  writeFileSync(join(dir, 'pack.json'), JSON.stringify({ name: 'local-a', slots: ['instruction-sources'], params: {}, linked: [] }))
  writeFileSync(join(dir, 'instruction-sources.md'), template)
  writeConfig(r, { slot_packs: { 'instruction-sources': 'local-a' } })
}
const localTemplate = (r, name, slot) => join(cfgDir(r), 'packs', name, `${slot}.md`)
const appendToLocalTemplate = (r, name, slot, text) => appendFileSync(localTemplate(r, name, slot), text)

const setUnknownParamInLocalTemplate = r => addLocalPack(r, '## L @{nope}\n')
const setUnclosedIfInLocalTemplate = r => addLocalPack(r, '<!-- @if agent_canvas -->\nx\n')
const setNestedIfInLocalTemplate = r => addLocalPack(r, '<!-- @if agent_canvas -->\n<!-- @if agent_canvas -->\nx\n<!-- @endif -->\n<!-- @endif -->\n')
const disableOnlyFlowSummary = r => writeConfig(r, { disabled_slots: ['flow-summary'] })
const splitLinkedGroup = r => writeConfig(r, { slot_packs: { 'flow-steps': 'beta' } })

// 改首行里某个发布包的版本，并按新正文重算 sha256（模拟旧版本生成的文件）
function rewriteHeaderVersion(file, pack, version) {
  const text = readFileSync(file, 'utf8')
  const nl = text.indexOf('\n')
  const rest = text.slice(nl + 1)
  const first = text.slice(0, nl).replace(new RegExp(`${pack}@[\\d.]+`), `${pack}@${version}`)
    .replace(/sha256=[0-9a-f]{64}/, `sha256=${createHash('sha256').update(rest).digest('hex')}`)
  writeFileSync(file, `${first}\n${rest}`)
}

let root, agents, emptyDir
beforeEach(() => { root = freshRoot(); agents = join(root, 'AGENTS.md'); emptyDir = tmp() })

test('V1 generate twice is byte-identical and check reports ok', () => {
  assert.equal(runGenerate({ root, packsDir }).code, 0)
  const a = readFileSync(agents)
  assert.equal(runGenerate({ root, packsDir }).code, 0)
  assert.ok(a.equals(readFileSync(agents)))
  const c = runCheck({ root, packsDir })
  assert.equal(c.code, 0); assert.ok(c.lines.includes('status=ok'))
})
test('header and slot markers follow the spec format', () => {
  runGenerate({ root, packsDir })
  const text = readFileSync(agents, 'utf8')
  const [first, ...rest] = text.split('\n')
  const h = parseHeader(text)
  assert.match(first, /^<!-- compose-agentsmd: packs=alpha@1\.0\.0 sha256=[0-9a-f]{64}; generated from \.hskill\/compose-agentsmd\/, do not edit -->$/)
  assert.equal(h.sha256, createHash('sha256').update(rest.join('\n')).digest('hex'))
  assert.ok(text.includes('<!-- slot:flow-steps pack=alpha@1.0.0 -->'))
  assert.ok(text.includes('<!-- slot:overview -->\n# T\n'))
  assert.ok(text.endsWith('\n') && !text.endsWith('\n\n'))
})
test('empty description slot is omitted, overview title always present', () => {
  runGenerate({ root, packsDir })
  const text = readFileSync(agents, 'utf8')
  assert.ok(!text.includes('slot:principles')); assert.ok(text.includes('# T'))
})
test('V5 hand edit is detected and generate refuses without --force', () => {
  runGenerate({ root, packsDir })
  writeFileSync(agents, readFileSync(agents, 'utf8').replace('# T', '# T!'))
  const before = readFileSync(agents)
  const c = runCheck({ root, packsDir }); assert.equal(c.code, 1); assert.match(c.lines.join('\n'), /status=.*hand-edited/)
  assert.equal(runGenerate({ root, packsDir }).code, 1); assert.ok(before.equals(readFileSync(agents)))
  assert.equal(runGenerate({ root, packsDir, force: true }).code, 0)
})
test('AGENTS.md without header counts as hand-edited', () => {
  writeFileSync(agents, '# handwritten\n')
  assert.equal(runGenerate({ root, packsDir }).code, 1)
  assert.match(runCheck({ root, packsDir }).lines.join('\n'), /hand-edited/)
})
test('missing AGENTS.md reports missing', () => {
  assert.match(runCheck({ root, packsDir }).lines.join('\n'), /status=missing/)
})
test('V6 older generated pack version reports outdated', () => {
  runGenerate({ root, packsDir })
  rewriteHeaderVersion(agents, 'alpha', '0.9.0')
  const c = runCheck({ root, packsDir })
  assert.equal(c.code, 1); assert.match(c.lines.join('\n'), /outdated/)
  assert.ok(c.lines.includes('pack=alpha installed=1.0.0 generated=0.9.0'))
})
test('newer generated version than installed reports stale, not outdated', () => {
  runGenerate({ root, packsDir }); rewriteHeaderVersion(agents, 'alpha', '9.0.0')
  const s = runCheck({ root, packsDir }).lines.join('\n')
  assert.match(s, /stale/); assert.doesNotMatch(s, /outdated/)
})
test('config change without regenerate reports stale', () => {
  runGenerate({ root, packsDir }); writeSlot(root, 'other', 'new text\n')
  assert.match(runCheck({ root, packsDir }).lines.join('\n'), /status=stale/)
})
test('V10 slot_packs moves a non-linked slot to a local pack and both packs are recorded', () => {
  addLocalPack(root)
  runGenerate({ root, packsDir })
  const text = readFileSync(agents, 'utf8')
  assert.ok(text.includes('<!-- slot:instruction-sources pack=local:local-a -->\n'))
  assert.ok(text.includes('LOCAL-A BODY'))
  assert.ok(text.includes('<!-- slot:flow-steps pack=alpha@1.0.0 -->'))
  assert.match(text.split('\n')[0], /^<!-- compose-agentsmd: packs=alpha@1\.0\.0,local:local-a sha256=/)
})
test('V11 editing a local pack template reports stale, not outdated', () => {
  addLocalPack(root)
  runGenerate({ root, packsDir }); appendToLocalTemplate(root, 'local-a', 'instruction-sources', 'x\n')
  const s = runCheck({ root, packsDir }).lines.join('\n')
  assert.match(s, /stale/); assert.doesNotMatch(s, /outdated/)
})
test('V7 config or template errors exit 2 and write nothing', () => {
  for (const breakIt of [setUnknownParamInLocalTemplate, setUnclosedIfInLocalTemplate, setNestedIfInLocalTemplate, disableOnlyFlowSummary, splitLinkedGroup]) {
    const r = freshRoot(); breakIt(r)
    assert.equal(runGenerate({ root: r, packsDir }).code, 2); assert.equal(existsSync(join(r, 'AGENTS.md')), false)
  }
})
test('description slot containing a slot marker is rejected', () => {
  writeSlot(root, 'other', '<!-- slot:x -->\n')
  assert.equal(runGenerate({ root, packsDir }).code, 2)
})
test('generate and check without config dir exit 2', () => {
  const r = tmp()
  assert.equal(runGenerate({ root: r, packsDir }).code, 2); assert.equal(runCheck({ root: r, packsDir }).code, 2)
})
test('init creates config and empty description slots; second init exits 1 and changes nothing', () => {
  const r = tmp()
  assert.equal(runInit({ root: r }).code, 0)
  assert.deepEqual(JSON.parse(readFileSync(join(r, '.hskill/compose-agentsmd/config.json'), 'utf8')).pack, 'devflow')
  for (const id of ['overview','principles','platform-adaptation','repo-env','other'])
    assert.equal(readFileSync(join(r, `.hskill/compose-agentsmd/slots/${id}.md`), 'utf8'), '')
  writeFileSync(join(r, '.hskill/compose-agentsmd/slots/other.md'), 'keep\n')
  assert.equal(runInit({ root: r }).code, 1)
  assert.equal(readFileSync(join(r, '.hskill/compose-agentsmd/slots/other.md'), 'utf8'), 'keep\n')
})
test('CLI maps results to stdout and exit codes', () => {
  const r = spawnSync(process.execPath, [CLI, 'check', '--root', emptyDir], { encoding: 'utf8' })
  assert.equal(r.status, 2)
  const u = spawnSync(process.execPath, [CLI, 'bogus'], { encoding: 'utf8' })
  assert.equal(u.status, 2)
})

// 以下为补充：描述槽拼装、无来源提示、init 经 CLI 的 stdout 形态
test('non-empty description slots are assembled with heading and body, joined by one blank line', () => {
  writeSlot(root, 'overview', 'What this is.\n'); writeSlot(root, 'principles', 'Be nice.\n\n\n\nReally.\n')
  runGenerate({ root, packsDir })
  const text = readFileSync(agents, 'utf8')
  assert.ok(text.includes('<!-- slot:overview -->\n# T\n\nWhat this is.\n\n<!-- slot:flow-summary pack=alpha@1.0.0 -->'))
  assert.ok(text.includes('<!-- slot:principles -->\n## 项目原则\n\nBe nice.\n\nReally.\n\n<!-- slot:instruction-sources'))
  assert.ok(!/\n{3,}/.test(text))
})
test('a standard slot without source warns but exits 0; release-acceptance is not warned when agent_canvas is false', () => {
  const g = runGenerate({ root, packsDir })
  assert.equal(g.code, 0)
  assert.ok(g.errors.some(e => e.includes('platform-fallbacks')))
  assert.ok(!g.errors.some(e => e.includes('release-acceptance')))
})
test('CLI init prints key=value lines', () => {
  const r = tmp()
  const out = spawnSync(process.execPath, [CLI, 'init', '--root', r], { encoding: 'utf8' })
  assert.equal(out.status, 0)
  for (const l of out.stdout.trim().split('\n')) assert.match(l, /^\w+=/)
})

// 加固：CRLF 模板、近似指令、必填空串、意外错误归 2、CLI 原型键
test('CRLF local template generates the same output as its LF twin', () => {
  const lf = '<!-- @if agent_canvas -->\nCANVAS\n<!-- @else -->\nPLAIN\n<!-- @endif -->\n'
  const r1 = freshRoot(); addLocalPack(r1, lf); assert.equal(runGenerate({ root: r1, packsDir }).code, 0)
  const r2 = freshRoot(); addLocalPack(r2, lf.replace(/\n/g, '\r\n')); assert.equal(runGenerate({ root: r2, packsDir }).code, 0)
  const a = readFileSync(join(r1, 'AGENTS.md'), 'utf8')
  assert.ok(a.includes('PLAIN') && !a.includes('CANVAS'))
  assert.equal(readFileSync(join(r2, 'AGENTS.md'), 'utf8').replace(/sha256=\w+/, ''), a.replace(/sha256=\w+/, ''))
  assert.ok(!readFileSync(join(r2, 'AGENTS.md'), 'utf8').includes('\r'))
})
test('near-miss directives and invalid @{} in a local template exit 2 and write nothing', () => {
  for (const bad of ['<!--  @if agent_canvas -->\nx\n<!-- @endif -->\n', '<!-- @if agent_canvas -->\nx\n<!-- @else-->\ny\n<!-- @endif -->\n', 'x @{foo-bar}\n']) {
    const r = freshRoot(); addLocalPack(r, bad)
    const g = runGenerate({ root: r, packsDir })
    assert.equal(g.code, 2, bad); assert.match(g.errors[0], /instruction-sources\.md:\d+/)
    assert.equal(existsSync(join(r, 'AGENTS.md')), false)
    assert.equal(runCheck({ root: r, packsDir }).code, 2)
  }
})
test('init then setting only title: generate exits 2 naming the empty required field and writes nothing', () => {
  const r = tmp(); runInit({ root: r })
  const file = join(cfgDir(r), 'config.json')
  writeFileSync(file, JSON.stringify({ ...JSON.parse(readFileSync(file, 'utf8')), title: 'Proj' }))
  const g = runGenerate({ root: r, packsDir: fileURLToPath(new URL('../skills/devflow/compose-agentsmd/assets/packs', import.meta.url)) })
  assert.equal(g.code, 2); assert.match(g.errors[0], /integration_branch/)
  assert.equal(existsSync(join(r, 'AGENTS.md')), false)
})
test('unexpected I/O errors map to exit 2 with a message, not a thrown stack', () => {
  mkdirSync(agents) // AGENTS.md 是目录：读取时 EISDIR
  const g = runGenerate({ root, packsDir, force: true }); assert.equal(g.code, 2); assert.ok(g.errors[0].length > 0)
  assert.equal(runCheck({ root, packsDir }).code, 2)
  const r = tmp(); writeFileSync(join(r, '.hskill'), 'file blocks mkdir')
  assert.equal(runInit({ root: r }).code, 2)
})
test('CLI treats Object prototype keys as unknown commands (exit 2)', () => {
  for (const cmd of ['constructor', 'toString', '__proto__', 'hasOwnProperty']) {
    const r = spawnSync(process.execPath, [CLI, cmd], { encoding: 'utf8' })
    assert.equal(r.status, 2, cmd); assert.match(r.stderr, /usage/)
  }
})
