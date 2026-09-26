import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
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
  assert.match(body, /不能可靠启动并追踪长期任务.*启动前.*停止/)
  assert.match(body, /package\.json.*npm run agent:serve.*存在/)
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

for (const name of ['sync-xtimeline', 'sync-ytchannel', 'sync-website']) {
  test(`${name}: shared entrypoint keeps one-shot run separate from scheduling`, async () => {
    const file = `skills/feed/${name}/SKILL.md`
    const body = await readFile(resolve(root, file), 'utf8')
    assert.doesNotMatch(body, /\/loop/, `${file}: host command belongs in an adapter`)
    assert.match(body, /当前宿主.*调度能力.*用户.*授权/, `${file}: scheduled runs require host capability and authorization`)
    assert.match(body, /### run（单次增量抓取/, `${file}: run remains a one-shot action`)
  })

  test(`${name}: Claude scheduling command stays in its adapter`, async () => {
    const file = `skills/feed/${name}/platforms/SKILL.claude.md`
    const body = await readFile(resolve(root, file), 'utf8')
    assert.match(body, /\/loop/)
    assert.match(body, /用户已授权/)
    assert.match(body, /当前会话.*提供/)
  })
}

test('question-me: current agent proposes clarification without promising host auto-trigger', async () => {
  const body = await readFile(resolve(root, 'skills/coding/question-me/SKILL.md'), 'utf8')
  assert.doesNotMatch(body, /Claude/)
  assert.match(body, /自动提议（等用户确认 y\/n）/)
  assert.match(body, /当前 agent/)
})

test('rephrase: manual invocation and reliability remain current-agent decisions', async () => {
  const body = await readFile(resolve(root, 'skills/coding/rephrase/SKILL.md'), 'utf8')
  assert.doesNotMatch(body, /Claude/)
  assert.match(body, /仅手动调用/)
  assert.match(body, /猜错的代价/)
  assert.match(body, /可靠 → 展示改写结果，直接执行/)
  assert.match(body, /不可靠 → 展示改写结果和存疑点，等用户确认/)
})

test('runby-opencode: verify uses an explicit source and compare requires both agents', async () => {
  const body = await readFile(resolve(root, 'skills/mint/runby-opencode/SKILL.md'), 'utf8')
  assert.match(body, /用户显式提供.*(?:优先|首先)/)
  assert.match(body, /确认.*opencode.*(?:搜索|发现)/)
  assert.match(body, /未经用户确认.*(?:不修改|不得修改).*配置/)
  assert.match(body, /缺少.*(?:Claude|opencode).*不.*比较结果/)
})

test('B portability release versions and index hashes match published SKILL.md content', async () => {
  const expectedVersions = new Map([
    ['feed/sync-xtimeline', '0.8.4'],
    ['feed/sync-ytchannel', '0.7.4'],
    ['feed/sync-website', '0.2.3'],
    ['coding/question-me', '3.0.2'],
    ['coding/rephrase', '1.0.2'],
    ['coding/init-project', '0.1.2'],
    ['mint/runby-opencode', '1.1.1'],
  ])
  const index = JSON.parse(await readFile(resolve(root, 'skills-index.json'), 'utf8'))
  for (const [path, version] of expectedVersions) {
    const body = await readFile(resolve(root, 'skills', path, 'SKILL.md'), 'utf8')
    const indexed = index.skills.find(skill => skill.path === path)
    const hash = createHash('sha256').update(body.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)
    assert.match(body, new RegExp(`^version: ["']?${version}["']?$`, 'm'), path)
    assert.equal(indexed.contentVersion, version, path)
    assert.equal(indexed.contentHash, hash, path)
  }
})
