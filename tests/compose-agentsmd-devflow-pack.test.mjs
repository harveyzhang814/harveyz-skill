import test, { after } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { runGenerate } from '../skills/devflow/compose-agentsmd/scripts/lib/compose.mjs'

const packsDir = fileURLToPath(new URL('../skills/devflow/compose-agentsmd/assets/packs', import.meta.url))
const PACK = join(packsDir, 'devflow')
const tmpRoots = []
after(() => tmpRoots.forEach(d => rmSync(d, { recursive: true, force: true })))

// 在临时根写配置、调用 runGenerate，返回生成的 AGENTS.md 文本
function generateWith(config) {
  const root = mkdtempSync(join(tmpdir(), 'compose-agentsmd-devflow-'))
  tmpRoots.push(root)
  const dir = join(root, '.hskill/compose-agentsmd')
  mkdirSync(join(dir, 'slots'), { recursive: true })
  writeFileSync(join(dir, 'config.json'), JSON.stringify(config))
  const r = runGenerate({ root, packsDir })
  assert.equal(r.code, 0, (r.errors ?? []).join('\n'))
  return readFileSync(join(root, 'AGENTS.md'), 'utf8')
}

const CANVAS_WORDS = ['describe-node','capture-requirement','relate-node','observe-node-quality','judge-release','Agent Canvas','Step 8','画布','节点','第二道关','版本验收','V<n>｜']
const PROJECT_WORDS = ['Electron','simulate-user','sync-design','.design-scratch','staging','merge-to-staging','main↔renderer','.claude/worktrees','AGENTS.pre-init-spec','2026-10-13-requirement-acceptance']
const cfg = { title: 'P', pack: 'devflow', integration_branch: 'develop', merge_command: 'make merge' }

test('V2 agent_canvas false leaves no canvas wording but keeps acceptance criteria', () => {
  const text = generateWith({ ...cfg, agent_canvas: false })
  for (const w of CANVAS_WORDS) assert.ok(!text.includes(w), w)
  assert.ok(text.includes('## 验收标准'))
  assert.ok(!text.includes('slot:release-acceptance'))
})
test('V2 agent_canvas true includes Step 8, release acceptance and V format', () => {
  const text = generateWith({ ...cfg, agent_canvas: true })
  assert.ok(text.includes('## Step 8')); assert.ok(text.includes('## 版本验收')); assert.ok(text.includes('V1｜'))
})
test('V4 devflow pack files contain no Agent Canvas project specifics', () => {
  for (const f of readdirSync(PACK)) for (const w of PROJECT_WORDS)
    assert.ok(!readFileSync(join(PACK, f), 'utf8').includes(w), `${f}: ${w}`)
})
test('params are substituted into the flow', () => {
  const text = generateWith({ ...cfg, e2e: 'Playwright E2E', complexity_signals: '改动公共 API' })
  for (const v of ['develop', 'make merge', 'Playwright E2E', '改动公共 API', 'docs/superpowers/specs']) assert.ok(text.includes(v), v)
  assert.ok(!text.includes('@{'))
})
test('pack.json matches the spec declaration', () => {
  const p = JSON.parse(readFileSync(join(PACK, 'pack.json'), 'utf8'))
  assert.deepEqual(p.slots, ['flow-summary','instruction-sources','platform-fallbacks','flow-steps','release-acceptance'])
  assert.deepEqual(p.linked, [['flow-summary','flow-steps']])
  assert.equal(p.params.integration_branch.required, true)
  assert.equal(readFileSync(join(PACK, 'VERSION'), 'utf8'), '1.1.0\n')
})
test('execution step defers the skill choice to develop-plan and bounds self-rulings', () => {
  const text = generateWith(cfg)
  assert.ok(text.includes('按 plan 开头的 `REQUIRED SUB-SKILL` 执行（由 `develop-plan` 按条件选定）'))
  assert.ok(text.includes('交出方按 `develop-plan` 的条件（执行方为全新会话）选定执行 skill'))
  assert.doesNotMatch(text, /develop-plan`? ?第 ?\d+ ?步/)
  assert.ok(text.includes('交接文档写明所选 skill 及理由'))
  assert.ok(text.includes('执行 skill 要求的自行裁决只适用于上述不可修改项以外的问题；涉及不可修改项的冲突，包括任务审查者提出的，一律停止并打回'))
  assert.ok(!text.includes('即\n  `superpowers:subagent-driven-development`'))
  assert.ok(!text.includes('填为 `superpowers:subagent-driven-development`'))
})
test('high tier is named the spec path, not SDD', () => {
  const text = generateWith(cfg)
  assert.ok(text.includes('**spec 路径**：spec → plan → execute'))
  assert.ok(text.includes('| 高（spec 路径） |'))
  assert.doesNotMatch(text.replace('走 spec 路径（旧称 SDD）', ''), /\bSDD\b/)
})
