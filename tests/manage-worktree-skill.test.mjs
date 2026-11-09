import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const PATH = 'skills/devflow/manage-worktree/SKILL.md'
const hash = b => createHash('sha256').update(b.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)

test('manage-worktree is registered in devflow with matching version and hash', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const index = JSON.parse(await readFile(resolve(root, 'skills-index.json'), 'utf8'))
  const entry = index.skills.find(s => s.path === 'devflow/manage-worktree')
  assert.match(body, /^name: manage-worktree$/m)
  assert.match(body, /^version: ["']?0\.1\.2["']?$/m)
  assert.equal(entry.bundle, 'devflow')
  assert.equal(entry.contentVersion, '0.1.2')
  assert.equal(entry.contentHash, hash(body))
})

test('manage-worktree states its actions, rules, hosts and boundaries', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  for (const phrase of [
    '「准备」', '「进入」', '「检测」', '「离开」',
    'scripts/inspect-worktree.sh',
    '`.hskill/init-workflow/workflow-config.yml`', '`.claude/workflow-config.yml`',
    '`.worktrees/<分支名，/ 换成 +>`',
    '锚点',
    '新建前向用户一次确认基线、分支名和路径',
    'EnterWorktree(path: "<工作区绝对路径>")', 'ExitWorktree(action: "keep")',
    'codex -C <工作区>', 'git -C <工作区>',
    '不合并、不清理 worktree、不删除分支', '绝不执行 `git worktree remove`',
    '非 git 目录', '不适用',
  ]) assert.ok(body.includes(phrase), phrase)
})

test('manage-worktree tells Claude Code to leave the current worktree before entering one outside .claude/worktrees', async () => {
  const body = await readFile(resolve(root, PATH), 'utf8')
  const section = body.slice(body.indexOf('### Claude Code'), body.indexOf('### Codex'))
  assert.ok(section.includes('Switching from this session is limited to worktrees managed by Claude Code'))
  assert.ok(section.includes('先 `ExitWorktree(action: "keep")` 回到启动目录，再 `EnterWorktree(path:)`'))
})
