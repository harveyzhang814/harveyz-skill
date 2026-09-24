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
  ['skills/research/fetch-paper/SKILL.md', ['WebFetch', 'WebSearch'], ['下载能力', '临时文件']],
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
