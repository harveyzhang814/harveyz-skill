import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import test from 'node:test'

const root = resolve(import.meta.dirname, '..')
const cases = [
  ['skills/coding/capture-vocab/SKILL.md', ['~/.claude/skills'], ['SKILL_DIR/scripts/vocab.py']],
  ['skills/writing/forge-doc/SKILL.md', ['~/.claude/skills', 'AskUserQuestion'], ['SKILL_DIR']],
  ['skills/mint/contribute-skill/SKILL.md', ['~/.claude/skills', '.claude/skills'], ['source_skill_dir', '~/.hskill/contribute-skill']],
  ['skills/coding/init-project/SKILL.md', ['user.claude.status', '--target claude', '~/.claude/skills'], ['TARGET', 'AGENTS.md']],
  ['skills/research/fetch-paper/SKILL.md', ['WebFetch', 'WebSearch', 'Read 工具', 'Write 工具', 'Bash 工具'], ['下载能力', '临时文件']],
  ['skills/coding/init-goal/SKILL.md', ['/loop'], ['持续执行']],
]

test('shared portability entrypoints state portable behavior', async () => {
  for (const [file, forbidden, required] of cases) {
    const body = await readFile(resolve(root, file), 'utf8')
    for (const token of forbidden) assert.ok(!body.includes(token), `${file}: forbids ${token}`)
    for (const token of required) assert.ok(body.includes(token), `${file}: requires ${token}`)
  }
})

test('Codex clip-url adapter states the sequential fallback', async () => {
  const file = 'skills/research/clip-url/platforms/SKILL.codex.md'
  const body = await readFile(resolve(root, file), 'utf8')
  for (const token of ['未验证', '待补']) assert.ok(!body.includes(token), `${file}: forbids ${token}`)
  assert.ok(body.includes('顺序执行'), `${file}: requires 顺序执行`)
})

test('learn-video: mode and script paths are host-neutral', async () => {
  const body = await readFile(resolve(root, 'skills/research/learn-video/SKILL.md'), 'utf8')
  assert.match(body, /当前宿主可用的提问方式/)
  assert.match(body, /\$SKILL_DIR\/scripts\/store_config\.py/)
  assert.match(body, /\$SKILL_DIR\/scripts\/archive\.py/)
  assert.match(body, /\$SKILL_DIR\/scripts\/build_creator_index\.py/)
  assert.doesNotMatch(body, /\$HOME\/Projects\/(harveyz-skill|Video-Learner)/)
})

test('extract-vision: delegation and vision have safe fallbacks', async () => {
  const body = await readFile(resolve(root, 'skills/research/extract-vision/SKILL.md'), 'utf8')
  assert.match(body, /当前 agent 顺序处理 OCR 文本/)
  assert.match(body, /无原图视觉能力则停止/)
})

test('close-node: receiver has a safe no-detach stop', async () => {
  const body = await readFile(resolve(root, 'skills/agent-canvas/close-node/SKILL.md'), 'utf8')
  assert.match(body, /Claude.*ExitWorktree\(action: "keep"\)/)
  assert.match(body, /无安全解除绑定能力.*停在第 4 步/)
  assert.match(body, /不得继续.*(?:hide|stop-node)/)
})
